export const Commands = Object.freeze({
  INVENTORY: 0x01,
  WRITE_DATA: 0x03,
  WRITE_EPC: 0x04,
  GET_READER_INFO: 0x21,
  SET_FREQUENCY: 0x22,
  SET_RF_POWER: 0x2f,
  SET_ANTENNA: 0x3f,
  PROFILE: 0x7f,
  READ_ANTENNA_POWER: 0x94,
  READ_REGION: 0x9e,
});

export function crc16(bytes) {
  let value = 0xffff;
  for (const byte of bytes) {
    value ^= byte;
    for (let i = 0; i < 8; i++) {
      value = value & 1 ? (value >> 1) ^ 0x8408 : value >> 1;
      value &= 0xffff;
    }
  }
  return value;
}

export function buildCommand(address, command, data = []) {
  const body = [data.length + 4, address, command, ...data];
  const crc = crc16(body);
  return new Uint8Array([...body, crc & 0xff, (crc >> 8) & 0xff]);
}

export function parseFrame(raw) {
  if (raw.length < 5) throw new Error("Frame is too short");
  const total = raw[0] + 1;
  if (total !== raw.length) throw new Error(`Length mismatch: ${total} != ${raw.length}`);
  const expected = raw[raw.length - 2] | (raw[raw.length - 1] << 8);
  const actual = crc16(raw.slice(0, -2));
  if (expected !== actual) throw new Error(`Bad CRC: expected ${expected}, got ${actual}`);
  return {
    raw,
    address: raw[1],
    command: raw[2],
    status: raw[3],
    data: raw.slice(4, -2),
  };
}

export function cleanHex(value) {
  return String(value || "").replace(/[^0-9a-fA-F]/g, "").toUpperCase();
}

export function hexToBytes(value, label = "hex") {
  const text = cleanHex(value);
  if (!text || text.length % 2 !== 0) {
    throw new Error(`${label} must contain an even number of hex digits`);
  }
  const out = [];
  for (let i = 0; i < text.length; i += 2) out.push(parseInt(text.slice(i, i + 2), 16));
  return out;
}

export function pcWordForEpc(epcBytes) {
  if (epcBytes.length % 2) throw new Error("EPC length must be even");
  const words = epcBytes.length / 2;
  if (words < 1 || words > 31) throw new Error("EPC length must be 1..31 words");
  return (words & 0x1f) << 11;
}

export function selectedAntennaCode(antenna) {
  if (antenna < 1 || antenna > 16) throw new Error("antenna must be 1..16");
  return 0x80 + (antenna - 1);
}

export function enabledAntennaMask(antennas, preserve = false) {
  let mask = 0;
  for (const antenna of antennas) {
    if (antenna < 1 || antenna > 8) throw new Error("this helper supports antenna 1..8");
    mask |= 1 << (antenna - 1);
  }
  if (!mask) throw new Error("at least one antenna must be enabled");
  return preserve ? mask : mask | 0x80;
}

function antennaList(mask) {
  const out = [];
  for (let i = 0; i < 8; i++) if (mask & (1 << i)) out.push(i + 1);
  return out.length ? out : [mask];
}

export class NWWebSerialReader extends EventTarget {
  constructor({ address = 0x00, baudRate = 115200, debug = false } = {}) {
    super();
    this.address = address;
    this.baudRate = baudRate;
    this.debug = debug;
    this.port = null;
    this.reader = null;
    this.reading = false;
    this.rx = [];
    this.pending = [];
  }

  async connect() {
    if (!("serial" in navigator)) throw new Error("Web Serial is not supported");
    this.port = await navigator.serial.requestPort();
    await this.port.open({ baudRate: this.baudRate });
    this.reading = true;
    this.readLoop();
  }

  async disconnect() {
    this.reading = false;
    if (this.reader) await this.reader.cancel();
    if (this.port) await this.port.close();
    this.port = null;
  }

  async readLoop() {
    while (this.port?.readable && this.reading) {
      this.reader = this.port.readable.getReader();
      try {
        while (this.reading) {
          const { value, done } = await this.reader.read();
          if (done) break;
          if (value) this.feed(Array.from(value));
        }
      } finally {
        this.reader.releaseLock();
        this.reader = null;
      }
    }
  }

