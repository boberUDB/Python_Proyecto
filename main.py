"""
main.py - Punto de entrada y máquina de estados para Paisaje de Tecleo.

Gestiona las tres pantallas (Inicio, Escritura, Resultado), la animación de revelado,
la captura en vivo a 60 FPS y el modo de demostración (--demo).
"""

import sys
import time
import argparse
from typing import List, Optional
import pygame

import paisaje
import captura
import render
import paletas


# Dimensiones base de la ventana
ANCHO_VENTANA = 1280
ALTO_VENTANA = 720
FPS = 60

# Estados de navegación
ESTADO_INICIO = "inicio"
ESTADO_ESCRITURA = "escritura"
ESTADO_RESULTADO = "resultado"


def formatear_lineas_con_ajuste(texto: str, fuente: pygame.font.Font, ancho_maximo: int) -> List[str]:
    """Divide el texto en líneas respetando saltos de línea explícitos y ancho disponible."""
    lineas_resultado = []
    parrafos = texto.split("\n")

    for parrafo in parrafos:
        if not parrafo:
            lineas_resultado.append("")
            continue

        palabras = parrafo.split(" ")
        linea_actual = ""

        for palabra in palabras:
            prueba = f"{linea_actual} {palabra}".strip()
            if fuente.size(prueba)[0] <= ancho_maximo:
                linea_actual = prueba
            else:
                if linea_actual:
                    lineas_resultado.append(linea_actual)
                linea_actual = palabra

        if linea_actual:
            lineas_resultado.append(linea_actual)

    return lineas_resultado


