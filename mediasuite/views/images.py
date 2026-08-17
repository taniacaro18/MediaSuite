from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from mediasuite.engines.images import compute_histogram, list_images, process_batch
from mediasuite.theme import BORDER, CANVAS, CARD, MUTED, TEXT
from mediasuite.widgets import DropZone, IMAGE_TYPES, PageHero, PathRow, SliderRow, chip_bar, rose_button, sage_button, styled_menu


class ImagesView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._photo = None

        PageHero(
            self, "imagenes", "Imágenes e histogramas",
            "Redimensiona, convierte y firma una carpeta entera. El histograma es de una imagen de muestra.",
        ).pack(fill="x", pady=(4, 14))

        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=22, border_width=1, border_color=BORDER)
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        self.input_dir = DropZone(inner, "Importar carpeta de imágenes", directory=True)
        self.input_dir.pack(fill="x", pady=(0, 12))
        self.output_dir = PathRow(inner, "Carpeta de salida", directory=True)
        self.output_dir.pack(fill="x", pady=(0, 10))

        size_row = ctk.CTkFrame(inner, fg_color="transparent")
        size_row.pack(fill="x", pady=6)
        self.max_w = SliderRow(size_row, "Ancho máximo (0 = sin límite)", 0, 4000, 1920, integer=True)
        self.max_w.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.max_h = SliderRow(size_row, "Alto máximo (0 = sin límite)", 0, 4000, 1080, integer=True)
        self.max_h.pack(side="left", fill="x", expand=True)

        fmt_row = ctk.CTkFrame(inner, fg_color="transparent")
        fmt_row.pack(fill="x", pady=8)
        ctk.CTkLabel(fmt_row, text="Formato de salida", text_color=MUTED).pack(side="left")
        self.fmt = chip_bar(fmt_row, ["Original", "JPG", "PNG", "WEBP"], default="JPG")
        self.fmt.pack(side="left", padx=12)
        self.quality = SliderRow(inner, "Calidad / peso (JPG y WEBP)", 40, 100, 82, integer=True)
        self.quality.pack(fill="x", pady=8)

        self.wm_text = ctk.CTkEntry(inner, placeholder_text="Texto de firma o marca de agua (opcional)", height=36)
        self.wm_text.pack(fill="x", pady=6)
        self.wm_image = PathRow(inner, "Imagen de marca de agua (PNG opcional)", filetypes=IMAGE_TYPES)
        self.wm_image.pack(fill="x", pady=6)

        pos_row = ctk.CTkFrame(inner, fg_color="transparent")
        pos_row.pack(fill="x", pady=8)
        ctk.CTkLabel(pos_row, text="Posición", text_color=MUTED).pack(side="left")
        self.position = styled_menu(
            pos_row,
            ["Inferior derecha", "Inferior izquierda", "Superior derecha", "Superior izquierda", "Centro"],
            width=180,
        )
        self.position.set("Inferior derecha")
        self.position.pack(side="left", padx=12)
        self.opacity = SliderRow(inner, "Opacidad de la marca", 0.15, 1.0, 0.55, fmt="{:.2f}")
        self.opacity.pack(fill="x", pady=6)
        self.scale = SliderRow(inner, "Tamaño relativo de la marca (%)", 6, 40, 14, integer=True)
        self.scale.pack(fill="x", pady=6)

        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))
        rose_button(actions, "Ver histograma", self._histogram, height=40).pack(side="left")
        sage_button(actions, "▶  Procesar lote", self._run, height=42).pack(side="left", padx=8)

        self.meta = ctk.CTkLabel(self, text="", text_color=MUTED)
        self.meta.pack(anchor="w", pady=(14, 4))
        self.preview_label = ctk.CTkLabel(self, text="")
        self.preview_label.pack(anchor="w")
        self.hist_canvas = ctk.CTkCanvas(self, height=180, bg=CANVAS, highlightthickness=0)
        self.hist_canvas.pack(fill="x", pady=(8, 16))

    def _histogram(self) -> None:
        folder = self.input_dir.get()
        path = None
        if folder:
            try:
                files = list_images(folder)
                path = str(files[0])
            except Exception:
                path = None
        if not path:
            path = filedialog.askopenfilename(filetypes=IMAGE_TYPES)
        if not path:
            return

        def work(ctx):
            ctx.log(f"Calculando histograma de {Path(path).name}…")
            ctx.progress(30, "Calculando histograma")
            data = compute_histogram(path)
            ctx.progress(100, "Histograma listo")
            return path, data

        def done(result):
            path, data = result
            w, h = data["size"]
            kb = data["bytes"] / 1024
            self.meta.configure(
                text=f"{Path(path).name}  ·  {w}×{h} px  ·  {data['format']}  ·  {kb:.0f} KB",
                text_color=TEXT,
            )
            preview = data["preview"]
            self._photo = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
            self.preview_label.configure(image=self._photo, text="")
            self._draw_hist(data["r"], data["g"], data["b"])

        self.app.run_job(work, done)

    def _draw_hist(self, r, g, b) -> None:
        canvas = self.hist_canvas
        canvas.delete("all")
        self.update_idletasks()
        width = max(256, canvas.winfo_width())
        height = 180
        canvas.create_rectangle(0, 0, width, height, fill=CANVAS, outline="")
        peak = max(max(r), max(g), max(b), 1)
        colors = (("#C45C6A", r), ("#5F8F7C", g), ("#D4849A", b))
        for color, series in colors:
            pts = []
            for i, value in enumerate(series):
                x = i / 255 * (width - 8) + 4
                y = height - 8 - (value / peak) * (height - 20)
                pts.extend((x, y))
            if len(pts) >= 4:
                canvas.create_line(*pts, fill=color, width=1.5)
        canvas.create_text(8, 12, anchor="nw", fill=MUTED, text="Histograma RGB")

    def _run(self) -> None:
        src, dst = self.input_dir.get(), self.output_dir.get()
        if not src or not dst:
            self.app.toast("Indica carpeta de entrada y de salida.")
            return
        fmt = self.fmt.get().lower()
        max_w, max_h = int(self.max_w.get()), int(self.max_h.get())
        quality = int(self.quality.get())
        text = self.wm_text.get().strip()
        wm_img = self.wm_image.get()
        position = self.position.get()
        opacity = float(self.opacity.get())
        scale = float(self.scale.get())

        def work(ctx):
            return process_batch(
                src, dst,
                max_width=max_w, max_height=max_h, out_format=fmt, quality=quality,
                watermark_text=text, watermark_image=wm_img, position=position,
                opacity=opacity, scale_pct=scale, ctx=ctx,
            )

        self.app.run_job(work, lambda n: self.app.toast(f"Listo · {n} imagen(es) guardadas"))
