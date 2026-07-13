from nw_sdk import NWReader


def main() -> None:
    with NWReader("COM3", baudrate=115200, debug=False) as reader:
        print("Power:", reader.get_antenna_power().values)
        print("Info:", reader.get_reader_info())

        reader.set_antennas([4], preserve=False)
        for tag in reader.inventory_loop(seconds=10, antenna=4):
            print(f"EPC={tag.epc} ANT={tag.antennas} RSSI={tag.rssi}")


if __name__ == "__main__":
    main()
