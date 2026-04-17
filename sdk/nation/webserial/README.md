# NRN SDK for Web Serial

TypeScript Web Serial SDK for Nextwaves NRN RFID readers.

## Install

```bash
npm install @nextwaves/nrn-sdk
```

## Quick start

```ts
import { createNRNReader } from "@nextwaves/nrn-sdk";

const reader = createNRNReader();
await reader.connect();
await reader.startInventory([1], (tag) => console.log(tag.epc));
```

## Development

```bash
npm install
npm run lint
npm run format:check
npm run typecheck
npm test
```
