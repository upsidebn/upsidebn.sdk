# Shared Frame Fixtures

These fixtures are hex-encoded raw protocol frames with no separators.

- `*.crc1021.hex` matches the current Python and TypeScript implementations.
- `*.crc8005.hex` matches the current Rust, Go, and C++ implementations.

The duplicated CRC variants are temporary. Once all SDKs converge on the same
CRC polynomial in v1.1.0, these fixtures should collapse back to a single
canonical frame set.
