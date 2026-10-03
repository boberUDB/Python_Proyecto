"""
render.py - Motor gráfico para dibujar cielo, siluetas vectoriales en capas,
cuerpos celestes, animaciones de revelado y panel de estadísticas.
"""

import os
import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pygame

import paisaje
import paletas


# Cache de degradados del cielo para evitar recalcular cada fotograma
_CACHE_CIELOS: Dict[Tuple[int, int, Tuple[int, int, int], Tuple[int, int, int]], pygame.Surface] = {}


def obtener_degradado_cielo(ancho: int, alto: int, c_arriba: Tuple[int, int, int], c_abajo: Tuple[int, int, int]) -> pygame.Surface:
    """Genera o recupera de caché un degradado vertical suave del cielo."""
    clave = (ancho, alto, c_arriba, c_abajo)
    if clave in _CACHE_CIELOS:
        return _CACHE_CIELOS[clave]

    # Renderizamos a 1xalto y escalamos suavemente para máximo rendimiento y gradiente limpio
    tira = pygame.Surface((1, alto))
    r1, g1, b1 = c_arriba
    r2, g2, b2 = c_abajo

    for y in range(alto):
        prog = y / max(alto - 1, 1)
        # Curva de interpolación suave (smoothstep)
        t = prog * prog * (3 - 2 * prog)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        tira.set_at((0, y), (r, g, b))

    cielo = pygame.transform.smoothscale(tira, (ancho, alto))
    _CACHE_CIELOS[clave] = cielo
    return cielo


def dibujar_estrellas(superficie: pygame.Surface, paleta: Dict[str, Any], ancho: int, alto: int, semilla: int = 42) -> None:
    """Dibuja partículas o estrellas discretas en la parte superior del firmamento."""
    if not paleta.get("estrellas", False):
        return

    rng = np.random.default_rng(semilla)
    num_estrellas = int(ancho * 0.05)  # Aproximadamente 60-100 estrellas
    color_base = paleta.get("color_estrellas", (230, 240, 255))

    capa_estrellas = pygame.Surface((ancho, alto), pygame.SRCALPHA)

    for _ in range(num_estrellas):
        x = int(rng.uniform(0, ancho))
        # Concentradas en el 45% superior del cielo
        y = int(rng.uniform(10, alto * 0.42))
        alfa = int(rng.uniform(70, 220))
        radio = 1 if rng.uniform() > 0.15 else 2

        pygame.draw.circle(capa_estrellas, (*color_base, alfa), (x, y), radio)

    superficie.blit(capa_estrellas, (0, 0))


def dibujar_cuerpo_celeste(
    superficie: pygame.Surface,
    paleta: Dict[str, Any],
    stats: Dict[str, Any],
    ancho: int,
    alto: int,
    progreso_animacion: float = 1.0
) -> None:
    """
    Dibuja el sol o la luna con su halo lumínico.
    Su altura en el cielo depende de la velocidad promedio de escritura.
    """
    cuerpo = paleta.get("cuerpo_celeste", {})
    tipo = cuerpo.get("tipo", "sol")
    color = cuerpo.get("color", (255, 240, 200))
    resplandor = cuerpo.get("resplandor", (255, 200, 120, 70))

    # Posición horizontal fija y elegante (tercio izquierdo)
    cx = int(ancho * 0.28)

    # Posición vertical según velocidad promedio
    vel = stats.get("velocidad_promedio", 3.0)
    # Rango de velocidad esperada: 1.0 (lento) a 6.0 (rápido)
    factor_vel = np.clip((vel - 1.0) / 5.0, 0.0, 1.0)
    # A mayor velocidad, más alto en el cielo
    y_min = alto * 0.16
    y_max = alto * 0.42
    cy_objetivo = y_max - (y_max - y_min) * factor_vel

    # Suave aparición durante la animación
    cy = int(cy_objetivo + (1.0 - min(progreso_animacion, 1.0)) * 60)

    radio_base = int(alto * 0.052)
    superficie_halo = pygame.Surface((ancho, alto), pygame.SRCALPHA)

    # Dibujar resplandor concéntrico difuso
    r_resp, g_resp, b_resp, a_resp = resplandor
    for mult, alfa_factor in [(3.4, 0.15), (2.4, 0.35), (1.6, 0.65)]:
        r_actual = int(radio_base * mult)
        alfa_actual = int(a_resp * alfa_factor * min(progreso_animacion, 1.0))
        if alfa_actual > 0:
            pygame.draw.circle(superficie_halo, (r_resp, g_resp, b_resp, alfa_actual), (cx, cy), r_actual)

    # Núcleo del cuerpo celeste
    pygame.draw.circle(superficie_halo, (*color, int(255 * min(progreso_animacion, 1.0))), (cx, cy), radio_base)

    # Si es luna, detalle de sombra suave para silueta menguante/creciente
    if tipo == "luna":
        offset_sombra = int(radio_base * 0.42)
        c_cielo = paleta["cielo_arriba"]
        pygame.draw.circle(
            superficie_halo,
            (*c_cielo, int(230 * min(progreso_animacion, 1.0))),
            (cx + offset_sombra, cy - int(radio_base * 0.15)),
            int(radio_base * 0.88)
        )

    superficie.blit(superficie_halo, (0, 0))


