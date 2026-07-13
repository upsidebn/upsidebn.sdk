from nw_sdk import NWReader


def main() -> None:
    with NWReader("COM3", baudrate=115200, debug=True) as reader:
        result = reader.blind_write_epc(
            new_epc="ABCD0001",
            antenna=4,
            access_password="00000000",
        )
        print("Write OK:", result)


if __name__ == "__main__":
    main()
