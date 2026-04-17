#!/usr/bin/env python3
"""Basic inventory example for the Python NRN SDK."""

import logging
import time
from nrn import NRNReader, create_reader, setup_logging

def main():
    """Run a short inventory session."""

    logger = setup_logging(level=logging.INFO)
    logger.info("Starting Python NRN inventory example")

    reader = create_reader(
        port="/dev/ttyUSB0",
        baudrate=115200,
        log_level=logging.INFO,
    )

    try:
        sdk_info = NRNReader.get_sdk_info()
        logger.info(f"Using {sdk_info['name']} v{sdk_info['version']}")

        reader.open()

        tags_found = []

        def on_tag_callback(tag):
            """Handle a single tag notification."""
            tag_info = f"EPC: {tag.get('epc', 'Unknown')}, "
            tag_info += f"RSSI: {tag.get('rssi', 'Unknown')}, "
            tag_info += f"Antenna: {tag.get('antenna_id', 'Unknown')}"
            logger.info(f"Tag found: {tag_info}")
            tags_found.append(tag)

        logger.info("Starting inventory for 5 seconds...")
        reader.start_inventory_with_mode(antenna_mask=[1], callback=on_tag_callback)

        time.sleep(5)
        reader.stop_inventory()
        logger.info("Inventory completed. Found %d tag notifications.", len(tags_found))
    except Exception as e:
        logger.error(f"Error during operation: {e}")
    finally:
        reader.close()
        logger.info("Example completed")

if __name__ == "__main__":
    main()
