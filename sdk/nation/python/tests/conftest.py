from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import pytest


TESTDATA_DIR = Path(__file__).resolve().parents[2] / "testdata"


def load_json(name: str) -> dict:
    return json.loads((TESTDATA_DIR / name).read_text())


def load_frame_hex(name: str) -> bytes:
    return bytes.fromhex((TESTDATA_DIR / "frames" / name).read_text().strip())


class FakeSerial:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.is_open = True
        self.writes: list[bytes] = []
        self.read_buffer = bytearray()
        self.flush_count = 0
        self.reset_count = 0

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def read(self, size: int = 64) -> bytes:
        if not self.read_buffer:
            return b""
        chunk = bytes(self.read_buffer[:size])
        del self.read_buffer[:size]
        return chunk

    def queue_read(self, data: bytes) -> None:
        self.read_buffer.extend(data)

    def flush(self) -> None:
        self.flush_count += 1

    def reset_input_buffer(self) -> None:
        self.reset_count += 1
        self.read_buffer.clear()


class ScriptedSerial(FakeSerial):
    def __init__(self, *args, scripted_reads: list[bytes] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scripted_reads = deque(scripted_reads or [])

    def read(self, size: int = 64) -> bytes:
        if self.scripted_reads:
            return self.scripted_reads.popleft()
        return super().read(size)


@pytest.fixture
def fake_serial_factory(monkeypatch):
    import nrn

    created: list[FakeSerial] = []

    def factory(*args, **kwargs):
        serial_obj = FakeSerial(*args, **kwargs)
        created.append(serial_obj)
        return serial_obj

    monkeypatch.setattr(nrn.serial, "Serial", factory)
    return created
