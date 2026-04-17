# NRN SDK for Rust

Rust SDK for Nextwaves NRN RFID readers.

## Install

```toml
[dependencies]
nrn-sdk = "1.0.0"
```

## Quick start

```rust
use nrn_sdk::NRNReader;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut reader = NRNReader::new("/dev/ttyUSB0", 115200)?;
    reader.connect_and_initialize()?;
    reader.start_inventory(0x01, |tag| println!("EPC: {}", tag.epc))?;
    reader.stop_inventory()?;
    Ok(())
}
```

## Development

```bash
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
```

Hardware integration tests are available behind the `hardware-tests` feature.
