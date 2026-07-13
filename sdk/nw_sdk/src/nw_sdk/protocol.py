from __future__ import annotations

from dataclasses import dataclass


class ProtocolError(Exception):
    """Raised when a reader frame is malformed or fails CRC validation."""


@dataclass(frozen=True)
class Frame:
    raw: bytes
    address: int
    command: int
    status: int
    data: bytes


def crc16(data: bytes) -> int:
    """CRC16 used by the reader protocol.

    Parameters are preset 0xFFFF and polynomial 0x8408. The returned value is
    transmitted little-endian: low byte first, high byte second.
    """

    value = 0xFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            if value & 0x0001:
                value = (value >> 1) ^ 0x8408
            else:
                value >>= 1
            value &= 0xFFFF
    return value


def build_command(address: int, command: int, data: bytes = b"") -> bytes:
    """Build a host-to-reader command frame."""

    if not 0 <= address <= 0xFF:
        raise ValueError("address must be in range 0..255")
    if not 0 <= command <= 0xFF:
        raise ValueError("command must be in range 0..255")
    if len(data) > 251:
        raise ValueError("data field is too long for one protocol frame")

    body = bytes([len(data) + 4, address, command]) + data
    crc = crc16(body)
    return body + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def parse_frame(raw: bytes) -> Frame:
    """Parse and validate a reader-to-host frame."""

    if len(raw) < 5:
        raise ProtocolError("frame is too short")

    declared_total = raw[0] + 1
    if declared_total != len(raw):
        raise ProtocolError(f"length mismatch: declared {declared_total}, got {len(raw)}")

    expected_crc = raw[-2] | (raw[-1] << 8)
    actual_crc = crc16(raw[:-2])
    if expected_crc != actual_crc:
        raise ProtocolError(
            f"bad CRC: expected 0x{expected_crc:04X}, calculated 0x{actual_crc:04X}"
        )

    return Frame(
        raw=raw,
        address=raw[1],
        command=raw[2],
        status=raw[3],
        data=raw[4:-2],
    )


def antenna_mask_to_list(mask: int, max_antennas: int = 8) -> list[int]:
    antennas = [idx + 1 for idx in range(max_antennas) if mask & (1 << idx)]
    return antennas or [mask]


def selected_antenna_code(antenna: int) -> int:
    """Return the inventory command antenna selector for antenna 1..16."""

    if not 1 <= antenna <= 16:
        raise ValueError("antenna must be 1..16")
    return 0x80 + (antenna - 1)


def enabled_antenna_mask(antennas: list[int] | tuple[int, ...], preserve: bool = False) -> int:
    """Return the antenna enable mask for command 0x3F."""

    mask = 0
    for antenna in antennas:
        if not 1 <= antenna <= 8:
            raise ValueError("this helper supports antenna 1..8")
        mask |= 1 << (antenna - 1)
    if mask == 0:
        raise ValueError("at least one antenna must be enabled")
    if not preserve:
        mask |= 0x80
    return mask


def clean_hex(value: str) -> str:
    return "".join(ch for ch in value if ch in "0123456789abcdefABCDEF").upper()


def bytes_from_hex(value: str, *, field_name: str = "hex") -> bytes:
    text = clean_hex(value)
    if not text or len(text) % 2:
        raise ValueError(f"{field_name} must contain an even number of hex digits")
    return bytes.fromhex(text)


def pc_word_for_epc(epc: bytes) -> int:
    """Build a basic EPC C1G2 PC word for an EPC payload.

    The length is stored in words in the upper five bits. This helper clears
    optional PC bits and is intended for basic EPC rewrite workflows.
    """

    if len(epc) % 2:
        raise ValueError("EPC length must be even")
    words = len(epc) // 2
    if not 1 <= words <= 31:
        raise ValueError("EPC length must be 1..31 words")
    return (words & 0x1F) << 11
