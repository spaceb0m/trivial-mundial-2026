#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador determinista de preguntas de trivial para el Mundial 2026.

Método anti-alucinación: NO se inventan datos. La respuesta correcta de cada
pregunta se lee directamente de mundial-2026.json (ya verificado) y los 3
distractores se muestrean de valores REALES del mismo campo en el dataset.
Por construcción, la respuesta correcta nunca puede ser falsa y ningún
distractor puede coincidir con ella.

Las plantillas incorporan las mejoras de la auditoría adversarial:
- distractores plausibles (misma liga, misma familia onomástica, edades cercanas)
- sin preguntas ambiguas (empates de edad, nombres duplicados entre selecciones)
- enunciado único por quiz y caps por plantilla (sin repeticiones)
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).parent
ENTRADA = BASE / "mundial-2026.json"
SALIDA = BASE / "preguntas-mundial-2026.json"

PREGUNTAS_POR_SELECCION = 50

CATEGORIAS = {"clubes", "edades", "posiciones", "convocatoria", "agregados"}
DIFICULTADES = {"facil", "media", "dificil"}

POSICIONES_CANON = ["Portero", "Defensa", "Centrocampista", "Delantero"]

# Familias onomástico-regionales: agrupan selecciones cuyos nombres "suenan"
# parecido, para que los distractores/intrusos de las preguntas de convocatoria
# no se delaten por el idioma del nombre. Se agrupan solo selecciones de
# onomástica REALMENTE similar; las onomásticamente únicas en el torneo quedan
# aisladas a propósito (Corea, Japón, Sudáfrica, Irán, Francia, Turquía,
# Uzbekistán) y para ellas se omiten T8/T9 en vez de delatar con un pool dispar.
FAMILIAS = {
    "hispano": ["México", "Paraguay", "Ecuador", "España", "Uruguay", "Argentina", "Colombia", "Panamá"],
    "lusofono": ["Brasil", "Portugal", "Cabo Verde"],
    "arabe": ["Catar", "Marruecos", "Túnez", "Egipto", "Arabia Saudita", "Irak", "Jordania", "Argelia"],
    "sureslavo": ["Bosnia y Herzegovina", "Croacia"],  # apellidos -ić/-ović
    "germanico": ["Alemania", "Suiza", "Austria", "Países Bajos", "Bélgica"],
    "nordico": ["Suecia", "Noruega"],
    "britanico": ["Escocia", "Inglaterra"],  # islas británicas
    "africa_oeste": ["Costa de Marfil", "Senegal", "Ghana", "República Democrática del Congo"],
    # Onomásticamente aisladas o demasiado heterogéneas (T8/T9 se omiten):
    # checo (distinto del sur-eslavo); selecciones de inmigración con plantillas
    # muy mixtas (EE.UU., Canadá, Australia, N. Zelanda) donde ningún pool afín
    # camufla; y onomásticas únicas en el torneo.
    "checo": ["República Checa"],
    "estados_unidos": ["Estados Unidos"],
    "canada": ["Canadá"],
    "australia": ["Australia"],
    "nueva_zelanda": ["Nueva Zelanda"],
    "haiti": ["Haití"],
    "curazao": ["Curazao"],
    "africa_austral": ["Sudáfrica"],
    "corea": ["Corea del Sur"],
    "japon": ["Japón"],
    "persa": ["Irán"],
    "francofono": ["Francia"],
    "turco": ["Turquía"],
    "asia_central": ["Uzbekistán"],
}
PAIS_FAMILIA = {pais: fam for fam, paises in FAMILIAS.items() for pais in paises}

# Pool afín mínimo (nombres distintos) para emitir preguntas de convocatoria.
MIN_POOL_FAMILIA = 6

