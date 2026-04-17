import { createNRNReader } from "@nextwaves/nrn-sdk";

const output = document.querySelector<HTMLPreElement>("#output");
const button = document.querySelector<HTMLButtonElement>("#connect");

button?.addEventListener("click", async () => {
  const reader = createNRNReader();
  await reader.connect();
  await reader.startInventory([1], (tag) => {
    if (output) {
      output.textContent += `${tag.epc}\n`;
    }
  });
});
