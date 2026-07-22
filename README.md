# UpsideBN NRN RFID Reader SDK

Multi-language SDK for NRN RFID readers.

## Install

| Language | Package | Install |
|---|---|---|
| Python | `nrn-sdk` | `pip install nrn-sdk` |
| Rust | `nrn-sdk` | `cargo add nrn-sdk` |
| Go | `github.com/upsidebn/upsidebn.sdk/sdk/nation/go` | `go get github.com/upsidebn/upsidebn.sdk/sdk/nation/go@v1.0.0` |
| TypeScript / WebSerial | `@upsidebn/nrn-sdk` | `npm install @upsidebn/nrn-sdk` |
| C++ | `sdk/nation/cpp` | CMake `FetchContent` or `add_subdirectory()` |

## Layout

- `sdk/nation/python` contains the Python module.
- `sdk/nation/rust` contains the Rust crate.
- `sdk/nation/go` contains the Go module.
- `sdk/nation/webserial` contains the TypeScript/Web Serial package.
- `sdk/nation/cpp` contains the C++ library and CMake package metadata.
- `examples/` contains per-language usage examples.
- `driver/` contains CP210x USB-to-UART drivers.
- `legacy/` contains archived vendor snapshots.

## Go import path

```go
import nrn "[github.com/upsidebn/upsidebn.sdk/sdk/nation/go](https://github.com/upsidebn/upsidebn.sdk/sdk/nation/go)"
- inquiry@upsidebn.com
- upsidebn.com
```

## CMake

include(FetchContent)

FetchContent_Declare(
  nrn_sdk
  GIT_REPOSITORY [https://github.com/upsidebn/upsidebn.sdk.git](https://github.com/upsidebn/upsidebn.sdk.git)
  GIT_TAG v1.0.0
  SOURCE_SUBDIR sdk/nation/cpp
)

FetchContent_MakeAvailable(nrn_sdk)

target_link_libraries(your_target PRIVATE nrn-sdk)

## Support

- inquiry@upsidebn.com
- upsidebn.com

## License

This repository is MIT-licensed for code under /sdk/nation/ and /examples/.
/legacy/ and /driver/ retain their own provenance and licensing.
