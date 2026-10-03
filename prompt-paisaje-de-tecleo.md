# Proyecto: Paisaje de tecleo

## Contexto

Quiero construir una aplicación de escritorio en **Python** llamada **Paisaje de tecleo**. La persona escribe un texto libre durante un tiempo limitado y, al terminar, el programa dibuja una cordillera generada a partir de su **ritmo de escritura**, no del contenido. Dos personas que escriben la misma frase deben obtener paisajes distintos.

La prioridad es que sea **rápido de terminar** (un fin de semana) y que el resultado final sea **visualmente atractivo**, algo que dé ganas de compartir como captura o fondo de pantalla.

## Stack

- Python 3.11 o superior
- `pygame-ce` para la ventana, la captura de teclas y el dibujo
- `numpy` para el suavizado y el procesamiento de datos
- Sin otras dependencias salvo que sean estrictamente necesarias
- Incluye un `requirements.txt`

## Flujo de la aplicación

1. **Pantalla de inicio**: título, una línea que explique la idea y la instrucción "Presiona cualquier tecla para empezar".
2. **Pantalla de escritura**:
   - Cuenta regresiva visible de **45 segundos**.
   - Área de texto donde se ve lo que se escribe (con salto de línea automático).
   - Debajo, una línea fina que se va dibujando en vivo como adelanto del paisaje.
   - Se puede terminar antes con `Enter` dos veces seguidas o con `Esc`.
3. **Pantalla de resultado**:
   - El paisaje a pantalla completa.
   - Un pequeño panel con estadísticas: teclas por minuto, pausa más larga, número de borrados, "ráfaga" más rápida.
   - Teclas: `S` guarda el PNG, `R` reinicia, `Esc` sale.

## Datos que hay que registrar

Por cada tecla presionada, guarda un evento con:

- `t`: tiempo en segundos desde el inicio (usa `time.perf_counter()`)
- `tipo`: `"caracter"`, `"espacio"`, `"borrar"` o `"enter"`
- `delta`: tiempo desde la tecla anterior

Ignora teclas modificadoras sueltas (Shift, Ctrl, Alt).

## Cómo se convierte el ritmo en paisaje

Este es el corazón del proyecto. Implementa el mapeo en un módulo separado (`paisaje.py`) con funciones puras y fáciles de ajustar.

- **Eje X**: el tiempo. Toda la sesión se estira al ancho de la ventana.
- **Altura**: velocidad local de escritura. Calcula la cantidad de teclas en una ventana deslizante (por ejemplo, 1 segundo). Más velocidad = pico más alto.
- **Valles**: cualquier pausa mayor a 1,2 s baja la altura hacia el mínimo, de forma proporcional a la duración de la pausa.
- **Grietas**: cada borrado produce una muesca angosta y afilada en la cresta, en el punto de tiempo donde ocurrió.
- **Saltos de línea**: generan una pequeña meseta plana.
- **Suavizado**: aplica un suavizado (media móvil o gaussiano con `numpy`) para que la cordillera sea orgánica, pero conserva las grietas después del suavizado para que sigan siendo nítidas.
- **Normalización**: escala el resultado para que incluso una sesión corta o lenta produzca un paisaje con drama visual. La altura máxima debe ocupar alrededor del 55 % de la ventana.

Deja todos estos números como constantes al inicio del módulo, con un comentario que explique qué hace cada uno.

## Dirección visual

El objetivo es un paisaje estilo atardecer en capas, limpio y plano, tipo ilustración vectorial.

- **Capas**: dibuja **4 siluetas** superpuestas. La del frente es la cordillera real; las de atrás son versiones desplazadas, más suaves y más bajas de la misma curva, para dar profundidad.
- **Color**: cada capa usa un tono de la misma familia, de más oscuro (frente) a más claro (fondo), con un cielo en degradado vertical.
- **Paleta según el ritmo**: elige la paleta según el estilo de escritura:
  - Escritura rápida y constante → paleta de atardecer cálido (naranjas, rosados, morado)
  - Escritura lenta con muchas pausas → paleta de amanecer frío (azules, lavanda, gris)
  - Muchos borrados → paleta de tormenta (verdes oscuros, gris azulado, un toque amarillo)
- **Detalles**: un sol o luna en el cielo cuya posición vertical depende de la velocidad promedio; unas pocas estrellas o partículas si la paleta es fría.
- **Tipografía**: una sola fuente legible, en tamaños claros. Nada de bordes ni recuadros gruesos.
- **Animación de revelado**: al pasar a la pantalla de resultado, las capas aparecen de atrás hacia adelante y la cresta frontal se "dibuja" de izquierda a derecha en unos 2 segundos.

Resolución por defecto: **1280×720**. El PNG exportado debe salir a **1920×1080** (redibuja a esa resolución, no escales la imagen de la ventana).

## Estructura de archivos

```
paisaje-de-tecleo/
├── main.py            # bucle principal y cambio de pantallas
├── captura.py         # registro de eventos de teclado
├── paisaje.py         # mapeo ritmo → curva (funciones puras)
├── render.py          # dibujo de cielo, capas, sol y animación
├── paletas.py         # definición de paletas y lógica de selección
├── requirements.txt
└── README.md
```

## Requisitos de calidad

- El código debe estar en español (nombres de variables, comentarios y textos de interfaz).
- Funciones cortas y con nombres claros. Nada de clases innecesarias.
- `paisaje.py` no debe importar `pygame`, para que pueda probarse por separado.
- Incluye un modo de demostración: `python main.py --demo` genera un paisaje con datos de tecleo sintéticos sin tener que escribir, útil para ajustar el aspecto visual.
- Los PNG se guardan en una carpeta `capturas/` con nombre basado en fecha y hora.
- El programa debe correr a 60 FPS sin tirones durante la escritura.

## README

Escribe un `README.md` breve con: qué es el proyecto en una frase, cómo instalarlo, cómo ejecutarlo, los controles, y una sección "Cómo ajustar el paisaje" que explique las constantes principales de `paisaje.py`.

## Orden de trabajo

1. Crea la estructura y `requirements.txt`.
2. Implementa `paisaje.py` y el modo `--demo` primero, para validar que la curva se vea bien antes de construir la interfaz.
3. Implementa `render.py` con las capas, el cielo y las paletas.
4. Implementa la captura de teclado y las tres pantallas.
5. Añade la animación de revelado y la exportación a PNG.
6. Prueba con al menos tres estilos de escritura (rápido, lento con pausas, con muchos borrados) y ajusta las constantes hasta que los tres paisajes se vean claramente distintos.
7. Escribe el README.

Cuando termines cada paso, muéstrame una captura del estado actual antes de seguir.