# Máximo de preguntas de cada plantilla por quiz (controla mezcla y repetición).
CAPS_PLANTILLA = {
    "t1_club": 14, "t2_quien_club": 6, "t3_paisclub": 10,
    "t4_posicion": 5, "t5_quien_pos": 4,
    "t6_edad": 8, "t7_entre_cuatro": 2,
    "t8_no_conv": 1, "t9_si_conv": 1,
    "t11_extremo": 2, "t12_conteo_pos": 3, "t13_conteo_pais": 5,
}

# Cuota orientativa por categoría (se rellena hasta 50 con el resto).
CUOTA_CATEGORIA = {
    "clubes": 18, "posiciones": 8, "edades": 9,
    "convocatoria": 2, "agregados": 9,
}


def cargar_datos():
    with open(ENTRADA, encoding="utf-8") as f:
        return json.load(f)


def _fmt(nombre):
    """Clase de formato de un nombre: 'mono' (un token) o 'multi'."""
    return "mono" if len(nombre.strip().split()) == 1 else "multi"


def sample_weighted(items_pesos, k, rng):
    """Muestreo sin reemplazo ponderado por peso (Efraimidis-Spirakis)."""
    keyed = []
    for it, w in items_pesos:
        w = max(float(w), 1e-9)
        keyed.append((rng.random() ** (1.0 / w), it))
    keyed.sort(reverse=True)
    return [it for _, it in keyed[:k]]


def elegir_distractores_jugadores(correcto, pool, rng, n=3):
    """Elige n distractores de un pool de nombres, prefiriendo el mismo
    formato (mono/multi) que el correcto para que el 'bicho raro' tipográfico
    no delate la respuesta."""
    fc = _fmt(correcto)
    mismo = [x for x in pool if x != correcto and _fmt(x) == fc]
    otros = [x for x in pool if x != correcto and _fmt(x) != fc]
    rng.shuffle(mismo)
    rng.shuffle(otros)
    elegidos = mismo[:n]
    if len(elegidos) < n:
        elegidos += otros[: n - len(elegidos)]
    return elegidos


def pregunta(rng, plantilla, categoria, dificultad, enunciado, correcta, distractores):
    """Construye una pregunta con 4 opciones barajadas. Devuelve None si no
    hay 3 distractores válidos (distintos entre sí y de la correcta)."""
    correcta = str(correcta)
    vistos = {correcta}
    limpios = []
    for d in distractores:
        d = str(d)
        if d not in vistos:
            vistos.add(d)
            limpios.append(d)
    if len(limpios) < 3:
        return None
    elegidos = rng.sample(limpios, 3) if len(limpios) > 3 else limpios[:3]
    opciones = elegidos + [correcta]
    rng.shuffle(opciones)
    return {
        "_plantilla": plantilla,
        "categoria": categoria,
        "dificultad": dificultad,
        "enunciado": enunciado,
        "opciones": opciones,
        "respuesta_correcta": opciones.index(correcta),
    }


