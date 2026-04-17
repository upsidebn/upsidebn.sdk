from __future__ import annotations

import math

import pytest

import nrn
from conftest import ScriptedSerial, load_frame_hex, load_json


def test_crc_vectors_match_current_python_implementation():
    vectors = load_json("crc_vectors.json")["crc_poly_1021_init_0000"]
    for vector in vectors:
        data = bytes.fromhex(vector["input_hex"])
        assert nrn.NRNReader.crc16_ccitt(data) == int(vector["expected_crc_hex"], 16)


@pytest.mark.xfail(reason="Known CRC parity drift tracked for v1.1.0")
def test_crc_ccitt_false_reference_vector_is_not_enforced_yet():
    assert nrn.NRNReader.crc16_ccitt(b"123456789") == 0x29B1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(vector["raw"], vector["dbm"]) for vector in load_json("rssi_vectors.json")["vectors"]],
)
def test_calculate_rssi_vectors(raw: int, expected: int):
    assert nrn.NRNReader.calculate_rssi(raw) == expected


def test_calculate_frequency_values():
    assert nrn.NRNReader.calculate_frequency(0) == 920.0
    assert nrn.NRNReader.calculate_frequency(10) == 925.0


def test_build_frame_round_trip():
    payload = b"\x00\x00\x00\x01\x01"
    frame = nrn.NRNReader.build_frame(nrn.MID.READ_EPC_TAG, payload)
    parsed = nrn.NRNReader.parse_frame(frame)

    assert parsed["valid"] is True
    assert parsed["category"] == 0x02
    assert parsed["mid"] == 0x10
    assert parsed["data"] == payload


def test_parse_frame_rejects_bad_header():
    with pytest.raises(ValueError, match="Invalid frame header"):
        nrn.NRNReader.parse_frame(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00")


def test_parse_frame_rejects_short_input():
    with pytest.raises(ValueError, match="Frame too short"):
        nrn.NRNReader.parse_frame(b"\x5A\x00\x01")


def test_parse_frame_rejects_crc_mismatch():
    frame = bytearray(load_frame_hex("query_info_request.crc1021.hex"))
    frame[-1] ^= 0xFF
    with pytest.raises(ValueError, match="CRC mismatch"):
        nrn.NRNReader.parse_frame(bytes(frame))


def test_build_epc_read_payload_defaults_to_antenna_1():
    reader = nrn.NRNReader("/dev/null", 115200)
    assert reader.build_epc_read_payload(0) == bytes.fromhex("0000000101")


def test_build_epc_read_payload_rejects_oversized_mask():
    reader = nrn.NRNReader("/dev/null", 115200)
    with pytest.raises(ValueError, match="32-bit unsigned integer"):
        reader.build_epc_read_payload(0x1_0000_0000)


def test_captured_inventory_notification_parse():
    frame = load_frame_hex("tag_notification.crc1021.hex")
    parsed = nrn.NRNReader.parse_frame(frame)
    tag = nrn.NRNReader("/dev/null", 115200).parse_epc(parsed["data"])

    assert tag["epc"] == "3000112233445566"
    assert tag["pc"] == "3000"
    assert tag["antenna_id"] == 1
    assert tag["rssi"] == -65
    assert math.isclose(tag["frequency"], 920.532, abs_tol=0.001)


def test_query_reader_information_uses_captured_response(monkeypatch):
    def serial_factory(*args, **kwargs):
        payload = (
            b"\x01\x08NRN00001"
            + (3600).to_bytes(4, "big")
            + b"\x00\x051.0.0"
            + b"\x02\x06Darwin"
        )
        return ScriptedSerial(*args, scripted_reads=[nrn.NRNReader.build_frame(nrn.MID.QUERY_INFO, payload)], **kwargs)

    monkeypatch.setattr(nrn.serial, "Serial", serial_factory)
    monkeypatch.setattr(nrn.time, "sleep", lambda *_args, **_kwargs: None)
    reader = nrn.create_reader("/dev/ttyUSB0")
    reader.open()

    info = reader.Query_Reader_Information()

    assert info["serial_number"] == "NRN00001"
    assert info["power_on_time_sec"] == 3600
    assert info["baseband_compile_time"] == "1.0.0"
    assert info["os_version"] == "Darwin"


def test_extract_valid_frames_recovers_single_frame():
    reader = nrn.NRNReader("/dev/null", 115200)
    noise = b"\x00\x01"
    frame = load_frame_hex("tag_notification.crc1021.hex")

    frames = reader.extract_valid_frames(noise + frame + b"\x02")

    assert frames == [frame]
