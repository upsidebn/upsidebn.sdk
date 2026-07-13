# Python SDK

## Install

From the SDK root:

```powershell
python -m pip install -e .
```

## Basic Inventory

```python
from nw_sdk import NWReader

with NWReader("COM3", baudrate=115200) as reader:
    reader.set_antennas([4], preserve=False)
    for tag in reader.inventory_loop(seconds=5, antenna=4):
        print(tag.epc, tag.antennas, tag.rssi)
```

## Reader Configuration

```python
with NWReader("COM3", baudrate=115200) as reader:
    info = reader.get_reader_info()
    power = reader.get_antenna_power()

    reader.set_antennas([4], preserve=False)
    reader.set_rf_power([30, 30, 30, 30], preserve=False)
    reader.set_frequency(band=27, min_channel=0, max_channel=7, preserve=False)
    reader.set_profile(12, preserve=False)
```

## Write EPC by Target

```python
with NWReader("COM3", baudrate=115200, debug=True) as reader:
    reader.write_epc_by_target(
        target_epc="E28011B0A505006F12316E2B",
        new_epc="ABCD0001",
        antenna=4,
        access_password="00000000",
    )
```

## Blind Write EPC

```python
with NWReader("COM3", baudrate=115200, debug=True) as reader:
    reader.blind_write_epc(
        new_epc="ABCD0001",
        antenna=4,
        access_password="00000000",
    )
```

Only use blind write when exactly one tag is in the active antenna field.
