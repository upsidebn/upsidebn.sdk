from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

from .commands import (
    CMD_GET_READER_INFO,
    CMD_INVENTORY,
    CMD_PROFILE,
    CMD_READ_ANTENNA_POWER,
    CMD_READ_REGION,
    CMD_SET_ANTENNA,
    CMD_SET_FREQUENCY,
    CMD_SET_RF_POWER,
    CMD_WRITE_DATA,
    CMD_WRITE_EPC,
)
from .protocol import (
    antenna_mask_to_list,
    bytes_from_hex,
    enabled_antenna_mask,
    pc_word_for_epc,
    selected_antenna_code,
)
from .transport import SerialConfig, SerialTransport


class ReaderStatusError(RuntimeError):
    def __init__(self, operation: str, status: int, raw: bytes):
        super().__init__(f"{operation} failed with status 0x{status:02X}: {raw.hex(' ')}")
        self.operation = operation
        self.status = status
        self.raw = raw


@dataclass(frozen=True)
class ReaderInfo:
    firmware: str
    model_type: int
    protocol_flags: int
    max_frequency: int
    min_frequency: int
    rf_power: int
    inventory_time: int
    antenna_mask: int
    antenna_check: int


@dataclass(frozen=True)
class AntennaPower:
    values: tuple[int, ...]


@dataclass(frozen=True)
class FrequencyConfig:
    band: int
    min_channel: int
    max_channel: int


@dataclass(frozen=True)
class InventoryTag:
    epc: str
    antenna_raw: int
    antennas: tuple[int, ...]
    rssi_raw: int
    rssi: int


@dataclass(frozen=True)
class WriteResult:
    command: int
    status: int
    raw: bytes


