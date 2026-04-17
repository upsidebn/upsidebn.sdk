import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const outputDir = join(process.cwd(), "dist", "cjs");

await mkdir(outputDir, { recursive: true });
await writeFile(join(outputDir, "package.json"), JSON.stringify({ type: "commonjs" }, null, 2));
