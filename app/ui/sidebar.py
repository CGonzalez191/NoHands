import tkinter as tk
from tkinter import ttk

import app
from app.constants import (
    IDIOMAS_DICTADO, IDIOMAS_TRADUCCION, TEMA_NOMBRES,
    MODELO_WHISPER_PREDET, MODELOS_WHISPER_DISP,
    VOSK_MODELO_PREDET,
)


class Sidebar:
    def __init__(self, parent, app_window, panel_frame, config, theme,
                 fonts, panel_width, font_scale):
        self.parent = parent
        self.app = app_window
        self.panel = panel_frame
        self.config = config
        self.theme = theme
        self._btn_font = fonts["btn"]
        self._btn_font_small = fonts["btn_small"]
        self._lbl_font = fonts["lbl"]
        self._chk_font = fonts["chk"]
        self._panel_width = panel_width
        self._font_scale = font_scale
        self._widgets = {}
        self._vars = {}
        self._build()

    def _c(self):
        return self.theme.colores

    def _build(self):
        c = self._c()
        self._build_mic()
        self._build_dictado_btns(c)
        self._build_file_ops(c)
        self._build_services(c)
        self._build_visual_config(c)
        self._build_recognition_mode(c)
        self._build_language(c)
        self._build_pausas(c)
        self._build_hands_free(c)
        self._build_comandos(c)

    def _build_mic(self):
        c = self._c()
        self._widgets["canvas_mic"] = tk.Canvas(
            self.panel, width=100, height=100, bg=c["panel"], highlightthickness=0)
        self._widgets["canvas_mic"].pack(pady=(20, 5))
        self._widgets["lbl_mic"] = tk.Label(
            self.panel, text="Microfono\napagado",
            font=("Segoe UI", round(9 * self._font_scale), "bold"),
            bg=c["panel"], fg=c["rojo"], justify="center")
        self._widgets["lbl_mic"].pack()

    def mic_widgets(self):
        return self._widgets.get("canvas_mic"), self._widgets.get("lbl_mic")

    def _build_dictado_btns(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=12)
        self._widgets["btn_iniciar"] = tk.Button(
            self.panel, text="   Iniciar Dictado", font=self._btn_font,
            bg=c["verde"], fg="#0d1b2a", activebackground="#3ab88f",
            relief="flat", pady=8, cursor="hand2", command=self.app.iniciar_dictado)
        self._widgets["btn_iniciar"].pack(fill="x", padx=12, pady=3)
        self._widgets["btn_detener"] = tk.Button(
            self.panel, text="   Detener Dictado", font=self._btn_font,
            bg=c["rojo"], fg="white", activebackground="#c73652",
            relief="flat", pady=8, cursor="hand2", state="disabled",
            command=self.app.detener_dictado)
        self._widgets["btn_detener"].pack(fill="x", padx=12, pady=3)

    def _build_file_ops(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=8)
        self._btn("  Guardar", self.app.guardar, c)
        self._btn("  Guardar Como...", self.app.guardar_como, c)

        btn_frame = tk.Frame(self.panel, bg=c["panel"])
        btn_frame.pack(fill="x", padx=12)
        for fmt, label, cmd in [
            ("docx", "  Exportar .docx", self.app._exportar_docx),
            ("pdf",  "  Exportar .pdf", self.app._exportar_pdf),
        ]:
            disp = app.DOCX_DISPONIBLE if fmt == "docx" else app.PDF_DISPONIBLE
            b = tk.Button(btn_frame, text=label, font=self._chk_font,
                          bg=c["acento"], fg=c["texto"],
                          activebackground=c.get("btn_activo", c["acento"]),
                          relief="flat", pady=3, cursor="hand2", command=cmd)
            b.pack(fill="x", pady=1)
            if not disp:
                b.config(state="disabled")

        self._btn("  Abrir Archivo", self.app.abrir, c)

    def _build_services(self, c):
        self._btn("  Transcribir Audio...", self.app._transcribir_audio, c, bg="#533483")
        btn_ocr = self._btn("  Extraer texto de imagen...", self.app._extraer_texto_imagen, c, bg="#533483")
        if not app.OCR_DISPONIBLE:
            btn_ocr.config(state="disabled")
        self._btn("  Limpiar Todo", self.app._borrar_todo, c, fg=c["subtexto"])

    def _build_visual_config(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=8)
        tk.Label(self.panel, text="CONFIGURACION VISUAL",
                 font=self._lbl_font, bg=c["panel"], fg=c["subtexto"]
                 ).pack(anchor="w", padx=12, pady=(5, 2))

        tema_frame = tk.Frame(self.panel, bg=c["panel"])
        tema_frame.pack(fill="x", padx=12, pady=1)
        self._vars["tema"] = tk.StringVar(value=self.config.get("tema", "oscuro"))
        for tema_id in ["oscuro", "claro", "alto_contraste"]:
            tk.Radiobutton(tema_frame, text=TEMA_NOMBRES[tema_id],
                           variable=self._vars["tema"], value=tema_id,
                           font=self._lbl_font, bg=c["panel"], fg=c["texto"],
                           selectcolor=c["panel"], activebackground=c["panel"],
                           command=self.app._cambiar_tema).pack(anchor="w")

        fs_frame = tk.Frame(self.panel, bg=c["panel"])
        fs_frame.pack(fill="x", padx=12, pady=3)
        tk.Label(fs_frame, text=f"Tamano fuente: {self.theme.fuente_actual}",
                 font=self._lbl_font, bg=c["panel"], fg=c["subtexto"]).pack(side="left")
        self._widgets["lbl_tam_fuente"] = fs_frame.winfo_children()[-1]
        self._widgets["scale_fuente"] = tk.Scale(
            self.panel, from_=8, to_=28, orient="horizontal",
            length=self._panel_width - 40, showvalue=True,
            font=self._lbl_font, bg=c["panel"], fg=c["texto"],
            troughcolor=c["acento"], highlightthickness=0,
            command=self.app._cambiar_fuente_slider)
        self._widgets["scale_fuente"].set(self.theme.fuente_actual)
        self._widgets["scale_fuente"].pack(fill="x", padx=12, pady=(0, 5))

    def _build_recognition_mode(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=5)
        tk.Label(self.panel, text="MODO DE RECONOCIMIENTO",
                 font=self._lbl_font, bg=c["panel"], fg=c["subtexto"]
                 ).pack(anchor="w", padx=12, pady=(0, 2))

        self._vars["modo"] = tk.StringVar(
            value="offline" if (app.VOSK_DISPONIBLE or app.WHISPER_DISPONIBLE) else "online")
        rb_frame = tk.Frame(self.panel, bg=c["panel"])
        rb_frame.pack(fill="x", padx=12, pady=1)
        tk.Radiobutton(rb_frame, text="  Online (Google)", variable=self._vars["modo"],
                       value="online", font=self._chk_font, bg=c["panel"], fg=c["texto"],
                       selectcolor=c["panel"], activebackground=c["panel"],
                       command=self.app._cambiar_modo).pack(anchor="w")
        tk.Radiobutton(rb_frame, text="  Offline (Vosk)", variable=self._vars["modo"],
                       value="offline", font=self._chk_font, bg=c["panel"], fg=c["texto"],
                       selectcolor=c["panel"], activebackground=c["panel"],
                       command=self.app._cambiar_modo).pack(anchor="w")

        wh_frame = tk.Frame(self.panel, bg=c["panel"])
        wh_frame.pack(fill="x", padx=12, pady=1)
        self._vars["engine"] = tk.StringVar(value=self.config.get("engine_offline", "vosk"))
        self._widgets["rb_whisper"] = tk.Radiobutton(
            wh_frame, text="  Whisper (mas preciso)", variable=self._vars["engine"],
            value="whisper", font=self._chk_font, bg=c["panel"], fg=c["texto"],
            selectcolor=c["panel"], activebackground=c["panel"],
            command=self.app._cambiar_engine)
        self._widgets["rb_whisper"].pack(anchor="w")
        if not app.WHISPER_DISPONIBLE:
            self._widgets["rb_whisper"].config(state="disabled")

        vosk_model_frame = tk.Frame(self.panel, bg=c["panel"])
        vosk_model_frame.pack(fill="x", padx=18, pady=(0, 2))
        tk.Label(vosk_model_frame, text="Modelo Vosk:", font=self._chk_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(side="left")
        self._vars["vosk_model"] = tk.StringVar(
            value=self.config.get("vosk_model", VOSK_MODELO_PREDET))
        self._widgets["cmb_vosk_model"] = ttk.Combobox(
            vosk_model_frame, textvariable=self._vars["vosk_model"],
            values=["small", "large"], state="readonly",
            font=self._chk_font, width=7)
        self._widgets["cmb_vosk_model"].pack(side="left", padx=3)
        self._widgets["cmb_vosk_model"].bind(
            "<<ComboboxSelected>>", self.app._cambiar_modelo_vosk)

        wh_model_frame = tk.Frame(self.panel, bg=c["panel"])
        if app.WHISPER_DISPONIBLE:
            wh_model_frame.pack(fill="x", padx=18, pady=(0, 3))
        tk.Label(wh_model_frame, text="Modelo:", font=self._chk_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(side="left")
        self._vars["whisper_model"] = tk.StringVar(
            value=self.config.get("whisper_model", MODELO_WHISPER_PREDET))
        self._widgets["cmb_whisper_model"] = ttk.Combobox(
            wh_model_frame, textvariable=self._vars["whisper_model"],
            values=MODELOS_WHISPER_DISP, state="readonly",
            font=self._chk_font, width=10)
        self._widgets["cmb_whisper_model"].pack(side="left", padx=3)
        self._widgets["cmb_whisper_model"].bind(
            "<<ComboboxSelected>>", self.app._cambiar_modelo_whisper)

        self._widgets["lbl_modelo"] = tk.Label(
            self.panel, text="", font=self._chk_font,
            bg=c["panel"], fg=c["subtexto"], anchor="w", justify="left")
        self._widgets["lbl_modelo"].pack(fill="x", padx=12, pady=(1, 3))
        self._widgets["btn_descargar"] = tk.Button(
            self.panel, text="  Descargar modelo", font=self._chk_font,
            bg=c["acento"], fg=c["texto"],
            activebackground=c.get("btn_activo", c["acento"]),
            relief="flat", pady=2, cursor="hand2", command=self.app._descargar_modelo)

    def _build_language(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=5)
        lbl_frame = tk.Frame(self.panel, bg=c["panel"])
        lbl_frame.pack(fill="x", padx=12, pady=(0, 1))
        tk.Label(lbl_frame, text="IDIOMA DE DICTADO", font=self._lbl_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(side="left")
        tk.Label(lbl_frame, text="(requiere internet en offline)",
                 font=("Segoe UI", max(6, round(6 * self._font_scale))),
                 bg=c["panel"], fg=c["rojo"]).pack(side="right")
        self._vars["idioma_dictado"] = tk.StringVar(value=IDIOMAS_DICTADO[0])
        self._widgets["cmb_idioma_dictado"] = ttk.Combobox(
            self.panel, textvariable=self._vars["idioma_dictado"],
            values=IDIOMAS_DICTADO, state="readonly",
            font=self._chk_font, height=10)
        self._widgets["cmb_idioma_dictado"].pack(fill="x", padx=12, pady=(0, 3))
        self._widgets["cmb_idioma_dictado"].bind(
            "<<ComboboxSelected>>", self.app._cambiar_idioma_dictado)

        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=3)
        lbl_frame2 = tk.Frame(self.panel, bg=c["panel"])
        lbl_frame2.pack(fill="x", padx=12, pady=(0, 1))
        tk.Label(lbl_frame2, text="TRADUCIR A", font=self._lbl_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(side="left")
        tk.Label(lbl_frame2, text="(requiere internet)",
                 font=("Segoe UI", max(6, round(6 * self._font_scale))),
                 bg=c["panel"], fg=c["rojo"]).pack(side="right")
        self._vars["idioma_trad"] = tk.StringVar(value=IDIOMAS_TRADUCCION[0])
        self._widgets["cmb_idioma_trad"] = ttk.Combobox(
            self.panel, textvariable=self._vars["idioma_trad"],
            values=IDIOMAS_TRADUCCION, state="readonly",
            font=self._chk_font, height=10)
        self._widgets["cmb_idioma_trad"].pack(fill="x", padx=12, pady=(0, 2))
        self._widgets["cmb_idioma_trad"].bind(
            "<<ComboboxSelected>>", self.app._cambiar_idioma_trad)
        self._btn("   Traducir documento", self.app._traducir_documento, c, bg="#533483",
                  font=self._btn_font_small, pady=3)

    def _build_pausas(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=5)
        tk.Label(self.panel, text="PAUSAS ACTIVAS", font=self._lbl_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(anchor="w", padx=12, pady=(0, 2))
        self._vars["pausas"] = tk.BooleanVar(value=self.config.get("pausas_activas", True))
        tk.Checkbutton(self.panel, text="Recordatorio 20-20-20 cada 20 min",
                       variable=self._vars["pausas"], font=self._chk_font,
                       bg=c["panel"], fg=c["texto"], selectcolor=c["panel"],
                       activebackground=c["panel"],
                       command=self.app._toggle_pausas).pack(anchor="w", padx=12)
        self._vars["auto_save"] = tk.BooleanVar(value=self.config.get("auto_guardar", True))
        tk.Checkbutton(self.panel, text="Auto-guardado cada",
                       variable=self._vars["auto_save"], font=self._chk_font,
                       bg=c["panel"], fg=c["texto"], selectcolor=c["panel"],
                       activebackground=c["panel"],
                       command=self.app._toggle_auto_save).pack(anchor="w", padx=12)
        as_frame = tk.Frame(self.panel, bg=c["panel"])
        as_frame.pack(fill="x", padx=20, pady=(0, 3))
        tk.Label(as_frame, text="minutos:", font=self._chk_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(side="left")
        self._widgets["auto_save_spin"] = tk.Spinbox(
            as_frame, from_=1, to_=60, width=3, font=self._chk_font,
            bg=c["texto_bg"], fg=c["texto"], buttonbackground=c["panel"], relief="flat")
        self._widgets["auto_save_spin"].delete(0, "end")
        self._widgets["auto_save_spin"].insert(
            0, str(self.config.get("intervalo_auto_guardar", 5)))
        self._widgets["auto_save_spin"].pack(side="left", padx=3)

        self._vars["feedback"] = tk.BooleanVar(value=self.config.get("feedback_sonoro", True))
        tk.Checkbutton(self.panel, text="Feedback sonoro",
                       variable=self._vars["feedback"], font=self._chk_font,
                       bg=c["panel"], fg=c["texto"], selectcolor=c["panel"],
                       activebackground=c["panel"],
                       command=self.app._toggle_feedback).pack(anchor="w", padx=12)

    def _build_hands_free(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=5)
        tk.Label(self.panel, text="MODO MANOS LIBRES", font=self._lbl_font,
                 bg=c["panel"], fg=c["subtexto"]).pack(anchor="w", padx=12, pady=(0, 2))
        self._vars["manos_libres"] = tk.BooleanVar(
            value=self.config.get("manos_libres", False))
        tk.Checkbutton(self.panel, text="Iniciar dictado automaticamente",
                       variable=self._vars["manos_libres"], font=self._chk_font,
                       bg=c["panel"], fg=c["texto"], selectcolor=c["panel"],
                       activebackground=c["panel"],
                       command=self.app._toggle_manos_libres).pack(anchor="w", padx=12)
        tk.Label(self.panel,
                 text="Al activarlo, el microfono se enciende solo al abrir la app.\nDeci 'ayuda' para ver todos los comandos.",
                 font=("Segoe UI", max(6, round(6 * self._font_scale))),
                 bg=c["panel"], fg=c["subtexto"], wraplength=220, justify="left"
                 ).pack(anchor="w", padx=12, pady=(0, 4))

    def _build_comandos(self, c):
        ttk.Separator(self.panel, orient="horizontal").pack(fill="x", padx=10, pady=5)
        tk.Label(self.panel,
                 text="COMANDOS: punto, coma, ayuda, cerrar, tabulacion, desplazar arriba/abajo, pagina arriba/abajo, fuente normal/grande/muy grande, usar vosk/whisper, auto guardar activado/desactivado, feedback sonoro activado/desactivado, tema alto contraste, modelo whisper tiny/base/small/medium/large -- Deci 'mostrar comandos' para la lista completa",
                 font=("Segoe UI", max(6, round(6 * self._font_scale))),
                 bg=c["panel"], fg=c["subtexto"], wraplength=220).pack(anchor="w", padx=12)

    def _btn(self, text, command, c, bg=None, fg=None, font=None, pady=6):
        b = tk.Button(
            self.panel, text=text,
            font=font or self._btn_font_small,
            bg=bg or c["acento"],
            fg=fg or c["texto"],
            activebackground=c.get("btn_activo", c["acento"]),
            relief="flat", pady=pady, cursor="hand2", command=command)
        b.pack(fill="x", padx=12, pady=2)
        return b

    def widget(self, name):
        return self._widgets.get(name)

    def var(self, name):
        return self._vars.get(name)
