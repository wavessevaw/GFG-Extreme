import { build } from "/opt/npm-tools/node_modules/esbuild/lib/main.js";
import fs from "node:fs";
const out = await build({ entryPoints: ["src/app.js"], bundle: true, format: "esm", write: false, minify: false, target: "es2020" });
let body = out.outputFiles[0].text;
fs.writeFileSync(process.argv[2] || "dist-out.js", fs.readFileSync("shim.js", "utf8") + "\n" + body);
console.log("built", body.length);