  feed(bytes) {
    this.rx.push(...bytes);
    while (this.rx.length) {
      const length = this.rx[0];
      if (length < 4) {
        this.rx.shift();
        continue;
      }
      const total = length + 1;
      if (this.rx.length < total) return;
      const raw = this.rx.splice(0, total);
      let frame;
      try {
        frame = parseFrame(raw);
      } catch (error) {
        this.dispatchEvent(new CustomEvent("protocolerror", { detail: { error, raw } }));
        continue;
      }
      this.handleFrame(frame);
    }
  }

  handleFrame(frame) {
    const pendingIndex = this.pending.findIndex((item) => item.commands.has(frame.command));
    if (pendingIndex >= 0) {
      const [item] = this.pending.splice(pendingIndex, 1);
      clearTimeout(item.timer);
      item.resolve(frame);
      return;
    }
    this.dispatchEvent(new CustomEvent("frame", { detail: frame }));
  }

  async command(command, data = [], { responseCommands = [command], timeoutMs = 1000 } = {}) {
    if (!this.port?.writable) throw new Error("Serial port is not writable");
    const raw = buildCommand(this.address, command, data);
    if (this.debug) console.log("OUT", Array.from(raw).map((x) => x.toString(16).padStart(2, "0")).join(" "));
    const promise = new Promise((resolve) => {
      const timer = setTimeout(() => {
        const idx = this.pending.findIndex((item) => item.resolve === resolve);
        if (idx >= 0) this.pending.splice(idx, 1);
        resolve(null);
      }, timeoutMs);
      this.pending.push({ commands: new Set(responseCommands), resolve, timer });
    });
    const writer = this.port.writable.getWriter();
    try {
      await writer.write(raw);
    } finally {
      writer.releaseLock();
    }
    return promise;
  }

  requireOk(operation, frame) {
    if (!frame) throw new Error(`${operation}: no response`);
    if (frame.status !== 0x00) throw new Error(`${operation}: status 0x${frame.status.toString(16)}`);
    return frame;
  }

  async getReaderInfo() {
    const frame = await this.command(Commands.GET_READER_INFO, [], { timeoutMs: 1000 });
    this.requireOk("getReaderInfo", frame);
    if (frame.data.length < 11) throw new Error("reader info response is too short");
    return {
      firmware: `${frame.data[0]}.${frame.data[1]}`,
      modelType: frame.data[2],
      protocolFlags: frame.data[3],
      maxFrequency: frame.data[4],
      minFrequency: frame.data[5],
      rfPower: frame.data[6],
      inventoryTime: frame.data[7],
      antennaMask: frame.data[8],
      antennaCheck: frame.data[10],
    };
  }

  async getAntennaPower() {
    const frame = await this.command(Commands.READ_ANTENNA_POWER, [], {
      responseCommands: [Commands.READ_ANTENNA_POWER, 0x51],
      timeoutMs: 1000,
    });
    this.requireOk("getAntennaPower", frame);
    return frame.data;
  }

  async setAntennas(antennas, { preserve = false } = {}) {
    const frame = await this.command(Commands.SET_ANTENNA, [enabledAntennaMask(antennas, preserve)]);
    this.requireOk("setAntennas", frame);
  }

  async setRfPower(powers, { preserve = false } = {}) {
    if (![1, 4, 8, 16].includes(powers.length)) {
      throw new Error("setRfPower accepts 1, 4, 8, or 16 values");
    }
    const payload = powers.map((power) => {
      if (power < 0 || power > 30) throw new Error("power must be 0..30");
      return power | (preserve ? 0 : 0x80);
    });
    const frame = await this.command(Commands.SET_RF_POWER, payload, { timeoutMs: 1000 });
    this.requireOk("setRfPower", frame);
  }

  async getFrequency() {
    const frame = await this.command(Commands.READ_REGION, [], { timeoutMs: 1000 });
    this.requireOk("getFrequency", frame);
    if (frame.data.length < 3) throw new Error("frequency response is too short");
    return { band: frame.data[0], maxChannel: frame.data[1], minChannel: frame.data[2] };
  }

