// Worker de "enlace para compartir" del Trivial Mundial 2026.
//
// Rutas (montadas en el propio dominio): trivial-mundial-2026.spacebom.com/s y /og
//   /s?p=&o=&a=&n=&r=  -> HTML con og:image (imagen ESTÁTICA por desenlace) + redirección al juego
//   /og?o=             -> 302 a la imagen estática del desenlace (compatibilidad con enlaces antiguos)
//
// IMPORTANTE: ya NO se renderiza ninguna imagen en el Worker. El plan Free de Cloudflare
// limita la CPU a 10 ms y rasterizar PNG con resvg-wasm consume ~250-290 ms -> daba 503
// intermitente (error 1102) y los crawlers (Twitter/WhatsApp) se quedaban sin imagen.
// Solución: 6 imágenes estáticas (res-C/F/S/Q/O/G.png) servidas por GitHub Pages, y aquí
// solo elegimos cuál según el desenlace. La portada (URL principal) es portada.png.

const JUEGO = "https://trivial-mundial-2026.spacebom.com/";

const DESENLACES = {
  C: "¡Campeón del Mundo!",
  G: "Eliminado en fase de grupos",
  O: "Eliminado en Octavos",
  Q: "Eliminado en Cuartos",
  S: "Semifinalista",
  F: "Subcampeón",
};

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function datos(params) {
  const p = (params.get("p") || "Mundial 2026").slice(0, 40);
  let o = (params.get("o") || "C").toUpperCase();
  if (!DESENLACES[o]) o = "C";
  const a = Math.max(0, parseInt(params.get("a") || "0", 10) || 0);
  const n = Math.max(1, parseInt(params.get("n") || "7", 10) || 7);
  return { p, o, a, n, titulo: DESENLACES[o] };
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const d = datos(url.searchParams);
    const imagen = `${url.origin}/res-${d.o}.png`; // estática (la sirve GitHub Pages)

    // Compatibilidad: enlaces antiguos a /og -> redirige a la imagen estática del desenlace.
    if (url.pathname === "/og" || url.pathname === "/og-home") {
      const destino = url.pathname === "/og-home" ? `${url.origin}/portada.png` : imagen;
      return Response.redirect(destino, 302);
    }

    // Página de compartir: og:image estático + redirección al juego (conserva utm_*)
    const destino = JUEGO + url.search;
    const titulo = `${d.titulo} — Trivial Mundial 2026`;
    const desc = `${d.p}: ${d.a}/${d.n} aciertos. ¿Puedes superarme?`;
    const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(titulo)}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(titulo)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${esc(imagen)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(titulo)}">
<meta name="twitter:description" content="${esc(desc)}">
<meta name="twitter:image" content="${esc(imagen)}">
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
