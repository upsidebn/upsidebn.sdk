# WebSerial SDK

The browser SDK lives at:

```text
web/nw-rfid-webserial.js
```

It requires Chrome or Edge with Web Serial support.

## Basic Usage

```html
<script type="module">
  import { NWWebSerialReader } from "./web/nw-rfid-webserial.js";

  const reader = new NWWebSerialReader({ baudRate: 115200, debug: true });
  await reader.connect();
  await reader.setAntennas([4]);

  const tags = await reader.inventoryOnce({ antenna: 4, scantime: 1 });
  console.log(tags);
</script>
```

## Configuration

```js
const info = await reader.getReaderInfo();
const power = await reader.getAntennaPower();

await reader.setAntennas([4], { preserve: false });
await reader.setRfPower([30, 30, 30, 30], { preserve: false });
await reader.setFrequency({ band: 27, minChannel: 0, maxChannel: 7, preserve: false });
await reader.setProfile(12, { preserve: false });

const frequency = await reader.getFrequency();
const profile = await reader.getProfile();
```

## Write EPC

```js
await reader.writeEpcByTarget({
  targetEpc: "E28011B0A505006F12316E2B",
  newEpc: "ABCD0001",
  antenna: 4,
  accessPassword: "00000000",
});
```

Blind write:

```js
await reader.blindWriteEpc({
  newEpc: "ABCD0001",
  antenna: 4,
  accessPassword: "00000000",
});
```

## Demo

Serve the SDK root with a local HTTP server:

```powershell
python -m http.server 8000
```

Open:

```text
http://localhost:8000/demos/webserial/
```
