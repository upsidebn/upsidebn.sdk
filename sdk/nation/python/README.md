# NRN SDK for Python

Python SDK for Nextwaves NRN RFID readers.

## Install

```bash
pip install nrn-sdk
```

## Quick start

```python
import logging

from nrn import create_reader


def on_tag(tag: dict) -> None:
    print(f"EPC={tag['epc']} RSSI={tag.get('rssi')}")


reader = create_reader("/dev/ttyUSB0", log_level=logging.INFO)
reader.open()
reader.start_inventory_with_mode(antenna_mask=[1], callback=on_tag)
reader.stop_inventory()
reader.close()
```

## API highlights

- `create_reader(...)` creates a configured `NRNReader`
- `NRNReader.open()` and `NRNReader.close()` manage the serial connection
- `NRNReader.start_inventory_with_mode(...)` and `NRNReader.stop_inventory()` control inventory
- `NRNReader.Query_Reader_Information()` queries device metadata
- `NRNReader.query_rfid_ability()` queries device capabilities

## Development

```bash
pip install -e .[dev]
ruff check .
ruff format --check .
pytest -m "not integration"
```

Hardware integration tests are skipped unless `NRN_SERIAL_PORT` is set.

## Troubleshooting

### Common Issues

1. **Connection Failed**: Check port name and permissions
2. **No Tags Found**: Verify antenna connection and power settings
3. **Write Failed**: Ensure tag is in range and not locked

### Debug Mode

Enable debug logging for detailed information:

```python
reader.set_log_level(logging.DEBUG)
```

## SDK Information

- **Name**: Nextwaves RFID SDK
- **Version**: 1.0.0
- **Supported Readers**: NRN RFID Readers
- **Protocol**: UART-based communication
- **Python Version**: 3.6+

## License

This SDK is provided by Nextwaves for use with their RFID readers.

## Support

For technical support and documentation, please contact Nextwaves support.
