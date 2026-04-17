import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, test } from "vitest";

import { MID, NRNUtils, createNRNReader } from "../src/index";

type CrcVector = {
  input_hex: string;
  expected_crc_hex: string;
};

type CrcVectorFile = {
  crc_poly_1021_init_0000: CrcVector[];
};

const testdataDir = join(import.meta.dirname, "..", "..", "testdata");

function loadHexFixture(name: string): Uint8Array {
  const hex = readFileSync(join(testdataDir, "frames", name), "utf8").trim();
  return Uint8Array.from(hex.match(/.{1,2}/g)?.map((pair) => Number.parseInt(pair, 16)) ?? []);
}

describe("NRNUtils", () => {
  test("matches current TypeScript CRC vectors", () => {
    const vectors = JSON.parse(
      readFileSync(join(testdataDir, "crc_vectors.json"), "utf8"),
    ) as CrcVectorFile;
    for (const vector of vectors.crc_poly_1021_init_0000) {
      const input = Uint8Array.from(
        vector.input_hex.match(/.{1,2}/g)?.map((pair) => Number.parseInt(pair, 16)) ?? [],
      );
      expect(NRNUtils.crc16CCITT(input)).toBe(Number.parseInt(vector.expected_crc_hex, 16));
    }
  });

  test.fails("keeps CCITT-FALSE reference as a known drift for v1.1.0", () => {
    expect(NRNUtils.crc16CCITT(new TextEncoder().encode("123456789"))).toBe(0x29b1);
  });

  test("calculates RSSI and frequency", () => {
    expect(NRNUtils.calculateRSSI(128)).toBe(-65);
    expect(NRNUtils.calculateFrequency(10)).toBe(925);
  });

  test("builds and parses a frame", () => {
    const payload = new Uint8Array([0x00, 0x00, 0x00, 0x01, 0x01]);
    const frame = NRNUtils.buildFrame(MID.READ_EPC_TAG, payload);
    const parsed = NRNUtils.parseFrame(frame);

    expect(parsed.valid).toBe(true);
    expect(parsed.category).toBe(0x02);
    expect(parsed.mid).toBe(0x10);
    expect(Array.from(parsed.data)).toEqual(Array.from(payload));
  });

  test("rejects bad headers and CRC mismatches", () => {
    expect(() => NRNUtils.parseFrame(new Uint8Array([0x00, 0x01, 0x02]))).toThrow();

    const corrupted = loadHexFixture("query_info_request.crc1021.hex");
    corrupted[corrupted.length - 1] ^= 0xff;
    expect(() => NRNUtils.parseFrame(corrupted)).toThrow(/CRC mismatch/);
  });

  test("extracts valid frames from noisy input", () => {
    const frame = loadHexFixture("tag_notification.crc1021.hex");
    const noisy = new Uint8Array([0x00, 0x01, ...frame, 0x02]);
    const frames = NRNUtils.extractValidFrames(noisy);

    expect(frames).toHaveLength(1);
    expect(Array.from(frames[0])).toEqual(Array.from(frame));
  });
});

describe("NRNWebSerial internals", () => {
  test("builds default inventory payload and antenna masks", () => {
    const reader = createNRNReader() as any;

    expect(Array.from(reader.buildEPCReadPayload(0, true, false))).toEqual([0, 0, 0, 1, 1]);
    expect(reader.buildAntennaMask([1, 4, 7, 32]) >>> 0).toBe(0x80000049);
  });

  test("rejects invalid antenna IDs", () => {
    const reader = createNRNReader() as any;
    expect(() => reader.buildAntennaMask([0])).toThrow(/out of valid range/);
  });

  test("parses captured inventory notifications", () => {
    const reader = createNRNReader() as any;
    const frame = loadHexFixture("tag_notification.crc1021.hex");
    const parsed = NRNUtils.parseFrame(frame);
    const tag = reader.parseEPC(parsed.data);

    expect(tag.epc).toBe("3000112233445566");
    expect(tag.pc).toBe("3000");
    expect(tag.antenna_id).toBe(1);
    expect(tag.rssi).toBe(-65);
    expect(tag.frequency).toBe(920.532);
  });
});
