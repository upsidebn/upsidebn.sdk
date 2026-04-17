package nrn

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

type crcVectorFile struct {
	CRCPoly8005Init0000 []crcVector `json:"crc_poly_8005_init_0000"`
}

type crcVector struct {
	InputHex       string `json:"input_hex"`
	ExpectedCRCHex string `json:"expected_crc_hex"`
}

type fakeSerial struct {
	reads  [][]byte
	writes [][]byte
}

func (f *fakeSerial) Read(buf []byte) (int, error) {
	if len(f.reads) == 0 {
		return 0, nil
	}
	chunk := f.reads[0]
	f.reads = f.reads[1:]
	copy(buf, chunk)
	return len(chunk), nil
}

func (f *fakeSerial) Write(buf []byte) (int, error) {
	f.writes = append(f.writes, append([]byte(nil), buf...))
	return len(buf), nil
}

func (f *fakeSerial) Close() error {
	return nil
}

func (f *fakeSerial) SetReadTimeout(time.Duration) error {
	return nil
}

func (f *fakeSerial) ResetInputBuffer() error {
	return nil
}

func loadFixture(t *testing.T, elems ...string) []byte {
	t.Helper()
	path := filepath.Join(append([]string{"..", "testdata"}, elems...)...)
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture %s: %v", path, err)
	}
	return data
}

func mustDecodeHex(t *testing.T, input string) []byte {
	t.Helper()
	input = strings.TrimSpace(input)
	decoded := make([]byte, len(input)/2)
	for i := 0; i < len(input); i += 2 {
		var value byte
		_, err := fmt.Sscanf(input[i:i+2], "%02X", &value)
		if err != nil {
			t.Fatalf("decode hex %q: %v", input[i:i+2], err)
		}
		decoded[i/2] = value
	}
	return decoded
}

func newTestReader(reads ...[]byte) *NRNReader {
	return NewNRNReaderWithTransport(&fakeSerial{reads: reads}, "mock", 115200)
}

func TestCRCVectors(t *testing.T) {
	var vectors crcVectorFile
	if err := json.Unmarshal(loadFixture(t, "crc_vectors.json"), &vectors); err != nil {
		t.Fatalf("unmarshal crc vectors: %v", err)
	}

	for _, vector := range vectors.CRCPoly8005Init0000 {
		if got := CRC16CCITT(mustDecodeHex(t, vector.InputHex)); got != parseHexU16(t, vector.ExpectedCRCHex) {
			t.Fatalf("crc mismatch for %s: got %04X", vector.InputHex, got)
		}
	}
}

func TestCalculateRSSI(t *testing.T) {
	cases := map[uint8]int32{
		0:   -100,
		128: -65,
		255: -30,
	}
	for raw, expected := range cases {
		if got := CalculateRSSI(raw); got != expected {
			t.Fatalf("raw %d: got %d want %d", raw, got, expected)
		}
	}
}

func TestCalculateFrequency(t *testing.T) {
	if got := CalculateFrequency(10); got != 925.0 {
		t.Fatalf("got %v", got)
	}
}

func TestBuildAntennaMask(t *testing.T) {
	if got := BuildAntennaMask([]int{1, 4, 7, 32}); got != 0x80000049 {
		t.Fatalf("got %08X", got)
	}
}

func TestBytesToHex(t *testing.T) {
	if got := BytesToHex([]byte{0xDE, 0xAD, 0xBE, 0xEF}); got != "DEADBEEF" {
		t.Fatalf("got %s", got)
	}
}

func TestBuildFrameRoundTrip(t *testing.T) {
	reader := newTestReader()
	payload := []byte{0x00, 0x00, 0x00, 0x01, 0x01}
	frame := reader.BuildFrame(MIDReadEpcTag, payload)
	parsed := reader.ParseFrame(frame)

	if !parsed.Valid || parsed.Category != 0x02 || parsed.MID != 0x10 {
		t.Fatalf("unexpected parsed frame: %+v", parsed)
	}
}

func TestBuildEPCReadPayloadDefaultsToAntenna1(t *testing.T) {
	reader := newTestReader()
	payload := reader.BuildEPCReadPayload(0, true, false)
	if got := BytesToHex(payload); got != "0000000101" {
		t.Fatalf("got %s", got)
	}
}

func TestParseFrameRejectsShortInput(t *testing.T) {
	reader := newTestReader()
	parsed := reader.ParseFrame([]byte{0x5A, 0x00, 0x01})
	if parsed.Valid {
		t.Fatal("expected invalid frame")
	}
}

func TestParseEPCFixture(t *testing.T) {
	reader := newTestReader()
	payload := mustDecodeHex(t, "00083000112233445566300001018008000E0BD40940")
	tag := reader.ParseEPC(payload)

	if tag.EPC != "3000112233445566" || tag.PC != "3000" || tag.AntennaID != 1 {
		t.Fatalf("unexpected tag: %+v", tag)
	}
	if tag.RSSI == nil || *tag.RSSI != -65 {
		t.Fatalf("unexpected rssi: %+v", tag.RSSI)
	}
	if tag.Frequency == nil || *tag.Frequency != 920.532 {
		t.Fatalf("unexpected frequency: %+v", tag.Frequency)
	}
}

func TestQueryReaderInformationFixture(t *testing.T) {
	template := newTestReader()
	payload := append([]byte{0x01, 0x08}, []byte("NRN00001")...)
	payload = append(payload, 0x02, 0x04, 0x00, 0x00, 0x0E, 0x10)
	payload = append(payload, 0x04, 0x05)
	payload = append(payload, []byte("1.0.0")...)
	response := template.BuildFrame(MIDQueryInfo, payload)
	reader := newTestReader(response)
	info, err := reader.QueryReaderInformation()
	if err != nil {
		t.Fatalf("query info: %v", err)
	}
	if info.SerialNumber != "NRN00001" || info.PowerOnTimeSec != 3600 || info.AppVersion != "1.0.0" {
		t.Fatalf("unexpected info: %+v", info)
	}
}

func parseHexU16(t *testing.T, input string) uint16 {
	t.Helper()
	var value uint16
	if _, err := fmt.Sscanf(strings.TrimSpace(input), "%04X", &value); err != nil {
		t.Fatalf("parse hex %s: %v", input, err)
	}
	return value
}
