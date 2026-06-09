# 🏆 Trivial Mundial 2026

Juego de trivial web sobre la **Copa Mundial de Fútbol de 2026** (Canadá · México · Estados Unidos).
48 selecciones, 2.400 preguntas, **100% datos reales verificados**.

**▶️ Jugar:** https://spaceb0m.github.io/trivial-mundial-2026/

![World Cup 2026](https://img.shields.io/badge/Mundial-2026-7B2FF7) ![Selecciones](https://img.shields.io/badge/Selecciones-48-FF2E92) ![Preguntas](https://img.shields.io/badge/Preguntas-2400-00E5FF)

## Cómo se juega

- **Camino al título**: cada partida son **7 preguntas** = los 7 partidos para ser campeón.
  Fase de grupos (×3) → Octavos → Cuartos → Semifinal → Final, con **dificultad creciente**.
- **Dos modos**: jugar una selección concreta, o un **reto mezcla** de 7 selecciones al azar.
- Feedback inmediato y avance automático. Al terminar, ves todas tus respuestas y puedes
  **compartir tu resultado** (con imagen) en WhatsApp, X y Telegram.

## Cómo está hecho

- **App** ([`index.html`](index.html)): una sola página. HTML + Tailwind (CDN) + JavaScript vanilla.
  Sin build ni backend: carga el JSON de preguntas con `fetch`.
- **Datos** ([`mundial-2026.json`](mundial-2026.json)): 48 selecciones y ~26 jugadores cada una
  (posición, edad, club), extraídos de Wikipedia.
- **Preguntas** ([`preguntas-mundial-2026.json`](preguntas-mundial-2026.json)): 48 × 50 = 2.400,
  generadas por [`generar-preguntas.py`](generar-preguntas.py).

### Método anti-alucinación

Las preguntas **no se inventan**: un script determinista lee la respuesta correcta del dataset
verificado y muestrea los 3 distractores de valores reales del mismo campo (misma liga, familia
onomástica afín, edades cercanas…). Por construcción, la respuesta correcta nunca es falsa.
El banco pasó tres rondas de auditoría adversarial y verificación determinista.

## Ejecutar en local

```bash
python3 -m http.server 8000
# abre http://localhost:8000
```

(La app hace `fetch` del JSON, por eso necesita servirse por HTTP; no funciona abriendo el
archivo con `file://`.)

## Regenerar las preguntas

```bash
python3 generar-preguntas.py
```

Es 100% reproducible (misma entrada → mismo `preguntas-mundial-2026.json`).
