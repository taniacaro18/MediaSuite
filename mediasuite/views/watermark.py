from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter

from mediasuite.engines.watermark import apply_blur_mask, apply_crop, extract_preview_frame
from mediasuite.theme import BORDER, CARD, MUTED, ROSE, TEXT
from mediasuite.widgets import DropZone, PageHero, PathRow, SliderRow, VIDEO_TYPES, chip_bar, rose_button, sage_button


class WatermarkView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._preview_path: str | None = None
        self._photo = None

        PageHero(
            self, "marcas", "Marcas de agua",
            "Recorta barras quemadas o difumina un logo. Mira primero un fotograma si quieres.",
        ).pack(fill="x", pady=(4, 14))

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=22, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=6)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        self.input_row = DropZone(inner, "Importar video", filetypes=VIDEO_TYPES, on_change=self._suggest)
        self.input_row.pack(fill="x", pady=(0, 12))
        self.output_row = PathRow(inner, "Video de salida", filetypes=[("MP4", "*.mp4")], save=True, defaultext=".mp4")
        self.output_row.pack(fill="x", pady=(0, 10))

        self.mode = ctk.StringVar(value="crop")
        modes = ctk.CTkFrame(inner, fg_color="transparent")
        modes.pack(fill="x", pady=8)
        self.mode_bar = chip_bar(modes, ["Recorte", "Desenfoque"], command=self._on_mode, default="Recorte")
        self.mode_bar.pack(anchor="w")

        self.top = SliderRow(inner, "Recorte superior (%)", 0, 40, 0, fmt="{:.1f} %")
        self.top.pack(fill="x", pady=6)
        self.bottom = SliderRow(inner, "Recorte inferior (%)", 0, 40, 8, fmt="{:.1f} %")
        self.bottom.pack(fill="x", pady=6)

        coords = ctk.CTkFrame(inner, fg_color="transparent")
        coords.pack(fill="x", pady=8)
        self.x = _int_entry(coords, "X", "0")
        self.y = _int_entry(coords, "Y", "0")
        self.w = _int_entry(coords, "Ancho", "240")
        self.h = _int_entry(coords, "Alto", "80")
        self.blur = SliderRow(inner, "Fuerza del desenfoque", 2, 24, 8, integer=True)
        self.blur.pack(fill="x", pady=6)
        self.crf = SliderRow(inner, "CRF de exportación", 16, 32, 20, integer=True)
        self.crf.pack(fill="x", pady=6)

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))
        rose_button(actions, "Vista previa", self._preview, height=42).pack(side="left")
        sage_button(actions, "▶  Exportar", self._run, height=42).pack(side="left", padx=8)

        self.preview_label = ctk.CTkLabel(self, text="Sin vista previa", text_color=MUTED)
        self.preview_label.pack(pady=16)

    def _on_mode(self, value: str) -> None:
        self.mode.set("crop" if value == "Recorte" else "blur")

    def _suggest(self, path: str) -> None:
        if not path:
            return
        p = Path(path)
        self.output_row.set(str(p.with_name(f"{p.stem}_limpio.mp4")))

    def _preview(self) -> None:
        src = self.input_row.get()
        if not src:
            self.app.toast("Selecciona un video.")
            return

        def work(ctx):
            return extract_preview_frame(self.app.runner(), src, ctx)

        def done(path):
            self._preview_path = path
            self._show_preview(path)
            self.app.log_line("Vista previa lista.")

        self.app.run_job(work, done)

    def _show_preview(self, path: str) -> None:
        image = Image.open(path).convert("RGB")
        if self.mode.get() == "crop":
            w, h = image.size
            top = int(h * self.top.get() / 100.0)
            bottom = int(h * self.bottom.get() / 100.0)
            top = max(0, min(top, h - 2))
            bottom = max(0, min(bottom, h - top - 2))
            image = image.crop((0, top, w, h - bottom))
        else:
            x = max(0, int(self.x.get()))
            y = max(0, int(self.y.get()))
            bw = max(8, int(self.w.get()))
            bh = max(8, int(self.h.get()))
            x = min(x, max(0, image.width - 8))
            y = min(y, max(0, image.height - 8))
            bw = min(bw, image.width - x)
            bh = min(bh, image.height - y)
            region = image.crop((x, y, x + bw, y + bh)).filter(ImageFilter.GaussianBlur(self.blur.get()))
            image.paste(region, (x, y))
            draw = ImageDraw.Draw(image)
            draw.rectangle((x, y, x + bw, y + bh), outline=ROSE, width=2)
        image.thumbnail((720, 400))
        self._photo = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        self.preview_label.configure(image=self._photo, text="")

    def _run(self) -> None:
        src, dst = self.input_row.get(), self.output_row.get()
        if not src or not dst:
            self.app.toast("Indica entrada y salida.")
            return
        mode = self.mode.get()
        top, bottom = self.top.get(), self.bottom.get()
        x, y, w, h = int(self.x.get()), int(self.y.get()), int(self.w.get()), int(self.h.get())
        strength, crf = int(self.blur.get()), int(self.crf.get())

        def work(ctx):
            if mode == "crop":
                apply_crop(self.app.runner(), src, dst, top, bottom, crf, ctx)
            else:
                apply_blur_mask(self.app.runner(), src, dst, x, y, w, h, strength, crf, ctx)

        self.app.run_job(work, lambda _: self.app.toast(f"Listo · video guardado en {Path(dst).name}"))


def _int_entry(master, label: str, default: str) -> ctk.CTkEntry:
    box = ctk.CTkFrame(master, fg_color="transparent")
    box.pack(side="left", padx=(0, 12))
    ctk.CTkLabel(box, text=label, text_color=MUTED).pack(anchor="w")
    entry = ctk.CTkEntry(box, width=90, height=34)
    entry.insert(0, default)
    entry.pack()
    return entry
