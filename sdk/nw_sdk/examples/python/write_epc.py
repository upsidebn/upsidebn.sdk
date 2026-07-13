from nw_sdk import NWReader


OLD_EPC = "E28011B0A505006F12316E2B"
NEW_EPC = "ABCD0001"


def main() -> None:
    with NWReader("COM3", baudrate=115200, debug=True) as reader:
        result = reader.write_epc_by_target(
            target_epc=OLD_EPC,
            new_epc=NEW_EPC,
            antenna=4,
            access_password="00000000",
        )
        print("Write OK:", result)


if __name__ == "__main__":
    main()