def dibujar_capas_montana(
    superficie: pygame.Surface,
    capas_y: List[np.ndarray],
    paleta: Dict[str, Any],
    ancho: int,
    alto: int,
    progreso_animacion: float = 1.0
) -> None:
    """
    Dibuja las 4 siluetas de montaña de atrás hacia adelante con animación de revelado.
    - Las capas de fondo emergen gradualmente.
    - La cresta frontal se 'traza' de izquierda a derecha.
    """
    colores_capas = paleta["capas"]  # [capa4 (fondo), capa3, capa2, capa1 (frente)]
    num_capas = len(capas_y)

    for i in range(num_capas):
        color = colores_capas[i]
        y_vals = capas_y[i]
        es_frente = (i == num_capas - 1)

        # Ventana de animación para cada capa
        # Capa 0 (fondo): [0.0, 0.45]
        # Capa 1: [0.15, 0.60]
        # Capa 2: [0.35, 0.80]
        # Capa 3 (frente): [0.15, 1.0] trazado horizontal
        t_inicio = i * 0.16
        t_fin = min(1.0, t_inicio + 0.50)

        if es_frente:
            # La cresta frontal se dibuja de izquierda a derecha entre 0.2 y 1.0
            prog_frente = np.clip((progreso_animacion - 0.20) / 0.80, 0.0, 1.0)
            if prog_frente <= 0.0:
                continue

            limite_x = max(2, int(prog_frente * ancho))

            # Construir polígono frontal hasta limite_x
            puntos = [(0, alto)]
            for x in range(limite_x):
                puntos.append((x, int(y_vals[x])))
            puntos.append((limite_x - 1, alto))

            if len(puntos) >= 3:
                pygame.draw.polygon(superficie, color, puntos)

                # Si aún se está dibujando, resaltar la punta de trazado
                if prog_frente < 0.999:
                    punta_x = limite_x - 1
                    punta_y = int(y_vals[punta_x])
                    c_acento = paleta.get("color_acento", (255, 255, 255))
                    pygame.draw.circle(superficie, c_acento, (punta_x, punta_y), 4)
                    pygame.draw.line(superficie, c_acento, (punta_x, punta_y), (punta_x, alto), 2)
        else:
            # Capas traseras: emergen suavemente desde abajo
            prog_capa = np.clip((progreso_animacion - t_inicio) / (t_fin - t_inicio), 0.0, 1.0)
            if prog_capa <= 0.0:
                continue

            # Desplazamiento de emergencia vertical hacia arriba
            offset_y = (1.0 - prog_capa) * (alto * 0.40)

            puntos = [(0, alto)]
            for x in range(0, ancho, 2):  # muestreo cada 2px para velocidad óptima
                puntos.append((x, int(y_vals[x] + offset_y)))
            puntos.append((ancho - 1, int(y_vals[-1] + offset_y)))
            puntos.append((ancho - 1, alto))

            if len(puntos) >= 3:
                pygame.draw.polygon(superficie, color, puntos)


