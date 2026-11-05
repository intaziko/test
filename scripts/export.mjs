// Exportación A3 horizontal (PDF vectorial + mapa ráster a ~290 ppp, y PNG) de los dos mapas.
// Uso: npm run build && npm run export   → carpeta exports/
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { preview } from "vite";
import { PDFDocument } from "pdf-lib";

// Playwright no es dependencia del proyecto (pesa ~150 MB con el navegador): ver README «Exportar PDF/PNG».
const { chromium } = createRequire(import.meta.url)("playwright");
const OUT = new URL("../exports/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const server = await preview({ preview: { port: 4321, strictPort: false }, logLevel: "error" });
const base = server.resolvedUrls.local[0];
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const ctx = await browser.newContext({ viewport: { width: 1587, height: 1123 }, deviceScaleFactor: 3 });
const views = [
  { file: "mapa1-madrid-metropolitano-A3", path: "index.html?print=a3" },
  { file: "mapa1-madrid-centro-A3", path: "index.html?print=a3-centro" },
  { file: "mapa2-ruta-IDA-A3", path: "ruta.html?print=a3&modo=ida" },
  { file: "mapa2-ruta-VUELTA-A3", path: "ruta.html?print=a3&modo=vuelta" },
];
const errors = [];
for (const v of views) {
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(`${v.file}: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && errors.push(`${v.file}: ${m.text()}`));
  await page.goto(base + v.path, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__READY === true, null, { timeout: 120000 });
  await page.evaluate(() => new Promise((r) => { window.__map.triggerRepaint(); window.__map.once("idle", r); }));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: OUT + v.file + ".png" });
  await page.pdf({ path: OUT + v.file + ".pdf", width: "420mm", height: "297mm", printBackground: true, pageRanges: "1" });
  console.log("✓", v.file);
  await page.close();
}
async function merge(name, files) {
  const doc = await PDFDocument.create();
  for (const f of files) {
    const src = await PDFDocument.load(readFileSync(OUT + f + ".pdf"));
    for (const p of await doc.copyPages(src, src.getPageIndices())) doc.addPage(p);
  }
  doc.setTitle(name); doc.setAuthor("Mapa de transporte de Madrid"); doc.setSubject("Exportación A3 horizontal");
  writeFileSync(OUT + name + ".pdf", await doc.save());
  console.log("✓", name + ".pdf");
}
await merge("MAPA1-red-transporte-Madrid-A3", ["mapa1-madrid-metropolitano-A3", "mapa1-madrid-centro-A3"]);
await merge("MAPA2-ruta-Cristo-Social-Club-IDA-y-VUELTA-A3", ["mapa2-ruta-IDA-A3", "mapa2-ruta-VUELTA-A3"]);
await browser.close();
await new Promise((r) => server.httpServer.close(r));
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
