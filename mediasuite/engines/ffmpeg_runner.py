"""Ejecución de FFmpeg con progreso en tiempo real y bajo uso de RAM."""

from __future__ import annotations

import os
import re
import subprocess
import threading
from collections import deque
from collections.abc import Callable

from mediasuite.errors import CancelledError, FFmpegError
from mediasuite.jobs import JobContext

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
OUT_TIME_HMS_RE = re.compile(r"^out_time=(\d+):(\d+):(\d+(?:\.\d+)?)")
OUT_TIME_US_RE = re.compile(r"^out_time_us=(-?\d+)")
OUT_TIME_MS_RE = re.compile(r"^out_time_ms=(-?\d+)")
TIME_RE = re.compile(r"time[=:](\d+):(\d+):(\d+(?:\.\d+)?)")
VIDEO_RES_RE = re.compile(r"Video:.*?(\d{2,5})x(\d{2,5})")


def hms_to_seconds(h: str, m: str, s: str) -> float:
    return int(h) * 3600 + int(m) * 60 + float(s)


def progress_seconds(line: str) -> float | None:
    """Convierte una línea de ``-progress`` a segundos reales.

    En FFmpeg, ``out_time_ms`` está en **microsegundos** (nombre histórico).
    Interpretarlo como milisegundos hace que la barra salte a 100 % al instante.
    """
    match = OUT_TIME_HMS_RE.match(line)
    if match:
        return hms_to_seconds(*match.groups())
    match = OUT_TIME_US_RE.match(line)
    if match:
        value = int(match.group(1))
        return None if value < 0 else value / 1_000_000.0
    match = OUT_TIME_MS_RE.match(line)
    if match:
        value = int(match.group(1))
        return None if value < 0 else value / 1_000_000.0
    return None


def format_seconds(value: float) -> str:
    if value < 0:
        value = 0
    h = int(value // 3600)
    m = int((value % 3600) // 60)
    s = value % 60
    if h:
        return f"{h:d}:{m:02d}:{s:05.2f}"
    return f"{m:d}:{s:05.2f}"


def probe_media(ffmpeg: str, path: str) -> dict:
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", path],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )
    stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
    info: dict = {
        "duration": 0.0,
        "has_video": "Video:" in stderr,
        "has_audio": "Audio:" in stderr,
        "width": 0,
        "height": 0,
        "raw": stderr,
    }
    match = DURATION_RE.search(stderr)
    if match:
        info["duration"] = hms_to_seconds(*match.groups())
    res = VIDEO_RES_RE.search(stderr)
    if res:
        info["width"] = int(res.group(1))
        info["height"] = int(res.group(2))
    return info


class FFmpegRunner:
    def __init__(self, ffmpeg_path: str):
        self.ffmpeg = ffmpeg_path
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def terminate(self) -> None:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.kill()
        except Exception:
            pass

    def run(
        self,
        args: list[str],
        *,
        duration: float | None = None,
        ctx: JobContext | None = None,
        on_stderr_line: Callable[[str], None] | None = None,
        progress_start: float = 0.0,
        progress_end: float = 100.0,
        collect_stderr: bool = False,
        label: str = "Procesando",
    ) -> str:
        """Ejecuta FFmpeg. ``args`` no debe incluir el binario.

        El progreso se lee de ``-progress pipe:1`` (stdout) y, si hace falta,
        de las líneas ``time=`` de stderr. No se carga el archivo en Python.
        """
        cmd = [self.ffmpeg, "-hide_banner", "-y", "-nostats", "-progress", "pipe:1", *args]
        stderr_tail: deque[str] = deque(maxlen=40)
        collected: list[str] = []
        last_seconds = -1.0
        pass_index = 0

        if ctx:
            ctx.check_cancel()
            ctx.bind_runner(self)
            ctx.set_stage(label)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        with self._lock:
            self._proc = proc

        def _map_seconds(seconds: float) -> None:
            nonlocal last_seconds, pass_index
            if ctx is None or seconds < 0:
                return
            if last_seconds >= 0 and seconds + 0.8 < last_seconds:
                pass_index += 1
            last_seconds = seconds
            if duration and duration > 0:
                total = duration * (pass_index + 1)
                current = pass_index * duration + min(seconds, duration)
                fraction = current / total
                extra = f" · pasada {pass_index + 1}" if pass_index else ""
                message = f"{label}{extra}  {format_seconds(min(seconds, duration))}"
            else:
                fraction = min(0.92, 0.04 + seconds / 600.0)
                message = f"{label}  {format_seconds(seconds)}"
            fraction = max(0.0, min(0.99, fraction))
            pct = progress_start + (progress_end - progress_start) * fraction
            ctx.progress(pct, message)

        def _read_stdout() -> None:
            assert proc.stdout is not None
            for raw in iter(proc.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                seconds = progress_seconds(line)
                if seconds is not None:
                    _map_seconds(seconds)

        def _read_stderr() -> None:
            assert proc.stderr is not None
            for raw in iter(proc.stderr.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                stderr_tail.append(line)
                if collect_stderr:
                    collected.append(line)
                if on_stderr_line:
                    on_stderr_line(line)
                match = TIME_RE.search(line)
                if match:
                    _map_seconds(hms_to_seconds(*match.groups()))

        t_out = threading.Thread(target=_read_stdout, daemon=True)
        t_err = threading.Thread(target=_read_stderr, daemon=True)
        t_out.start()
        t_err.start()
        code = proc.wait()
        t_out.join(timeout=2)
        t_err.join(timeout=2)
        with self._lock:
            self._proc = None

        if ctx and ctx.is_cancelled():
            raise CancelledError("Proceso cancelado por el usuario.")
        if code != 0:
            detail = "\n".join(stderr_tail) or f"código {code}"
            raise FFmpegError(f"FFmpeg falló (código {code}):\n{detail}")

        if ctx:
            ctx.progress(progress_end)
        return "\n".join(collected)
