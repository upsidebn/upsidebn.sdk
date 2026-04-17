#![cfg(feature = "hardware-tests")]

use nrn_sdk::NRNReader;

#[test]
fn query_reader_information_with_real_hardware() {
    let Ok(port) = std::env::var("NRN_SERIAL_PORT") else {
        return;
    };

    let mut reader = NRNReader::new(&port, 115_200).expect("reader should open");
    let _ = reader
        .query_reader_information()
        .expect("query should succeed");
}
