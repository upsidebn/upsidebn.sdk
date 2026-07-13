import argparse
import sys
import time
from dataclasses import dataclass

import serial


CMD_SET_ANTENNA = 0x3F
CMD_INVENTORY = 0x01
CMD_STOP_INVENTORY = 0x93
CMD_START_FAST_INVENTORY = 0x50
CMD_STOP_FAST_INVENTORY = 0x51
CMD_READ_ANTENNA_POWER = 0x94

RECMD_TAG_UPLOAD = 0xEE


STATUS_TEXT = {
    0x00: "OK",
    0x01: "Inventory succeed",
    0x02: "Inventory timeout",
    0x03: "More data",
    0x04: "Reader memory full",
    0xF8: "Antenna error",
}


@dataclass
class Frame:
    raw: bytes
    adr: int
    recmd: int
    status: int
    data: bytes


def crc16(data: bytes) -> int:
    """CRC16 from the reader manual: preset 0xFFFF, polynomial 0x8408."""
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
    if not 0 <= address <= 0xFF:
        raise ValueError("address must be 0..255")
    if len(data) > 251:
        raise ValueError("data too long for one reader frame")

    # Manual: command Len = len(Data[]) + 4.
    body = bytes([len(data) + 4, address, command]) + data
    crc = crc16(body)
    return body + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def read_frame(ser: serial.Serial, timeout: float = 0.2, debug: bool = False) -> Frame | None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        first = ser.read(1)
        if not first:
            continue

        length = first[0]
        if length < 4:
            continue

        rest = ser.read(length)
        if len(rest) != length:
            continue

        raw = first + rest
        expected = raw[-2] | (raw[-1] << 8)
        actual = crc16(raw[:-2])
        if actual != expected:
            print(
                f"Bad CRC: raw={raw.hex(' ')} expected={expected:04X} actual={actual:04X}",
                file=sys.stderr,
            )
            continue

        adr = raw[1]
        recmd = raw[2]
        status = raw[3] if len(raw) >= 4 else 0
        data = raw[4:-2] if len(raw) > 6 else b""
        if debug:
            print(f"IN  {raw.hex(' ')}")
        return Frame(raw=raw, adr=adr, recmd=recmd, status=status, data=data)

    return None


def send_command(
    ser: serial.Serial,
    address: int,
    command: int,
    data: bytes = b"",
    response_timeout: float = 1.0,
    response_commands: set[int] | None = None,
    debug: bool = False,
) -> Frame | None:
    if response_commands is None:
        response_commands = {command}

    frame = build_command(address, command, data)
    if debug:
        print(f"OUT {frame.hex(' ')}")
    ser.write(frame)
    ser.flush()

    deadline = time.monotonic() + response_timeout
    while time.monotonic() < deadline:
        resp = read_frame(ser, timeout=0.1, debug=debug)
        if resp is None:
            continue
        if resp.recmd in response_commands:
            return resp

        # Fast inventory may upload tag frames while we are waiting for an ACK.
        if resp.recmd == RECMD_TAG_UPLOAD:
            tag = parse_fast_inventory_tag(resp)
            if tag:
                print_tag(tag)
            continue

        print(f"RX other: {resp.raw.hex(' ')}")

    return None


def send_no_response_command(
    ser: serial.Serial,
    address: int,
    command: int,
    data: bytes = b"",
    debug: bool = False,
) -> None:
    frame = build_command(address, command, data)
    if debug:
        print(f"OUT {frame.hex(' ')}")
    ser.write(frame)
    ser.flush()


def require_ok(resp: Frame | None, name: str) -> Frame:
    if resp is None:
        raise RuntimeError(f"{name}: no response")
    if resp.status != 0x00:
        text = STATUS_TEXT.get(resp.status, "Unknown status")
        raise RuntimeError(f"{name}: status=0x{resp.status:02X} ({text}), raw={resp.raw.hex(' ')}")
    return resp


def setup_four_antennas(ser: serial.Serial, address: int, preserve: bool, debug: bool) -> None:
    # Format 1 from manual:
    # Ant bit0..bit3 enable ANT1..ANT4. bit7=1 means do not preserve after power-off.
    ant_mask = 0x0F if preserve else 0x8F
    resp = send_command(ser, address, CMD_SET_ANTENNA, bytes([ant_mask]), debug=debug)
    require_ok(resp, "setup antenna ANT1..ANT4")
    print(f"Enabled ANT1..ANT4 ({'preserved' if preserve else 'not preserved'})")


