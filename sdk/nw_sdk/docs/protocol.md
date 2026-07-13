# NW RFID Protocol Notes

This document captures the protocol subset implemented by the SDK. It is
self-contained so the SDK can be used without external manuals.

## Frame Format

Host command frame:

```text
Len Adr Cmd Data... CRC_L CRC_H
```

Reader response frame:

```text
Len Adr ReCmd Status Data... CRC_L CRC_H
```

`Len` is the number of bytes from `Adr` through `CRC_H`. For host commands:

```text
Len = Data.length + 4
```

For normal responses:

```text
Len = Data.length + 5
```

CRC uses preset `0xFFFF`, polynomial `0x8408`, and is transmitted low byte
first.

## Core Commands

| Command | Name | Direction | SDK Method |
| --- | --- | --- | --- |
| `0x01` | Inventory | host -> reader | `inventory_once`, `inventory_loop` |
| `0x03` | Write data | host -> reader | `write_epc_by_target` |
| `0x04` | Blind write EPC | host -> reader | `blind_write_epc` |
| `0x21` | Get reader info | host -> reader | `get_reader_info` |
| `0x22` | Set frequency | host -> reader | `set_frequency` |
| `0x2F` | Set RF power | host -> reader | `set_rf_power` |
| `0x3F` | Set antenna mask | host -> reader | `set_antennas` |
| `0x7F` | Get/set profile | host -> reader | `get_profile`, `set_profile` |
| `0x94` | Read antenna power | host -> reader | `get_antenna_power` |
| `0x9E` | Read region/frequency | host -> reader | `get_frequency` |

## Inventory `0x01`

The SDK uses this payload:

```text
QValue Session Target Ant ScanTime
```

`Ant` is `0x80` for ANT1, `0x81` for ANT2, `0x82` for ANT3, `0x83` for ANT4.

Response data:

```text
Ant Num [Len EPC RSSI]...
```

`Ant` is a bitmask in common 4-port readers. `0x08` means ANT4.

## Antenna Mask `0x3F`

Payload format:

```text
AntMask
```

Bits:

```text
bit0 ANT1
bit1 ANT2
bit2 ANT3
bit3 ANT4
bit7 1 = do not persist after power off, 0 = persist
```

For ANT4 only, not persisted:

```text
0x88
```

## Write EPC by Target

The SDK uses command `0x03` to select a tag by its old EPC and write a new EPC.
It writes EPC memory from word `1`, which includes the PC word followed by the
new EPC data:

```text
WNum ENum OldEPC Mem WordPtr PC NewEPC AccessPwd
```

Where:

```text
Mem = 0x01      # EPC memory
WordPtr = 0x01  # PC word
PC = (new_epc_word_count << 11)
```

Example: new EPC `ABCD0001` is 2 words, so PC is `0x1000`.

## Blind Write EPC

Command `0x04` writes EPC without a target EPC:

```text
ENum AccessPwd NewEPC
```

Use this only when exactly one tag is in the antenna field.

## Frequency

The SDK uses frequency format 2:

```text
Flag FreBand MaxFre MinFre
```

`Flag = 0` persists the change, `Flag = 1` makes it temporary.

Common bands:

| Band | Region | Formula |
| --- | --- | --- |
| `2` | US | `902.75 + N * 0.5 MHz` |
| `4` | EU | `865.1 + N * 0.2 MHz` |
| `23` | Singapore | `920.25 + N * 0.5 MHz` |
| `27` | Vietnam | `918.75 + N * 0.5 MHz` |

## Profile

The SDK uses profile format 2:

```text
Opt ProfileHi ProfileLo
```

`Opt = 0` reads, `1` sets and saves, `2` sets temporarily.

Common values:

| Profile | Meaning |
| --- | --- |
| `1` | 640 kHz, Miller2, Tari 7.5 us |
| `3` | 320 kHz, Miller2, Tari 20 us |
| `5` | 320 kHz, Miller4, Tari 20 us |
| `7` | 250 kHz, Miller4, Tari 20 us |
| `11` | 640 kHz, FM0, Tari 7.5 us |
| `12` | 320 kHz, Miller2, Tari 15 us |
| `15` | 640 kHz, Miller4, Tari 7.5 us |
