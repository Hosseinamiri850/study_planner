// Copy the canonical locale JSON from ../locales (backend source of truth)
// into ./locales so Next's compiler can bundle them. Run automatically via
// the predev/prebuild hooks; never edit files inside frontend/locales.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = dirname(fileURLToPath(import.meta.url));
const sourceDir = join(frontendDir, "..", "..", "locales");
const targetDir = join(frontendDir, "..", "locales");
mkdirSync(targetDir, { recursive: true });
for (const name of ["en.json", "fa.json"]) {
  copyFileSync(join(sourceDir, name), join(targetDir, name));
}
console.log("locales synced from ../locales");