class NWReader:
    """High-level client for NW UHF RFID readers."""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = 115200,
        address: int = 0x00,
        debug: bool = False,
    ):
        self.address = address
        self.transport = SerialTransport(SerialConfig(port=port, baudrate=baudrate))
        self.transport.debug = debug

    def open(self) -> None:
        self.transport.open()

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "NWReader":
        self.open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def _require_ok(self, operation: str, frame) -> None:
        if frame is None:
            raise TimeoutError(f"{operation}: no response")
        if frame.status != 0x00:
            raise ReaderStatusError(operation, frame.status, frame.raw)

    def get_reader_info(self) -> ReaderInfo:
        frame = self.transport.transact(self.address, CMD_GET_READER_INFO, timeout=1.0)
        self._require_ok("get_reader_info", frame)
        data = frame.data
        if len(data) < 11:
            raise ValueError(f"reader info response too short: {data.hex(' ')}")
        return ReaderInfo(
            firmware=f"{data[0]}.{data[1]}",
            model_type=data[2],
            protocol_flags=data[3],
            max_frequency=data[4],
            min_frequency=data[5],
            rf_power=data[6],
            inventory_time=data[7],
            antenna_mask=data[8],
            antenna_check=data[10],
        )

    def get_antenna_power(self) -> AntennaPower:
        frame = self.transport.transact(
            self.address,
            CMD_READ_ANTENNA_POWER,
            response_commands=[CMD_READ_ANTENNA_POWER, 0x51],
            timeout=1.0,
        )
        self._require_ok("get_antenna_power", frame)
        return AntennaPower(tuple(frame.data))

    def set_antennas(self, antennas: Iterable[int], *, preserve: bool = False) -> None:
        mask = enabled_antenna_mask(tuple(antennas), preserve=preserve)
        frame = self.transport.transact(self.address, CMD_SET_ANTENNA, bytes([mask]), timeout=1.0)
        self._require_ok("set_antennas", frame)

    def set_rf_power(self, powers: Iterable[int], *, preserve: bool = False) -> None:
        payload = []
        for power in powers:
            if not 0 <= int(power) <= 30:
                raise ValueError("power must be in range 0..30")
            payload.append(int(power) | (0 if preserve else 0x80))
        if len(payload) not in (1, 4, 8, 16):
            raise ValueError("set_rf_power accepts 1, 4, 8, or 16 values")
        frame = self.transport.transact(self.address, CMD_SET_RF_POWER, bytes(payload), timeout=1.0)
        self._require_ok("set_rf_power", frame)

    def get_frequency(self) -> FrequencyConfig:
        frame = self.transport.transact(self.address, CMD_READ_REGION, timeout=1.0)
        self._require_ok("get_frequency", frame)
        if len(frame.data) < 3:
            raise ValueError(f"frequency response too short: {frame.data.hex(' ')}")
        band, max_channel, min_channel = frame.data[:3]
        return FrequencyConfig(band=band, min_channel=min_channel, max_channel=max_channel)

    def set_frequency(
        self,
        *,
        band: int,
        min_channel: int,
        max_channel: int,
        preserve: bool = False,
    ) -> None:
        if max_channel < min_channel:
            raise ValueError("max_channel must be >= min_channel")
        flag = 0 if preserve else 1
        payload = bytes([flag, band & 0xFF, max_channel & 0xFF, min_channel & 0xFF])
        frame = self.transport.transact(self.address, CMD_SET_FREQUENCY, payload, timeout=1.0)
        self._require_ok("set_frequency", frame)

    def get_profile(self) -> int:
        frame = self.transport.transact(self.address, CMD_PROFILE, b"\x00\x00\x00", timeout=1.0)
        if frame is None or frame.status != 0x00 or len(frame.data) < 2:
            frame = self.transport.transact(self.address, CMD_PROFILE, b"\x00", timeout=1.0)
        self._require_ok("get_profile", frame)
        if len(frame.data) >= 2:
            return (frame.data[0] << 8) | frame.data[1]
        if len(frame.data) == 1:
            return frame.data[0] & 0x7F
        raise ValueError("profile response has no data")

    def set_profile(self, profile: int, *, preserve: bool = False) -> None:
        opt = 1 if preserve else 2
        payload = bytes([opt, (profile >> 8) & 0xFF, profile & 0xFF])
        frame = self.transport.transact(self.address, CMD_PROFILE, payload, timeout=1.0)
        self._require_ok("set_profile", frame)

    def inventory_once(
        self,
        *,
        antenna: int = 4,
        qvalue: int = 4,
        session: int = 0x00,
        target: int = 0x00,
        scantime: int = 1,
        timeout: float = 0.5,
    ) -> list[InventoryTag]:
        payload = bytes(
            [
                qvalue & 0x0F,
                session & 0xFF,
                target & 0xFF,
                selected_antenna_code(antenna),
                scantime & 0xFF,
            ]
        )
        frame = self.transport.transact(self.address, CMD_INVENTORY, payload, timeout=timeout)
        if frame is None:
            return []
        if frame.status not in (0x01, 0x02, 0x03, 0x04):
            raise ReaderStatusError("inventory_once", frame.status, frame.raw)
        return self._parse_inventory_tags(frame.data)

    def inventory_loop(
        self,
        *,
        seconds: float,
        antenna: int = 4,
        on_tag: Callable[[InventoryTag], None] | None = None,
        **inventory_options,
    ) -> list[InventoryTag]:
        seen: list[InventoryTag] = []
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            tags = self.inventory_once(antenna=antenna, **inventory_options)
            for tag in tags:
                seen.append(tag)
                if on_tag:
                    on_tag(tag)
        return seen

    def write_epc_by_target(
        self,
        *,
        target_epc: str,
        new_epc: str,
        antenna: int = 4,
        access_password: str = "00000000",
    ) -> WriteResult:
        """Write a new EPC to a specific old EPC.

        The SDK writes EPC memory word 1 onward: PC word followed by the new EPC.
        This supports changing the EPC length for basic EPCs.
        """

        self.set_antennas([antenna], preserve=False)
        old = bytes_from_hex(target_epc, field_name="target_epc")
        new = bytes_from_hex(new_epc, field_name="new_epc")
        pwd = bytes_from_hex(access_password, field_name="access_password")
        if len(pwd) != 4:
            raise ValueError("access_password must be exactly 4 bytes")
        if len(old) % 2 or not 2 <= len(old) <= 30:
            raise ValueError("target_epc must be 1..15 words")
        if len(new) % 2:
            raise ValueError("new_epc must contain an even number of bytes")

        pc = pc_word_for_epc(new)
        words_to_write = pc.to_bytes(2, "big") + new
        payload = (
            bytes([len(words_to_write) // 2, len(old) // 2])
            + old
            + bytes([0x01, 0x01])
            + words_to_write
            + pwd
        )
        frame = self.transport.transact(self.address, CMD_WRITE_DATA, payload, timeout=10.0)
        self._require_ok("write_epc_by_target", frame)
        return WriteResult(command=CMD_WRITE_DATA, status=frame.status, raw=frame.raw)

    def blind_write_epc(
        self,
        *,
        new_epc: str,
        antenna: int = 4,
        access_password: str = "00000000",
    ) -> WriteResult:
        """Write EPC without target EPC. Use only when one tag is in the RF field."""

        self.set_antennas([antenna], preserve=False)
        new = bytes_from_hex(new_epc, field_name="new_epc")
        pwd = bytes_from_hex(access_password, field_name="access_password")
        if len(pwd) != 4:
            raise ValueError("access_password must be exactly 4 bytes")
        if len(new) % 2 or not 2 <= len(new) <= 30:
            raise ValueError("new_epc must be 1..15 words")
        payload = bytes([len(new) // 2]) + pwd + new
        frame = self.transport.transact(self.address, CMD_WRITE_EPC, payload, timeout=10.0)
        self._require_ok("blind_write_epc", frame)
        return WriteResult(command=CMD_WRITE_EPC, status=frame.status, raw=frame.raw)

    @staticmethod
    def _parse_inventory_tags(data: bytes) -> list[InventoryTag]:
        if len(data) < 2:
            return []
        ant_raw = data[0]
        count = data[1]
        if count == 0:
            return []

        tags: list[InventoryTag] = []
        pos = 2
        while pos < len(data):
            length_byte = data[pos]
            pos += 1
            epc_len = length_byte & 0x3F
            has_phase_freq = bool(length_byte & 0x40)
            if pos + epc_len + 1 > len(data):
                break
            epc = data[pos : pos + epc_len]
            pos += epc_len
            rssi = data[pos]
            pos += 1
            if has_phase_freq and pos + 7 <= len(data):
                pos += 7
            tags.append(
                InventoryTag(
                    epc=epc.hex().upper(),
                    antenna_raw=ant_raw,
                    antennas=tuple(antenna_mask_to_list(ant_raw)),
                    rssi_raw=rssi,
                    rssi=rssi,
                )
            )
        return tags
