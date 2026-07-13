from nw_sdk import NWReader


def main() -> None:
    with NWReader("COM3", baudrate=115200, debug=True) as reader:
        reader.set_antennas([4], preserve=False)
        reader.set_rf_power([30, 30, 30, 30], preserve=False)
        reader.set_frequency(band=27, min_channel=0, max_channel=7, preserve=False)
        reader.set_profile(12, preserve=False)

        print("Power:", reader.get_antenna_power().values)
        print("Frequency:", reader.get_frequency())
        print("Profile:", reader.get_profile())


if __name__ == "__main__":
    main()
