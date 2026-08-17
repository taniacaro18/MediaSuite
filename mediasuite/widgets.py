"""Controles reutilizables, con hover e importación tipo editor."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

from mediasuite.art import logo, pil_icon
from mediasuite.theme import (
    BLUE,
    BLUE_HOVER,
    BLUE_SOFT,
    BORDER,
    CARD,
    ENTRY,
    MUTED,
    PURPLE,
    PURPLE_HOVER,
    PURPLE_SOFT,
    ROSE,
    ROSE_HOVER,
    ROSE_SOFT,
    SAGE,
    SAGE_HOVER,
    TEXT,
)

VIDEO_TYPES = [
    ("Video", "*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.wmv"),
    ("Todos", "*.*"),
]
AUDIO_TYPES = [
    ("Audio/Video", "*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.wav *.m4a *.aac *.flac"),
    ("Todos", "*.*"),
]
IMAGE_TYPES = [
    ("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
    ("Todos", "*.*"),
]

ACCENT = ROSE


def _bind_tree(widget, sequence: str, handler) -> None:
    widget.bind(sequence, handler, add="+")
    for child in widget.winfo_children():
        _bind_tree(child, sequence, handler)


def make_hoverable(widget, on_enter, on_leave) -> None:
    depth = [0]

    def enter(_event=None):
        depth[0] += 1
        if depth[0] == 1:
            on_enter()

    def leave(_event=None):
        depth[0] = max(0, depth[0] - 1)
        if depth[0] == 0:
            on_leave()

    def walk(node):
        node.bind("<Enter>", enter, add="+")
        node.bind("<Leave>", leave, add="+")
        for child in node.winfo_children():
            walk(child)

    walk(widget)


def make_clickable(widget, command) -> None:
    def click(_event=None):
        command()
        return "break"

    def walk(node):
        node.bind("<Button-1>", click, add="+")
        try:
            node.configure(cursor="hand2")
        except Exception:
            pass
        for child in node.winfo_children():
            walk(child)

    walk(widget)


class Card(ctk.CTkFrame):
    def __init__(self, master, title: str | None = None, **kwargs):
        kwargs.setdefault("fg_color", CARD)
        kwargs.setdefault("corner_radius", 22)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", BORDER)
        super().__init__(master, **kwargs)
        if title:
            ctk.CTkLabel(
                self, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT
            ).pack(anchor="w", padx=18, pady=(16, 8))


def rose_button(master, text: str, command, *, width=None, height=42) -> ctk.CTkButton:
    kwargs = dict(
        text=text,
        command=command,
        height=height,
        corner_radius=18,
        fg_color=ROSE,
        hover_color=ROSE_HOVER,
        text_color=CARD,
        font=ctk.CTkFont(size=13, weight="bold"),
        cursor="hand2",
    )
    if width is not None:
        kwargs["width"] = width
    return ctk.CTkButton(master, **kwargs)


def sage_button(master, text: str, command, *, width=None, height=42) -> ctk.CTkButton:
    kwargs = dict(
        text=text,
        command=command,
        height=height,
        corner_radius=18,
        fg_color=PURPLE,
        hover_color=PURPLE_HOVER,
        text_color=CARD,
        font=ctk.CTkFont(size=13, weight="bold"),
        cursor="hand2",
    )
    if width is not None:
        kwargs["width"] = width
    return ctk.CTkButton(master, **kwargs)


def soft_button(master, text: str, command, *, width=None, height=42) -> ctk.CTkButton:
    kwargs = dict(
        text=text,
        command=command,
        height=height,
        corner_radius=18,
        fg_color=BLUE_SOFT,
        hover_color=BLUE,
        text_color=TEXT,
        font=ctk.CTkFont(size=13, weight="bold"),
        cursor="hand2",
    )
    if width is not None:
        kwargs["width"] = width
    return ctk.CTkButton(master, **kwargs)


def styled_menu(master, values: list[str], **kwargs) -> ctk.CTkOptionMenu:
    kwargs.setdefault("width", 130)
    kwargs.setdefault("fg_color", PURPLE)
    kwargs.setdefault("button_color", PURPLE_HOVER)
    kwargs.setdefault("button_hover_color", "#8B5CF6")
    kwargs.setdefault("dropdown_fg_color", CARD)
    kwargs.setdefault("dropdown_hover_color", PURPLE_SOFT)
    kwargs.setdefault("text_color", CARD)
    kwargs.setdefault("dropdown_text_color", TEXT)
    kwargs.setdefault("corner_radius", 12)
    return ctk.CTkOptionMenu(master, values=values, **kwargs)


def chip_bar(master, values: list[str], command=None, default: str | None = None) -> ctk.CTkSegmentedButton:
    bar = ctk.CTkSegmentedButton(
        master,
        values=values,
        command=command,
        fg_color=PURPLE_SOFT,
        selected_color=PURPLE,
        selected_hover_color=PURPLE_HOVER,
        unselected_color=CARD,
        unselected_hover_color=BLUE_SOFT,
        text_color=TEXT,
        text_color_disabled=MUTED,
        corner_radius=12,
        height=36,
    )
    if default:
        bar.set(default)
    elif values:
        bar.set(values[0])
    return bar


class PathRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        label: str,
        *,
        filetypes=None,
        save: bool = False,
        directory: bool = False,
        defaultext: str = "",
        on_change: Callable[[str], None] | None = None,
    ):
        super().__init__(master, fg_color="transparent")
        self.filetypes = filetypes or VIDEO_TYPES
        self.save = save
        self.directory = directory
        self.defaultext = defaultext
        self.on_change = on_change
        self.var = ctk.StringVar()
        ctk.CTkLabel(self, text=label, text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        self.entry = ctk.CTkEntry(
            row,
            textvariable=self.var,
            height=38,
            corner_radius=14,
            border_color=BORDER,
            fg_color=ENTRY,
            text_color=TEXT,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        rose_button(row, "Examinar", self._browse, width=118, height=38).pack(side="right")
        self.var.trace_add("write", lambda *_: self._notify())

    def _notify(self) -> None:
        if self.on_change:
            self.on_change(self.get())

    def _browse(self) -> None:
        if self.directory:
            path = filedialog.askdirectory()
        elif self.save:
            path = filedialog.asksaveasfilename(
                defaultextension=self.defaultext,
                filetypes=self.filetypes,
            )
        else:
            path = filedialog.askopenfilename(filetypes=self.filetypes)
        if path:
            self.var.set(path)

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str) -> None:
        self.var.set(value)


class DropZone(ctk.CTkFrame):
    """Zona de importar media, tipo CapCut: hover + clic."""

    def __init__(
        self,
        master,
        title: str = "Importar media",
        *,
        filetypes=None,
        directory: bool = False,
        on_change: Callable[[str], None] | None = None,
    ):
        super().__init__(
            master, fg_color=BLUE_SOFT, corner_radius=20,
            border_width=2, border_color=BLUE, height=118,
        )
        self.pack_propagate(False)
        self.filetypes = filetypes or VIDEO_TYPES
        self.directory = directory
        self.on_change = on_change
        self.var = ctk.StringVar()
        self._idle = BLUE_SOFT
        self._hover = ROSE_SOFT

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=16, pady=14)
        self.title_label = ctk.CTkLabel(
            inner, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT
        )
        self.title_label.pack()
        self.hint = ctk.CTkLabel(
            inner, text="Haz clic para elegir el archivo  ·  como en CapCut",
            text_color=MUTED, font=ctk.CTkFont(size=12),
        )
        self.hint.pack(pady=(2, 0))
        self.file_label = ctk.CTkLabel(inner, text="Ningún archivo todavía", text_color=PURPLE)
        self.file_label.pack(pady=(6, 0))

        make_hoverable(
            self,
            lambda: self.configure(fg_color=self._hover, border_color=ROSE, border_width=3),
            lambda: self.configure(fg_color=self._idle, border_color=BLUE, border_width=2),
        )
        make_clickable(self, self._browse)
        self.var.trace_add("write", lambda *_: self._refresh())

    def _refresh(self) -> None:
        path = self.get()
        if path:
            self.file_label.configure(text=Path(path).name, text_color=TEXT)
            self.hint.configure(text="Clic otra vez para cambiar de archivo")
        else:
            self.file_label.configure(text="Ningún archivo todavía", text_color=PURPLE)
        if self.on_change:
            self.on_change(path)

    def _browse(self) -> None:
        if self.directory:
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename(filetypes=self.filetypes)
        if path:
            self.var.set(path)

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str) -> None:
        self.var.set(value)


class SliderRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        label: str,
        from_: float,
        to: float,
        default: float,
        *,
        fmt: str = "{:.1f}",
        integer: bool = False,
    ):
        super().__init__(master, fg_color="transparent")
        self.fmt = fmt
        self.integer = integer
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text=label, text_color=MUTED).pack(side="left")
        self.value_label = ctk.CTkLabel(head, text=self._format(default), width=70, anchor="e", text_color=PURPLE)
        self.value_label.pack(side="right")
        self.slider = ctk.CTkSlider(
            self,
            from_=from_,
            to=to,
            number_of_steps=max(1, int(to - from_) if integer else 200),
            command=self._on_slide,
            progress_color=PURPLE,
            button_color=ROSE,
            button_hover_color=ROSE_HOVER,
            fg_color=BLUE_SOFT,
        )
        self.slider.set(default)
        self.slider.pack(fill="x", pady=(4, 0))

    def _format(self, value: float) -> str:
        if self.integer:
            return str(int(round(value)))
        return self.fmt.format(value)

    def _on_slide(self, value: float) -> None:
        self.value_label.configure(text=self._format(value))

    def get(self) -> float:
        value = self.slider.get()
        return int(round(value)) if self.integer else float(value)


_CTK_IMAGES: dict[tuple[str, int], ctk.CTkImage] = {}


def ctk_icon(kind: str, size: int) -> ctk.CTkImage:
    key = (kind, size)
    if key not in _CTK_IMAGES:
        pil = logo(size) if kind == "logo" else pil_icon(kind, size)
        _CTK_IMAGES[key] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
    return _CTK_IMAGES[key]


class PageHero(ctk.CTkFrame):
    def __init__(self, master, kind: str, title: str, subtitle: str):
        super().__init__(master, fg_color=PURPLE_SOFT, corner_radius=24)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)
        self._icon = ctk_icon(kind, 84)
        ctk.CTkLabel(row, image=self._icon, text="").pack(side="left", padx=(2, 16))
        col = ctk.CTkFrame(row, fg_color="transparent")
        col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            col, text=title, font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT, anchor="w", justify="left",
        ).pack(anchor="w")
        ctk.CTkLabel(
            col, text=subtitle, text_color=MUTED, wraplength=640,
            justify="left", anchor="w",
        ).pack(anchor="w", pady=(4, 0))


class ModuleCard(ctk.CTkFrame):
    """Tile de herramienta: hover + clic en toda la tarjeta."""

    def __init__(self, master, kind: str, title: str, desc: str, command):
        super().__init__(
            master, fg_color=CARD, corner_radius=24,
            border_width=2, border_color=BORDER, cursor="hand2",
        )
        self._command = command
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=16)
        self._icon = ctk_icon(kind, 72)
        ctk.CTkLabel(body, image=self._icon, text="").pack()
        ctk.CTkLabel(
            body, text=title, font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT
        ).pack(pady=(10, 2))
        ctk.CTkLabel(
            body, text=desc, text_color=MUTED, wraplength=200, justify="center",
            font=ctk.CTkFont(size=12),
        ).pack()
        ctk.CTkLabel(body, text="Abrir →", text_color=PURPLE, font=ctk.CTkFont(size=12, weight="bold")).pack(
            pady=(10, 0)
        )

        make_hoverable(
            self,
            lambda: self.configure(fg_color=ROSE_SOFT, border_color=PURPLE, border_width=3),
            lambda: self.configure(fg_color=CARD, border_color=BORDER, border_width=2),
        )
        make_clickable(self, command)