def read_antenna_power(ser: serial.Serial, address: int, debug: bool) -> list[int]:
    # The manual lists command 0x94, but the response example appears to show
    # 0x51. Accept both so the test can run against either firmware behavior.
    resp = send_command(
        ser,
        address,
        CMD_READ_ANTENNA_POWER,
        response_commands={CMD_READ_ANTENNA_POWER, CMD_STOP_FAST_INVENTORY},
        debug=debug,
    )
    resp = require_ok(resp, "read antenna power")

    # Manual says Data[]=Pwrs, one byte per antenna port.
    powers = list(resp.data)
    if not powers:
        print(f"Antenna power: no data, raw={resp.raw.hex(' ')}")
        return []

    for idx, power in enumerate(powers, start=1):
        print(f"ANT{idx} power: {power}")
    return powers


def parse_antenna(value: int) -> list[int]:
    # For 1/4/8-port readers, Ant is a bit mask. Example from manual:
    # 0x05 means ANT1 and ANT3.
    ants = [idx + 1 for idx in range(8) if value & (1 << idx)]
    return ants or [value]


def parse_fast_inventory_tag(frame: Frame) -> dict | None:
    if frame.recmd != RECMD_TAG_UPLOAD:
        return None
    if frame.status not in (0x00, 0x28):
        return {
            "status": frame.status,
            "status_text": STATUS_TEXT.get(frame.status, "Unknown status"),
            "raw": frame.raw.hex(" "),
        }
    if len(frame.data) < 3:
        return None

    ant = frame.data[0]
    epc_len = frame.data[1]
    if len(frame.data) < 2 + epc_len + 1:
        return None

    epc = frame.data[2 : 2 + epc_len]
    rssi = frame.data[2 + epc_len]
    extra = frame.data[3 + epc_len :]
    return {
        "ant_raw": ant,
        "ants": parse_antenna(ant),
        "epc": epc.hex().upper(),
        "rssi_raw": rssi,
        "rssi": -rssi if rssi > 127 else rssi,
        "extra": extra.hex(" ").upper(),
        "raw": frame.raw.hex(" "),
    }


def parse_epc_blocks(data: bytes, start: int = 2) -> list[dict]:
    tags = []
    pos = start
    while pos < len(data):
        length_byte = data[pos]
        pos += 1

        has_phase_freq = bool(length_byte & 0x40)
        epc_len = length_byte & 0x3F
        if pos + epc_len + 1 > len(data):
            break

        epc = data[pos : pos + epc_len]
        pos += epc_len
        rssi = data[pos]
        pos += 1

        phase = None
        freq_khz = None
        if has_phase_freq and pos + 7 <= len(data):
            phase = data[pos : pos + 4].hex().upper()
            pos += 4
            freq_khz = int.from_bytes(data[pos : pos + 3], "big")
            pos += 3

        tags.append(
            {
                "epc": epc.hex().upper(),
                "rssi_raw": rssi,
                "rssi": -rssi if rssi > 127 else rssi,
                "phase": phase,
                "freq_khz": freq_khz,
            }
        )
    return tags


def parse_inventory_response(frame: Frame) -> list[dict]:
    if frame.recmd != CMD_INVENTORY or len(frame.data) < 2:
        return []
    ant_raw = frame.data[0]
    num = frame.data[1]
    tags = parse_epc_blocks(frame.data, start=2)
    for tag in tags:
        tag["ant_raw"] = ant_raw
        tag["ants"] = parse_antenna(ant_raw)
        tag["num"] = num
    return tags


def print_tag(tag: dict) -> None:
    if "epc" not in tag:
        print(f"TAG status=0x{tag['status']:02X} {tag['status_text']} raw={tag['raw']}")
        return

    ant = ",".join(f"ANT{x}" for x in tag["ants"])
    print(
        f"TAG epc={tag['epc']} ant={ant} ant_raw=0x{tag['ant_raw']:02X} "
        f"rssi={tag['rssi']} rssi_raw=0x{tag['rssi_raw']:02X}"
    )


def start_fast_inventory(ser: serial.Serial, address: int, target: int, debug: bool) -> None:
    # Manual: Target: 0=target A, 1=target B.
    resp = send_command(ser, address, CMD_START_FAST_INVENTORY, bytes([target]), debug=debug)
    require_ok(resp, "start fast inventory")
    print("Started fast inventory")


def stop_fast_inventory(ser: serial.Serial, address: int, debug: bool) -> None:
    resp = send_command(ser, address, CMD_STOP_FAST_INVENTORY, response_timeout=2.0, debug=debug)
    require_ok(resp, "stop fast inventory")
    print("Stopped fast inventory")