def dibujar_panel_estadisticas(
    superficie: pygame.Surface,
    stats: Dict[str, Any],
    paleta: Dict[str, Any],
    fuente_titulo: pygame.font.Font,
    fuente_cuerpo: pygame.font.Font,
    fuente_pie: pygame.font.Font,
    ancho: int,
    alto: int,
    alfa_aparicion: float = 1.0
) -> None:
    """Dibuja la tarjeta limpia con las estadísticas de ritmo y los atajos de teclado."""
    if alfa_aparicion <= 0.05:
        return

    # Dimensiones del panel de estadísticas
    ancho_panel = int(min(360, ancho * 0.30))
    alto_panel = int(min(220, alto * 0.32))
    pad = 20

    # Ubicado en la esquina superior derecha con margen
    x_panel = ancho - ancho_panel - pad
    y_panel = pad

    # Superficie con canal alfa para fondo traslúcido
    panel_surf = pygame.Surface((ancho_panel, alto_panel), pygame.SRCALPHA)
    c_panel = paleta.get("color_panel", (25, 20, 35, 210))
    alfa_global = int(c_panel[3] * min(alfa_aparicion, 1.0))
    pygame.draw.rect(panel_surf, (*c_panel[:3], alfa_global), (0, 0, ancho_panel, alto_panel), border_radius=12)

    # Borde sutil acentuado
    c_acento = paleta.get("color_acento", (255, 200, 100))
    pygame.draw.rect(panel_surf, (*c_acento, int(90 * min(alfa_aparicion, 1.0))), (0, 0, ancho_panel, alto_panel), width=1, border_radius=12)

    superficie.blit(panel_surf, (x_panel, y_panel))

    # Textos dentro del panel
    c_texto = paleta.get("color_texto", (255, 255, 255))

    # Título: nombre de la paleta / estilo
    txt_titulo = fuente_titulo.render(paleta.get("nombre", "Cordillera"), True, c_acento)
    superficie.blit(txt_titulo, (x_panel + 18, y_panel + 16))

    # Lista de métricas
    metricas = [
        ("Teclas por minuto:", f"{stats.get('teclas_por_minuto', 0)} TPM"),
        ("Pausa más larga:", f"{stats.get('pausa_mas_larga', 0.0)} s"),
        ("Número de borrados:", f"{stats.get('num_borrados', 0)}"),
        ("Ráfaga más rápida:", f"{stats.get('rafaga_mas_rapida', 0.0)} TPM")
    ]

    y_linea = y_panel + 55
    for etiqueta, valor in metricas:
        lbl = fuente_cuerpo.render(etiqueta, True, (*c_texto[:3],))
        val = fuente_cuerpo.render(valor, True, c_acento)
        superficie.blit(lbl, (x_panel + 18, y_linea))
        superficie.blit(val, (x_panel + ancho_panel - val.get_width() - 18, y_linea))
        y_linea += 30

    # Barra inferior con controles
    txt_pie = fuente_pie.render("[S] Guardar captura PNG       [R] Escribir de nuevo       [ESC] Salir", True, (*c_texto[:3],))
    x_pie = (ancho - txt_pie.get_width()) // 2
    y_pie = alto - 36
    # Fondo muy sutil para la barra de ayuda
    banda_surf = pygame.Surface((txt_pie.get_width() + 32, 28), pygame.SRCALPHA)
    pygame.draw.rect(banda_surf, (10, 10, 15, int(160 * min(alfa_aparicion, 1.0))), (0, 0, banda_surf.get_width(), 28), border_radius=8)
    superficie.blit(banda_surf, (x_pie - 16, y_pie - 4))
    superficie.blit(txt_pie, (x_pie, y_pie))


def renderizar_paisaje_completo(
    eventos: List[Dict[str, Any]],
    ancho: int,
    alto: int,
    progreso_animacion: float = 1.0,
    incluir_panel: bool = True,
    fuente_titulo: Optional[pygame.font.Font] = None,
    fuente_cuerpo: Optional[pygame.font.Font] = None,
    fuente_pie: Optional[pygame.font.Font] = None,
    paleta_forzada: Optional[Dict[str, Any]] = None
) -> Tuple[pygame.Surface, Dict[str, Any], Dict[str, Any]]:
    """
    Renderiza la escena completa del paisaje a la resolución especificada.
    Retorna la superficie generada, el diccionario de estadísticas y la paleta utilizada.
    """
    stats = paisaje.calcular_estadisticas(eventos)
    paleta = paleta_forzada if paleta_forzada is not None else paletas.seleccionar_paleta(stats)

    superficie = pygame.Surface((ancho, alto))

    # 1. Cielo en degradado vertical
    cielo = obtener_degradado_cielo(ancho, alto, paleta["cielo_arriba"], paleta["cielo_abajo"])
    superficie.blit(cielo, (0, 0))

    # 2. Estrellas (si aplica según paleta fría/tormenta)
    dibujar_estrellas(superficie, paleta, ancho, alto)

    # 3. Sol o Luna con halo
    dibujar_cuerpo_celeste(superficie, paleta, stats, ancho, alto, progreso_animacion)

    # 4. Capas de cordillera
    capas_y = paisaje.calcular_todas_las_capas(eventos, ancho, alto)
    dibujar_capas_montana(superficie, capas_y, paleta, ancho, alto, progreso_animacion)

    # 5. Panel de estadísticas y controles
    if incluir_panel:
        alfa_panel = np.clip((progreso_animacion - 0.70) / 0.30, 0.0, 1.0)
        # Inicializar fuentes si no se suministraron
        if fuente_titulo is None:
            fuente_titulo = pygame.font.SysFont("segoeui,helvetica,arial", max(18, int(alto * 0.026)), bold=True)
        if fuente_cuerpo is None:
            fuente_cuerpo = pygame.font.SysFont("segoeui,helvetica,arial", max(14, int(alto * 0.020)))
        if fuente_pie is None:
            fuente_pie = pygame.font.SysFont("segoeui,helvetica,arial", max(13, int(alto * 0.018)))

        dibujar_panel_estadisticas(
            superficie, stats, paleta,
            fuente_titulo, fuente_cuerpo, fuente_pie,
            ancho, alto, alfa_aparicion=alfa_panel
        )

    return superficie, stats, paleta


