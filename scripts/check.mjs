// Comprobación técnica en navegador real (Chromium): ambos mapas en escritorio y móvil, sin errores de
// consola, con datos cargados, buscador, capas, selección de línea y cambio IDA/VUELTA.
// Uso: npm run build && npm run check
import { createRequire } from "node:module";
import { preview } from "vite";

const { chromium, devices } = createRequire(import.meta.url)("playwright");
const server = await preview({ preview: { port: 4322, strictPort: false }, logLevel: "error" });
const base = server.resolvedUrls.local[0];
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const fails = [];
const ok = (cond, msg) => { console.log(`${cond ? "✓" : "✗"} ${msg}`); if (!cond) fails.push(msg); };

async function open(path, ctxOpts) {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(e.message));
  page.on("console", (m) => (m.type() === "error" || (m.type() === "warning" && /MapLibre/.test(m.text()))) && errs.push(m.text()));
  // las peticiones canceladas por MapLibre al mover el mapa (net::ERR_ABORTED) no son errores
  page.on("requestfailed", (r) => r.failure()?.errorText !== "net::ERR_ABORTED" && errs.push("request failed " + r.url()));
  await page.goto(base + path, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__READY === true, null, { timeout: 90000 });
  return { page, errs, ctx };
}

for (const [label, opts] of [["escritorio", { viewport: { width: 1440, height: 900 } }], ["móvil", devices["iPhone 13"]]]) {
  // ---------------- Mapa 1
  const { page, errs, ctx } = await open("index.html", opts);
  const n = await page.evaluate(() => ({
    lines: window.__map.querySourceFeatures("lineas").length,
    st: window.__map.getSource("estaciones")._data?.features?.length ?? 0,
    layers: ["metro-line", "ml-line", "cer-line", "dist-fill", "mun-line", "lbl-dist"].every((l) => window.__map.getLayer(l)),
  }));
  ok(n.lines > 0 && n.layers, `[${label}] Mapa 1: capas de líneas, distritos y municipios cargadas`);
  await page.fill("#q", "diego de leon");
  ok((await page.textContent("#results")).includes("Diego de León"), `[${label}] buscador: estación «Diego de León»`);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1500);
  ok((await page.textContent("#info-c")).includes("Salamanca"), `[${label}] ficha de estación con distrito (Salamanca)`);
  ok((await page.textContent("#info-c")).includes("hacia"), `[${label}] ficha con estaciones anterior/siguiente por línea`);
  for (const [q, want] of [["getafe", "Municipio"], ["fuencarral", "Distrito de Madrid"], ["torrejon", "Municipio"]]) {
    await page.fill("#q", q);
    ok((await page.textContent("#results")).includes(want), `[${label}] buscador: «${q}» → ${want}`);
  }
  await page.fill("#q", "");
  await page.evaluate(() => document.querySelector('[data-net="cercanias"]').click());
  const hidden = await page.evaluate(() => JSON.stringify(window.__map.getFilter("cer-line")).includes("cercanias:C1"));
  ok(hidden, `[${label}] desactivar la red de Cercanías filtra sus líneas`);
  await page.evaluate(() => document.querySelector('.chip[data-key="metro:10"]').click());
  await page.waitForTimeout(800);
  ok((await page.textContent("#info-c")).includes("Puerta del Sur"), `[${label}] seleccionar L10 muestra su recorrido`);
  ok(!errs.length, `[${label}] Mapa 1 sin errores de consola ${errs.join(" | ")}`);
  await ctx.close();
  // ---------------- Mapa 2
  const r = await open("ruta.html", opts);
  ok((await r.page.textContent("#steps")).includes("Plaza Elíptica"), `[${label}] Mapa 2: pasos de la IDA`);
  ok((await r.page.textContent("#steps")).includes("Andén 1"), `[${label}] IDA indica el andén/sentido de la L6`);
  await r.page.click('#modes [data-m="vuelta"]');
  await r.page.waitForTimeout(800);
  ok((await r.page.textContent("#steps")).includes("La Fortuna"), `[${label}] VUELTA: L11 dirección La Fortuna`);
  const nsc = await r.page.$$eval("#scen button", (b) => b.length);
  ok(nsc >= 3, `[${label}] VUELTA con ${nsc} escenarios (recomendada, corte L6, búho nocturno, SC2)`);
  const feats = await r.page.evaluate(() => window.__map.querySourceFeatures("route").length);
  ok(feats > 0, `[${label}] recorrido dibujado en el mapa`);
  ok(!r.errs.length, `[${label}] Mapa 2 sin errores de consola ${r.errs.join(" | ")}`);
  await r.ctx.close();
}
await browser.close();
await new Promise((r) => server.httpServer.close(r));
console.log(fails.length ? `\n${fails.length} comprobaciones fallidas` : "\nTodas las comprobaciones técnicas superadas");
process.exit(fails.length ? 1 : 0);
