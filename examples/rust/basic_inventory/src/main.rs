use nrn_sdk::NRNReader;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut reader = NRNReader::new("/dev/ttyUSB0", 115200)?;
    reader.connect_and_initialize()?;
    reader.start_inventory(0x01, |tag| println!("EPC: {}", tag.epc))?;
    reader.stop_inventory()?;
    Ok(())
}
