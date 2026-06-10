"""

INSTALACIÓN (ejecutar una sola vez):
    pip install -r requirements.txt


"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import speech_recognition as sr
import threading
import datetime
import os
import queue
import re
import sys

# ─────────────────────────────────────────────
#  MODO OFFLINE (Vosk) — import opcional
# ─────────────────────────────────────────────
VOSK_DISPONIBLE = False
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    import sounddevice as sd
    import json
    import urllib.request
    import zipfile
    VOSK_DISPONIBLE = True
except ImportError:
    pass

# ─────────────────────────────────────────────
#  OCR (EasyOCR) — import opcional
# ─────────────────────────────────────────────
OCR_DISPONIBLE = False
try:
    import easyocr
    OCR_DISPONIBLE = True
except ImportError:
    pass

RUTA_MODELO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "models", "vosk-model-small-es-0.42"
)
URL_MODELO = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"

# ─────────────────────────────────────────────
#  IDIOMAS SOPORTADOS
# ─────────────────────────────────────────────
IDIOMAS_DICTADO = [
    "Español (Argentina)",
    "Español (España)",
    "English (US)",
    "English (UK)",
    "Português (Brasil)",
    "Français",
    "Deutsch",
    "Italiano",
    "日本語",
    "中文",
]
CODIGOS_DICTADO = {
    "Español (Argentina)": "es-AR",
    "Español (España)": "es-ES",
    "English (US)": "en-US",
    "English (UK)": "en-GB",
    "Português (Brasil)": "pt-BR",
    "Français": "fr-FR",
    "Deutsch": "de-DE",
    "Italiano": "it-IT",
    "日本語": "ja-JP",
    "中文": "zh-CN",
}
IDIOMAS_TRADUCCION = [
    "English",
    "Português",
    "Français",
    "Deutsch",
    "Italiano",
    "日本語",
    "中文",
]
CODIGOS_TRADUCCION = {
    "English": "en",
    "Português": "pt",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "日本語": "ja",
    "中文": "zh-cn",
}

# ─────────────────────────────────────────────
#  COMANDOS DE VOZ → ACCIÓN
# ─────────────────────────────────────────────
COMANDOS = {
    # Puntuación
    "punto":                    ("insertar", "."),
    "coma":                     ("insertar", ","),
    "punto y coma":             ("insertar", ";"),
    "dos puntos":               ("insertar", ":"),
    "signo de pregunta":        ("insertar", "?"),
    "interrogación":            ("insertar", "?"),
    "signo de exclamación":     ("insertar", "!"),
    "admiración":               ("insertar", "!"),
    "puntos suspensivos":       ("insertar", "..."),
    "guión":                    ("insertar", " - "),
    "apertura de paréntesis":   ("insertar", "("),
    "cierre de paréntesis":     ("insertar", ")"),
    "comillas":                 ("insertar", '"'),
    # Formato
    "nueva línea":              ("accion", "nueva_linea"),
    "nuevo párrafo":            ("accion", "nuevo_parrafo"),
    "espacio":                  ("insertar", " "),
    "mayúsculas":               ("accion", "mayusculas"),
    # Edición
    "borrar última palabra":    ("accion", "borrar_ultima"),
    "borrar última línea":      ("accion", "borrar_ultima_linea"),
    "borrar todo":              ("accion", "borrar_todo"),
    # Archivo
    "guardar":                  ("accion", "guardar"),
    "guardar como":             ("accion", "guardar_como"),
    # Control del dictado
    "detener":                  ("accion", "detener"),
    "parar":                    ("accion", "detener"),
    "stop":                     ("accion", "detener"),
    "pausar":                   ("accion", "detener"),
}


class RedactorPorVoz:
    def __init__(self, root):
        self.root = root
        self.root.title("✍ NoHands")
        self.root.configure(bg="#1a1a2e")
        self.root.minsize(800, 580)

        ancho = self.root.winfo_screenwidth()
        alto = self.root.winfo_screenheight()
        geo_ancho = min(int(ancho * 0.78), 1200)
        geo_alto = min(int(alto * 0.82), 800)
        x = (ancho - geo_ancho) // 2
        y = (alto - geo_alto) // 2
        self.root.geometry(f"{geo_ancho}x{geo_alto}+{x}+{y}")
        self._panel_width = max(200, min(240, int(geo_ancho * 0.18)))
        self._font_scale = min(1.3, max(0.8, geo_ancho / 1100))
        self._btn_font = ("Segoe UI", max(8, round(9 * self._font_scale)))
        self._btn_font_small = ("Segoe UI", max(7, round(8 * self._font_scale)))
        self._lbl_font = ("Segoe UI", max(8, round(7 * self._font_scale)))
        self._chk_font = ("Segoe UI", max(7, round(7 * self._font_scale)))

        # Estado
        self.escuchando = False
        self.archivo_actual = None
        self.hilo_dictado = None
        self.cola_texto = queue.Queue()
        self.mayusculas_siguiente = False
        self.reconocedor = sr.Recognizer()
        self.reconocedor.pause_threshold = 0.8
        self.reconocedor.energy_threshold = 300

        # Estado modo offline
        self.modo_offline = False
        self.modelo_vosk = None
        self.rec_vosk = None
        self._temp_wav = None

        # OCR
        self._ocr_reader = None

        # Idiomas
        self.idioma_dictado = "es-AR"
        self.idioma_traduccion = "en"
        self.traductor = None

        self._construir_ui()
        self._actualizar_cola()

    # ──────────────────────────────────────────
    #  INTERFAZ GRÁFICA
    # ──────────────────────────────────────────
    def _construir_ui(self):
        # Paleta de colores
        BG       = "#1a1a2e"
        PANEL    = "#16213e"
        ACENTO   = "#0f3460"
        VERDE    = "#4ecca3"
        ROJO     = "#e94560"
        TEXTO    = "#eaeaea"
        SUBTEXTO = "#8892b0"

        self.root.configure(bg=BG)

        # ── Encabezado ──
        header = tk.Frame(self.root, bg=ACENTO, pady=12)
        header.pack(fill="x")

        tk.Label(
            header, text="🎙 NoHands",
            font=("Segoe UI", round(17 * self._font_scale), "bold"),
            bg=ACENTO, fg=VERDE
        ).pack(side="left", padx=20)

        tk.Label(
            header,
            text="Diseñado para personas con discapacidad o lesiones",
            font=("Segoe UI", round(9 * self._font_scale)),
            bg=ACENTO, fg=SUBTEXTO
        ).pack(side="left", padx=10)

        # ── Barra de estado superior ──
        barra_top = tk.Frame(self.root, bg=PANEL, pady=6)
        barra_top.pack(fill="x")

        self.lbl_estado = tk.Label(
            barra_top,
            text="⏸  Dictado detenido — presioná 'Iniciar Dictado'",
            font=("Segoe UI", max(8, round(9 * self._font_scale))),
            bg=PANEL, fg=SUBTEXTO, anchor="w"
        )
        self.lbl_estado.pack(side="left", padx=15)

        self.lbl_archivo = tk.Label(
            barra_top,
            text="📄 Sin guardar",
            font=("Segoe UI", max(8, round(9 * self._font_scale))),
            bg=PANEL, fg=SUBTEXTO, anchor="e"
        )
        self.lbl_archivo.pack(side="right", padx=15)

        # ── Área principal (texto + panel lateral) ──
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Bloc de notas
        frame_texto = tk.Frame(main, bg=PANEL, bd=1, relief="flat")
        frame_texto.pack(side="left", fill="both", expand=True)

        tk.Label(
            frame_texto, text="DOCUMENTO",
            font=("Segoe UI", max(8, round(7 * self._font_scale)), "bold"),
            bg=PANEL, fg=SUBTEXTO, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 0))

        self.texto = scrolledtext.ScrolledText(
            frame_texto,
            font=("Georgia", max(10, round(12 * self._font_scale))),
            bg="#0d1b2a",
            fg=TEXTO,
            insertbackground=VERDE,
            selectbackground=ACENTO,
            relief="flat",
            wrap="word",
            padx=16, pady=12,
            undo=True,
        )
        self.texto.pack(fill="both", expand=True, padx=8, pady=8)

        # Panel lateral
        panel = tk.Frame(main, bg=PANEL, width=self._panel_width, bd=0)
        panel.pack(side="right", fill="y", padx=(8, 0))
        panel.pack_propagate(False)

        # Indicador de micrófono
        self.canvas_mic = tk.Canvas(
            panel, width=100, height=100,
            bg=PANEL, highlightthickness=0
        )
        self.canvas_mic.pack(pady=(20, 5))
        self._dibujar_mic(activo=False)

        self.lbl_mic = tk.Label(
            panel, text="Micrófono\napagado",
            font=("Segoe UI", round(9 * self._font_scale), "bold"),
            bg=PANEL, fg=ROJO, justify="center"
        )
        self.lbl_mic.pack()

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=15)

        # Botones de control
        self.btn_iniciar = tk.Button(
            panel, text="▶  Iniciar Dictado",
            font=self._btn_font,
            bg=VERDE, fg="#0d1b2a",
            activebackground="#3ab88f",
            relief="flat", pady=8, cursor="hand2",
            command=self.iniciar_dictado
        )
        self.btn_iniciar.pack(fill="x", padx=12, pady=3)

        self.btn_detener = tk.Button(
            panel, text="⏹  Detener Dictado",
            font=self._btn_font,
            bg=ROJO, fg="white",
            activebackground="#c73652",
            relief="flat", pady=8, cursor="hand2",
            state="disabled",
            command=self.detener_dictado
        )
        self.btn_detener.pack(fill="x", padx=12, pady=3)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=10)

        tk.Button(
            panel, text="💾  Guardar",
            font=self._btn_font_small,
            bg=ACENTO, fg=TEXTO,
            activebackground="#1a4a7a",
            relief="flat", pady=6, cursor="hand2",
            command=self.guardar
        ).pack(fill="x", padx=12, pady=2)

        tk.Button(
            panel, text="📂  Guardar Como…",
            font=self._btn_font_small,
            bg=ACENTO, fg=TEXTO,
            activebackground="#1a4a7a",
            relief="flat", pady=6, cursor="hand2",
            command=self.guardar_como
        ).pack(fill="x", padx=12, pady=2)

        tk.Button(
            panel, text="📁  Abrir Archivo",
            font=self._btn_font_small,
            bg=ACENTO, fg=TEXTO,
            activebackground="#1a4a7a",
            relief="flat", pady=6, cursor="hand2",
            command=self.abrir
        ).pack(fill="x", padx=12, pady=2)

        tk.Button(
            panel, text="📂  Transcribir Audio…",
            font=self._btn_font_small,
            bg="#533483", fg=TEXTO,
            activebackground="#6b44a3",
            relief="flat", pady=6, cursor="hand2",
            command=self._transcribir_audio
        ).pack(fill="x", padx=12, pady=2)

        btn_ocr = tk.Button(
            panel, text="📸  Extraer texto de imagen…",
            font=self._btn_font_small,
            bg="#533483", fg=TEXTO,
            activebackground="#6b44a3",
            relief="flat", pady=6, cursor="hand2",
            command=self._extraer_texto_imagen
        )
        btn_ocr.pack(fill="x", padx=12, pady=2)
        if not OCR_DISPONIBLE:
            btn_ocr.config(state="disabled")

        tk.Button(
            panel, text="🗑  Limpiar Todo",
            font=self._btn_font_small,
            bg="#2d2d44", fg=SUBTEXTO,
            activebackground="#3d3d54",
            relief="flat", pady=6, cursor="hand2",
            command=self._borrar_todo
        ).pack(fill="x", padx=12, pady=2)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=10)

        # ── Selector de modo: Online / Offline ──
        tk.Label(
            panel, text="MODO DE RECONOCIMIENTO",
            font=self._lbl_font,
            bg=PANEL, fg=SUBTEXTO
        ).pack(anchor="w", padx=12, pady=(0, 2))

        self.modo_var = tk.StringVar(value="online")
        rb_frame = tk.Frame(panel, bg=PANEL)
        rb_frame.pack(fill="x", padx=12, pady=1)

        tk.Radiobutton(
            rb_frame, text="🌐 Online (Google)",
            variable=self.modo_var, value="online",
            font=self._chk_font, bg=PANEL, fg=TEXTO,
            selectcolor=PANEL, activebackground=PANEL,
            command=self._cambiar_modo
        ).pack(anchor="w")

        tk.Radiobutton(
            rb_frame, text="💻 Offline (Vosk)",
            variable=self.modo_var, value="offline",
            font=self._chk_font, bg=PANEL, fg=TEXTO,
            selectcolor=PANEL, activebackground=PANEL,
            command=self._cambiar_modo
        ).pack(anchor="w")

        self.lbl_modelo = tk.Label(
            panel, text="",
            font=self._chk_font,
            bg=PANEL, fg=SUBTEXTO, anchor="w", justify="left"
        )
        self.lbl_modelo.pack(fill="x", padx=12, pady=(1, 3))

        self.btn_descargar = tk.Button(
            panel, text="📥 Descargar modelo",
            font=self._chk_font,
            bg=ACENTO, fg=TEXTO,
            activebackground="#1a4a7a",
            relief="flat", pady=2, cursor="hand2",
            command=self._descargar_modelo
        )

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # ── Selector de idioma de dictado ──
        lbl_frame = tk.Frame(panel, bg=PANEL)
        lbl_frame.pack(fill="x", padx=12, pady=(0, 1))
        tk.Label(
            lbl_frame, text="IDIOMA DE DICTADO",
            font=self._lbl_font,
            bg=PANEL, fg=SUBTEXTO
        ).pack(side="left")
        tk.Label(
            lbl_frame, text="(requiere internet en offline)",
            font=("Segoe UI", max(6, round(6 * self._font_scale))),
            bg=PANEL, fg="#e94560"
        ).pack(side="right")

        self.idioma_dictado_var = tk.StringVar(value=IDIOMAS_DICTADO[0])
        self.cmb_idioma_dictado = ttk.Combobox(
            panel, textvariable=self.idioma_dictado_var,
            values=IDIOMAS_DICTADO, state="readonly",
            font=self._chk_font, height=10
        )
        self.cmb_idioma_dictado.pack(fill="x", padx=12, pady=(0, 3))
        self.cmb_idioma_dictado.bind("<<ComboboxSelected>>", self._cambiar_idioma_dictado)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=3)

        # ── Traducción ──
        lbl_frame2 = tk.Frame(panel, bg=PANEL)
        lbl_frame2.pack(fill="x", padx=12, pady=(0, 1))
        tk.Label(
            lbl_frame2, text="TRADUCIR A",
            font=self._lbl_font,
            bg=PANEL, fg=SUBTEXTO
        ).pack(side="left")
        tk.Label(
            lbl_frame2, text="(requiere internet)",
            font=("Segoe UI", max(6, round(6 * self._font_scale))),
            bg=PANEL, fg="#e94560"
        ).pack(side="right")

        self.idioma_trad_var = tk.StringVar(value=IDIOMAS_TRADUCCION[0])
        self.cmb_idioma_trad = ttk.Combobox(
            panel, textvariable=self.idioma_trad_var,
            values=IDIOMAS_TRADUCCION, state="readonly",
            font=self._chk_font, height=10
        )
        self.cmb_idioma_trad.pack(fill="x", padx=12, pady=(0, 2))
        self.cmb_idioma_trad.bind("<<ComboboxSelected>>", self._cambiar_idioma_trad)

        btn_traducir = tk.Button(
            panel, text="🌐  Traducir documento",
            font=self._btn_font_small,
            bg="#533483", fg=TEXTO,
            activebackground="#6b44a3",
            relief="flat", pady=3, cursor="hand2",
            command=self._traducir_documento
        )
        btn_traducir.pack(fill="x", padx=12, pady=(0, 2))

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=10, pady=3)

        # Mini-ayuda de comandos
        tk.Label(
            panel, text="COMANDOS: punto, coma, nueva línea, guardar, borrar última palabra, detener",
            font=("Segoe UI", max(6, round(6 * self._font_scale))),
            bg=PANEL, fg=SUBTEXTO, wraplength=200
        ).pack(anchor="w", padx=12)

        # ── Barra inferior (última frase reconocida) ──
        barra_bot = tk.Frame(self.root, bg="#0d1b2a", pady=6)
        barra_bot.pack(fill="x", side="bottom")

        tk.Label(barra_bot, text="Última frase reconocida:",
                 font=("Segoe UI", max(7, round(8 * self._font_scale))), bg="#0d1b2a", fg=SUBTEXTO).pack(side="left", padx=10)

        self.lbl_ultima = tk.Label(
            barra_bot, text="—",
            font=("Segoe UI", max(8, round(9 * self._font_scale)), "italic"),
            bg="#0d1b2a", fg=VERDE, anchor="w"
        )
        self.lbl_ultima.pack(side="left", padx=5)

        # Contador de palabras
        self.lbl_palabras = tk.Label(
            barra_bot, text="Palabras: 0",
            font=("Segoe UI", max(7, round(8 * self._font_scale))),
            bg="#0d1b2a", fg=SUBTEXTO
        )
        self.lbl_palabras.pack(side="right", padx=15)

        self.texto.bind("<<Modified>>", self._actualizar_contador)

        # Estado inicial del selector de modo
        self._actualizar_estado_modelo()

    def _dibujar_mic(self, activo: bool):
        self.canvas_mic.delete("all")
        color = "#4ecca3" if activo else "#e94560"
        if activo:
            self.canvas_mic.create_oval(10, 10, 90, 90, outline=color, width=2)
        self.canvas_mic.create_rectangle(35, 20, 65, 60,
                                          fill=color, outline="", width=0)
        self.canvas_mic.create_oval(30, 45, 70, 65,
                                     fill=color, outline="", width=0)
        self.canvas_mic.create_line(50, 65, 50, 80, fill=color, width=3)
        self.canvas_mic.create_line(38, 80, 62, 80, fill=color, width=3)

    # ──────────────────────────────────────────
    #  SELECCIÓN DE MODO
    # ──────────────────────────────────────────
    def _actualizar_estado_modelo(self):
        """Actualiza la etiqueta de estado del modelo y muestra/oculta botón descarga."""
        if not VOSK_DISPONIBLE:
            self.lbl_modelo.config(text="⚠️ Vosk no instalado\nCorré: pip install vosk", fg="#e94560")
            self.btn_descargar.pack_forget()
            return
        if os.path.isdir(RUTA_MODELO):
            self.lbl_modelo.config(text="✅ Modelo Vosk listo", fg="#4ecca3")
            self.btn_descargar.pack_forget()
        else:
            self.lbl_modelo.config(text="❌ Modelo no descargado", fg="#e94560")
            self.btn_descargar.pack(fill="x", padx=12, pady=(0, 3))

    def _cambiar_modo(self):
        """Callback al cambiar el radio button de modo."""
        if self.escuchando:
            self.detener_dictado()
        es_offline = self.modo_var.get() == "offline"
        self.modo_offline = es_offline
        if es_offline:
            if not VOSK_DISPONIBLE:
                self.lbl_estado.config(text="❌ Vosk no está instalado. Ejecutá: pip install vosk", fg="#e94560")
                self.modo_var.set("online")
                self.modo_offline = False
                return
            if not os.path.isdir(RUTA_MODELO):
                self.lbl_estado.config(text="❌ Modelo Vosk no encontrado. Descargalo abajo.", fg="#e94560")
                self.modo_var.set("online")
                self.modo_offline = False
                return
            if self._cargar_modelo_vosk():
                self.lbl_estado.config(text="✅ Modo offline listo para dictar", fg="#4ecca3")
            else:
                self.lbl_estado.config(text="❌ Error al cargar modelo Vosk", fg="#e94560")
                self.modo_var.set("online")
                self.modo_offline = False
        else:
            self.modelo_vosk = None
            self.rec_vosk = None
            self.lbl_estado.config(text="🌐 Modo online (Google) seleccionado", fg="#8892b0")

    def _cargar_modelo_vosk(self):
        """Carga el modelo Vosk en memoria. Retorna True si éxito."""
        if not VOSK_DISPONIBLE:
            return False
        if self.modelo_vosk is not None:
            return True
        try:
            SetLogLevel(-1)
            self.modelo_vosk = Model(RUTA_MODELO)
            self.rec_vosk = KaldiRecognizer(self.modelo_vosk, 16000)
            return True
        except Exception as e:
            self.modelo_vosk = None
            self.rec_vosk = None
            return False

    def _descargar_modelo(self):
        """Descarga y extrae el modelo Vosk español en segundo plano."""
        if not VOSK_DISPONIBLE:
            return
        self.btn_descargar.config(state="disabled", text="⏳ Descargando…")
        self.lbl_modelo.config(text="⏳ Descargando modelo (38 MB)…", fg="#8892b0")
        self.root.update()

        def tarea():
            try:
                zip_path = RUTA_MODELO + ".zip"
                urllib.request.urlretrieve(URL_MODELO, zip_path)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(os.path.dirname(RUTA_MODELO))
                os.remove(zip_path)
                self.root.after(0, lambda: self.lbl_modelo.config(
                    text="✅ Modelo descargado correctamente", fg="#4ecca3"))
                self.root.after(0, lambda: self.btn_descargar.pack_forget())
                self.root.after(0, lambda: self.lbl_estado.config(
                    text="✅ Modelo Vosk listo. Podés cambiar a modo offline.", fg="#4ecca3"))
                if self.modo_offline:
                    self.root.after(0, self._cargar_modelo_vosk)
            except Exception as e:
                self.root.after(0, lambda: self.lbl_modelo.config(
                    text=f"❌ Error: {e}", fg="#e94560"))
            finally:
                self.root.after(0, lambda: self.btn_descargar.config(
                    state="normal", text="📥 Descargar modelo"))

        threading.Thread(target=tarea, daemon=True).start()

    # ──────────────────────────────────────────
    #  SELECCIÓN DE IDIOMAS
    # ──────────────────────────────────────────
    def _cambiar_idioma_dictado(self, event=None):
        nombre = self.idioma_dictado_var.get()
        self.idioma_dictado = CODIGOS_DICTADO.get(nombre, "es-AR")
        if not self.escuchando:
            self.lbl_estado.config(text=f"🌐 Idioma: {nombre} ({self.idioma_dictado})", fg="#8892b0")

    def _cambiar_idioma_trad(self, event=None):
        nombre = self.idioma_trad_var.get()
        self.idioma_traduccion = CODIGOS_TRADUCCION.get(nombre, "en")

    def _traducir_documento(self):
        contenido = self.texto.get("1.0", "end-1c").strip()
        if not contenido:
            self.lbl_estado.config(text="⚠️ No hay texto para traducir", fg="#e94560")
            return
        self.lbl_estado.config(text="⏳ Traduciendo…", fg="#8892b0")
        threading.Thread(target=self._ejecutar_traduccion, daemon=True).start()

    def _ejecutar_traduccion(self):
        try:
            import asyncio
            from googletrans import Translator
            if self.traductor is None:
                self.traductor = Translator()
            contenido = self.texto.get("1.0", "end-1c").strip()
            destino = self.idioma_traduccion
            resultado = asyncio.run(
                self.traductor.translate(contenido, dest=destino)
            )
            texto_traducido = resultado.text
            self.root.after(0, lambda: self.texto.delete("1.0", "end"))
            self.root.after(0, lambda: self.texto.insert("1.0", texto_traducido))
            self.root.after(0, lambda: self.lbl_estado.config(
                text=f"✅ Traducción lista", fg="#4ecca3"))
        except Exception as e:
            self.root.after(0, lambda: self.lbl_estado.config(
                text=f"❌ Error al traducir: {e}", fg="#e94560"))

    # ──────────────────────────────────────────
    #  LÓGICA DE DICTADO
    # ──────────────────────────────────────────
    def iniciar_dictado(self):
        if self.escuchando:
            return
        self.escuchando = True
        self.btn_iniciar.config(state="disabled")
        self.btn_detener.config(state="normal")

        if self.modo_offline:
            self.lbl_estado.config(text="🔴  Dictando (offline)… hablá con claridad", fg="#4ecca3")
            self.lbl_mic.config(text="Micrófono\nactivo (offline)", fg="#4ecca3")
            self._dibujar_mic(activo=True)
            self.hilo_dictado = threading.Thread(target=self._bucle_dictado_offline, daemon=True)
        else:
            self.lbl_estado.config(text="🔴  Dictando (online)… hablá con claridad", fg="#4ecca3")
            self.lbl_mic.config(text="Micrófono\nactivo (online)", fg="#4ecca3")
            self._dibujar_mic(activo=True)
            self.hilo_dictado = threading.Thread(target=self._bucle_dictado, daemon=True)
        self.hilo_dictado.start()

    def detener_dictado(self):
        self.escuchando = False
        self.btn_iniciar.config(state="normal")
        self.btn_detener.config(state="disabled")
        modo = "offline" if self.modo_offline else "online"
        self.lbl_estado.config(
            text=f"⏸  Dictado detenido ({modo}) — presioná 'Iniciar Dictado'",
            fg="#8892b0"
        )
        self.lbl_mic.config(text="Micrófono\napagado", fg="#e94560")
        self._dibujar_mic(activo=False)

    def _bucle_dictado(self):
        """Modo online: usa Google Speech API a través de speech_recognition."""
        try:
            microfono = sr.Microphone()
        except Exception:
            self.cola_texto.put(("error",
                "❌ No se encontró micrófono. Conectá uno e intentá de nuevo."))
            self.root.after(0, self.detener_dictado)
            return

        with microfono as fuente:
            self.reconocedor.adjust_for_ambient_noise(fuente, duration=0.5)

        while self.escuchando:
            try:
                with microfono as fuente:
                    audio = self.reconocedor.listen(fuente, timeout=5, phrase_time_limit=10)
                frase = self.reconocedor.recognize_google(audio, language=self.idioma_dictado).lower().strip()
                self.cola_texto.put(("frase", frase))
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                self.cola_texto.put(("info", "…"))
            except sr.RequestError:
                self.cola_texto.put(("comando", "fallback_offline"))
                break
            except Exception as e:
                self.cola_texto.put(("error", f"❌ Error: {e}"))
                break

    def _bucle_dictado_offline(self):
        """Modo offline: usa Vosk con sounddevice para captura de audio."""
        if not VOSK_DISPONIBLE or self.rec_vosk is None:
            self.cola_texto.put(("error", "❌ Vosk no disponible o modelo no cargado"))
            return

        try:
            q_audio = queue.Queue()

            def callback(indata, frames, time, status):
                if status:
                    print(status, file=sys.stderr)
                q_audio.put(bytes(indata))

            with sd.RawInputStream(samplerate=16000, blocksize=8000,
                                   dtype="int16", channels=1,
                                   callback=callback):
                self.cola_texto.put(("info", "offline_iniciado"))

                while self.escuchando:
                    data = q_audio.get()
                    if self.rec_vosk.AcceptWaveform(data):
                        result = json.loads(self.rec_vosk.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self.cola_texto.put(("frase", text))
        except Exception as e:
            self.cola_texto.put(("error", f"❌ Error en modo offline: {e}"))
        finally:
            self.root.after(0, self.detener_dictado)

    def _actualizar_cola(self):
        """Procesa mensajes del hilo de audio en el hilo de UI (cada 100ms)."""
        try:
            while True:
                tipo, dato = self.cola_texto.get_nowait()
                if tipo == "frase":
                    self._procesar_frase(dato)
                elif tipo == "info":
                    if dato == "offline_iniciado":
                        self.lbl_estado.config(text="🔴  Dictando (offline)… hablá con claridad", fg="#4ecca3")
                    elif dato == "…":
                        pass
                elif tipo == "comando":
                    if dato == "fallback_offline":
                        if VOSK_DISPONIBLE and os.path.isdir(RUTA_MODELO):
                            self.lbl_estado.config(
                                text="⚠️ Sin conexión, cambiando a modo offline…", fg="#e94560")
                            self.root.update()
                            self.modo_offline = True
                            self.modo_var.set("offline")
                            if self._cargar_modelo_vosk():
                                self.root.after(500, self.iniciar_dictado)
                            else:
                                self.lbl_estado.config(
                                    text="❌ No se pudo cargar modelo offline", fg="#e94560")
                        else:
                            self.lbl_estado.config(
                                text="❌ Sin conexión y Vosk no disponible", fg="#e94560")
                elif tipo == "error":
                    self.lbl_estado.config(text=dato, fg="#e94560")
                    self.detener_dictado()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._actualizar_cola)

    # ──────────────────────────────────────────
    #  PROCESAMIENTO DE FRASES / COMANDOS
    # ──────────────────────────────────────────
    def _procesar_frase(self, frase: str):
        self.lbl_ultima.config(text=f'"{frase}"')

        # Revisar si es un comando exacto
        for cmd, (tipo_accion, valor) in COMANDOS.items():
            if frase == cmd or frase.endswith(" " + cmd) and len(frase.split()) <= 4:
                if frase == cmd:
                    self._ejecutar_accion(tipo_accion, valor)
                    return

        # Revisar comandos incrustados al inicio o final
        for cmd, (tipo_accion, valor) in sorted(COMANDOS.items(), key=lambda x: -len(x[0])):
            if frase.startswith(cmd + " ") or frase == cmd:
                texto_extra = frase[len(cmd):].strip()
                self._ejecutar_accion(tipo_accion, valor)
                if texto_extra:
                    self._insertar_texto(texto_extra)
                return
            if frase.endswith(" " + cmd):
                texto_previo = frase[: -(len(cmd) + 1)].strip()
                if texto_previo:
                    self._insertar_texto(texto_previo)
                self._ejecutar_accion(tipo_accion, valor)
                return

        # Texto normal → insertar
        self._insertar_texto(frase)

    def _ejecutar_accion(self, tipo: str, valor: str):
        if tipo == "insertar":
            contenido = self.texto.get("1.0", "end-1c")
            if valor in ".,:;?!" and contenido.endswith(" "):
                self.texto.delete("end-2c", "end-1c")
            self.texto.insert("end", valor + " ")
        elif tipo == "accion":
            accion = valor
            if accion == "nueva_linea":
                self.texto.insert("end", "\n")
            elif accion == "nuevo_parrafo":
                self.texto.insert("end", "\n\n")
            elif accion == "mayusculas":
                self.mayusculas_siguiente = True
            elif accion == "borrar_ultima":
                self._borrar_ultima_palabra()
            elif accion == "borrar_ultima_linea":
                self._borrar_ultima_linea()
            elif accion == "borrar_todo":
                self._borrar_todo()
            elif accion == "guardar":
                self.root.after(0, self.guardar)
            elif accion == "guardar_como":
                self.root.after(0, self.guardar_como)
            elif accion == "detener":
                self.root.after(0, self.detener_dictado)

        self.texto.see("end")

    def _insertar_texto(self, texto: str):
        if not texto:
            return
        if self.mayusculas_siguiente:
            texto = texto.capitalize()
            self.mayusculas_siguiente = False
        else:
            contenido = self.texto.get("1.0", "end-1c").rstrip()
            if not contenido or contenido.endswith((".", "?", "!")):
                texto = texto.capitalize()
        self.texto.insert("end", texto + " ")
        self.texto.see("end")

    def _borrar_ultima_palabra(self):
        contenido = self.texto.get("1.0", "end-1c")
        palabras = contenido.rstrip().rsplit(" ", 1)
        nuevo = palabras[0] + " " if len(palabras) > 1 else ""
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", nuevo)

    def _borrar_ultima_linea(self):
        contenido = self.texto.get("1.0", "end-1c")
        lineas = contenido.rsplit("\n", 1)
        nuevo = lineas[0] if len(lineas) > 1 else ""
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", nuevo)

    def _borrar_todo(self):
        if messagebox.askyesno("Confirmar", "¿Borrar todo el contenido del documento?"):
            self.texto.delete("1.0", "end")

    # ──────────────────────────────────────────
    #  MANEJO DE ARCHIVOS
    # ──────────────────────────────────────────
    def guardar(self):
        if not self.archivo_actual:
            self.guardar_como()
            return
        contenido = self.texto.get("1.0", "end-1c")
        with open(self.archivo_actual, "w", encoding="utf-8") as f:
            f.write(contenido)
        self.lbl_archivo.config(text=f"💾 Guardado: {os.path.basename(self.archivo_actual)}")
        self.lbl_estado.config(text=f"✅ Guardado en {self.archivo_actual}")

    def guardar_como(self):
        nombre = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
            initialfile=f"dictado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        )
        if nombre:
            self.archivo_actual = nombre
            self.guardar()

    def abrir(self):
        nombre = filedialog.askopenfilename(
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")]
        )
        if nombre:
            with open(nombre, "r", encoding="utf-8") as f:
                contenido = f.read()
            self.texto.delete("1.0", "end")
            self.texto.insert("1.0", contenido)
            self.archivo_actual = nombre
            self.lbl_archivo.config(text=f"📄 {os.path.basename(nombre)}")

    # ──────────────────────────────────────────
    #  TRANSCRIPCIÓN DE ARCHIVOS DE AUDIO
    # ──────────────────────────────────────────
    def _transcribir_audio(self):
        nombre = filedialog.askopenfilename(
            title="Seleccionar archivo de audio",
            filetypes=[
                ("Audio", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma"),
                ("WAV", "*.wav"),
                ("MP3", "*.mp3"),
                ("M4A", "*.m4a"),
                ("FLAC", "*.flac"),
                ("OGG", "*.ogg"),
                ("Todos", "*.*"),
            ]
        )
        if not nombre:
            return

        self.btn_iniciar.config(state="disabled")
        self.lbl_estado.config(text="⏳ Transcribiendo audio…", fg="#8892b0")

        ventana_progreso = tk.Toplevel(self.root)
        ventana_progreso.title("Transcribiendo")
        ventana_progreso.geometry("300x100")
        ventana_progreso.configure(bg="#1a1a2e")
        ventana_progreso.resizable(False, False)
        ventana_progreso.transient(self.root)
        ventana_progreso.grab_set()

        tk.Label(ventana_progreso, text="⏳ Procesando audio…",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#4ecca3").pack(pady=(15, 5))
        barra = ttk.Progressbar(ventana_progreso, mode="indeterminate", length=250)
        barra.pack(pady=5)
        barra.start(10)

        def tarea():
            try:
                wav_path = self._convertir_a_wav(nombre)
                if wav_path is None:
                    self.root.after(0, ventana_progreso.destroy)
                    return

                self._temp_wav = wav_path if wav_path != nombre else None
                modo = "offline" if self.modo_offline else "online"

                if modo == "offline":
                    if not VOSK_DISPONIBLE or self.modelo_vosk is None:
                        self.root.after(0, ventana_progreso.destroy)
                        self.lbl_estado.config(
                            text="❌ Vosk no disponible. Cambiá a modo online.", fg="#e94560")
                        return
                    texto = self._transcribir_vosk(wav_path)
                else:
                    texto = self._transcribir_google(wav_path)

                self.root.after(0, ventana_progreso.destroy)

                if texto.strip():
                    self.root.after(0, lambda t=texto, n=nombre: self._insertar_texto_transcripcion(t, n))
                else:
                    self.lbl_estado.config(text="⚠️ No se reconoció audio en el archivo", fg="#e94560")

            except Exception as e:
                self.root.after(0, ventana_progreso.destroy)
                self.root.after(0, lambda: self.lbl_estado.config(
                    text=f"❌ Error al transcribir: {e}", fg="#e94560"))
            finally:
                self.root.after(0, lambda: self.btn_iniciar.config(state="normal"))

        threading.Thread(target=tarea, daemon=True).start()

    # ─────────────────────────────────────────────
    #  OCR — Extraer texto de imágenes
    # ─────────────────────────────────────────────
    def _obtener_ocr_reader(self):
        if self._ocr_reader is not None:
            return self._ocr_reader
        codigo = CODIGOS_DICTADO.get(self.idioma_dictado_var.get(), "es-AR")
        langs = [codigo.split("-")[0]]
        if langs[0] != "es":
            langs.append("es")
        self._ocr_reader = easyocr.Reader(langs, gpu=False)
        return self._ocr_reader

    def _extraer_texto_imagen(self):
        nombre = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("BMP", "*.bmp"),
                ("TIFF", "*.tiff *.tif"),
                ("WEBP", "*.webp"),
                ("Todos", "*.*"),
            ]
        )
        if not nombre:
            return

        self.lbl_estado.config(text="⏳ Extrayendo texto de imagen…", fg="#8892b0")
        self.btn_iniciar.config(state="disabled")

        ventana_progreso = tk.Toplevel(self.root)
        ventana_progreso.title("OCR")
        ventana_progreso.geometry("300x100")
        ventana_progreso.configure(bg="#1a1a2e")
        ventana_progreso.resizable(False, False)
        ventana_progreso.transient(self.root)
        ventana_progreso.grab_set()

        tk.Label(ventana_progreso, text="⏳ Procesando imagen…",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#4ecca3").pack(pady=(15, 5))
        barra = ttk.Progressbar(ventana_progreso, mode="indeterminate", length=250)
        barra.pack(pady=5)
        barra.start(10)

        def tarea():
            try:
                reader = self._obtener_ocr_reader()
                resultado = reader.readtext(nombre, paragraph=True)
                texto = "\n".join(p[1] for p in resultado)

                self.root.after(0, ventana_progreso.destroy)

                if texto.strip():
                    timestamp = datetime.datetime.now().strftime("%H:%M")
                    encabezado = f"\n\n── Texto extraído de imagen ({os.path.basename(nombre)}) [{timestamp}] ──\n"
                    self.root.after(0, lambda t=texto, e=encabezado: self._insertar_texto_ocr(t, e))
                else:
                    self.lbl_estado.config(text="⚠️ No se encontró texto en la imagen", fg="#e94560")

            except Exception as e:
                self.root.after(0, ventana_progreso.destroy)
                self.root.after(0, lambda: self.lbl_estado.config(
                    text=f"❌ Error OCR: {e}", fg="#e94560"))
            finally:
                self.root.after(0, lambda: self.btn_iniciar.config(state="normal"))

        threading.Thread(target=tarea, daemon=True).start()

    def _insertar_texto_ocr(self, texto, encabezado):
        self.texto.insert("end", encabezado)
        self.texto.insert("end", texto)
        self.texto.see("end")
        self.lbl_estado.config(text=f"✅ Texto extraído de imagen insertado", fg=VERDE)

    def _convertir_a_wav(self, ruta):
        """Convierte cualquier formato de audio a WAV 16kHz mono.
        Retorna la ruta del WAV, o None si falla."""
        if ruta.lower().endswith(".wav"):
            return ruta
        try:
            from pydub import AudioSegment
            import subprocess, shutil
            # Buscar ffmpeg en PATH o en ubicaciones comunes
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                candidates = [
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"),
                    r"C:\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                ]
                for c in candidates:
                    if os.path.isfile(c):
                        ffmpeg_path = c
                        break
            if ffmpeg_path:
                AudioSegment.converter = ffmpeg_path
            audio = AudioSegment.from_file(ruta)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            wav_path = ruta + "_temp.wav"
            audio.export(wav_path, format="wav")
            return wav_path
        except Exception as e:
            self.lbl_estado.config(
                text=f"❌ No se pudo convertir el audio: {e}", fg="#e94560")
            return None

    def _transcribir_google(self, wav_path):
        """Transcribe un archivo WAV usando Google Speech API."""
        with sr.AudioFile(wav_path) as source:
            audio = self.reconocedor.record(source)
        return self.reconocedor.recognize_google(audio, language=self.idioma_dictado)

    def _transcribir_vosk(self, wav_path):
        """Transcribe un archivo WAV usando Vosk offline."""
        import wave
        with wave.open(wav_path, "rb") as wf:
            rec = KaldiRecognizer(self.modelo_vosk, wf.getframerate())
            texto_parts = []
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        texto_parts.append(text)
            result = json.loads(rec.FinalResult())
            text = result.get("text", "").strip()
            if text:
                texto_parts.append(text)
        return " ".join(texto_parts)

    def _insertar_texto_transcripcion(self, texto, nombre_archivo):
        """Inserta el texto transcrito en el documento."""
        self.texto.insert("end", "\n")
        for parrafo in texto.split(". "):
            parrafo = parrafo.strip()
            if parrafo:
                self.texto.insert("end", parrafo.capitalize() + ".\n\n")
        self.lbl_ultima.config(text=f"✅ Transcripción completada")
        self.lbl_estado.config(
            text=f"✅ Transcripción insertada desde {os.path.basename(nombre_archivo)}",
            fg="#4ecca3")
        self.texto.see("end")
        if self._temp_wav and os.path.exists(self._temp_wav):
            try:
                os.remove(self._temp_wav)
            except Exception:
                pass
            self._temp_wav = None

    # ──────────────────────────────────────────
    #  UTILIDADES
    # ──────────────────────────────────────────
    def _actualizar_contador(self, event=None):
        contenido = self.texto.get("1.0", "end-1c")
        palabras = len(contenido.split()) if contenido.strip() else 0
        self.lbl_palabras.config(text=f"Palabras: {palabras}")
        self.texto.edit_modified(False)


# ─────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()

    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    app = RedactorPorVoz(root)

    def al_cerrar():
        app.escuchando = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", al_cerrar)
    root.mainloop()
