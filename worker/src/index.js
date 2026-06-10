// Worker de "imagen dinámica de enlace" para el Trivial Mundial 2026.
//
// Rutas:
//   /og?p=&o=&a=&n=&q=   -> PNG 1080x1350 con el resultado y la lista de respuestas
//   /s?...               -> HTML con og:image dinámico + redirección al juego
//
// El juego sigue en GitHub Pages (dominio trivial-mundial-2026.spacebom.com);
// este Worker sirve el enlace de compartir para que WhatsApp/X/Telegram muestren
// la imagen del resultado (también en escritorio) y redirige a la persona al juego.

import { ImageResponse, loadGoogleFont } from "workers-og";

const JUEGO = "https://trivial-mundial-2026.spacebom.com/";
const W = 1080, H = 1350;

const DESENLACES = {
  C: { titulo: "¡Campeón del Mundo!", emoji: "🏆", accent: "#FFD24A" },
  G: { titulo: "Eliminado en fase de grupos", emoji: "🧹", accent: "#FF8FA3" },
  O: { titulo: "Eliminado en Octavos", emoji: "👏", accent: "#FFC36B" },
  Q: { titulo: "Eliminado en Cuartos", emoji: "⚔️", accent: "#FFC36B" },
  S: { titulo: "Semifinalista", emoji: "🎖️", accent: "#8FE3FF" },
  F: { titulo: "Subcampeón", emoji: "🥈", accent: "#CBD2FF" },
};
const ETAPA_NOMBRE = ["Fase de grupos", "Fase de grupos", "Fase de grupos", "Octavos de final", "Cuartos de final", "Semifinal", "Final"];

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const trunc = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

function datos(params) {
  const p = (params.get("p") || "Mundial 2026").slice(0, 40);
  const o = (params.get("o") || "C").toUpperCase();
  const a = Math.max(0, parseInt(params.get("a") || "0", 10) || 0);
  const n = Math.max(1, parseInt(params.get("n") || "7", 10) || 7);
  let filas = [];
  try {
    const arr = JSON.parse(params.get("q") || "[]");
    if (Array.isArray(arr)) {
      filas = arr.slice(0, 7).map((it, i) => ({
        ok: String(it[0]) === "1",
        pais: String(it[1] || p).slice(0, 28),
        enun: trunc(String(it[2] || ""), 70),
        etapa: ETAPA_NOMBRE[i] || "Partido",
      }));
    }
  } catch (e) { /* sin lista */ }
  const d = DESENLACES[o] || DESENLACES.C;
  return { p, a, n, filas, ...d };
}

function ogHtml(d) {
  const filas = d.filas.map((f) => `
    <div style="display:flex;align-items:flex-start;margin-bottom:22px;">
      <div style="display:flex;font-size:42px;margin-right:22px;">${f.ok ? "✅" : "❌"}</div>
      <div style="display:flex;flex-direction:column;flex:1;">
        <div style="display:flex;font-size:22px;font-weight:700;letter-spacing:1px;color:rgba(255,255,255,0.55);margin-bottom:4px;">${esc(f.etapa.toUpperCase())} · ${esc(f.pais.toUpperCase())}</div>
        <div style="display:flex;font-size:31px;font-weight:600;color:white;line-height:1.18;">${esc(f.enun)}</div>
      </div>
    </div>`).join("");
  return `
  <div style="display:flex;flex-direction:column;width:${W}px;height:${H}px;padding:64px;background-color:#5b21b6;background-image:linear-gradient(135deg,#3a1078 0%,#7B2FF7 55%,#9d1f8e 100%);font-family:Montserrat;color:white;">
    <div style="display:flex;justify-content:center;font-size:30px;font-weight:700;letter-spacing:6px;color:rgba(255,255,255,0.85);">TRIVIAL MUNDIAL 2026</div>
    <div style="display:flex;justify-content:center;font-size:120px;margin-top:14px;">${d.emoji}</div>
    <div style="display:flex;justify-content:center;font-size:64px;font-weight:800;line-height:1.05;margin-top:4px;color:${d.accent};text-align:center;">${esc(d.titulo)}</div>
    <div style="display:flex;justify-content:center;font-size:34px;color:rgba(255,255,255,0.88);margin-top:8px;">${esc(d.p)} · ${d.a}/${d.n} aciertos</div>
    <div style="display:flex;width:100%;height:2px;background:rgba(255,255,255,0.18);margin:28px 0;"></div>
    <div style="display:flex;flex-direction:column;flex:1;">${filas}</div>
    <div style="display:flex;justify-content:center;font-size:26px;color:rgba(255,255,255,0.7);margin-top:8px;">Juega en trivial-mundial-2026.spacebom.com</div>
  </div>`;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const params = url.searchParams;
    const d = datos(params);

    if (url.pathname === "/og") {
      const texto =
        "TRIVIAL MUNDIAL 2026 Juega en trivial-mundial-2026.spacebom.com aciertos · " +
        d.p + " " + d.titulo + " " + d.filas.map((f) => f.etapa + " " + f.pais + " " + f.enun).join(" ") +
        " 0123456789/¡!¿?ÁÉÍÓÚÜÑáéíóúüabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
      let fonts = [];
      try {
        const data = await loadGoogleFont({ family: "Montserrat", weight: 800, text: texto });
        fonts = [{ name: "Montserrat", data, weight: 800, style: "normal" }];
      } catch (e) { /* fuente por defecto */ }
      return new ImageResponse(ogHtml(d), {
        width: W, height: H, fonts, emoji: "twemoji",
        headers: { "cache-control": "public, max-age=86400" },
      });
    }

    // Página de compartir: og:image dinámico + redirección al juego (conserva utm_*)
    const ogImg = url.origin + "/og" + url.search;
    const destino = JUEGO + url.search;
    const titulo = `${d.titulo} — Trivial Mundial 2026`;
    const desc = `${d.p}: ${d.a}/${d.n} aciertos. ¿Puedes superarme?`;
    const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(titulo)}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(titulo)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${esc(ogImg)}">
<meta property="og:image:width" content="${W}">
<meta property="og:image:height" content="${H}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(titulo)}">
<meta name="twitter:description" content="${esc(desc)}">
<meta name="twitter:image" content="${esc(ogImg)}">
<meta http-equiv="refresh" content="0;url=${esc(destino)}">
</head><body style="font-family:sans-serif;background:#2b0f4a;color:#fff;text-align:center;padding-top:48px">
<script>location.replace(${JSON.stringify(destino)})</script>
<p>Redirigiendo al Trivial Mundial 2026… <a style="color:#FFE45E" href="${esc(destino)}">Entrar</a></p>
</body></html>`;
    return new Response(html, {
      headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=300" },
    });
  },
};