def inventory_loop(ser: serial.Serial, duration: float, debug: bool) -> None:
    deadline = time.monotonic() + duration
    seen = set()

    while time.monotonic() < deadline:
        resp = read_frame(ser, timeout=0.2, debug=debug)
        if resp is None:
            continue

        if resp.recmd == RECMD_TAG_UPLOAD:
            tag = parse_fast_inventory_tag(resp)
            if tag is None:
                print(f"RX tag unparsed: {resp.raw.hex(' ')}")
                continue
            key = (tag.get("epc"), tag.get("ant_raw"), tag.get("rssi_raw"))
            if key not in seen:
                seen.add(key)
                print_tag(tag)
            continue

        print(
            f"RX recmd=0x{resp.recmd:02X} status=0x{resp.status:02X} "
            f"data={resp.data.hex(' ')} raw={resp.raw.hex(' ')}"
        )


def build_inventory_payload(
    qvalue: int,
    session: int,
    target: int | None,
    antenna: int | None,
    scantime: int | None,
    mask_mode: str = "omit",
) -> bytes:
    payload = bytes([qvalue & 0x0F, session])
    if mask_mode == "empty-epc":
        # Some firmware wants the mask fields present even when MaskLen=0.
        # MaskMem=EPC, MaskAdr=0, MaskLen=0, MaskData omitted.
        payload += bytes([0x01, 0x00, 0x00, 0x00])
    elif mask_mode != "omit":
        raise ValueError(f"unknown mask mode: {mask_mode}")

    if target is None and antenna is None and scantime is None:
        return payload
    if target is None or antenna is None or scantime is None:
        raise ValueError("target, antenna, and scantime must be provided together")
    return payload + bytes([target, antenna, scantime])


def run_single_inventory(
    ser: serial.Serial,
    address: int,
    qvalue: int,
    session: int,
    target: int | None,
    antenna: int | None,
    scantime: int | None,
    debug: bool,
    mask_mode: str = "omit",
    response_timeout: float | None = None,
) -> None:
    payload = build_inventory_payload(qvalue, session, target, antenna, scantime, mask_mode)
    if response_timeout is None:
        response_timeout = max(0.4, (scantime or 20) / 10 + 0.3)
    resp = send_command(
        ser,
        address,
        CMD_INVENTORY,
        payload,
        response_timeout=response_timeout,
        debug=debug,
    )
    if resp is None:
        print("Inventory 0x01: no response")
        send_no_response_command(ser, address, CMD_STOP_INVENTORY, debug=debug)
        time.sleep(0.2)
        return

    status_text = STATUS_TEXT.get(resp.status, "Unknown status")
    print(f"Inventory 0x01 status=0x{resp.status:02X} ({status_text})")
    if resp.status == 0x26:
        print(f"Statistic packet data={resp.data.hex(' ')}")
        return

    tags = parse_inventory_response(resp)
    if not tags:
        print(f"No parsed tag. data={resp.data.hex(' ')} raw={resp.raw.hex(' ')}")
        return

    for tag in tags:
        print_tag(tag)


def run_cycle4_inventory(
    ser: serial.Serial,
    address: int,
    seconds: float,
    qvalue: int,
    session: int,
    target: int,
    scantime: int,
    debug: bool,
    ant_style: str,
    mask_mode: str,
    no_response_timeout: float,
) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for ant_index in range(4):
            if time.monotonic() >= deadline:
                break
            # Manual says optional Ant uses 0x80=ANT1 ... 0x83=ANT4.
            # Some firmware variants use response-style bit masks instead.
            ant_code = (0x80 + ant_index) if ant_style == "code" else (1 << ant_index)
            print(f"Inventory 0x01 on ANT{ant_index + 1}")
            run_single_inventory(
                ser,
                address,
                qvalue,
                session,
                target,
                ant_code,
                scantime,
                debug,
                mask_mode,
                response_timeout=no_response_timeout,
            )


def run_one_antenna_loop(
    ser: serial.Serial,
    address: int,
    antenna: int,
    seconds: float,
    qvalue: int,
    session: int,
    target: int,
    scantime: int,
    debug: bool,
    mask_mode: str,
    interval: float,
    no_response_timeout: float,
) -> None:
    if not 1 <= antenna <= 16:
        raise ValueError("antenna must be 1..16")

    deadline = time.monotonic() + seconds
    ant_code = 0x80 + (antenna - 1)
    while time.monotonic() < deadline:
        print(f"Inventory 0x01 on ANT{antenna}")
        run_single_inventory(
            ser,
            address,
            qvalue,
            session,
            target,
            ant_code,
            scantime,
            debug,
            mask_mode,
            response_timeout=no_response_timeout,
        )
        if interval > 0:
            time.sleep(interval)