def generar_candidatas(seleccion, datos, rng):
    pais = seleccion["pais"]
    jugadores = seleccion["jugadores"]
    nombres_equipo = {j["nombre"] for j in jugadores}

    # ---- Pools globales (valores reales de TODO el dataset) ----
    todos_clubes = []
    clubes_por_pais = defaultdict(set)
    paises_club = []
    paises_sel = []
    jugadores_otras_sel = []  # (nombre, pais_seleccion)
    for s in datos["selecciones"]:
        paises_sel.append(s["pais"])
        for j in s["jugadores"]:
            cl = j["club"]["nombre"]
            pc = j["club"]["pais"]
            todos_clubes.append(cl)
            clubes_por_pais[pc].add(cl)
            paises_club.append(pc)
            if s["pais"] != pais:
                jugadores_otras_sel.append((j["nombre"], s["pais"]))
    clubes_unicos = set(todos_clubes)
    freq_pais_club = Counter(paises_club)

    # Máximo real de jugadores por posición en cualquier convocatoria (techo
    # para que los distractores de conteo nunca sean estructuralmente imposibles).
    max_pos = Counter()
    for s in datos["selecciones"]:
        cnt = Counter(j["posicion"] for j in s["jugadores"])
        for p, n in cnt.items():
            if n > max_pos[p]:
                max_pos[p] = n

    # Distractores onomásticamente afines (misma familia que esta selección).
    fam = PAIS_FAMILIA.get(pais)
    companeras = set(FAMILIAS.get(fam, [])) - {pais}
    externos_familia = sorted({n for (n, p) in jugadores_otras_sel
                               if p in companeras and n not in nombres_equipo})
    # Solo hay camuflaje onomástico si la familia aporta pool afín suficiente.
    familia_ok = len(externos_familia) >= MIN_POOL_FAMILIA

    candidatas = []

    # ============ CLUBES ============
    # T1: ¿En qué club juega [jugador]?  (distractores de la misma liga)
    for j in jugadores:
        club = j["club"]["nombre"]
        pc = j["club"]["pais"]
        # sorted() antes de barajar: el orden de iteración de un set de strings
        # varía entre procesos (hash aleatorio), así random.Random(pais) deja de
        # ser reproducible. Ordenar primero garantiza determinismo real.
        misma_liga = sorted(c for c in clubes_por_pais[pc] if c != club)
        rng.shuffle(misma_liga)
        distr = misma_liga[:3]
        # Fallback al pool global SOLO si la liga (país) tiene <3 clubes en el dataset.
        if len(distr) < 3:
            resto = sorted(c for c in clubes_unicos if c != club and c not in distr)
            rng.shuffle(resto)
            distr += resto[: 3 - len(distr)]
        q = pregunta(rng, "t1_club", "clubes", "media",
                     f"¿En qué club juega {j['nombre']}?", club, distr)
        if q:
            candidatas.append(q)

    # T2: ¿Cuál de estos jugadores de [país] milita en [club]?
    clubes_equipo = defaultdict(list)
    for j in jugadores:
        clubes_equipo[j["club"]["nombre"]].append(j["nombre"])
    for club, jugs in clubes_equipo.items():
        correcta = rng.choice(jugs)
        pool = [j["nombre"] for j in jugadores if j["club"]["nombre"] != club]
        distr = elegir_distractores_jugadores(correcta, pool, rng)
        q = pregunta(rng, "t2_quien_club", "clubes", "media",
                     f"¿Cuál de estos jugadores de {pais} milita en {club}?",
                     correcta, distr)
        if q:
            candidatas.append(q)

    # T3: ¿En qué país juega [jugador] a nivel de clubes?
    #     Solo jugadores que militan en el EXTRANJERO (si juega en su país la
    #     respuesta es trivial y crea la heurística "marca el país local").
    #     Distractores: países de club ponderados por frecuencia real, excluido
    #     el país de la selección para no dejar ninguna pista de patrón.
    for j in jugadores:
        pc = j["club"]["pais"]
        if pc == pais:
            continue
        cand = [(p, w) for p, w in freq_pais_club.items() if p != pc and p != pais]
        distr = sample_weighted(cand, 3, rng)
        q = pregunta(rng, "t3_paisclub", "clubes", "dificil",
                     f"¿En qué país juega {j['nombre']} a nivel de clubes?",
                     pc, distr)
        if q:
            candidatas.append(q)

    # ============ POSICIONES ============
    # T4: ¿En qué posición juega [jugador]?
    for j in jugadores:
        pos = j["posicion"]
        otras = [p for p in POSICIONES_CANON if p != pos]
        q = pregunta(rng, "t4_posicion", "posiciones", "facil",
                     f"¿En qué posición juega {j['nombre']}?", pos, otras)
        if q:
            candidatas.append(q)

    # T5: ¿Cuál de estos jugadores de [país] juega de [posición]?
    por_posicion = defaultdict(list)
    for j in jugadores:
        por_posicion[j["posicion"]].append(j["nombre"])
    for pos, jugs in por_posicion.items():
        correcta = rng.choice(jugs)
        pool = [j["nombre"] for j in jugadores if j["posicion"] != pos]
        distr = elegir_distractores_jugadores(correcta, pool, rng)
        q = pregunta(rng, "t5_quien_pos", "posiciones", "facil",
                     f"¿Cuál de estos jugadores de {pais} juega de {pos.lower()}?",
                     correcta, distr)
        if q:
            candidatas.append(q)

    # ============ EDADES ============
    # T6: ¿Qué edad tiene [jugador]?  (distractores a >=2 años)
    for j in jugadores:
        edad = j["edad"]
        cercanas = [e for e in range(edad - 5, edad + 6) if e > 0 and abs(e - edad) >= 2]
        q = pregunta(rng, "t6_edad", "edades", "media",
                     f"¿Qué edad tiene {j['nombre']} al inicio del Mundial?",
                     edad, cercanas)
        if q:
            candidatas.append(q)

    # T7: Entre estos cuatro, ¿quién es el más joven / de más edad?
    #     Excluye el extremo opuesto del pool y exige brecha >=3 (respuesta única).
    if len(jugadores) >= 6:
        ordenados = sorted(jugadores, key=lambda m: m["edad"])
        for modo, etiqueta in (("mayor", "de más edad"), ("joven", "más joven")):
            pool = ordenados[3:] if modo == "mayor" else ordenados[:-3]
            generadas = 0
            intentos = 0
            while generadas < 1 and intentos < 40:
                intentos += 1
                if len(pool) < 4:
                    break
                muestra = rng.sample(pool, 4)
                edades_ord = sorted(m["edad"] for m in muestra)
                brecha = (edades_ord[-1] - edades_ord[-2]) if modo == "mayor" \
                    else (edades_ord[1] - edades_ord[0])
                if brecha < 3:
                    continue
                correcto = max(muestra, key=lambda m: m["edad"]) if modo == "mayor" \
                    else min(muestra, key=lambda m: m["edad"])
                opciones = [m["nombre"] for m in muestra]
                rng.shuffle(opciones)
                candidatas.append({
                    "_plantilla": "t7_entre_cuatro",
                    "categoria": "edades", "dificultad": "media",
                    "enunciado": f"Entre estos jugadores de {pais}, ¿quién es el {etiqueta}?",
                    "opciones": opciones,
                    "respuesta_correcta": opciones.index(correcto["nombre"]),
                })
                generadas += 1

    # ============ CONVOCATORIA ============
    # T8/T9 solo se emiten si la familia onomástica aporta pool afín; las
    # selecciones aisladas (Corea, Japón, Sudáfrica, Irán...) las omiten, porque
    # cualquier intruso/distractor se delataría por la forma del nombre.
    # T8: ¿Cuál NO está convocado? (intruso afín y del formato dominante del equipo)
    if familia_ok and len(jugadores) >= 3:
        fmt_equipo = Counter(_fmt(j["nombre"]) for j in jugadores).most_common(1)[0][0]
        reales_fmt = [j["nombre"] for j in jugadores if _fmt(j["nombre"]) == fmt_equipo]
        base_reales = reales_fmt if len(reales_fmt) >= 3 else [j["nombre"] for j in jugadores]
        intrusos = [n for n in externos_familia if _fmt(n) == fmt_equipo] or externos_familia
        usados = set()
        for _ in range(6):
            libres = [n for n in intrusos if n not in usados]
            if not libres or len(base_reales) < 3:
                break
            externo = rng.choice(libres)
            usados.add(externo)
            opciones = rng.sample(base_reales, 3) + [externo]
            rng.shuffle(opciones)
            candidatas.append({
                "_plantilla": "t8_no_conv",
                "categoria": "convocatoria", "dificultad": "media",
                "enunciado": f"¿Cuál de estos jugadores NO está convocado por {pais}?",
                "opciones": opciones,
                "respuesta_correcta": opciones.index(externo),
            })

    # T9: ¿Quién fue convocado por [país]? (distractores afines y del formato de la correcta)
    if familia_ok and jugadores:
        for _ in range(6):
            real = rng.choice([j["nombre"] for j in jugadores])
            distr = elegir_distractores_jugadores(real, externos_familia, rng)
            if len(set(distr)) < 3:
                break
            opciones = distr + [real]
            rng.shuffle(opciones)
            candidatas.append({
                "_plantilla": "t9_si_conv",
                "categoria": "convocatoria", "dificultad": "facil",
                "enunciado": f"De esta lista, ¿quién fue convocado por {pais} para el Mundial?",
                "opciones": opciones,
                "respuesta_correcta": opciones.index(real),
            })

    # ============ AGREGADOS ============
    # T11: más joven / de más edad de TODA la convocatoria (sin empate; distractores cercanos)
    if len(jugadores) >= 4:
        for clave, etiqueta in (("min", "más joven"), ("max", "de más edad")):
            edades = [j["edad"] for j in jugadores]
            objetivo = min(edades) if clave == "min" else max(edades)
            empatados = [j for j in jugadores if j["edad"] == objetivo]
            if len(empatados) != 1:
                continue  # empate -> respuesta no única, se descarta
            correcto = empatados[0]
            resto = [j for j in jugadores if j["nombre"] != correcto["nombre"]]
            resto.sort(key=lambda j: abs(j["edad"] - correcto["edad"]))
            cercanos = [j["nombre"] for j in resto[:8]]
            distr = elegir_distractores_jugadores(correcto["nombre"], cercanos, rng)
            q = pregunta(rng, "t11_extremo", "agregados", "media",
                         f"¿Quién es el jugador {etiqueta} de la convocatoria de {pais}?",
                         correcto["nombre"], distr)
            if q:
                candidatas.append(q)

    # T12: ¿Cuántos [defensas/centrocampistas/delanteros]? (sin porteros)
    #      Distractores en una ventana realista ALREDEDOR del valor correcto, así
    #      nunca aparecen recuentos absurdos (10-11 delanteros) ni un relleno fijo.
    conteo_pos = Counter(j["posicion"] for j in jugadores)
    for pos, n in conteo_pos.items():
        if pos == "Portero":
            continue  # casi siempre 3: acierto gratuito, no discrimina
        techo = max_pos.get(pos, n + 3)
        cercanos = [c for c in range(max(3, n - 3), min(techo, n + 3) + 1) if c != n]
        q = pregunta(rng, "t12_conteo_pos", "agregados", "dificil",
                     f"¿Cuántos {pos.lower()}s tiene la convocatoria de {pais}?",
                     n, cercanos)
        if q:
            candidatas.append(q)

    # T13: ¿Cuántos militan en clubes de [país]? (solo conteos notables n>=3; sin el 0)
    conteo_paisclub = Counter(j["club"]["pais"] for j in jugadores)
    for pc, n in conteo_paisclub.items():
        if n < 3:
            continue
        cercanos = [c for c in range(max(1, n - 3), n + 4) if c != n]
        q = pregunta(rng, "t13_conteo_pais", "agregados", "dificil",
                     f"¿Cuántos jugadores de {pais} militan en clubes de {pc}?",
                     n, cercanos)
        if q:
            candidatas.append(q)

    return candidatas


