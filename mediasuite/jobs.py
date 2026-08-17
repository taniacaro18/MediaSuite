"""Ejecución de trabajos en hilos secundarios y puente hacia la UI."""

from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable
from typing import Any

from mediasuite.errors import CancelledError, MediaSuiteError


class JobContext:
    """Contexto que los motores usan para progreso, log y cancelación."""

    def __init__(self, ui_call: Callable[..., None], cancel_event: threading.Event):
        self._ui_call = ui_call
        self._cancel_event = cancel_event
        self._lock = threading.Lock()
        self.active_runner = None
        self.stage = "Iniciando…"
        self._last_pct = -1.0
        self._last_ui = 0.0

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def check_cancel(self) -> None:
        if self._cancel_event.is_set():
            raise CancelledError("Proceso cancelado por el usuario.")

    def log(self, message: str) -> None:
        self._ui_call("log", message)

    def set_stage(self, message: str) -> None:
        self.stage = message
        self.log(message)
        pct = 0.0 if self._last_pct < 0 else self._last_pct
        self._ui_call("progress", pct, message)

    def progress(self, percent: float, message: str | None = None) -> None:
        pct = max(0.0, min(100.0, float(percent)))
        if message:
            self.stage = message
        now = time.monotonic()
        small = abs(pct - self._last_pct) < 0.35
        too_soon = (now - self._last_ui) < 0.18
        edge = pct <= 0.05 or pct >= 99.6 or self._last_pct < 0
        if small and too_soon and not edge:
            return
        self._last_pct = pct
        self._last_ui = now
        self._ui_call("progress", pct, self.stage)

    def bind_runner(self, runner: Any) -> None:
        with self._lock:
            self.active_runner = runner


class JobManager:
    def __init__(self, widget: Any):
        self._widget = widget
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._busy = False
        self._ctx: JobContext | None = None
        self.on_busy_change: Callable[[bool], None] | None = None
        self.on_log: Callable[[str], None] | None = None
        self.on_progress: Callable[[float, str | None], None] | None = None
        self.on_result: Callable[[str, bool], None] | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def _ui(self, kind: str, *args: Any) -> None:
        def _apply() -> None:
            if kind == "log" and self.on_log:
                self.on_log(str(args[0]))
            elif kind == "progress" and self.on_progress:
                self.on_progress(float(args[0]), args[1] if len(args) > 1 else None)
            elif kind == "result" and self.on_result:
                self.on_result(str(args[0]), bool(args[1]))

        try:
            self._widget.after(0, _apply)
        except Exception:
            pass

    def start(self, work: Callable[[JobContext], Any], on_done: Callable[[Any], None] | None = None) -> None:
        if self._busy:
            raise MediaSuiteError("Ya hay un proceso en ejecución. Cancélalo o espera a que termine.")

        self._cancel.clear()
        ctx = JobContext(self._ui, self._cancel)
        self._ctx = ctx
        self._busy = True
        if self.on_busy_change:
            self.on_busy_change(True)
        ctx.set_stage("Iniciando…")

        def _run() -> None:
            error: Exception | None = None
            result: Any = None
            try:
                result = work(ctx)
            except CancelledError as exc:
                error = exc
            except Exception as exc:
                error = exc
                traceback.print_exc()

            def _finish() -> None:
                self._busy = False
                self._ctx = None
                if self.on_busy_change:
                    self.on_busy_change(False)
                if error is None:
                    self._ui("progress", 100.0, "Listo")
                    self._ui("log", "Listo. El archivo se guardó correctamente.")
                    self._ui("result", "Listo · el proceso terminó bien", True)
                    if on_done:
                        on_done(result)
                elif isinstance(error, CancelledError):
                    self._ui("progress", 0.0, "Cancelado")
                    self._ui("log", "Proceso cancelado por el usuario.")
                    self._ui("result", "Cancelado", False)
                else:
                    self._ui("progress", 0.0, "Error")
                    self._ui("log", f"Error: {error}")
                    self._ui("result", f"Error: {error}", False)

            try:
                self._widget.after(0, _finish)
            except Exception:
                pass

        self._thread = threading.Thread(target=_run, name="MediaSuiteJob", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        if not self._busy:
            return
        self._cancel.set()
        ctx = self._ctx
        if ctx and ctx.active_runner is not None:
            try:
                ctx.active_runner.terminate()
            except Exception:
                pass
        self._ui("log", "Cancelando…")
