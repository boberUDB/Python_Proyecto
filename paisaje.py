"""
paisaje.py - Mapeo de ritmo de tecleo a siluetas de cordillera.

Este módulo es una librería pura (sin dependencias de Pygame) que transforma
una secuencia de eventos de teclado temporizados en coordenadas de curvas montañosas.
"""

from typing import List, Dict, Any, Tuple
import numpy as np


# ==============================================================================
# CONSTANTES DE CONFIGURACIÓN DEL PAISAJE
# ==============================================================================

# Ancho de la ventana deslizante (en segundos) para calcular la velocidad local de tecleo.
# Valores más bajos hacen la cordillera más dentada; valores más altos la hacen más ondulada.
VENTANA_VELOCIDAD_SEG: float = 1.2

# Umbral de pausa (en segundos). Si el lapso entre teclas supera este tiempo,
# se considera una interrupción del flujo y se forma un valle profundo.
UMBRAL_PAUSA_SEG: float = 1.2

# Factor de profundidad del valle según la duración de la pausa.
# Multiplica la duración excedente para hundir la altura hacia la base.
FACTOR_PROFUNDIDAD_VALLE: float = 0.65

# Ancho de la muesca provocada por una pulsación de tecla "borrar" (en proporción del ancho total).
ANCHO_GRIETA_RATIO: float = 0.007

# Profundidad de la grieta de borrado (fracción de la altura local a sustraer, entre 0 y 1).
PROFUNDIDAD_GRIETA: float = 0.50

# Ancho del aplanamiento generado por una tecla "enter" (en proporción del ancho total).
ANCHO_MESETA_RATIO: float = 0.025

# Desviación estándar (sigma en píxeles normalizados) para el filtro de suavizado gaussiano base.
SIGMA_SUAVIZADO: float = 4.0

# Proporción máxima de la altura de la ventana que ocupa la cumbre frontal (55% de la ventana).
ALTURA_MAXIMA_RATIO: float = 0.52

# Configuración de las 4 capas de siluetas (de fondo [capa 4] a frente [capa 1]):
# Cada tupla contiene:
# (proporcion_altura_picos, posicion_base_y, sigma_suavizado, desplazamiento_horizontal_x)
CONFIG_CAPAS: List[Tuple[float, float, float, float]] = [
    # Capa 4 (fondo lejano): montañas altas en el horizonte, muy suaves
    (0.42, 0.76, 10.0, -0.18),
    # Capa 3 (media lejana): colinas intermedias
    (0.46, 0.84, 7.0, 0.14),
    # Capa 2 (media cercana): cordillera prefrontal
    (0.48, 0.92, 4.5, -0.06),
    # Capa 1 (frente): silueta principal nítida con grietas
    (0.52, 1.00, 2.0, 0.00)
]


# ==============================================================================
# CÁLCULO DE ESTADÍSTICAS
# ==============================================================================