  async setFrequency({ band, minChannel, maxChannel, preserve = false }) {
    if (maxChannel < minChannel) throw new Error("maxChannel must be >= minChannel");
    const flag = preserve ? 0 : 1;
    const frame = await this.command(
      Commands.SET_FREQUENCY,
      [flag, band & 0xff, maxChannel & 0xff, minChannel & 0xff],
      { timeoutMs: 1000 },
    );
    this.requireOk("setFrequency", frame);
  }

  async getProfile() {
    let frame = await this.command(Commands.PROFILE, [0x00, 0x00, 0x00], { timeoutMs: 1000 });
    if (!frame || frame.status !== 0x00 || frame.data.length < 2) {
      frame = await this.command(Commands.PROFILE, [0x00], { timeoutMs: 1000 });
    }
    this.requireOk("getProfile", frame);
    if (frame.data.length >= 2) return (frame.data[0] << 8) | frame.data[1];
    if (frame.data.length === 1) return frame.data[0] & 0x7f;
    throw new Error("profile response has no data");
  }

  async setProfile(profile, { preserve = false } = {}) {
    const opt = preserve ? 1 : 2;
    const frame = await this.command(Commands.PROFILE, [opt, (profile >> 8) & 0xff, profile & 0xff], {
      timeoutMs: 1000,
    });
    this.requireOk("setProfile", frame);
  }

  async inventoryOnce({ antenna = 4, qvalue = 4, session = 0, target = 0, scantime = 1 } = {}) {
    const data = [qvalue & 0x0f, session & 0xff, target & 0xff, selectedAntennaCode(antenna), scantime & 0xff];
    const frame = await this.command(Commands.INVENTORY, data, { timeoutMs: Math.max(500, scantime * 100 + 250) });
    if (!frame) return [];
    return this.parseInventory(frame.data);
  }

  parseInventory(data) {
    if (data.length < 2 || data[1] === 0) return [];
    const antRaw = data[0];
    const tags = [];
    let pos = 2;
    while (pos < data.length) {
      const lenByte = data[pos++];
      const epcLen = lenByte & 0x3f;
      if (pos + epcLen + 1 > data.length) break;
      const epc = data.slice(pos, pos + epcLen);
      pos += epcLen;
      const rssi = data[pos++];
      tags.push({
        epc: Array.from(epc).map((x) => x.toString(16).padStart(2, "0")).join("").toUpperCase(),
        antennaRaw: antRaw,
        antennas: antennaList(antRaw),
        rssi,
        rssiRaw: rssi,
      });
    }
    return tags;
  }

  async writeEpcByTarget({ targetEpc, newEpc, antenna = 4, accessPassword = "00000000" }) {
    await this.setAntennas([antenna], { preserve: false });
    const oldBytes = hexToBytes(targetEpc, "targetEpc");
    const newBytes = hexToBytes(newEpc, "newEpc");
    const pwd = hexToBytes(accessPassword, "accessPassword");
    if (pwd.length !== 4) throw new Error("accessPassword must be 4 bytes");
    const pc = pcWordForEpc(newBytes);
    const wordsToWrite = [(pc >> 8) & 0xff, pc & 0xff, ...newBytes];
    const payload = [
      wordsToWrite.length / 2,
      oldBytes.length / 2,
      ...oldBytes,
      0x01,
      0x01,
      ...wordsToWrite,
      ...pwd,
    ];
    const frame = await this.command(Commands.WRITE_DATA, payload, { timeoutMs: 10000 });
    this.requireOk("writeEpcByTarget", frame);
    return frame;
  }

  async blindWriteEpc({ newEpc, antenna = 4, accessPassword = "00000000" }) {
    await this.setAntennas([antenna], { preserve: false });
    const newBytes = hexToBytes(newEpc, "newEpc");
    const pwd = hexToBytes(accessPassword, "accessPassword");
    if (pwd.length !== 4) throw new Error("accessPassword must be 4 bytes");
    const frame = await this.command(Commands.WRITE_EPC, [newBytes.length / 2, ...pwd, ...newBytes], {
      timeoutMs: 10000,
    });
    this.requireOk("blindWriteEpc", frame);
    return frame;
  }
}
