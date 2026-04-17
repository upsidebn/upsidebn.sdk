# NRN SDK for Go

Go SDK for Nextwaves NRN RFID readers.

## Install

```bash
go get github.com/Nextwaves-Industries/nextwaves-sdk/sdk/nation/go@v1.0.0
```

## Quick start

```go
package main

import (
	"fmt"

	nrn "github.com/Nextwaves-Industries/nextwaves-sdk/sdk/nation/go"
)

func main() {
	reader, err := nrn.NewNRNReader("/dev/ttyUSB0", 115200)
	if err != nil {
		panic(err)
	}
	defer reader.Close()

	if err := reader.ConnectAndInitialize(); err != nil {
		panic(err)
	}

	_ = reader.StartInventory(0x01, func(tag nrn.TagData) {
		fmt.Println(tag.EPC)
	})
}
```

## Development

```bash
gofmt -w .
go vet ./...
golangci-lint run ./...
go test ./...
```
