// Worker de "imagen dinámica de enlace" para el Trivial Mundial 2026.
//
// Rutas (montadas en el propio dominio): trivial-mundial-2026.spacebom.com/og y /s
//   /og?p=&o=&a=&n=&r=   -> PNG con el resultado (tarjeta ligera, sin fetches de emoji)
//   /s?...               -> HTML con og:image dinámico + redirección al juego
//
// PLAN FREE: el límite de CPU es 10 ms. Rasterizar a 1200x630 lo supera de forma
// intermitente (error 1102 / exceededCpu). Por eso renderizamos a 600x315 (1/4 de
// píxeles, ~1/4 de CPU) y además cacheamos el PNG en el edge: solo el primer render
// paga el coste, el resto se sirve desde caché. La imagen de la URL principal es
// estática (share-default.png en GitHub Pages), no pasa por aquí.

import { ImageResponse, loadGoogleFont } from "workers-og";

const JUEGO = "https://trivial-mundial-2026.spacebom.com/";
const W = 600, H = 315; // 1.905:1, válido para Twitter/Facebook large image.

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
    .map((c) => `<div style="display:flex;width:27px;height:27px;border-radius:27px;margin-right:9px;background:${c === "1" ? "#22c55e" : "#f43f5e"};"></div>`)
    .join("");
  return `
  <div style="display:flex;flex-direction:column;width:${W}px;height:${H}px;padding:36px;background-color:#5b21b6;background-image:linear-gradient(135deg,#3a1078 0%,#7B2FF7 55%,#9d1f8e 100%);font-family:Montserrat;color:white;">
    <div style="display:flex;font-size:16px;font-weight:700;letter-spacing:4px;color:rgba(255,255,255,0.85);">TRIVIAL MUNDIAL 2026</div>
    <div style="display:flex;flex-direction:column;margin-top:auto;">
      <div style="display:flex;font-size:20px;color:rgba(255,255,255,0.9);">${esc(d.p)} · ${d.a}/${d.n} aciertos</div>
      <div style="display:flex;font-size:48px;font-weight:800;line-height:1.04;margin-top:4px;color:${d.accent};">${esc(d.titulo)}</div>
      <div style="display:flex;margin-top:19px;">${dots}</div>
    </div>
    <div style="display:flex;margin-top:17px;font-size:14px;color:rgba(255,255,255,0.7);">Juega en trivial-mundial-2026.spacebom.com</div>
  </div>`;
}

// Imagen OG por defecto (fallback del Worker; la home usa el PNG estático).
function ogHome() {
  const dots = Array.from({ length: 7 })
    .map((_, i) => `<div style="display:flex;width:24px;height:24px;border-radius:24px;margin-right:8px;background:${i === 6 ? "#FFE45E" : "rgba(255,255,255,0.35)"};"></div>`)
    .join("");
  return `
  <div style="display:flex;flex-direction:column;width:${W}px;height:${H}px;padding:40px;background-color:#5b21b6;background-image:linear-gradient(135deg,#3a1078 0%,#7B2FF7 55%,#9d1f8e 100%);font-family:Montserrat;color:white;">
    <div style="display:flex;font-size:17px;font-weight:700;letter-spacing:5px;color:rgba(255,255,255,0.85);">TRIVIAL · MUNDIAL 2026</div>
    <div style="display:flex;flex-direction:column;margin-top:auto;">
      <div style="display:flex;font-size:52px;font-weight:800;line-height:1.0;">¿Llegas a</div>
      <div style="display:flex;font-size:64px;font-weight:800;line-height:1.0;color:#FFE45E;">CAMPEÓN?</div>
      <div style="display:flex;margin-top:18px;font-size:20px;color:rgba(255,255,255,0.92);">48 selecciones · 2.400 preguntas · 7 partidos</div>
      <div style="display:flex;margin-top:20px;">${dots}</div>
    </div>
    <div style="display:flex;margin-top:18px;font-size:14px;color:rgba(255,255,255,0.7);">Juega en trivial-mundial-2026.spacebom.com</div>
  </div>`;
}

async function render(html, texto) {
  let fonts = [];
  try {
    const data = await loadGoogleFont({ family: "Montserrat", weight: 800, text: texto });
    fonts = [{ name: "Montserrat", data, weight: 800, style: "normal" }];
  } catch (e) { /* fuente por defecto de workers-og */ }
  return new ImageResponse(html, {
    width: W, height: H, fonts,
    headers: { "cache-control": "public, max-age=31536000, immutable" },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const params = url.searchParams;
    const d = datos(params);

    // Imagen PNG: cacheamos en el edge por (path + parámetros de resultado), así solo
    // el primer crawler paga el render y el resto (reintentos de Twitter/FB) va a caché.
    if (url.pathname === "/og" || url.pathname === "/og-home") {
      const home = url.pathname === "/og-home";
      const cacheUrl = new URL(url.origin + url.pathname);
      if (!home) ["p", "o", "a", "n", "r"].forEach((k) => { if (params.get(k)) cacheUrl.searchParams.set(k, params.get(k)); });
      const cacheKey = new Request(cacheUrl.toString());
      const cache = caches.default;
      const hit = await cache.match(cacheKey);
      if (hit) return hit;

      const texto = home
        ? "TRIVIAL · MUNDIAL 2026 ¿Llegas a CAMPEÓN? 48 selecciones · 2.400 preguntas · 7 partidos Juega en trivial-mundial-2026.spacebom.com ¡!¿?ÁÉÍÓÚÜÑáéíóúüabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        : "TRIVIAL MUNDIAL 2026 Juega en trivial-mundial-2026.spacebom.com aciertos · " + d.p + " " + d.titulo + " 0123456789/¡!¿?ÁÉÍÓÚÜÑáéíóúüabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
      const resp = await render(home ? ogHome() : ogHtml(d), texto);
      ctx.waitUntil(cache.put(cacheKey, resp.clone()));
      return resp;
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
