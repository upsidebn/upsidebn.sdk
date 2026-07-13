from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import serial

from .protocol import Frame, ProtocolError, build_command, parse_frame


@dataclass
class SerialConfig:
    port: str
    baudrate: int = 115200
    timeout: float = 0.05
    write_timeout: float = 1.0


class SerialTransport:
    """Small serial transport for the NW RFID frame protocol."""

    def __init__(self, config: SerialConfig):
        self.config = config
        self.serial: serial.Serial | None = None
        self.debug = False

    def open(self) -> None:
        self.serial = serial.Serial(
            port=self.config.port,
            baudrate=self.config.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.config.timeout,
            write_timeout=self.config.write_timeout,
        )
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def close(self) -> None:
        if self.serial and self.serial.is_open:
            self.serial.close()

    def __enter__(self) -> "SerialTransport":
        self.open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    @property
    def is_open(self) -> bool:
        return bool(self.serial and self.serial.is_open)

    def write_command(self, address: int, command: int, data: bytes = b"") -> bytes:
        if not self.serial:
            raise RuntimeError("serial transport is not open")
        raw = build_command(address, command, data)
        if self.debug:
            print(f"OUT {raw.hex(' ')}")
        self.serial.write(raw)
        self.serial.flush()
        return raw

    def read_frame(self, timeout: float = 0.2) -> Frame | None:
        if not self.serial:
            raise RuntimeError("serial transport is not open")

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            first = self.serial.read(1)
            if not first:
                continue
            length = first[0]
            if length < 4:
                continue
            rest = self.serial.read(length)
            if len(rest) != length:
                continue
            raw = first + rest
            try:
                frame = parse_frame(raw)
            except ProtocolError as exc:
                if self.debug:
                    print(f"BAD {raw.hex(' ')} {exc}")
                continue
            if self.debug:
                print(f"IN  {frame.raw.hex(' ')}")
            return frame
        return None

    def transact(
        self,
        address: int,
        command: int,
        data: bytes = b"",
        *,
        response_commands: Iterable[int] | None = None,
        timeout: float = 1.0,
    ) -> Frame | None:
        expected = set(response_commands or [command])
        self.write_command(address, command, data)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.read_frame(timeout=min(0.1, max(0.01, deadline - time.monotonic())))
            if frame is None:
                continue
            if frame.command in expected:
                return frame
        return None
