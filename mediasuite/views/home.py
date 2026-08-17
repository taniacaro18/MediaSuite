from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from mediasuite.theme import MUTED
from mediasuite.widgets import ModuleCard, PageHero


class HomeView(ctk.CTkScrollableFrame):
    def __init__(self, master, navigate: Callable[[str], None]):
        super().__init__(master, fg_color="transparent")
        self.navigate = navigate
        self._cards: list[ModuleCard] = []

        PageHero(
            self,
            "inicio",
            "¿Qué quieres editar?",
            "Pasa el mouse sobre una herramienta y haz clic en toda la tarjeta. Igual que en CapCut o Filmora.",
        ).pack(fill="x", pady=(4, 14))

        cards = [
            ("silencios", "Recortar silencios", "Quita pausas de videos largos."),
            ("marcas", "Marcas de agua", "Crop de barras o blur de logo."),
            ("convertir", "Convertir", "MP4, MKV, MOV, WebM y CRF."),
            ("imagenes", "Imágenes", "Lote, firma e histograma."),
            ("audio", "Audio", "Extrae MP3/WAV y normaliza."),
        ]
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        for i, (key, title, desc) in enumerate(cards):
            card = ModuleCard(grid, key, title, desc, lambda k=key: self.navigate(k))
            self._cards.append(card)
            r, c = divmod(i, 3)
            card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
        grid.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            self,
            text="La línea de tiempo de abajo se mueve cuando exportas. El botón Parar cancela el render.",
            text_color=MUTED,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(10, 8))