class AplicacionPaisaje:
    """Controlador principal de la ventana, bucle de eventos y pantallas."""

    def __init__(self, modo_demo: bool = False, estilo_demo: str = "rapido"):
        pygame.init()
        pygame.display.set_caption("Paisaje de tecleo")
        self.pantalla = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
        self.reloj = pygame.time.Clock()

        # Carga de tipografía limpia del sistema
        self.fuente_gran_titulo = pygame.font.SysFont("segoeui,helvetica,arial", 56, bold=True)
        self.fuente_subtitulo = pygame.font.SysFont("segoeui,helvetica,arial", 22)
        self.fuente_instruccion = pygame.font.SysFont("segoeui,helvetica,arial", 20)
        self.fuente_contador = pygame.font.SysFont("segoeui,helvetica,arial", 38, bold=True)
        self.fuente_editor = pygame.font.SysFont("segoeui,helvetica,arial", 24)
        self.fuente_pista = pygame.font.SysFont("segoeui,helvetica,arial", 16)

        # Gestor de teclado
        self.gestor = captura.GestorCaptura(duracion_maxima=45.0)

        # Variables de estado
        self.estado = ESTADO_INICIO
        self.modo_demo = modo_demo
        self.estilo_demo = estilo_demo
        self.tiempo_inicio_resultado: float = 0.0
        self.mensaje_notificacion: Optional[str] = None
        self.tiempo_notificacion: float = 0.0

        if self.modo_demo:
            # En modo demo, cargar directamente datos sintéticos en pantalla de resultado
            self.activar_modo_demo(self.estilo_demo)

    def activar_modo_demo(self, estilo: str) -> None:
        """Carga datos de tecleo sintéticos y pasa a la pantalla de resultado."""
        self.estilo_demo = estilo
        eventos = paisaje.generar_datos_sinteticos(estilo)
        self.gestor.eventos = eventos
        self.gestor.texto = "Modo Demostración Sintético"
        self.estado = ESTADO_RESULTADO
        self.tiempo_inicio_resultado = time.perf_counter()
        self.mensaje_notificacion = f"Modo Demo activo: estilo '{estilo}'. Usa [1, 2, 3] para alternar."
        self.tiempo_notificacion = time.perf_counter()

    def cambiar_a_escritura(self) -> None:
        """Inicia una sesión de escritura interactiva."""
        self.gestor.iniciar()
        self.estado = ESTADO_ESCRITURA
        self.mensaje_notificacion = None

    def cambiar_a_resultado(self) -> None:
        """Finaliza la escritura y activa la pantalla de resultado con animación."""
        self.gestor.activo = False
        # Si no hubo pulsaciones, generar un evento simbólico para no fallar
        if not self.gestor.eventos:
            self.gestor.eventos = [{"t": 0.1, "tipo": "caracter", "delta": 0.1}]
        self.estado = ESTADO_RESULTADO
        self.tiempo_inicio_resultado = time.perf_counter()

    def ejecutar(self) -> None:
        """Bucle principal de la aplicación a 60 FPS."""
        ejecutando = True

        while ejecutando:
            delta_ms = self.reloj.tick(FPS)

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False

                elif evento.type == pygame.KEYDOWN:
                    if self.estado == ESTADO_INICIO:
                        if evento.key == pygame.K_ESCAPE:
                            ejecutando = False
                        else:
                            self.cambiar_a_escritura()

                    elif self.estado == ESTADO_ESCRITURA:
                        if evento.key == pygame.K_ESCAPE:
                            self.cambiar_a_resultado()
                        else:
                            self.gestor.procesar_evento_teclado(evento)
                            if self.gestor.terminado_por_doble_enter:
                                self.cambiar_a_resultado()

                    elif self.estado == ESTADO_RESULTADO:
                        if evento.key == pygame.K_ESCAPE:
                            ejecutando = False
                        elif evento.key in (pygame.K_r, pygame.K_F5):
                            self.cambiar_a_escritura()
                        elif evento.key == pygame.K_s:
                            # Guardar PNG en resolución 1920x1080
                            ruta = render.guardar_captura_hd(self.gestor.eventos)
                            self.mensaje_notificacion = f"¡Guardado en {ruta}!"
                            self.tiempo_notificacion = time.perf_counter()
                        elif self.modo_demo and evento.key == pygame.K_1:
                            self.activar_modo_demo("rapido")
                        elif self.modo_demo and evento.key == pygame.K_2:
                            self.activar_modo_demo("lento")
                        elif self.modo_demo and evento.key == pygame.K_3:
                            self.activar_modo_demo("borrados")

            # Comprobar expiración del temporizador de 45 segundos
            if self.estado == ESTADO_ESCRITURA and self.gestor.ha_expirado:
                self.cambiar_a_resultado()

            # Renderizar pantalla correspondiente
            if self.estado == ESTADO_INICIO:
                self.dibujar_pantalla_inicio()
            elif self.estado == ESTADO_ESCRITURA:
                self.dibujar_pantalla_escritura()
            elif self.estado == ESTADO_RESULTADO:
                self.dibujar_pantalla_resultado()

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

    # ==========================================================================
    # PANTALLA 1: INICIO
    # ==========================================================================
    def dibujar_pantalla_inicio(self) -> None:
        """Dibuja la carátula inicial limpia y minimalista."""
        cielo = render.obtener_degradado_cielo(ANCHO_VENTANA, ALTO_VENTANA, (20, 24, 45), (55, 40, 70))
        self.pantalla.blit(cielo, (0, 0))

        # Silueta decorativa sutil de fondo (colinas vectoriales en la base)
        capa_decor = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA), pygame.SRCALPHA)
        # Resplandor solar suave en el horizonte
        pygame.draw.circle(capa_decor, (255, 200, 110, 35), (ANCHO_VENTANA // 2, ALTO_VENTANA // 2 - 40), 140)
        pygame.draw.circle(capa_decor, (255, 230, 160, 55), (ANCHO_VENTANA // 2, ALTO_VENTANA // 2 - 40), 90)

        # Montañas decorativas estáticas en la base de la pantalla de inicio
        puntos_fondo = [(0, ALTO_VENTANA), (0, 570), (280, 500), (520, 550), (750, 480), (1050, 540), (ANCHO_VENTANA, 510), (ANCHO_VENTANA, ALTO_VENTANA)]
        pygame.draw.polygon(capa_decor, (42, 28, 55, 180), puntos_fondo)
        puntos_frente = [(0, ALTO_VENTANA), (0, 620), (320, 570), (640, 610), (920, 560), (ANCHO_VENTANA, 600), (ANCHO_VENTANA, ALTO_VENTANA)]
        pygame.draw.polygon(capa_decor, (26, 18, 38, 240), puntos_frente)
        self.pantalla.blit(capa_decor, (0, 0))

        # Título principal
        txt_titulo = self.fuente_gran_titulo.render("PAISAJE DE TECLEO", True, (255, 245, 235))
        r_titulo = txt_titulo.get_rect(center=(ANCHO_VENTANA // 2, ALTO_VENTANA // 2 - 80))
        self.pantalla.blit(txt_titulo, r_titulo)

        # Línea descriptiva
        txt_desc = self.fuente_subtitulo.render(
            "Escribe libremente y descubre la cordillera que oculta tu ritmo de tecleo",
            True, (220, 215, 235)
        )
        r_desc = txt_desc.get_rect(center=(ANCHO_VENTANA // 2, ALTO_VENTANA // 2 - 15))
        self.pantalla.blit(txt_desc, r_desc)

        # Instrucción parpadeante
        alfa_pulso = 0.6 + 0.4 * abs(((time.perf_counter() * 2) % 2) - 1)
        c_inst = (int(255 * alfa_pulso), int(215 * alfa_pulso), int(130 * alfa_pulso))
        txt_inst = self.fuente_instruccion.render("— Presiona cualquier tecla para empezar —", True, c_inst)
        r_inst = txt_inst.get_rect(center=(ANCHO_VENTANA // 2, ALTO_VENTANA // 2 + 75))
        self.pantalla.blit(txt_inst, r_inst)

        # Información técnica en el pie
        txt_pie = self.fuente_pista.render("Sesión de 45 segundos   •   Puedes terminar antes con [Enter] dos veces o [Esc]", True, (160, 165, 195))
        r_pie = txt_pie.get_rect(center=(ANCHO_VENTANA // 2, ALTO_VENTANA - 35))
        self.pantalla.blit(txt_pie, r_pie)

    # ==========================================================================
    # PANTALLA 2: ESCRITURA EN VIVO
    # ==========================================================================
    def dibujar_pantalla_escritura(self) -> None:
        """Dibuja la pantalla de escritura con cuenta regresiva, editor y línea previa en vivo."""
        cielo = render.obtener_degradado_cielo(ANCHO_VENTANA, ALTO_VENTANA, (20, 24, 38), (35, 42, 64))
        self.pantalla.blit(cielo, (0, 0))

        # 1. Cabecera con cronómetro
        segundos_restantes = int(self.gestor.tiempo_restante)
        milisegundos = int((self.gestor.tiempo_restante - segundos_restantes) * 10)
        c_contador = (255, 120, 100) if segundos_restantes < 10 else (255, 215, 120)

        texto_reloj = f"{segundos_restantes:02d}.{milisegundos} s"
        txt_tiempo = self.fuente_contador.render(texto_reloj, True, c_contador)
        self.pantalla.blit(txt_tiempo, (80, 45))

        txt_pista_arriba = self.fuente_pista.render(
            "Escribe lo que quieras (pensamientos, una historia, tus ideas). [Enter] dos veces o [Esc] para finalizar.",
            True, (170, 185, 210)
        )
        self.pantalla.blit(txt_pista_arriba, (240, 56))

        # 2. Marco del área de texto
        rect_editor = pygame.Rect(80, 110, ANCHO_VENTANA - 160, 440)
        pygame.draw.rect(self.pantalla, (16, 20, 32, 230), rect_editor, border_radius=10)
        pygame.draw.rect(self.pantalla, (60, 75, 105), rect_editor, width=1, border_radius=10)

        # Ajuste de líneas de texto
        ancho_util_texto = rect_editor.width - 40
        lineas = formatear_lineas_con_ajuste(self.gestor.texto, self.fuente_editor, ancho_util_texto)

        # Cursor parpadeante
        cursor_visible = (int(time.perf_counter() * 2.5) % 2) == 0
        alto_linea = 34
        max_lineas_visibles = (rect_editor.height - 40) // alto_linea

        # Auto-scroll para mantener la última línea a la vista
        lineas_mostrar = lineas[-max_lineas_visibles:] if len(lineas) > max_lineas_visibles else lineas

        y_texto = rect_editor.top + 20
        for i, linea in enumerate(lineas_mostrar):
            txt_render = self.fuente_editor.render(linea, True, (240, 245, 255))
            self.pantalla.blit(txt_render, (rect_editor.left + 20, y_texto))

            # Dibujar cursor al final de la última línea
            if i == len(lineas_mostrar) - 1 and cursor_visible:
                cx = rect_editor.left + 20 + txt_render.get_width() + 3
                pygame.draw.line(self.pantalla, (255, 200, 90), (cx, y_texto + 4), (cx, y_texto + alto_linea - 6), 2)

            y_texto += alto_linea

        if not self.gestor.texto and cursor_visible:
            # Cursor inicial si no ha escrito nada
            pygame.draw.line(self.pantalla, (255, 200, 90), (rect_editor.left + 20, rect_editor.top + 24), (rect_editor.left + 20, rect_editor.top + 48), 2)
            txt_placeholder = self.fuente_editor.render("Empieza a escribir aquí...", True, (80, 100, 130))
            self.pantalla.blit(txt_placeholder, (rect_editor.left + 30, rect_editor.top + 20))

        # 3. Línea fina viva que adelanta el paisaje debajo del área de texto
        rect_linea_previa = pygame.Rect(80, 575, ANCHO_VENTANA - 160, 65)
        render.dibujar_linea_previa_escritura(
            self.pantalla, rect_linea_previa,
            self.gestor.eventos, self.gestor.tiempo_transcurrido,
            duracion_maxima=self.gestor.duracion_maxima
        )

        txt_adelanto = self.fuente_pista.render("Adelanto de la cresta en tiempo real", True, (130, 150, 180))
        self.pantalla.blit(txt_adelanto, (82, 648))

        # Contador de pulsaciones en vivo
        txt_total_teclas = self.fuente_pista.render(f"Teclas registradas: {len(self.gestor.eventos)}", True, (160, 180, 210))
        self.pantalla.blit(txt_total_teclas, (ANCHO_VENTANA - 80 - txt_total_teclas.get_width(), 648))

    # ==========================================================================
    # PANTALLA 3: RESULTADO FINAL Y PAISAJE COMPLETO
    # ==========================================================================
    def dibujar_pantalla_resultado(self) -> None:
        """Dibuja el paisaje final a pantalla completa con animación y panel de estadísticas."""
        tiempo_animacion = time.perf_counter() - self.tiempo_inicio_resultado
        progreso = min(1.0, tiempo_animacion / 2.0)  # Animación de 2 segundos

        # Renderizar la escena completa a la resolución de la ventana
        superficie_paisaje, stats, paleta = render.renderizar_paisaje_completo(
            eventos=self.gestor.eventos,
            ancho=ANCHO_VENTANA,
            alto=ALTO_VENTANA,
            progreso_animacion=progreso,
            incluir_panel=True
        )

        self.pantalla.blit(superficie_paisaje, (0, 0))

        # Mensaje flotante de notificación (p. ej. al guardar captura PNG)
        if self.mensaje_notificacion:
            tiempo_notif = time.perf_counter() - self.tiempo_notificacion
            if tiempo_notif < 3.5:
                alfa_notif = int(255 * min(1.0, (3.5 - tiempo_notif)))
                txt_notif = self.fuente_instruccion.render(self.mensaje_notificacion, True, (255, 255, 255))
                pad_x, pad_y = 20, 10
                caja_surf = pygame.Surface((txt_notif.get_width() + pad_x * 2, txt_notif.get_height() + pad_y * 2), pygame.SRCALPHA)
                pygame.draw.rect(caja_surf, (20, 25, 35, int(alfa_notif * 0.85)), caja_surf.get_rect(), border_radius=8)
                pygame.draw.rect(caja_surf, (255, 210, 100, alfa_notif), caja_surf.get_rect(), width=1, border_radius=8)
                caja_surf.blit(txt_notif, (pad_x, pad_y))

                pos_x = (ANCHO_VENTANA - caja_surf.get_width()) // 2
                self.pantalla.blit(caja_surf, (pos_x, 30))
            else:
                self.mensaje_notificacion = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Paisaje de tecleo - Generador de paisajes a partir de tu ritmo de escritura.")
    parser.add_argument("--demo", action="store_true", help="Inicia en modo demostración con datos sintéticos sin necesidad de teclear.")
    parser.add_argument("--estilo", type=str, default="rapido", choices=["rapido", "lento", "borrados"], help="Estilo sintético para el modo demo (rapido, lento, borrados).")

    args = parser.parse_args()

    app = AplicacionPaisaje(modo_demo=args.demo, estilo_demo=args.estilo)
    app.ejecutar()


if __name__ == "__main__":
    main()
