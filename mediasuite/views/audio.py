from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from mediasuite.engines.audio import extract_audio
from mediasuite.theme import BORDER, CARD, MUTED, ROSE, TEXT
from mediasuite.widgets import AUDIO_TYPES, DropZone, PageHero, PathRow, SliderRow, chip_bar, sage_button


class AudioView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        PageHero(
            self, "audio", "Extraer y cuidar el audio",
            "Saca la pista de un video, normaliza el volumen y, si quieres, baja un poco el ruido de fondo.",
        ).pack(fill="x", pady=(4, 14))

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=22, border_width=1, border_color=BORDER)
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=18)

        self.input_row = DropZone(
            inner, "Importar video o audio", filetypes=AUDIO_TYPES, on_change=self._suggest
        )
        self.input_row.pack(fill="x", pady=(0, 12))
        self.output_row = PathRow(
            inner, "Dónde guardar el audio", save=True, defaultext=".mp3",
            filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav")],
        )
        self.output_row.pack(fill="x", pady=(0, 10))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkLabel(row, text="Formato", text_color=MUTED).pack(side="left")
        self.fmt = chip_bar(row, ["MP3", "WAV"], command=self._on_fmt, default="MP3")
        self.fmt.pack(side="left", padx=12)

        self.normalize = ctk.BooleanVar(value=True)
        self.denoise = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            inner, text="Normalizar volumen (queda más parejo)", variable=self.normalize,
            fg_color=ROSE, hover_color="#C46B86", text_color=TEXT, checkmark_color="#FFFCFB",
        ).pack(anchor="w", pady=6)
        ctk.CTkCheckBox(
            inner, text="Reducción de ruido suave", variable=self.denoise,
            fg_color=ROSE, hover_color="#C46B86", text_color=TEXT, checkmark_color="#FFFCFB",
        ).pack(anchor="w", pady=6)
        self.noise = SliderRow(inner, "Agresividad del denoiser (más bajo = más fuerte)", -50, -20, -25, integer=True)
        self.noise.pack(fill="x", pady=8)

        sage_button(inner, "▶  Extraer audio", self._run).pack(anchor="w", pady=(12, 0))

    def _on_fmt(self, value: str) -> None:
        if self.input_row.get():
            self._suggest(self.input_row.get())

    def _suggest(self, path: str) -> None:
        if not path:
            return
        p = Path(path)
        ext = self.fmt.get().lower()
        self.output_row.set(str(p.with_name(f"{p.stem}_audio.{ext}")))

    def _run(self) -> None:
        src, dst = self.input_row.get(), self.output_row.get()
        if not src or not dst:
            self.app.toast("Elige el archivo de entrada y dónde guardarlo.", ok=False)
            return
        fmt = self.fmt.get().lower()
        if not dst.lower().endswith(f".{fmt}"):
            dst = str(Path(dst).with_suffix(f".{fmt}"))
            self.output_row.set(dst)
        normalize = bool(self.normalize.get())
        denoise = bool(self.denoise.get())
        nf = float(self.noise.get())

        def work(ctx):
            extract_audio(self.app.runner(), src, dst, fmt, normalize, denoise, nf, ctx)

        self.app.run_job(work, lambda _: self.app.toast(f"Listo · audio guardado en {Path(dst).name}"))