def run_probe(
    ser: serial.Serial,
    address: int,
    qvalue: int,
    session: int,
    target: int,
    scantime: int,
    debug: bool,
) -> None:
    print("Probe 1/5: fast inventory target A, wait 2s")
    try:
        start_fast_inventory(ser, address, 0, debug)
        inventory_loop(ser, 2.0, debug)
    finally:
        stop_fast_inventory(ser, address, debug)

    print("Probe 2/5: inventory 0x01 with current antenna config")
    run_single_inventory(ser, address, qvalue, session, None, None, None, debug)

    print("Probe 3/5: inventory 0x01 ANT4 using manual antenna code 0x83")
    run_single_inventory(ser, address, qvalue, session, target, 0x83, scantime, debug)

    print("Probe 4/5: inventory 0x01 ANT4 using bit-mask antenna code 0x08")
    run_single_inventory(ser, address, qvalue, session, target, 0x08, scantime, debug)

    print("Probe 5/5: inventory 0x01 ANT4 with explicit empty EPC mask")
    run_single_inventory(
        ser,
        address,
        qvalue,
        session,
        target,
        0x83,
        scantime,
        debug,
        mask_mode="empty-epc",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Basic UHF RFID reader test: get power, enable 4 antennas, inventory 5s, stop."
    )
    parser.add_argument("--port", default="COM3", help="Serial port, e.g. COM3")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate from manual default")
    parser.add_argument("--address", type=lambda x: int(x, 0), default=0x00, help="Reader address")
    parser.add_argument("--seconds", type=float, default=5.0, help="Inventory duration")
    parser.add_argument("--target", type=int, choices=[0, 1], default=0, help="Fast inventory target A=0/B=1")
    parser.add_argument("--qvalue", type=int, default=4, help="Q value for command 0x01 inventory")
    parser.add_argument("--session", type=lambda x: int(x, 0), default=0x00, help="Session for command 0x01; default 0x00=S0")
    parser.add_argument("--scantime", type=int, default=2, help="ScanTime for command 0x01, units of 100ms")
    parser.add_argument(
        "--method",
        choices=["fast", "single", "cycle4", "ant", "probe"],
        default="ant",
        help="fast=0x50, single=0x01 default antenna, cycle4=0x01 ANT1..ANT4, ant=one antenna loop, probe=try variants",
    )
    parser.add_argument("--antenna", type=int, default=4, help="Antenna number for --method ant")
    parser.add_argument("--interval", type=float, default=0.0, help="Delay between inventory loops")
    parser.add_argument(
        "--no-response-timeout",
        type=float,
        default=0.45,
        help="How long to wait for each 0x01 response before moving on",
    )
    parser.add_argument(
        "--ant-style",
        choices=["code", "mask"],
        default="code",
        help="For 0x01 cycle4: code uses 0x80..0x83, mask uses 0x01/0x02/0x04/0x08",
    )
    parser.add_argument(
        "--mask-mode",
        choices=["omit", "empty-epc"],
        default="omit",
        help="For 0x01: omit mask fields or send explicit empty EPC mask fields",
    )
    parser.add_argument("--debug", action="store_true", help="Print raw OUT/IN frames")
    parser.add_argument(
        "--preserve-antenna",
        action="store_true",
        help="Persist ANT1..ANT4 config in reader power-off memory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with serial.Serial(
        port=args.port,
        baudrate=args.baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.05,
        write_timeout=1.0,
    ) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print(f"Connected {args.port} @ {args.baud}, address=0x{args.address:02X}")
        read_antenna_power(ser, args.address, args.debug)
        setup_four_antennas(ser, args.address, args.preserve_antenna, args.debug)

        if args.method == "fast":
            try:
                start_fast_inventory(ser, args.address, args.target, args.debug)
                inventory_loop(ser, args.seconds, args.debug)
            finally:
                stop_fast_inventory(ser, args.address, args.debug)
        elif args.method == "single":
            run_single_inventory(
                ser,
                args.address,
                args.qvalue,
                args.session,
                None,
                None,
                None,
                args.debug,
                args.mask_mode,
            )
        elif args.method == "cycle4":
            run_cycle4_inventory(
                ser,
                args.address,
                args.seconds,
                args.qvalue,
                args.session,
                args.target,
                args.scantime,
                args.debug,
                args.ant_style,
                args.mask_mode,
                args.no_response_timeout,
            )
        elif args.method == "ant":
            run_one_antenna_loop(
                ser,
                args.address,
                args.antenna,
                args.seconds,
                args.qvalue,
                args.session,
                args.target,
                args.scantime,
                args.debug,
                args.mask_mode,
                args.interval,
                args.no_response_timeout,
            )
        elif args.method == "probe":
            run_probe(
                ser,
                args.address,
                args.qvalue,
                args.session,
                args.target,
                args.scantime,
                args.debug,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
