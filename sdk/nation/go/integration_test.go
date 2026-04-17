//go:build integration

package nrn

import (
	"os"
	"testing"
)

func TestQueryReaderInformationWithRealHardware(t *testing.T) {
	port := os.Getenv("NRN_SERIAL_PORT")
	if port == "" {
		t.Skip("NRN_SERIAL_PORT is not set")
	}

	reader, err := NewNRNReader(port, 115200)
	if err != nil {
		t.Fatalf("open reader: %v", err)
	}
	defer reader.Close()

	if _, err := reader.QueryReaderInformation(); err != nil {
		t.Fatalf("query reader information: %v", err)
	}
}
