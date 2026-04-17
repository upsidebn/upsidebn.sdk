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

	if err := reader.StartInventory(0x01, func(tag nrn.TagData) {
		fmt.Println(tag.EPC)
	}); err != nil {
		panic(err)
	}

	_ = reader.StopInventory()
}