def calcular_estadisticas(eventos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula métricas clave del ritmo a partir de los eventos registrados:
    - teclas_por_minuto (PPM)
    - pausa_mas_larga (segundos)
    - num_borrados (conteo)
    - rafaga_mas_rapida (teclas por minuto en la mejor ventana de 2 segundos)
    - velocidad_promedio (teclas por segundo)
    """
    if not eventos:
        return {
            "total_teclas": 0,
            "tiempo_total": 0.0,
            "teclas_por_minuto": 0.0,
            "pausa_mas_larga": 0.0,
            "num_borrados": 0,
            "rafaga_mas_rapida": 0.0,
            "velocidad_promedio": 0.0
        }

    total_teclas = len(eventos)
    t_inicio = eventos[0]["t"]
    t_fin = eventos[-1]["t"]
    tiempo_total = max(t_fin - t_inicio, 0.5)

    num_borrados = sum(1 for e in eventos if e.get("tipo") == "borrar")
    deltas = [e.get("delta", 0.0) for e in eventos[1:]]
    pausa_mas_larga = max(deltas) if deltas else 0.0

    # Teclas por minuto globales
    tpm = (total_teclas / tiempo_total) * 60.0
    velocidad_promedio = total_teclas / tiempo_total

    # Ráfaga más rápida: calculamos la tasa máxima en ventanas móviles de 2 segundos
    tiempos = np.array([e["t"] - t_inicio for e in eventos])
    max_teclas_en_ventana = 1
    for t_actual in tiempos:
        # Contar teclas entre [t_actual, t_actual + 2.0]
        conteo = np.sum((tiempos >= t_actual) & (tiempos <= t_actual + 2.0))
        if conteo > max_teclas_en_ventana:
            max_teclas_en_ventana = conteo

    # Convertir ráfaga a PPM equivalente
    rafaga_ppm = (max_teclas_en_ventana / 2.0) * 60.0

    return {
        "total_teclas": int(total_teclas),
        "tiempo_total": float(round(tiempo_total, 2)),
        "teclas_por_minuto": float(round(tpm, 1)),
        "pausa_mas_larga": float(round(pausa_mas_larga, 2)),
        "num_borrados": int(num_borrados),
        "rafaga_mas_rapida": float(round(float(rafaga_ppm), 1)),
        "velocidad_promedio": float(round(velocidad_promedio, 2))
    }


# ==============================================================================
# GENERACIÓN DE LA CURVA DEL PAISAJE
# ==============================================================================

def _suavizado_gaussiano(curva: np.ndarray, sigma: float) -> np.ndarray:
    """Aplica un filtro gaussiano 1D unidimensional usando numpy."""
    if sigma <= 0.1:
        return curva.copy()
    radio = int(np.ceil(3 * sigma))
    x = np.arange(-radio, radio + 1)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    # Convolución con relleno por borde reflejado
    pad = np.pad(curva, radio, mode="edge")
    suavizada = np.convolve(pad, kernel, mode="same")
    return suavizada[radio:-radio]


def generar_curva_base(eventos: List[Dict[str, Any]], num_puntos: int) -> Tuple[np.ndarray, List[int], List[int]]:
    """
    Genera la señal de altura base normalizada [0.0, 1.0] a lo largo de `num_puntos`.
    Retorna:
    - curva_suave: la cordillera suavizada orgánicamente
    - indices_grietas: posiciones X donde ocurrieron borrados (para conservar muescas nítidas)
    - indices_mesetas: posiciones X donde hubo teclas Enter
    """
    if not eventos or num_puntos <= 1:
        # Curva suave por defecto si no hay eventos
        x = np.linspace(0, np.pi * 2, num_puntos)
        return (0.3 + 0.2 * np.sin(x)), [], []

    t_inicio = eventos[0]["t"]
    t_fin = eventos[-1]["t"]
    duracion = max(t_fin - t_inicio, 1.0)

    tiempos_eventos = np.array([e["t"] - t_inicio for e in eventos])
    tipos_eventos = [e.get("tipo", "caracter") for e in eventos]

    # Muestrear el tiempo uniformemente a lo largo del eje X
    t_muestras = np.linspace(0.0, duracion, num_puntos)
    alturas = np.zeros(num_puntos, dtype=np.float64)

    mitad_ventana = VENTANA_VELOCIDAD_SEG / 2.0

    # 1. Altura basada en la velocidad local continua (KDE orgánico por pulsación)
    # Cada pulsación aporta una curva suave gaussiana en el tiempo.
    # Ritmos veloces acumulan crestas elevadas; ritmos pausados crean colinas onduladas.
    sigma_pulso = 0.50  # dispersión temporal en segundos
    for t_ev in tiempos_eventos:
        # Solo calcular en el vecindario relevante (+- 3 sigmas) para máxima eficiencia
        mascara = np.abs(t_muestras - t_ev) <= (3.0 * sigma_pulso)
        if np.any(mascara):
            alturas[mascara] += np.exp(-0.5 * ((t_muestras[mascara] - t_ev) / sigma_pulso) ** 2)

    # 2. Valles para pausas > UMBRAL_PAUSA_SEG
    deltas = [e.get("delta", 0.0) for e in eventos]
    for idx in range(1, len(eventos)):
        delta = deltas[idx]
        if delta > UMBRAL_PAUSA_SEG:
            t_pausa_inicio = tiempos_eventos[idx - 1]
            t_pausa_fin = tiempos_eventos[idx]
            pausa_exceso = delta - UMBRAL_PAUSA_SEG
            factor_hundimiento = np.clip(pausa_exceso * FACTOR_PROFUNDIDAD_VALLE, 0.2, 0.85)

            # Hundir la curva gradualmente en ese rango temporal
            mascara_pausa = (t_muestras >= t_pausa_inicio) & (t_muestras <= t_pausa_fin)
            if np.any(mascara_pausa):
                alturas[mascara_pausa] *= (1.0 - factor_hundimiento)

    # 3. Identificar puntos de grietas (borrados) y mesetas (enter)
    indices_grietas = []
    indices_mesetas = []
    ancho_grieta_px = max(int(num_puntos * ANCHO_GRIETA_RATIO), 2)
    ancho_meseta_px = max(int(num_puntos * ANCHO_MESETA_RATIO), 4)

    for i, ev in enumerate(eventos):
        t_ev = tiempos_eventos[i]
        idx_x = int(np.clip((t_ev / duracion) * (num_puntos - 1), 0, num_puntos - 1))
        tipo = tipos_eventos[i]

        if tipo == "borrar":
            indices_grietas.append(idx_x)
        elif tipo == "enter":
            indices_mesetas.append(idx_x)

    # 4. Generar mesetas para saltos de línea (antes de suavizar para que se integren)
    for idx_m in indices_mesetas:
        x_min = max(0, idx_m - ancho_meseta_px // 2)
        x_max = min(num_puntos, idx_m + ancho_meseta_px // 2)
        valor_medio = np.mean(alturas[x_min:x_max])
        alturas[x_min:x_max] = valor_medio

    # 5. Suavizado orgánico con filtro gaussiano
    curva_suave = _suavizado_gaussiano(alturas, sigma=SIGMA_SUAVIZADO)

    # 6. Re-aplicar grietas afiladas y nítidas DESPUÉS del suavizado
    for idx_g in indices_grietas:
        r = ancho_grieta_px
        x_min = max(0, idx_g - r)
        x_max = min(num_puntos, idx_g + r + 1)
        for px in range(x_min, x_max):
            dist = abs(px - idx_g) / r
            factor_muesca = (1.0 - dist) * PROFUNDIDAD_GRIETA
            curva_suave[px] *= (1.0 - factor_muesca)

    # 7. Normalización dramática:
    # Dividimos por el máximo para que la cumbre más alta alcance 1.0,
    # permitiendo que el ritmo continuo mantenga una cresta alta y solo las pausas reales formen valles.
    val_max = np.max(curva_suave)
    if val_max > 1e-4:
        curva_norm = curva_suave / val_max
    else:
        curva_norm = np.ones_like(curva_suave) * 0.4

    # Asegurar rango [0.0, 1.0]
    curva_norm = np.clip(curva_norm, 0.0, 1.0)

    return curva_norm, indices_grietas, indices_mesetas


def calcular_todas_las_capas(eventos: List[Dict[str, Any]], ancho: int, alto: int) -> List[np.ndarray]:
    """
    Calcula las 4 capas de siluetas de montañas en coordenadas de pantalla Y (0 = arriba, alto = abajo).
    Retorna una lista de 4 arrays 1D de longitud `ancho`, ordenadas de fondo a frente:
    [capa_4 (fondo), capa_3, capa_2, capa_1 (frente)].
    """
    curva_norm, _, _ = generar_curva_base(eventos, ancho)

    capas = []

    for f_alt, base_ratio, sigma_extra, shift_ratio in CONFIG_CAPAS:
        # Aplicar desplazamiento horizontal para generar variación de crestas
        if abs(shift_ratio) > 1e-4:
            shift_px = int(shift_ratio * ancho)
            c = np.roll(curva_norm, shift_px)
        else:
            c = curva_norm.copy()

        # Suavizado extra para capas más lejanas
        if sigma_extra > 0.1:
            c = _suavizado_gaussiano(c, sigma=sigma_extra)

        base_y = alto * base_ratio
        h_montana = c * (alto * f_alt)
        y_capa = base_y - h_montana
        # Mantener dentro de los márgenes visuales
        y_capa = np.clip(y_capa, alto * 0.12, alto)
        capas.append(y_capa)

    return capas


# ==============================================================================
# GENERACIÓN DE DATOS SINTÉTICOS PARA MODO DEMO Y PRUEBAS
# ==============================================================================

def generar_datos_sinteticos(estilo: str = "rapido") -> List[Dict[str, Any]]:
    """
    Genera eventos sintéticos de tecleo para probar y afinar el paisaje.
    Estilos disponibles:
    - 'rapido': flujo constante, veloz, pocos descansos (Atardecer Cálido)
    - 'lento': tecleo espaciado con varias pausas largas > 1.5s (Amanecer Frío)
    - 'borrados': muchas correcciones y borrados consecutivos (Tormenta)
    """
    rng = np.random.default_rng(seed=42)
    eventos: List[Dict[str, Any]] = []
    t_actual = 0.0

    if estilo == "rapido":
        # 160 teclas en ~30 segundos, rítmico y consistente
        num_teclas = 175
        for i in range(num_teclas):
            delta = float(rng.uniform(0.10, 0.22))
            # Ocasional micro-pausa
            if i % 40 == 0 and i > 0:
                delta += 0.8
            t_actual += delta
            tipo = "espacio" if (i % 6 == 0) else ("enter" if (i % 65 == 0) else "caracter")
            eventos.append({"t": round(t_actual, 3), "tipo": tipo, "delta": round(delta, 3)})

    elif estilo == "lento":
        # Pocas teclas (~60) con pausas notables de 2.0s a 4.0s
        num_teclas = 65
        for i in range(num_teclas):
            # Pausas largas cada 10-12 teclas
            if i in [12, 25, 42, 55]:
                delta = float(rng.uniform(2.2, 4.0))
            else:
                delta = float(rng.uniform(0.40, 0.90))
            t_actual += delta
            tipo = "espacio" if (i % 5 == 0) else "caracter"
            eventos.append({"t": round(t_actual, 3), "tipo": tipo, "delta": round(delta, 3)})

    elif estilo == "borrados":
        # Escritura errática con frecuentes secuencias de backspace
        num_teclas = 140
        for i in range(num_teclas):
            delta = float(rng.uniform(0.12, 0.35))
            # Secuencias de borrado en bloques
            if 30 <= i <= 37 or 75 <= i <= 83 or 110 <= i <= 118:
                tipo = "borrar"
                delta = float(rng.uniform(0.08, 0.16))
            elif i % 5 == 0:
                tipo = "espacio"
            elif i == 60:
                tipo = "enter"
            else:
                tipo = "caracter"
            t_actual += delta
            eventos.append({"t": round(t_actual, 3), "tipo": tipo, "delta": round(delta, 3)})

    return eventos
