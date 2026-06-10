#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador determinista de preguntas para el modo "Leyendas del Mundial".

Mismo método anti-alucinación que generar-preguntas.py: NO se inventan datos.
La respuesta correcta de cada pregunta se lee directamente de mundial-historia.json
(ya verificado) y los distractores se muestrean de valores REALES del mismo campo
en el dataset. Por construcción, la respuesta correcta nunca puede ser falsa y
ningún distractor puede coincidir con ella.

Salida: preguntas-historia.json, una lista plana de preguntas con el esquema que
consume el front (id, categoria, dificultad, enunciado, opciones[4],
respuesta_correcta), para alimentar el modo de 7 rondas tipo torneo.
"""

import json
import random
from collections import Counter
from pathlib import Path

BASE = Path(__file__).parent
ENTRADA = BASE / "mundial-historia.json"
SALIDA = BASE / "preguntas-historia.json"

CATEGORIAS = {"ediciones", "palmares", "goleadores", "partidos", "premios"}
DIFICULTADES = {"facil", "media", "dificil"}

# Ediciones "recientes" => preguntas de premios algo más fáciles (memoria fresca).
RECIENTES = {2010, 2014, 2018, 2022}
# Campeón y sede de ediciones desde este año se consideran de cultura general (fácil).
ANIO_FACIL = 1990


def cargar():
    with open(ENTRADA, encoding="utf-8") as f:
        return json.load(f)


def pregunta(rng, categoria, dificultad, enunciado, correcta, distractores):
    """Construye una pregunta con 4 opciones únicas barajadas. Devuelve None si
    no hay 3 distractores válidos (distintos entre sí y de la correcta)."""
    correcta = str(correcta)
    vistos = {correcta}
    limpios = []
    for d in distractores:
        d = str(d)
        if d and d not in vistos:
            vistos.add(d)
            limpios.append(d)
    if len(limpios) < 3:
        return None
    elegidos = rng.sample(limpios, 3)
    opciones = elegidos + [correcta]
    rng.shuffle(opciones)
    return {
        "categoria": categoria,
        "dificultad": dificultad,
        "enunciado": enunciado,
        "opciones": opciones,
        "respuesta_correcta": opciones.index(correcta),
    }


def cercanos(valor, lo, hi):
    """Enteros alrededor de 'valor' (excluyéndolo) en el rango [lo, hi]."""
    return [c for c in range(lo, hi + 1) if c != valor]


def generar(datos, rng):
    ed = datos["ediciones"]
    pal = datos["palmares"]
    gol = datos["goleadores_historicos"]
    part = datos["mas_partidos"]

    # ----- Pools globales de valores REALES (para distractores) -----
    sedes = sorted({e["sede"] for e in ed})
    campeones = sorted({e["campeon"] for e in ed})
    finalistas = sorted({e["campeon"] for e in ed} | {e["subcampeon"] for e in ed})
    resultados = sorted({e["resultado_final"] for e in ed})
    anios = [e["anio"] for e in ed]
    # Selecciones que SÍ han sido campeonas (para el intruso "nunca campeón").
    nunca_campeon = sorted({p["seleccion"] for p in pal if not p["campeon"]})
    ganadores_balon = sorted({e["balon_oro"]["jugador"] for e in ed if e["balon_oro"]})
    todos_goleadores_ed = sorted({e["goleador"]["jugador"] for e in ed if e["goleador"]["jugador"]})

    qs = []

    # ===================== EDICIONES =====================
    for e in ed:
        a = e["anio"]
        dif_ed = "facil" if a >= ANIO_FACIL else "media"

        # ¿Qué selección ganó el Mundial de [año]?
        q = pregunta(rng, "ediciones", dif_ed,
                     f"¿Qué selección ganó el Mundial de {a}?",
                     e["campeon"], [c for c in campeones if c != e["campeon"]])
        if q: qs.append(q)

        # ¿En qué país se celebró el Mundial de [año]?
        q = pregunta(rng, "ediciones", dif_ed,
                     f"¿En qué país (o países) se celebró el Mundial de {a}?",
                     e["sede"], [s for s in sedes if s != e["sede"]])
        if q: qs.append(q)

        # ¿Quién fue subcampeón en [año]?
        q = pregunta(rng, "ediciones", "media",
                     f"¿Qué selección fue subcampeona del Mundial de {a}?",
                     e["subcampeon"], [c for c in finalistas if c != e["subcampeon"]])
        if q: qs.append(q)

        # ¿En qué año ganó [campeón] el Mundial de [sede]?
        q = pregunta(rng, "ediciones", "media",
                     f"¿En qué año ganó {e['campeon']} el Mundial celebrado en {e['sede']}?",
                     a, [x for x in anios if x != a])
        if q: qs.append(q)

        # ¿Cuál fue el resultado de la final de [año]? (difícil)
        q = pregunta(rng, "ediciones", "dificil",
                     f"¿Cuál fue el resultado de la final del Mundial de {a}?",
                     e["resultado_final"], [r for r in resultados if r != e["resultado_final"]])
        if q: qs.append(q)

    # ===================== PALMARÉS =====================
    conteo_campeon = {p["seleccion"]: len(p["campeon"]) for p in pal}
    campeonas = [p for p in pal if p["campeon"]]

    for p in pal:
        sel = p["seleccion"]
        n = len(p["campeon"])
        if n >= 1:
            # ¿Cuántas veces ha sido campeona del mundo [selección]?
            q = pregunta(rng, "palmares", "media",
                         f"¿Cuántas veces ha sido campeona del mundo {sel}?",
                         n, cercanos(n, max(1, n - 2), n + 3))
            if q: qs.append(q)

            # ¿En cuál de estos años se proclamó campeona [selección]?
            no_titulo = [x for x in anios if x not in p["campeon"]]
            q = pregunta(rng, "palmares", "dificil",
                         f"¿En cuál de estos años se proclamó campeona {sel}?",
                         rng.choice(p["campeon"]), no_titulo)
            if q: qs.append(q)

    # ¿Cuál de estas selecciones ha ganado más Mundiales? (4 con conteos distintos)
    for _ in range(8):
        muestra = rng.sample(campeonas, 4)
        conteos = [len(m["campeon"]) for m in muestra]
        top = max(conteos)
        if conteos.count(top) != 1:
            continue  # empate en el máximo -> respuesta no única
        ganadora = max(muestra, key=lambda m: len(m["campeon"]))
        opciones = [m["seleccion"] for m in muestra]
        rng.shuffle(opciones)
        qs.append({
            "categoria": "palmares", "dificultad": "dificil",
            "enunciado": "De estas selecciones, ¿cuál ha ganado más Copas del Mundo?",
            "opciones": opciones,
            "respuesta_correcta": opciones.index(ganadora["seleccion"]),
        })

    # ¿Cuál de estas selecciones NUNCA ha ganado un Mundial? (3 campeonas + 1 nunca)
    for _ in range(8):
        if len(nunca_campeon) < 1 or len(campeones) < 3:
            break
        intruso = rng.choice(nunca_campeon)
        q = pregunta(rng, "palmares", "media",
                     "¿Cuál de estas selecciones NUNCA ha ganado la Copa del Mundo?",
                     intruso, campeones)
        if q: qs.append(q)

    # ===================== GOLEADORES (históricos) =====================
    nombres_gol = [g["jugador"] for g in gol]
    for g in gol:
        # ¿Cuántos goles marcó [jugador] en la historia de los Mundiales?
        n = g["goles"]
        q = pregunta(rng, "goleadores", "dificil",
                     f"¿Cuántos goles marcó {g['jugador']} en la historia de los Mundiales?",
                     n, cercanos(n, n - 4, n + 4))
        if q: qs.append(q)

        # ¿De qué selección era [goleador]?
        otras = sorted({x["seleccion"] for x in gol if x["seleccion"] != g["seleccion"]})
        q = pregunta(rng, "goleadores", "media",
                     f"¿Con qué selección jugó {g['jugador']} en los Mundiales?",
                     g["seleccion"], otras)
        if q: qs.append(q)

    # ¿Quién es el máximo goleador en la historia de los Mundiales? (fácil; Klose)
    maximo = max(gol, key=lambda g: g["goles"])
    q = pregunta(rng, "goleadores", "facil",
                 "¿Quién es el máximo goleador en la historia de las Copas del Mundo?",
                 maximo["jugador"], [n for n in nombres_gol if n != maximo["jugador"]])
    if q: qs.append(q)

    # De estos jugadores, ¿quién marcó más goles? (4 con totales distintos)
    for _ in range(6):
        muestra = rng.sample(gol, 4)
        topg = max(m["goles"] for m in muestra)
        if [m["goles"] for m in muestra].count(topg) != 1:
            continue
        ganador = max(muestra, key=lambda m: m["goles"])
        opciones = [m["jugador"] for m in muestra]
        rng.shuffle(opciones)
        qs.append({
            "categoria": "goleadores", "dificultad": "media",
            "enunciado": "De estos jugadores, ¿quién marcó más goles en la historia de los Mundiales?",
            "opciones": opciones,
            "respuesta_correcta": opciones.index(ganador["jugador"]),
        })

    # ===================== PARTIDOS (más participaciones) =====================
    nombres_part = [m["jugador"] for m in part]
    for m in part:
        n = m["partidos"]
        q = pregunta(rng, "partidos", "dificil",
                     f"¿Cuántos partidos disputó {m['jugador']} en fases finales de Mundiales?",
                     n, cercanos(n, n - 4, n + 4))
        if q: qs.append(q)

    # ¿Qué jugador ha disputado más partidos en la historia de los Mundiales? (Messi)
    maxp = max(part, key=lambda m: m["partidos"])
    q = pregunta(rng, "partidos", "facil",
                 "¿Qué jugador ha disputado más partidos en la historia de los Mundiales?",
                 maxp["jugador"], [n for n in nombres_part if n != maxp["jugador"]])
    if q: qs.append(q)

    for _ in range(6):
        muestra = rng.sample(part, 4)
        topp = max(m["partidos"] for m in muestra)
        if [m["partidos"] for m in muestra].count(topp) != 1:
            continue
        ganador = max(muestra, key=lambda m: m["partidos"])
        opciones = [m["jugador"] for m in muestra]
        rng.shuffle(opciones)
        qs.append({
            "categoria": "partidos", "dificultad": "media",
            "enunciado": "De estos jugadores, ¿quién disputó más partidos en Mundiales?",
            "opciones": opciones,
            "respuesta_correcta": opciones.index(ganador["jugador"]),
        })

    # ===================== PREMIOS (por edición) =====================
    for e in ed:
        a = e["anio"]
        dif_base = "media" if a in RECIENTES else "dificil"

        # Balón de Oro
        if e["balon_oro"]:
            j = e["balon_oro"]["jugador"]
            q = pregunta(rng, "premios", dif_base,
                         f"¿Quién ganó el Balón de Oro al mejor jugador del Mundial de {a}?",
                         j, [x for x in ganadores_balon if x != j])
            if q: qs.append(q)
            # ¿De qué selección era el Balón de Oro de [año]?
            equipos_oro = sorted({e2["balon_oro"]["seleccion"] for e2 in ed if e2["balon_oro"]})
            q = pregunta(rng, "premios", "dificil",
                         f"¿De qué selección era {j}, Balón de Oro del Mundial de {a}?",
                         e["balon_oro"]["seleccion"], [s for s in equipos_oro if s != e["balon_oro"]["seleccion"]])
            if q: qs.append(q)

        # Máximo goleador (Bota de Oro) de la edición — solo si hubo goleador único
        g = e["goleador"]
        if g["jugador"]:
            q = pregunta(rng, "premios", dif_base,
                         f"¿Quién fue el máximo goleador (Bota de Oro) del Mundial de {a}?",
                         g["jugador"], [x for x in todos_goleadores_ed if x != g["jugador"]])
            if q: qs.append(q)
        # ¿Cuántos goles marcó el máximo goleador de [año]? (siempre answerable)
        goles_ed = sorted({e2["goleador"]["goles"] for e2 in ed})
        q = pregunta(rng, "premios", "dificil",
                     f"¿Cuántos goles marcó el máximo goleador del Mundial de {a}?",
                     g["goles"], [x for x in goles_ed if x != g["goles"]])
        if q: qs.append(q)

    return qs


def seleccionar(qs, rng):
    """Enunciado único en todo el pool, baraja, y asigna ids 1..N."""
    rng.shuffle(qs)
    vistos = set()
    unicas = []
    for q in qs:
        if q["enunciado"] in vistos:
            continue
        vistos.add(q["enunciado"])
        unicas.append(q)
    rng.shuffle(unicas)
    final = []
    for idx, q in enumerate(unicas, start=1):
        final.append({
            "id": idx,
            "categoria": q["categoria"],
            "dificultad": q["dificultad"],
            "enunciado": q["enunciado"],
            "opciones": q["opciones"],
            "respuesta_correcta": q["respuesta_correcta"],
        })
    return final


def verificar(salida):
    pres = salida["preguntas"]
    enunciados = set()
    por_dif = Counter()
    por_cat = Counter()
    for q in pres:
        assert len(q["opciones"]) == 4, f"q{q['id']}: no tiene 4 opciones"
        assert len(set(q["opciones"])) == 4, f"q{q['id']}: opciones duplicadas -> {q['opciones']}"
        assert 0 <= q["respuesta_correcta"] <= 3, f"q{q['id']}: índice inválido"
        assert q["categoria"] in CATEGORIAS, f"q{q['id']}: categoría inválida {q['categoria']}"
        assert q["dificultad"] in DIFICULTADES, f"q{q['id']}: dificultad inválida"
        assert q["enunciado"] not in enunciados, f"q{q['id']}: enunciado repetido -> {q['enunciado']}"
        enunciados.add(q["enunciado"])
        por_dif[q["dificultad"]] += 1
        por_cat[q["categoria"]] += 1
    # El modo de 7 rondas necesita >=3 fáciles, >=1 media y >=3 difíciles por partida.
    assert por_dif["facil"] >= 3, f"Muy pocas fáciles: {por_dif['facil']}"
    assert por_dif["media"] >= 1, f"Muy pocas medias: {por_dif['media']}"
    assert por_dif["dificil"] >= 3, f"Muy pocas difíciles: {por_dif['dificil']}"
    print(f"✓ Verificación superada: {len(pres)} preguntas, 4 opciones únicas, enunciado único.")
    print(f"  Dificultad: {dict(por_dif)}")
    print(f"  Categoría:  {dict(por_cat)}")


def main():
    datos = cargar()
    rng = random.Random("leyendas-mundial")  # semilla fija: salida reproducible
    candidatas = generar(datos, rng)
    preguntas = seleccionar(candidatas, rng)
    salida = {
        "modo": "Leyendas del Mundial",
        "fuente": datos["fuente"],
        "fecha_generacion": datos["fecha_generacion"],
        "total_preguntas": len(preguntas),
        "preguntas": preguntas,
    }
    verificar(salida)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"✓ Escrito {SALIDA.name} — {len(preguntas)} preguntas.")


if __name__ == "__main__":
    main()
