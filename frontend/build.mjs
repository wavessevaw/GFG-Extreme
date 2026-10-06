import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
async function loadEsbuild() {
  for (const spec of ["esbuild", "/opt/npm-tools/node_modules/esbuild/lib/main.js"]) {
    try { return await import(spec.startsWith("/") ? pathToFileURL(spec).href : spec); } catch (e) {}
  }
  throw new Error("esbuild not found (npm i -D esbuild)");
}
const { build } = await loadEsbuild();
const out = await build({ entryPoints: [path.join(here, "src/app.js")], bundle: true, format: "esm", write: false, target: "es2020" });
const target = process.argv[2] || path.join(here, "..", "dist", "index.js");
fs.writeFileSync(target, fs.readFileSync(path.join(here, "shim.js"), "utf8") + "\n" + out.outputFiles[0].text);
console.log("built", target);
