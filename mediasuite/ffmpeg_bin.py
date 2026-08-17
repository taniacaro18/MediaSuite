"""Localización del binario FFmpeg sin depender del PATH del sistema."""

from __future__ import annotations

import os
import shutil
from functools import lru_cache


class FFmpegNotFoundError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_ffmpeg_path() -> str:
    """Devuelve la ruta absoluta de FFmpeg.

    Prioridad:
    1. Binario embebido de ``imageio_ffmpeg`` (no requiere PATH).
    2. ``ffmpeg`` encontrado en PATH como respaldo.
    """
    try:
        import imageio_ffmpeg

        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    except Exception:
        pass

    fallback = shutil.which("ffmpeg")
    if fallback:
        return os.path.abspath(fallback)

    raise FFmpegNotFoundError(
        "No se encontró FFmpeg. Instala la dependencia imageio-ffmpeg "
        "con: pip install imageio-ffmpeg"
    )
