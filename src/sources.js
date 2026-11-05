import { esc } from "./common.js";

// Contenido del diálogo «Fuentes y fechas» (mismo registro que docs/FUENTES.md: data/fuentes.json)
export function renderSources(el, fuentes, avisos) {
  el.innerHTML = `<p class="muted">Consulta de datos: ${esc(fuentes.consulta)}. Información orientativa, no en tiempo real.</p>
  <ol>${fuentes.fuentes.map((f) => `<li><b>${esc(f.nombre)}</b> — ${esc(f.organismo)}<br><span class="small">${esc(f.tipo)}</span><br>
    <span class="small muted">Versión: ${esc(f.version)} · Licencia: ${esc(f.licencia)}</span>
    ${f.limitaciones && f.limitaciones !== "—" ? `<br><span class="small">Limitaciones: ${esc(f.limitaciones)}</span>` : ""}</li>`).join("")}</ol>
  <p class="small">${esc(avisos.nota)}</p>`;
}
