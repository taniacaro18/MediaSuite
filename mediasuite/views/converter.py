from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from mediasuite.engines.converter import FORMATS, convert_video
from mediasuite.theme import BORDER, CARD, MUTED, TEXT
from mediasuite.widgets import DropZone, PageHero, PathRow, SliderRow, VIDEO_TYPES, chip_bar, sage_button


class ConverterView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        PageHero(
            self, "convertir", "Convertir y comprimir",
            "CRF más bajo = más calidad y más peso. 18–23 suele verse muy bien.",
        ).pack(fill="x", pady=(4, 14))

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=22, border_width=1, border_color=BORDER)
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        self.input_row = DropZone(inner, "Importar video", filetypes=VIDEO_TYPES, on_change=self._suggest)
        self.input_row.pack(fill="x", pady=(0, 12))
        self.output_row = PathRow(inner, "Archivo de salida", save=True, defaultext=".mp4", filetypes=VIDEO_TYPES)
        self.output_row.pack(fill="x", pady=(0, 10))

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkLabel(row, text="Formato", text_color=MUTED).pack(side="left")
        self.fmt = chip_bar(row, [f.upper() for f in FORMATS], command=self._on_fmt, default="MP4")
        self.fmt.pack(side="left", padx=12, fill="x", expand=True)
        ctk.CTkLabel(row, text="Escala", text_color=MUTED).pack(side="left", padx=(16, 0))
        self.scale = chip_bar(row, ["Original", "1080p", "720p", "480p"], default="Original")
        self.scale.pack(side="left", padx=12)

        self.crf = SliderRow(inner, "Calidad CRF", 15, 35, 23, integer=True)
        self.crf.pack(fill="x", pady=10)

        sage_button(inner, "▶  Exportar", self._run).pack(anchor="w", pady=(8, 0))

    def _on_fmt(self, value: str) -> None:
        src = self.input_row.get()
        if src:
            self._suggest(src)

    def _suggest(self, path: str) -> None:
        if not path:
            return
        p = Path(path)
        ext = self.fmt.get().lower()
        self.output_row.set(str(p.with_name(f"{p.stem}_convertido.{ext}")))

    def _run(self) -> None:
        src, dst = self.input_row.get(), self.output_row.get()
        if not src or not dst:
            self.app.toast("Indica entrada y salida.")
            return
        fmt = self.fmt.get().lower()
        if not dst.lower().endswith(f".{fmt}"):
            dst = str(Path(dst).with_suffix(f".{fmt}"))
            self.output_row.set(dst)
        crf = int(self.crf.get())
        scale = self.scale.get()

        def work(ctx):
            convert_video(self.app.runner(), src, dst, fmt, crf, scale, ctx)

        self.app.run_job(work, lambda _: self.app.toast(f"Listo · {fmt.upper()} guardado"))
