"""
captura.py - Registro y gestión de eventos de teclado durante la sesión de escritura.

Se encarga de filtrar modificadores, calcular los tiempos precisos (delta y acumulado),
mantener el buffer de texto del usuario y detectar la finalización anticipada.
"""

import time
from typing import List, Dict, Any, Optional
import pygame


# Teclas modificadoras que no representan ritmo de escritura y deben ignorarse
TECLAS_IGNORADAS = {
    pygame.K_LSHIFT, pygame.K_RSHIFT,
    pygame.K_LCTRL, pygame.K_RCTRL,
    pygame.K_LALT, pygame.K_RALT,
    pygame.K_CAPSLOCK, pygame.K_NUMLOCK, pygame.K_SCROLLOCK,
    pygame.K_LMETA, pygame.K_RMETA,
    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
    pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END,
    pygame.K_INSERT
}


class GestorCaptura:
    """Administra la sesión de escritura y el registro temporal de pulsaciones."""

    def __init__(self, duracion_maxima: float = 45.0):
        self.duracion_maxima = duracion_maxima
        self.t_inicio: Optional[float] = None
        self.ultimo_t: Optional[float] = None
        self.eventos: List[Dict[str, Any]] = []
        self.texto: str = ""
        self.activo: bool = False
        self.ultimo_fue_enter: bool = False
        self.terminado_por_doble_enter: bool = False

    def iniciar(self) -> None:
        """Comienza una nueva sesión de registro."""
        ahora = time.perf_counter()
        self.t_inicio = ahora
        self.ultimo_t = ahora
        self.eventos = []
        self.texto = ""
        self.activo = True
        self.ultimo_fue_enter = False
        self.terminado_por_doble_enter = False

    @property
    def tiempo_transcurrido(self) -> float:
        if self.t_inicio is None:
            return 0.0
        return time.perf_counter() - self.t_inicio

    @property
    def tiempo_restante(self) -> float:
        restante = self.duracion_maxima - self.tiempo_transcurrido
        return max(0.0, restante)

    @property
    def ha_expirado(self) -> bool:
        return self.tiempo_transcurrido >= self.duracion_maxima

    def procesar_evento_teclado(self, event: pygame.event.Event) -> Optional[Dict[str, Any]]:
        """
        Procesa un evento pygame.KEYDOWN.
        Retorna el diccionario de evento registrado o None si fue ignorado.
        """
        if not self.activo:
            return None

        # Ignorar modificadores y flechas de navegación
        if event.key in TECLAS_IGNORADAS:
            return None

        ahora = time.perf_counter()
        t_relativo = ahora - self.t_inicio
        delta = ahora - self.ultimo_t if self.ultimo_t is not None else 0.0
        self.ultimo_t = ahora

        tipo = None

        if event.key == pygame.K_BACKSPACE:
            tipo = "borrar"
            if len(self.texto) > 0:
                self.texto = self.texto[:-1]
            self.ultimo_fue_enter = False

        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            tipo = "enter"
            if self.ultimo_fue_enter:
                # Doble Enter detectado: finalizar sesión anticipadamente
                self.terminado_por_doble_enter = True
            self.ultimo_fue_enter = True
            self.texto += "\n"

        elif event.key == pygame.K_SPACE:
            tipo = "espacio"
            self.texto += " "
            self.ultimo_fue_enter = False

        elif event.unicode and event.unicode.isprintable():
            tipo = "caracter"
            self.texto += event.unicode
            self.ultimo_fue_enter = False

        if tipo is not None:
            evento_registro = {
                "t": round(t_relativo, 4),
                "tipo": tipo,
                "delta": round(delta, 4)
            }
            self.eventos.append(evento_registro)
            return evento_registro

        return None
