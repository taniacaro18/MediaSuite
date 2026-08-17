from __future__ import annotations

import threading
from datetime import datetime

import customtkinter as ctk

from mediasuite import __version__
from mediasuite.errors import MediaSuiteError
from mediasuite.jobs import JobManager
from mediasuite.theme import (
    BG,
    BLUE,
    BLUE_SOFT,
    CARD,
    DANGER,
    DANGER_HOVER,
    MUTED,
    PROGRESS_TRACK,
    PURPLE,
    PURPLE_HOVER,
    ROSE,
    ROSE_HOVER,
    SAGE,
    SIDEBAR,
    SIDEBAR_MUTED,
    SIDEBAR_TEXT,
    TEXT,
    TIMELINE,
)
from mediasuite.views.audio import AudioView
from mediasuite.views.converter import ConverterView
from mediasuite.views.home import HomeView
from mediasuite.views.images import ImagesView
from mediasuite.views.silence import SilenceView
from mediasuite.views.watermark import WatermarkView
from mediasuite.widgets import ctk_icon

NAV = [
    ("inicio", "Inicio"),
    ("silencios", "Silencio"),
    ("marcas", "Marcas"),
    ("convertir", "Convertir"),
    ("imagenes", "Imagen"),
    ("audio", "Audio"),
]

TITLES = {
    "inicio": "Proyectos",
    "silencios": "Recortar silencios",
    "marcas": "Marcas de agua",
    "convertir": "Convertir / Comprimir",
    "imagenes": "Imágenes / Histogramas",
    "audio": "Audio / Pistas",
}


class MediaSuiteApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MediaSuite")
        self.minsize(1180, 740)
        self.geometry("1320x840")
        self.configure(fg_color=BG)
        self._runner = None
        self._views: dict = {}
        self._toast_job = None
        self._icon_photo = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._center()
        try:
            from PIL import ImageTk

            from mediasuite.art import logo as draw_logo

            photo = ImageTk.PhotoImage(draw_logo(32))
            self._icon_photo = photo
            self.iconphoto(True, photo)
        except Exception:
            pass

        self.jobs = JobManager(self)
        self.jobs.on_log = self.log_line
        self.jobs.on_progress = self._on_progress
        self.jobs.on_busy_change = self._on_busy
        self.jobs.on_result = self._on_result

        self.show("inicio")
        self.after(150, self._init_ffmpeg)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _center(self) -> None:
        self.update_idletasks()
        w, h = 1320, 840
        x = (self.winfo_screenwidth() - w) // 2
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, width=96, corner_radius=0, fg_color=SIDEBAR)
        bar.grid(row=0, column=0, sticky="nsew")
        bar.grid_propagate(False)

        self._logo = ctk_icon("logo", 48)
        ctk.CTkLabel(bar, image=self._logo, text="").pack(pady=(18, 6))
        ctk.CTkLabel(bar, text="MS", text_color=SIDEBAR_TEXT, font=ctk.CTkFont(size=11, weight="bold")).pack()

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_icons = []
        for key, title in NAV:
            icon = ctk_icon(key, 32)
            self._nav_icons.append(icon)
            btn = ctk.CTkButton(
                bar,
                text=title,
                image=icon,
                compound="top",
                width=80,
                height=70,
                corner_radius=16,
                fg_color="transparent",
                hover_color="#4A3570",
                text_color=SIDEBAR_TEXT,
                font=ctk.CTkFont(size=11),
                cursor="hand2",
                command=lambda k=key: self.show(k),
            )
            btn.pack(pady=4, padx=8)
            self.nav_buttons[key] = btn

        spacer = ctk.CTkFrame(bar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self.ffmpeg_label = ctk.CTkLabel(
            bar, text="FFmpeg…", text_color=SIDEBAR_MUTED, wraplength=84,
            justify="center", font=ctk.CTkFont(size=10),
        )
        self.ffmpeg_label.pack(pady=(0, 8))
        self.cancel_btn = ctk.CTkButton(
            bar, text="Parar", width=76, height=32, corner_radius=14,
            fg_color=DANGER, hover_color=DANGER_HOVER, text_color=CARD,
            command=self._cancel, state="disabled", cursor="hand2",
        )
        self.cancel_btn.pack(pady=(0, 16))

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(main, fg_color=CARD, corner_radius=0, height=56)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=22)
        self._spark = ctk_icon("inicio", 28)
        self.header_icon = ctk.CTkLabel(inner, image=self._spark, text="")
        self.header_icon.pack(side="left", padx=(0, 10))
        col = ctk.CTkFrame(inner, fg_color="transparent")
        col.pack(side="left")
        self.header_title = ctk.CTkLabel(
            col, text="Proyectos", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT
        )
        self.header_title.pack(anchor="w")
        ctk.CTkLabel(
            col, text=f"MediaSuite  ·  v{__version__}", text_color=MUTED, font=ctk.CTkFont(size=11)
        ).pack(anchor="w")
        self.toast_label = ctk.CTkLabel(inner, text="", text_color=BLUE, font=ctk.CTkFont(size=13, weight="bold"))
        self.toast_label.pack(side="right")

        self.body = ctk.CTkFrame(main, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=18, pady=10)
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        timeline = ctk.CTkFrame(main, fg_color=TIMELINE, corner_radius=0)
        timeline.grid(row=2, column=0, sticky="ew")
        t_top = ctk.CTkFrame(timeline, fg_color="transparent")
        t_top.pack(fill="x", padx=18, pady=(10, 0))
        ctk.CTkLabel(t_top, text="Línea de tiempo", text_color=SIDEBAR_MUTED, font=ctk.CTkFont(size=11)).pack(side="left")
        self.progress_text = ctk.CTkLabel(
            t_top, text="0 %", text_color=ROSE, font=ctk.CTkFont(size=14, weight="bold")
        )
        self.progress_text.pack(side="right")
        self.stage_label = ctk.CTkLabel(timeline, text="Lista · importa un archivo y pulsa Exportar", text_color=SIDEBAR_TEXT)
        self.stage_label.pack(anchor="w", padx=18, pady=(2, 0))
        self.progress = ctk.CTkProgressBar(
            timeline, height=16, corner_radius=8, progress_color=ROSE, fg_color="#3D2C5C"
        )
        self.progress.set(0)
        self.progress.pack(fill="x", padx=18, pady=(6, 6))
        self.result_banner = ctk.CTkLabel(timeline, text="", text_color=BLUE, font=ctk.CTkFont(size=12, weight="bold"))
        self.result_banner.pack(anchor="w", padx=18)
        self.log = ctk.CTkTextbox(
            timeline, height=72, font=ctk.CTkFont(size=11),
            fg_color="#1C122C", text_color="#E8DFF8", corner_radius=10,
        )
        self.log.pack(fill="x", padx=18, pady=(4, 12))
        self.log.configure(state="disabled")

        self._views = {
            "inicio": HomeView(self.body, self.show),
            "silencios": SilenceView(self.body, self),
            "marcas": WatermarkView(self.body, self),
            "convertir": ConverterView(self.body, self),
            "imagenes": ImagesView(self.body, self),
            "audio": AudioView(self.body, self),
        }

    def show(self, key: str) -> None:
        for name, view in self._views.items():
            if name == key:
                view.grid(row=0, column=0, sticky="nsew")
            else:
                view.grid_remove()
        self.header_title.configure(text=TITLES.get(key, key))
        self._spark = ctk_icon(key, 28)
        self.header_icon.configure(image=self._spark)
        for name, btn in self.nav_buttons.items():
            if name == key:
                btn.configure(fg_color=PURPLE, text_color=CARD, hover_color=PURPLE_HOVER)
            else:
                btn.configure(fg_color="transparent", text_color=SIDEBAR_TEXT, hover_color="#4A3570")

    def runner(self):
        if self._runner is None:
            from mediasuite.engines.ffmpeg_runner import FFmpegRunner
            from mediasuite.ffmpeg_bin import get_ffmpeg_path

            self._runner = FFmpegRunner(get_ffmpeg_path())
        return self._runner

    def run_job(self, work, on_done=None) -> None:
        try:
            self.jobs.start(work, on_done)
        except MediaSuiteError as exc:
            self.toast(str(exc), ok=False)
            self.log_line(str(exc))

    def toast(self, message: str, ok: bool = True) -> None:
        self.toast_label.configure(text=message, text_color=BLUE if ok else DANGER)
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(8000, lambda: self.toast_label.configure(text=""))

    def log_line(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{stamp}]  {message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_progress(self, percent: float, message: str | None) -> None:
        self.progress.set(percent / 100.0)
        self.progress_text.configure(text=f"{percent:.0f} %")
        if message:
            self.stage_label.configure(text=message, text_color=SIDEBAR_TEXT)

    def _on_busy(self, busy: bool) -> None:
        self.cancel_btn.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.set(0)
            self.progress_text.configure(text="0 %")
            self.stage_label.configure(text="Renderizando…")
            self.result_banner.configure(text="")

    def _on_result(self, message: str, ok: bool) -> None:
        self.result_banner.configure(text=message, text_color=BLUE if ok else DANGER)
        self.toast(message, ok=ok)

    def _cancel(self) -> None:
        self.jobs.cancel()

    def _init_ffmpeg(self) -> None:
        def work() -> None:
            try:
                from mediasuite.ffmpeg_bin import get_ffmpeg_path

                path = get_ffmpeg_path()
                self.after(0, lambda: self._ffmpeg_ok("Listo"))
            except Exception as exc:
                self.after(0, lambda e=exc: self._ffmpeg_fail(e))

        threading.Thread(target=work, daemon=True, name="FFmpegDetect").start()

    def _ffmpeg_ok(self, short: str) -> None:
        self.ffmpeg_label.configure(text="FFmpeg\nlisto", text_color="#B8F0C8")
        self.log_line("FFmpeg listo. Importa un archivo y exporta.")

    def _ffmpeg_fail(self, exc: Exception) -> None:
        self.ffmpeg_label.configure(text="Sin\nFFmpeg", text_color=DANGER)
        self.log_line(str(exc))
        self.toast("No se encontró FFmpeg.", ok=False)

    def _close(self) -> None:
        if self.jobs.busy:
            self.jobs.cancel()
        self.destroy()


def run() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = MediaSuiteApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        try:
            app.destroy()
        except Exception:
            pass
