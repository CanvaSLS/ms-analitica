"""Semáforo de riesgo académico: 3 reglas simples, deterministas y explicables (sin IA).

Entrada  : resumen del alumno {promedio, n_tardias, caida_ultima}  (lo calcula ms-evaluaciones)
Salida   : (puntaje 0-100, nivel VERDE|AMBAR|ROJO, motivos[])
Umbrales : VERDE < 25 · AMBAR 25-49 · ROJO >= 50

Esta misma función está copiada en datos-seed/seed.py para que los datos sembrados
sean coherentes con lo que calculará el sistema en vivo.
"""


def calcular_riesgo(resumen):
    puntaje, motivos = 0, []
    prom = resumen.get("promedio")
    if prom is not None:
        if prom < 10.5:
            puntaje += 40
            motivos.append(f"R1 · promedio {float(prom):.1f} (menor a 10.5)")
        elif prom < 13:
            puntaje += 20
            motivos.append(f"R1 · promedio {float(prom):.1f} (menor a 13)")
    tard = int(resumen.get("n_tardias") or 0)
    if tard >= 2:
        puntaje += 20
        motivos.append(f"R2 · {tard} entregas tardías")
    elif tard == 1:
        puntaje += 10
        motivos.append("R2 · 1 entrega tardía")
    caida = resumen.get("caida_ultima") or 0
    if caida >= 8:
        puntaje += 35
        motivos.append(f"R3 · la última nota cayó {float(caida):.1f} pts bajo su promedio previo")
    elif caida >= 4:
        puntaje += 15
        motivos.append(f"R3 · la última nota cayó {float(caida):.1f} pts bajo su promedio previo")
    nivel = "ROJO" if puntaje >= 50 else "AMBAR" if puntaje >= 25 else "VERDE"
    return puntaje, nivel, motivos