def guardar_captura_hd(
    eventos: List[Dict[str, Any]],
    ruta_carpeta: str = "capturas",
    nombre_archivo: Optional[str] = None
) -> str:
    """
    Renderiza el paisaje a resolución completa 1920x1080 (sin escalar) y lo guarda en disco.
    Retorna la ruta absoluta del archivo generado.
    """
    os.makedirs(ruta_carpeta, exist_ok=True)
    if not nombre_archivo:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"paisaje_{timestamp}.png"
    ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)

    ancho_hd, alto_hd = 1920, 1080

    # Fuentes proporcionales para resolución 1080p
    f_titulo = pygame.font.SysFont("segoeui,helvetica,arial", 28, bold=True)
    f_cuerpo = pygame.font.SysFont("segoeui,helvetica,arial", 20)
    f_pie = pygame.font.SysFont("segoeui,helvetica,arial", 18)

    superficie_hd, _, _ = renderizar_paisaje_completo(
        eventos=eventos,
        ancho=ancho_hd,
        alto=alto_hd,
        progreso_animacion=1.0,
        incluir_panel=True,
        fuente_titulo=f_titulo,
        fuente_cuerpo=f_cuerpo,
        fuente_pie=f_pie
    )

    pygame.image.save(superficie_hd, ruta_completa)
    return ruta_completa


def dibujar_linea_previa_escritura(
    superficie: pygame.Surface,
    rect: pygame.Rect,
    eventos: List[Dict[str, Any]],
    tiempo_transcurrido: float,
    duracion_maxima: float = 45.0,
    color_linea: Tuple[int, int, int] = (255, 205, 120)
) -> None:
    """
    Dibuja una línea viva debajo del área de texto durante la escritura.
    Muestra la curva naciendo en tiempo real como adelanto de la cordillera.
    """
    # Fondo tenue para el carril
    pygame.draw.rect(superficie, (30, 32, 45, 140), rect, border_radius=4)
    pygame.draw.line(superficie, (60, 65, 85), (rect.left, rect.centery), (rect.right, rect.centery), 1)

    if not eventos or len(eventos) < 2:
        return

    ancho_util = rect.width
    alto_util = rect.height - 6

    # Porción horizontal completada según el tiempo transcurrido
    progreso_tiempo = np.clip(tiempo_transcurrido / max(duracion_maxima, 1.0), 0.05, 1.0)
    num_puntos = max(10, int(ancho_util * progreso_tiempo))

    curva_norm, _, _ = paisaje.generar_curva_base(eventos, num_puntos)

    puntos = []
    for i in range(num_puntos):
        px = rect.left + int((i / (num_puntos - 1)) * (ancho_util * progreso_tiempo))
        # Invertir para que los picos suban
        py = rect.bottom - 3 - int(curva_norm[i] * alto_util)
        puntos.append((px, py))

    if len(puntos) >= 2:
        pygame.draw.lines(superficie, color_linea, False, puntos, 2)
        # Indicador de cabezal de escritura
        cabeza_x, cabeza_y = puntos[-1]
        pygame.draw.circle(superficie, (255, 255, 255), (cabeza_x, cabeza_y), 3)
