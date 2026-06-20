import tkinter as tk
from tkinter import ttk

from app.constants import TEMAS


class ThemeManager:
    def __init__(self, root, texto_widget, config_manager):
        self.root = root
        self.texto = texto_widget
        self.config = config_manager
        self._tema_actual = None
        self._fuente_actual = self.config.get("tamano_fuente", 12)
        self._nom_fuente = "Georgia"
        self._header_ref = None
        self._barra_top_ref = None
        self._lbl_estado_ref = None
        self._lbl_archivo_ref = None
        self._main_ref = None
        self._frame_texto_ref = None
        self._panel_outer_ref = None
        self._canvas_ref = None
        self._panel_ref = None
        self._canvas_mic_ref = None
        self._lbl_mic_ref = None
        self._barra_bot_ref = None

    def registrar_widgets(self, header, barra_top, lbl_estado, lbl_archivo,
                          main, frame_texto, panel_outer, canvas, panel,
                          canvas_mic, lbl_mic, barra_bot):
        self._header_ref = header
        self._barra_top_ref = barra_top
        self._lbl_estado_ref = lbl_estado
        self._lbl_archivo_ref = lbl_archivo
        self._main_ref = main
        self._frame_texto_ref = frame_texto
        self._panel_outer_ref = panel_outer
        self._canvas_ref = canvas
        self._panel_ref = panel
        self._canvas_mic_ref = canvas_mic
        self._lbl_mic_ref = lbl_mic
        self._barra_bot_ref = barra_bot

    @property
    def colores(self):
        return TEMAS.get(self._tema_actual, TEMAS["oscuro"])

    @property
    def tema_actual(self):
        return self._tema_actual

    @property
    def fuente_actual(self):
        return self._fuente_actual

    def aplicar(self, nombre_tema):
        self._tema_actual = nombre_tema
        c = TEMAS.get(nombre_tema, TEMAS["oscuro"])

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Vertical.TScrollbar",
                        background=c.get("acento", c["panel"]),
                        troughcolor=c["panel"],
                        bordercolor=c["panel"],
                        arrowcolor=c["texto"], relief="flat")
        style.configure("Horizontal.TScale",
                        background=c["panel"], troughcolor=c["acento"])

        self.root.configure(bg=c["bg"])
        if self._header_ref:
            self._header_ref.configure(bg=c["acento"])
            for w in self._header_ref.winfo_children():
                if isinstance(w, tk.Label):
                    w.configure(bg=c["acento"], fg=c["verde"] if "bold" in (w.cget("font") or "") else c["subtexto"])

        if self._barra_top_ref:
            self._barra_top_ref.configure(bg=c["panel"])
        if self._lbl_estado_ref:
            self._lbl_estado_ref.configure(bg=c["panel"], fg=c["subtexto"])
        if self._lbl_archivo_ref:
            self._lbl_archivo_ref.configure(bg=c["panel"], fg=c["subtexto"])

        if self._main_ref:
            self._main_ref.configure(bg=c["bg"])
        if self._frame_texto_ref:
            self._frame_texto_ref.configure(bg=c["panel"])
            for w in self._frame_texto_ref.winfo_children():
                if isinstance(w, tk.Label):
                    w.configure(bg=c["panel"], fg=c["subtexto"])

        self.texto.configure(
            bg=c["entrada_bg"], fg=c["texto"],
            insertbackground=c["verde"], selectbackground=c["acento"],
        )
        self._actualizar_tags_formato()

        if self._panel_outer_ref:
            self._panel_outer_ref.configure(bg=c["panel"])
        if self._canvas_ref:
            self._canvas_ref.configure(bg=c["panel"])
        if self._panel_ref:
            self._panel_ref.configure(bg=c["panel"])

        if self._canvas_mic_ref:
            self._canvas_mic_ref.configure(bg=c["panel"])
        if self._lbl_mic_ref:
            self._lbl_mic_ref.configure(bg=c["panel"])

        if self._panel_ref:
            for child in self._panel_ref.winfo_children():
                if isinstance(child, (tk.Label, tk.Frame, tk.Canvas)):
                    child.configure(bg=c["panel"])
                    if isinstance(child, tk.Label):
                        child.configure(bg=c["panel"])

        if self._barra_bot_ref:
            self._barra_bot_ref.configure(bg=c["barra_inferior"])
            for w in self._barra_bot_ref.winfo_children():
                if isinstance(w, tk.Label):
                    w.configure(bg=c["barra_inferior"])

    def _actualizar_tags_formato(self):
        t = self._fuente_actual
        fn = self._nom_fuente
        self.texto.tag_configure("bold", font=(fn, t, "bold"))
        self.texto.tag_configure("italic", font=(fn, t, "italic"))
        self.texto.tag_configure("underline", font=(fn, t, "underline"))
        self.texto.tag_configure("bold_italic", font=(fn, t, "bold italic"))

    def actualizar_fuente(self, tamano=None):
        if tamano is None:
            tamano = self._fuente_actual
        else:
            self._fuente_actual = tamano
            self.config.set("tamano_fuente", tamano)
        self.texto.configure(font=(self._nom_fuente, tamano))
        self._actualizar_tags_formato()
