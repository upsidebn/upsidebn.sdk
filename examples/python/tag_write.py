#!/usr/bin/env python3
"""Write a new EPC to a single tag."""

from nrn import create_reader


def main() -> None:
    reader = create_reader("/dev/ttyUSB0")
    reader.open()
    try:
        result = reader.write_epc_tag_auto(
            target_tag_epc="3000112233445566",
            new_epc_hex="3000112233445567",
        )
        print(result)
    finally:
        reader.close()


if __name__ == "__main__":
    main()
