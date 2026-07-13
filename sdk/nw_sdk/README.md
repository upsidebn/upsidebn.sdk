# NW SDK

NW SDK is a self-contained SDK for UHF RFID readers using the NW serial frame
protocol. It includes:

- Python SDK package: `src/nw_sdk`
- WebSerial SDK module: `web/nw-rfid-webserial.js`
- Python examples: `examples/python`
- Browser demo: `demos/webserial`
- Protocol notes: `docs/protocol.md`

## Features

- Connect over serial / WebSerial
- Read antenna power
- Enable one or more antennas
- Set per-antenna RF power
- Read and set frequency band and channel range
- Read and set reader profile
- Inventory tags and parse EPC, antenna, and RSSI
- Write EPC by target EPC
- Blind write EPC when only one tag is present

## Python Quickstart

```powershell
python -m pip install -e .
python examples/python/inventory.py
```

Change the COM port in the example if needed.

## WebSerial Quickstart

```powershell
python -m http.server 8000
```

Open:

```text
http://localhost:8000/demos/webserial/
```

Use Chrome or Edge and select the reader COM port when prompted.

## Typical Reader Settings

For a four-port setup where only ANT4 is connected:

```python
reader.set_antennas([4], preserve=False)
reader.set_rf_power([30, 30, 30, 30], preserve=False)
reader.set_frequency(band=27, min_channel=0, max_channel=7, preserve=False)
reader.set_profile(12, preserve=False)
```

## EPC Write Modes

### Write by Target

Selects a tag by its current EPC and writes a new EPC:

```python
reader.write_epc_by_target(
    target_epc="E28011B0A505006F12316E2B",
    new_epc="ABCD0001",
    antenna=4,
)
```

### Blind Write

Writes the EPC without a target EPC. Use only when one tag is in the active
antenna field:

```python
reader.blind_write_epc(new_epc="ABCD0001", antenna=4)
```

## Documentation

- [Protocol notes](docs/protocol.md)
- [Python SDK](docs/python.md)
- [WebSerial SDK](docs/webserial.md)
