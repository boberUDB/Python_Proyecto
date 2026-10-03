"""
paletas.py - Definición de esquemas de color y selección según el ritmo de tecleo.

Cada paleta define:
- nombre: Identificador legible.
- cielo_arriba / cielo_abajo: Colores del degradado del cielo (RGB).
- capas: Lista de 4 tuplas RGB, ordenadas de fondo a frente (más clara a más oscura).
- cuerpo_celeste: Diccionario con 'tipo' ('sol' o 'luna'), 'color' y 'resplandor'.
- estrellas: True si debe mostrar destellos/estrellas en el cielo.
- color_estrellas: Color para las estrellas.
- color_panel: Color base y acento para el panel de estadísticas.
- color_texto: Color para textos sobreimpresos.
"""

from typing import Dict, Any


PALETAS: Dict[str, Dict[str, Any]] = {
    # 1. Escritura rápida y constante: atardecer cálido
    "atardecer_calido": {
        "nombre": "Atardecer Cálido",
        "descripcion": "Ritmo fluido, veloz y consistente",
        "cielo_arriba": (42, 22, 68),       # Púrpura noche profunda
        "cielo_abajo": (245, 142, 85),     # Naranja dorado brillante
        "capas": [
            (198, 88, 102),   # Capa 4 (fondo): Rosa terracota suave
            (152, 58, 98),    # Capa 3: Magenta crepuscular
            (98, 38, 82),     # Capa 2: Púrpura morado
            (48, 18, 56)      # Capa 1 (frente): Violeta muy oscuro
        ],
        "cuerpo_celeste": {
            "tipo": "sol",
            "color": (255, 235, 170),
            "resplandor": (255, 180, 100, 75)
        },
        "estrellas": False,
        "color_estrellas": (255, 240, 220),
        "color_panel": (35, 14, 45, 210),
        "color_texto": (250, 240, 235),
        "color_acento": (255, 175, 95)
    },

    # 2. Escritura pausada, lenta o reflexiva: amanecer frío
    "amanecer_frio": {
        "nombre": "Amanecer Frío",
        "descripcion": "Ritmo medido, pausado y reflexivo",
        "cielo_arriba": (18, 28, 54),       # Azul marino oscuro
        "cielo_abajo": (168, 186, 216),    # Lavanda / azul niebla claro
        "capas": [
            (130, 148, 178),  # Capa 4 (fondo): Azul lavanda grisáceo
            (90, 108, 142),   # Capa 3: Azul pizarra
            (56, 70, 102),    # Capa 2: Azul índigo medio
            (24, 32, 54)      # Capa 1 (frente): Azul noche profundo
        ],
        "cuerpo_celeste": {
            "tipo": "luna",
            "color": (230, 240, 255),
            "resplandor": (180, 210, 255, 60)
        },
        "estrellas": True,
        "color_estrellas": (220, 235, 255),
        "color_panel": (18, 25, 42, 210),
        "color_texto": (240, 245, 255),
        "color_acento": (145, 195, 255)
    },

    # 3. Muchos borrados o escritura errática: tormenta
    "tormenta": {
        "nombre": "Tormenta Eléctrica",
        "descripcion": "Múltiples correcciones y cambios de rumbo",
        "cielo_arriba": (26, 34, 38),       # Ceniza oscuro casi negro
        "cielo_abajo": (88, 105, 98),      # Gris verdoso neblinoso
        "capas": [
            (74, 92, 85),     # Capa 4 (fondo): Musgo agrisado suave
            (52, 68, 62),     # Capa 3: Verde petróleo grisáceo
            (36, 48, 44),     # Capa 2: Carbón verde oliva
            (18, 26, 24)      # Capa 1 (frente): Abisal oscuro
        ],
        "cuerpo_celeste": {
            "tipo": "sol",
            "color": (255, 225, 110),       # Sol velado entre nubes o luna pálida
            "resplandor": (240, 210, 90, 80)
        },
        "estrellas": True,
        "color_estrellas": (255, 245, 160), # Chispas / destellos
        "color_panel": (20, 28, 26, 215),
        "color_texto": (235, 245, 240),
        "color_acento": (245, 215, 80)
    }
}


def seleccionar_paleta(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Selecciona la paleta más adecuada a partir de las estadísticas de tecleo.

    Criterios:
    - Si el porcentaje de borrados respecto al total de teclas es alto (>= 10%)
      o hay más de 8 borrados en una sesión corta -> Paleta Tormenta.
    - Si la velocidad promedio es alta (>= 40 PPM o ráfagas altas) y pocas pausas largas -> Atardecer Cálido.
    - Si la velocidad es baja o la pausa máxima supera los 2.5s -> Amanecer Frío.
    """
    total_teclas = stats.get("total_teclas", 0)
    borrados = stats.get("num_borrados", 0)
    ppm = stats.get("teclas_por_minuto", 0.0)
    pausa_max = stats.get("pausa_mas_larga", 0.0)

    # 1. Evaluar correcciones frecuentes
    ratio_borrados = (borrados / total_teclas) if total_teclas > 0 else 0.0
    if ratio_borrados >= 0.10 or borrados >= 10:
        return PALETAS["tormenta"]

    # 2. Evaluar velocidad vs pausas
    if ppm >= 180 and pausa_max <= 2.0:
        return PALETAS["atardecer_calido"]
    elif ppm < 120 or pausa_max >= 2.5:
        return PALETAS["amanecer_frio"]
    else:
        # Zona intermedia: si no hay casi borrados y la fluidez es buena, atardecer
        if ratio_borrados < 0.04 and pausa_max < 3.0:
            return PALETAS["atardecer_calido"]
        return PALETAS["amanecer_frio"]
