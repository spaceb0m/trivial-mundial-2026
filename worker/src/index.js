// Worker de "imagen dinámica de enlace" para el Trivial Mundial 2026.
//
// Rutas (montadas en el propio dominio): trivial-mundial-2026.spacebom.com/og y /s
//   /og?p=&o=&a=&n=&r=   -> PNG 1200x630 con el resultado (tarjeta ligera, sin fetches de emoji)
//   /s?...               -> HTML con og:image dinámico + redirección al juego
//
// IMPORTANTE: la imagen NO usa emojis (que requieren fetches externos a un CDN y hacían
// fallar el render para los crawlers). Solo depende de una fuente, con fallback. Así es
// fiable y la URL queda corta (sin los textos de las preguntas).

import { ImageResponse, loadGoogleFont } from "workers-og";

const JUEGO = "https://trivial-mundial-2026.spacebom.com/";
const W = 1200, H = 630;

const DESENLACES = {
  C: { titulo: "¡Campeón del Mundo!", accent: "#FFD24A" },
  G: { titulo: "Eliminado en fase de grupos", accent: "#FF8FA3" },
  O: { titulo: "Eliminado en Octavos", accent: "#FFC36B" },
  Q: { titulo: "Eliminado en Cuartos", accent: "#FFC36B" },
  S: { titulo: "Semifinalista", accent: "#8FE3FF" },
  F: { titulo: "Subcampeón", accent: "#CBD2FF" },
};

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function datos(params) {
  const p = (params.get("p") || "Mundial 2026").slice(0, 40);
  const o = (params.get("o") || "C").toUpperCase();
  const a = Math.max(0, parseInt(params.get("a") || "0", 10) || 0);
  const n = Math.max(1, parseInt(params.get("n") || "7", 10) || 7);
  const r = (params.get("r") || "").replace(/[^01]/g, "").slice(0, 7);
  const d = DESENLACES[o] || DESENLACES.C;
  return { p, a, n, r, titulo: d.titulo, accent: d.accent };
}

function ogHtml(d) {
  const dots = (d.r || "")
    .split("")
    .map((c) => `<div style="display:flex;width:54px;height:54px;border-radius:54px;margin-right:18px;background:${c === "1" ? "#22c55e" : "#f43f5e"};"></div>`)
    .join("");
  return `
  <div style="display:flex;flex-direction:column;width:${W}px;height:${H}px;padding:72px;background-color:#5b21b6;background-image:linear-gradient(135deg,#3a1078 0%,#7B2FF7 55%,#9d1f8e 100%);font-family:Montserrat;color:white;">
    <div style="display:flex;font-size:32px;font-weight:700;letter-spacing:7px;color:rgba(255,255,255,0.85);">TRIVIAL MUNDIAL 2026</div>
    <div style="display:flex;flex-direction:column;margin-top:auto;">
      <div style="display:flex;font-size:40px;color:rgba(255,255,255,0.9);">${esc(d.p)} · ${d.a}/${d.n} aciertos</div>
      <div style="display:flex;font-size:96px;font-weight:800;line-height:1.04;margin-top:8px;color:${d.accent};">${esc(d.titulo)}</div>
      <div style="display:flex;margin-top:38px;">${dots}</div>
    </div>
    <div style="display:flex;margin-top:34px;font-size:28px;color:rgba(255,255,255,0.7);">Juega en trivial-mundial-2026.spacebom.com</div>
  </div>`;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const params = url.searchParams;
    const d = datos(params);

    if (url.pathname === "/og") {
      const texto = "TRIVIAL MUNDIAL 2026 Juega en trivial-mundial-2026.spacebom.com aciertos · " +
        d.p + " " + d.titulo + " 0123456789/¡!¿?ÁÉÍÓÚÜÑáéíóúüabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
      let fonts = [];
      try {
        const data = await loadGoogleFont({ family: "Montserrat", weight: 800, text: texto });
        fonts = [{ name: "Montserrat", data, weight: 800, style: "normal" }];
      } catch (e) { /* fuente por defecto de workers-og */ }
      return new ImageResponse(ogHtml(d), {
        width: W, height: H, fonts,
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
