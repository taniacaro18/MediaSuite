# MediaSuite

Suite de escritorio en Python para procesar video, audio e imágenes en local. La interfaz (CustomTkinter) se mantiene fluida porque cada trabajo corre en un hilo secundario y FFmpeg se invoca como proceso externo: los archivos pesados no se cargan en la RAM de Python.

## Módulos

1. **Recortador de silencios** — Detecta pausas por umbral en dB y duración mínima, deja un margen de habla y exporta un MP4 limpio, sin marcas de agua. El análisis solo decodifica audio a 16 kHz mono; en videos largos (> 2 h) los muchos cortes se procesan por segmentos temporales en disco.
2. **Marcas de agua** — Recorte superior/inferior en porcentaje (barras quemadas) o desenfoque `boxblur` en una región `x, y, ancho, alto`, con vista previa de un fotograma.
3. **Convertidor / compresor** — MP4, MKV, AVI, MOV y WebM, con calidad CRF y escala opcional (1080p / 720p / 480p).
4. **Imágenes e histogramas** — Lote: redimensionado, conversión PNG/JPG/WEBP, optimización de peso, firma de texto o PNG, e histograma RGB de una muestra.
5. **Audio / pistas** — Extracción a MP3 o WAV, normalización loudnorm (−16 LUFS) y reducción de ruido FFT (`afftdn`).

## Requisitos

- Windows 10/11, Python 3.10 o superior
- FFmpeg **no hace falta** instalarlo a mano ni añadir PATH: se usa el binario que trae `imageio-ffmpeg`

## Instalación

```bash
cd MediaSuite
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

También puedes usar `run.bat` (usa el `.venv` si existe) o `python -m mediasuite` desde esta carpeta.

## Uso

- Elige un módulo en la barra lateral.
- Indica archivos o carpetas y pulsa el botón de proceso.
- El panel inferior muestra la barra de progreso y un historial con marca de tiempo.
- **Cancelar proceso** detiene el FFmpeg en curso.

Las exportaciones de video van con `libx264` (o VP9/VP8 en WebM) y no añaden marca de agua de la aplicación.