def seleccionar_50(candidatas, rng):
    """Enunciado único por quiz + caps por plantilla + cuota por categoría."""
    rng.shuffle(candidatas)

    # 1) Enunciado único.
    vistos = set()
    unicas = []
    for q in candidatas:
        if q["enunciado"] in vistos:
            continue
        vistos.add(q["enunciado"])
        unicas.append(q)

    # 2) Cap por plantilla.
    por_plantilla = defaultdict(list)
    for q in unicas:
        por_plantilla[q["_plantilla"]].append(q)
    capadas = []
    for t, items in por_plantilla.items():
        capadas.extend(items[: CAPS_PLANTILLA.get(t, len(items))])

    # 3) Cuota por categoría.
    por_cat = defaultdict(list)
    for q in capadas:
        por_cat[q["categoria"]].append(q)
    for c in por_cat:
        rng.shuffle(por_cat[c])

    seleccion = []
    elegidos = set()
    for c, quota in CUOTA_CATEGORIA.items():
        for q in por_cat[c][:quota]:
            seleccion.append(q)
            elegidos.add(id(q))

    # 4) Rellenar hasta 50: primero con el resto capado (respeta la mezcla);
    #    si aún falta (selecciones de liga muy local, con poco T3/T13), los caps
    #    se vuelven blandos y se completa con el resto de enunciados únicos.
    def rellenar(fuente):
        for q in fuente:
            if len(seleccion) >= PREGUNTAS_POR_SELECCION:
                break
            if id(q) in elegidos:
                continue
            seleccion.append(q)
            elegidos.add(id(q))

    resto = [q for q in capadas if id(q) not in elegidos]
    rng.shuffle(resto)
    rellenar(resto)
    if len(seleccion) < PREGUNTAS_POR_SELECCION:
        extra = [q for q in unicas if id(q) not in elegidos]
        rng.shuffle(extra)
        rellenar(extra)

    seleccion = seleccion[:PREGUNTAS_POR_SELECCION]
    rng.shuffle(seleccion)

    final = []
    for idx, q in enumerate(seleccion, start=1):
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
    sels = salida["selecciones"]
    assert len(sels) == 48, f"Esperadas 48 selecciones, hay {len(sels)}"
    for s in sels:
        pres = s["preguntas"]
        assert len(pres) == PREGUNTAS_POR_SELECCION, \
            f"{s['pais']}: {len(pres)} preguntas (esperadas {PREGUNTAS_POR_SELECCION})"
        enunciados = set()
        for q in pres:
            assert len(q["opciones"]) == 4, f"{s['pais']} q{q['id']}: no tiene 4 opciones"
            assert len(set(q["opciones"])) == 4, f"{s['pais']} q{q['id']}: opciones duplicadas"
            assert 0 <= q["respuesta_correcta"] <= 3, f"{s['pais']} q{q['id']}: índice inválido"
            assert q["categoria"] in CATEGORIAS, f"{s['pais']} q{q['id']}: categoría inválida"
            assert q["dificultad"] in DIFICULTADES, f"{s['pais']} q{q['id']}: dificultad inválida"
            assert q["enunciado"] not in enunciados, \
                f"{s['pais']} q{q['id']}: enunciado repetido -> {q['enunciado']}"
            enunciados.add(q["enunciado"])
    print("✓ Verificación superada: 48×50, 4 opciones únicas, enunciado único por quiz.")


def main():
    datos = cargar_datos()
    selecciones_salida = []
    incompletas = []

    for s in datos["selecciones"]:
        rng = random.Random(s["pais"])
        candidatas = generar_candidatas(s, datos, rng)
        preguntas = seleccionar_50(candidatas, rng)
        if len(preguntas) < PREGUNTAS_POR_SELECCION:
            incompletas.append((s["pais"], len(preguntas)))
        selecciones_salida.append({
            "pais": s["pais"],
            "bandera": s["bandera"],
            "preguntas": preguntas,
        })

    salida = {
        "torneo": datos["torneo"],
        "fecha_generacion": datos["fecha_generacion"],
        "total_selecciones": len(selecciones_salida),
        "preguntas_por_seleccion": PREGUNTAS_POR_SELECCION,
        "selecciones": selecciones_salida,
    }

    if incompletas:
        print("⚠ Selecciones que no alcanzaron 50 preguntas:")
        for pais, n in incompletas:
            print(f"   - {pais}: {n}")

    verificar(salida)

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    total = sum(len(s["preguntas"]) for s in selecciones_salida)
    print(f"✓ Escrito {SALIDA.name} — {len(selecciones_salida)} selecciones, {total} preguntas.")


if __name__ == "__main__":
    main()
