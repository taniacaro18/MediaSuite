from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from mediasuite.engines import ffmpeg_runner as ff
from mediasuite.engines.silence import detect_silences, export_without_silences, keep_intervals, summarize_cut
from mediasuite.theme import BORDER, CANVAS, CARD, MUTED, ROSE, TEXT
from mediasuite.widgets import DropZone, PageHero, PathRow, SliderRow, VIDEO_TYPES, rose_button, sage_button


class SilenceView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._silences: list[tuple[float, float]] = []
        self._keeps: list[tuple[float, float]] = []
        self._info: dict = {}

        PageHero(
            self, "silencios", "Recortar silencios",
            "Detecta pausas por nivel de dB. El video no se carga en RAM: sirve para archivos larguísimos.",
        ).pack(fill="x", pady=(4, 14))

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=22, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=6)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        self.input_row = DropZone(
            inner, "Importar video", filetypes=VIDEO_TYPES, on_change=self._suggest_output
        )
        self.input_row.pack(fill="x", pady=(0, 12))
        self.output_row = PathRow(
            inner, "Video de salida", filetypes=[("MP4", "*.mp4")], save=True, defaultext=".mp4"
        )
        self.output_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            inner,
            text="Pulsa Exportar recorte. La línea de tiempo de abajo empieza a correr.",
            text_color=MUTED,
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 8))

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 14))
        self.start_btn = sage_button(actions, "▶  Exportar recorte", self._start, height=46)
        self.start_btn.pack(side="left")
        self.analyze_btn = rose_button(actions, "Solo analizar", self._analyze, height=46)
        self.analyze_btn.pack(side="left", padx=8)

        self.noise = SliderRow(inner, "Umbral de silencio (dB)", -60, -15, -30, fmt="{:.0f} dB", integer=True)
        self.noise.pack(fill="x", pady=8)
        self.min_dur = SliderRow(inner, "Duración mínima de silencio", 0.15, 3.0, 0.50, fmt="{:.2f} s")
        self.min_dur.pack(fill="x", pady=8)
        self.margin = SliderRow(inner, "Margen a conservar junto al habla", 0.0, 1.2, 0.20, fmt="{:.2f} s")
        self.margin.pack(fill="x", pady=8)
        self.crf = SliderRow(inner, "Calidad de exportación (CRF, menor = mejor)", 16, 32, 20, integer=True)
        self.crf.pack(fill="x", pady=8)

        self.summary = ctk.CTkLabel(self, text="Aún no hay análisis.", text_color=MUTED, justify="left")
        self.summary.pack(anchor="w", pady=(14, 8))

        self.timeline = ctk.CTkCanvas(self, height=42, bg=CANVAS, highlightthickness=0)
        self.timeline.pack(fill="x", pady=(0, 12))

    def _suggest_output(self, path: str) -> None:
        if not path:
            return
        p = Path(path)
        self.output_row.set(str(p.with_name(f"{p.stem}_sin_silencios.mp4")))

    def _analyze(self) -> None:
        src = self.input_row.get()
        if not src:
            self.app.toast("Selecciona un video de entrada.", ok=False)
            return

        def work(ctx):
            runner = self.app.runner()
            silences, info = detect_silences(runner, src, float(self.noise.get()), float(self.min_dur.get()), ctx)
            keeps = keep_intervals(info["duration"], silences, float(self.margin.get()))
            stats = summarize_cut(info["duration"], keeps, silences)
            return silences, keeps, info, stats

        def done(result):
            self._silences, self._keeps, self._info, stats = result
            self.summary.configure(
                text=(
                    f"Duración original: {ff.format_seconds(stats['duration'])}   ·   "
                    f"Silencios: {stats['silence_count']}   ·   "
                    f"A recortar: {ff.format_seconds(stats['removed_time'])}   ·   "
                    f"Duración final: {ff.format_seconds(stats['keep_time'])}"
                ),
                text_color=TEXT,
            )
            self._draw_timeline(stats["duration"], self._silences, self._keeps)
            self.app.log_line("Análisis de silencios completado.")

        self.app.run_job(work, done)

    def _start(self) -> None:
        src = self.input_row.get()
        dst = self.output_row.get()
        if not src:
            self.app.toast("Elige primero el video de entrada.", ok=False)
            return
        if not dst:
            self.app.toast("Indica dónde guardar el video de salida.", ok=False)
            return

        noise = float(self.noise.get())
        min_dur = float(self.min_dur.get())
        margin = float(self.margin.get())
        crf = int(self.crf.get())

        def work(ctx):
            runner = self.app.runner()
            silences, info = detect_silences(runner, src, noise, min_dur, ctx, progress_start=0, progress_end=30)
            keeps = keep_intervals(info["duration"], silences, margin)
            stats = summarize_cut(info["duration"], keeps, silences)
            ctx.set_stage("Exportando video sin silencios…")
            export_without_silences(runner, src, dst, keeps, info, crf, ctx, progress_start=30, progress_end=100)
            return silences, keeps, info, stats

        def done(result):
            self._silences, self._keeps, self._info, stats = result
            self.summary.configure(
                text=(
                    f"Duración original: {ff.format_seconds(stats['duration'])}   ·   "
                    f"Silencios: {stats['silence_count']}   ·   "
                    f"A recortar: {ff.format_seconds(stats['removed_time'])}   ·   "
                    f"Duración final: {ff.format_seconds(stats['keep_time'])}"
                ),
                text_color=TEXT,
            )
            self._draw_timeline(stats["duration"], self._silences, self._keeps)
            self.app.toast(f"Listo · video guardado en {Path(dst).name}")

        self.app.run_job(work, done)

    def _draw_timeline(self, duration: float, silences, keeps) -> None:
        self.timeline.delete("all")
        self.update_idletasks()
        w = max(100, self.timeline.winfo_width())
        h = 42
        self.timeline.create_rectangle(0, 0, w, h, fill=CANVAS, outline="")
        if duration <= 0:
            return
        for a, b in silences:
            x0 = w * a / duration
            x1 = w * b / duration
            self.timeline.create_rectangle(x0, 8, x1, h - 8, fill="#E8B4B8", outline="")
        for a, b in keeps:
            x0 = w * a / duration
            x1 = w * b / duration
            self.timeline.create_rectangle(x0, 8, x1, h - 8, fill=ROSE, outline="")
        self.timeline.create_text(8, h - 6, anchor="sw", fill=MUTED, text="Rosa: se conserva    Palo: silencio")
