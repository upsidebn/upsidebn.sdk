# Nextwaves NRN RFID Reader SDK

Multi-language SDK for Nextwaves NRN RFID readers.

## Install

| Language | Package | Install |
|---|---|---|
| Python | `nrn-sdk` | `pip install nrn-sdk` |
| Rust | `nrn-sdk` | `cargo add nrn-sdk` |
| Go | `github.com/Nextwaves-Industries/nextwaves-sdk/sdk/nation/go` | `go get github.com/Nextwaves-Industries/nextwaves-sdk/sdk/nation/go@v1.0.0` |
| TypeScript / WebSerial | `@nextwaves/nrn-sdk` | `npm install @nextwaves/nrn-sdk` |
| C++ | `sdk/nation/cpp` | CMake `FetchContent` or `add_subdirectory()` |

## Layout

- `sdk/nation/python` contains the Python module.
- `sdk/nation/rust` contains the Rust crate.
- `sdk/nation/go` contains the Go module.
- `sdk/nation/webserial` contains the TypeScript/Web Serial package.
- `sdk/nation/cpp` contains the C++ library and CMake package metadata.
- `examples/` contains per-language usage examples.
- `driver/` contains CP210x USB-to-UART drivers.
- `legacy/` contains archived vendor snapshots that are not covered by the root MIT license.

## Go import path

```go
import nrn "github.com/Nextwaves-Industries/nextwaves-sdk/sdk/nation/go"
```

## CMake consumption

```cmake
include(FetchContent)

FetchContent_Declare(
  nrn_sdk
  GIT_REPOSITORY https://github.com/Nextwaves-Industries/nextwaves-sdk.git
  GIT_TAG v1.0.0
  SOURCE_SUBDIR sdk/nation/cpp
)

FetchContent_MakeAvailable(nrn_sdk)

target_link_libraries(your_target PRIVATE nrn-sdk)
```

## Guides

- [Examples](/Users/dea/code_env/nextwaves/nextwaves-sdk/examples/README.md)
- [Python SDK](/Users/dea/code_env/nextwaves/nextwaves-sdk/sdk/nation/python/README.md)
- [Rust SDK](/Users/dea/code_env/nextwaves/nextwaves-sdk/sdk/nation/rust/README.md)
- [Go SDK](/Users/dea/code_env/nextwaves/nextwaves-sdk/sdk/nation/go/README.md)
- [C++ SDK](/Users/dea/code_env/nextwaves/nextwaves-sdk/sdk/nation/cpp/README.md)
- [WebSerial SDK](/Users/dea/code_env/nextwaves/nextwaves-sdk/sdk/nation/webserial/README.md)

## Support

- `tech@nextwaves.industries`
- [nextwaves.com](https://nextwaves.com)
- [app.nextwaves.com](https://app.nextwaves.com)

## License

This repository is MIT-licensed for code under `/sdk/nation/` and `/examples/`.
`/legacy/` and `/driver/` retain their own provenance and licensing.
