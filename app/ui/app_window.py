import datetime
import os
import queue
import re
import sys
import threading
import time

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import app
from app.config import ConfigManager
from app.constants import (
    CODIGOS_DICTADO, CODIGOS_TRADUCCION,
    COMANDOS, TEMAS, MAPA_IDIOMAS_COMANDO, MAPA_TRADUCCION_VOZ,
    MODELO_WHISPER_PREDET, MODELOS_WHISPER_DISP, ruta_vosk, VOSK_MODELO_PREDET, VOSK_MODELOS,
)
from app.feedback import FeedbackSonoro
from app.recognition import (
    Listener, GoogleEngine, VoskEngine, WhisperEngine, convertir_a_wav,
)
from app.services import TranslationService, OcrService, FileService
from app.ui.theme_manager import ThemeManager
from app.ui.sidebar import Sidebar


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.config = ConfigManager()
        self.feedback = FeedbackSonoro(self.config)
        self.theme = ThemeManager(root, None, self.config)
        self.translator = TranslationService()
        self.ocr_service = OcrService()
        self.file_service = FileService()
        self._listener = Listener(queue.Queue(), self.config)

        self.cola_texto = self._listener.cola_texto
        self.escuchando = False
        self.archivo_actual = None
        self.mayusculas_siguiente = False
        self.idioma_dictado = "es-AR"
        self.idioma_traduccion = "en"

        self._sesion_inicio = None
        self._ultimo_break = 0
        self._alerta_sesion_larga_mostrada = False
        self._auto_save_after_id = None
        self._break_check_after_id = None
        self._temp_wav = None
        self._cerrando = False
        self._semaforo_tareas = threading.BoundedSemaphore(4)

        self._configurar_ventana()
        self._construir_ui()
        self.theme.registrar_widgets(
            self._header, self._barra_top, self.lbl_estado, self.lbl_archivo,
            self._main, self._frame_texto, self._panel_outer, self._canvas,
            self._panel, self.canvas_mic, self.lbl_mic, self._barra_bot,
        )
        self.theme.aplicar(self.config.get("tema", "oscuro"))
        self._inicializar_motor()
        self._procesar_cola()
        self._iniciar_temporizadores()
        self.root.after(1000, self._iniciar_listener)
        if self.config.get("manos_libres", False):
            self.root.after(2000, self.iniciar_dictado)

    def _configurar_ventana(self):
        self.root.title("  NoHands")
        self.root.minsize(800, 580)
        ancho = self.root.winfo_screenwidth()
        alto = self.root.winfo_screenheight()
        geo_ancho = min(int(ancho * 0.78), 1200)
        geo_alto = min(int(alto * 0.82), 800)
        x = (ancho - geo_ancho) // 2
        y = (alto - geo_alto) // 2
        self.root.geometry(f"{geo_ancho}x{geo_alto}+{x}+{y}")
        self._panel_width = max(200, min(260, int(geo_ancho * 0.20)))
        fs = min(1.3, max(0.8, geo_ancho / 1100))
        self._btn_font = ("Segoe UI", max(8, round(9 * fs)))
        self._btn_font_small = ("Segoe UI", max(7, round(8 * fs)))
        self._lbl_font = ("Segoe UI", max(8, round(7 * fs)))
        self._chk_font = ("Segoe UI", max(7, round(7 * fs)))
        self._font_scale = fs

    def _ruta_vosk_actual(self):
        nombre = self.config.get("vosk_model", VOSK_MODELO_PREDET)
        return ruta_vosk(nombre)

    def _inicializar_motor(self):
        engine_offline = self.config.get("engine_offline", "vosk")
        self._listener.engine_offline = engine_offline
        self._listener.idioma_dictado = self.idioma_dictado
        if self.sidebar.var("modo").get() == "offline":
            self._listener.modo_offline = True
            if engine_offline == "whisper" and app.WHISPER_DISPONIBLE:
                motor = WhisperEngine(self.config.get("whisper_model", MODELO_WHISPER_PREDET))
                if motor.cargar_modelo():
                    self._listener.motor = motor
                    self.lbl_estado.config(text="  Whisper activo", fg=self.theme.colores["verde"])
            elif engine_offline == "vosk" and app.VOSK_DISPONIBLE:
                motor = VoskEngine()
                if motor.cargar_modelo():
                    self._listener.motor = motor
                    self.lbl_estado.config(text="  Modo offline (Vosk) activo", fg=self.theme.colores["verde"])

    # -- UI Construction --

    def _construir_ui(self):
        c = self.theme.colores

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Vertical.TScrollbar", background=c.get("acento", c["panel"]),
                        troughcolor=c["panel"], bordercolor=c["panel"],
                        arrowcolor=c["texto"], relief="flat")
        style.configure("Horizontal.TScale", background=c["panel"], troughcolor=c["acento"])

        self._header = tk.Frame(self.root, bg=c["acento"], pady=12)
        self._header.pack(fill="x")
        tk.Label(self._header, text="  NoHands",
                 font=("Segoe UI", round(17 * self._font_scale), "bold"),
                 bg=c["acento"], fg=c["verde"]).pack(side="left", padx=20)
        tk.Label(self._header,
                 text="Disenado para personas con discapacidad o lesiones",
                 font=("Segoe UI", round(9 * self._font_scale)),
                 bg=c["acento"], fg=c["subtexto"]).pack(side="left", padx=10)

        self._barra_top = tk.Frame(self.root, bg=c["panel"], pady=6)
        self._barra_top.pack(fill="x")
        self.lbl_estado = tk.Label(self._barra_top,
                                   text="   Dictado detenido",
                                   font=("Segoe UI", max(8, round(9 * self._font_scale))),
                                   bg=c["panel"], fg=c["subtexto"], anchor="w")
        self.lbl_estado.pack(side="left", padx=15)
        self.lbl_archivo = tk.Label(self._barra_top,
                                    text="  Sin guardar",
                                    font=("Segoe UI", max(8, round(9 * self._font_scale))),
                                    bg=c["panel"], fg=c["subtexto"], anchor="e")
        self.lbl_archivo.pack(side="right", padx=15)

        self._main = tk.Frame(self.root, bg=c["bg"])
        self._main.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self._frame_texto = tk.Frame(self._main, bg=c["panel"], bd=1, relief="flat")
        self._frame_texto.pack(side="left", fill="both", expand=True)
        tk.Label(self._frame_texto, text="DOCUMENTO",
                 font=("Segoe UI", max(8, round(7 * self._font_scale)), "bold"),
                 bg=c["panel"], fg=c["subtexto"], anchor="w").pack(fill="x", padx=10, pady=(8, 0))

        self.texto = scrolledtext.ScrolledText(
            self._frame_texto, font=("Georgia", self.config.get("tamano_fuente", 12)),
            bg=c["entrada_bg"], fg=c["texto"], insertbackground=c["verde"],
            selectbackground=c["acento"], relief="flat", wrap="word",
            padx=16, pady=12, undo=True)
        self.texto.pack(fill="both", expand=True, padx=8, pady=8)
        self.theme.texto = self.texto

        self.texto.bind("<<Modified>>", self._actualizar_contador)

        self._panel_outer = tk.Frame(self._main, bg=c["panel"], width=self._panel_width, bd=0)
        self._panel_outer.pack(side="right", fill="y", padx=(8, 0))
        self._panel_outer.pack_propagate(False)

        self._canvas = tk.Canvas(self._panel_outer, bg=c["panel"], width=self._panel_width,
                                 highlightthickness=0, bd=0)
        scrollbar_p = ttk.Scrollbar(self._panel_outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar_p.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar_p.pack(side="right", fill="y")

        self._panel = tk.Frame(self._canvas, bg=c["panel"], width=self._panel_width)
        self._canvas.create_window((0, 0), window=self._panel, anchor="nw", width=self._panel_width)

        def conf_scroll(e):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._panel.bind("<Configure>", conf_scroll)

        def scroll(e):
            self._canvas.yview_scroll(-1 * (e.delta // 120), "units")
        self._canvas.bind("<Enter>", lambda e: self._canvas.bind_all("<MouseWheel>", scroll))
        self._canvas.bind("<Leave>", lambda e: self._canvas.unbind_all("<MouseWheel>"))

        self.sidebar = Sidebar(
            self, self, self._panel, self.config, self.theme,
            {"btn": self._btn_font, "btn_small": self._btn_font_small,
             "lbl": self._lbl_font, "chk": self._chk_font},
            self._panel_width, self._font_scale)
        self.canvas_mic, self.lbl_mic = self.sidebar.mic_widgets()

        self._barra_bot = tk.Frame(self.root, bg=c["barra_inferior"], pady=6)
        self._barra_bot.pack(fill="x", side="bottom")
        tk.Label(self._barra_bot, text="Ultima frase:",
                 font=("Segoe UI", max(7, round(8 * self._font_scale))),
                 bg=c["barra_inferior"], fg=c["subtexto"]).pack(side="left", padx=10)
        self.lbl_ultima = tk.Label(self._barra_bot, text="--",
                                   font=("Segoe UI", max(8, round(9 * self._font_scale)), "italic"),
                                   bg=c["barra_inferior"], fg=c["verde"], anchor="w")
        self.lbl_ultima.pack(side="left", padx=5)
        self.lbl_palabras = tk.Label(self._barra_bot, text="Palabras: 0",
                                     font=("Segoe UI", max(7, round(8 * self._font_scale))),
                                     bg=c["barra_inferior"], fg=c["subtexto"])
        self.lbl_palabras.pack(side="right", padx=15)
        self.lbl_tiempo_sesion = tk.Label(self._barra_bot, text="",
                                          font=("Segoe UI", max(7, round(8 * self._font_scale))),
                                          bg=c["barra_inferior"], fg=c["subtexto"])
        self.lbl_tiempo_sesion.pack(side="right", padx=15)

        self._actualizar_estado_modelo()

    # -- Listener Management --

    def _iniciar_listener(self):
        self._listener.detener()
        if self._listener.motor and self._listener.motor.nombre != "google":
            self._listener.iniciar()

    def _cambiar_modo(self):
        if self.escuchando:
            self.detener_dictado()
        es_offline = self.sidebar.var("modo").get() == "offline"
        self._listener.modo_offline = es_offline
        c = self.theme.colores
        if es_offline:
            engine = self.sidebar.var("engine").get()
            self._listener.engine_offline = engine
            if engine == "whisper":
                if not app.WHISPER_DISPONIBLE:
                    self.lbl_estado.config(text="  faster-whisper no instalado. Usa: pip install faster-whisper", fg=c["rojo"])
                    self.sidebar.var("modo").set("online")
                    self._listener.modo_offline = False
                    self._iniciar_listener()
                    return
                motor = WhisperEngine(self.sidebar.var("whisper_model").get())
                if motor.cargar_modelo():
                    self._listener.motor = motor
                    self.lbl_estado.config(text=f'  Whisper ({self.sidebar.var("whisper_model").get()}) listo', fg=c["verde"])
                else:
                    self.lbl_estado.config(text="  Error al cargar Whisper. Proba con un modelo mas chico.", fg=c["rojo"])
                    self.sidebar.var("modo").set("online")
                    self._listener.modo_offline = False
                    self._iniciar_listener()
                    return
            else:
                if not app.VOSK_DISPONIBLE:
                    self.lbl_estado.config(text="  Vosk no instalado", fg=c["rojo"])
                    self.sidebar.var("modo").set("online")
                    self._listener.modo_offline = False
                    self._iniciar_listener()
                    return
                if not os.path.isdir(self._ruta_vosk_actual()):
                    self.lbl_estado.config(text="  Modelo Vosk no encontrado. Descargalo abajo.", fg=c["rojo"])
                    self.sidebar.var("modo").set("online")
                    self._listener.modo_offline = False
                    self._iniciar_listener()
                    return
                motor = VoskEngine(self.config.get("vosk_model", VOSK_MODELO_PREDET))
                if motor.cargar_modelo():
                    self._listener.motor = motor
                    self.lbl_estado.config(text="  Modo offline listo para dictar", fg=c["verde"])
                else:
                    self.lbl_estado.config(text="  Error al cargar modelo Vosk", fg=c["rojo"])
                    self.sidebar.var("modo").set("online")
                    self._listener.modo_offline = False
                    self._iniciar_listener()
                    return
        else:
            self._listener.motor = GoogleEngine()
            self.lbl_estado.config(text="  Modo online (Google) seleccionado", fg=c["subtexto"])
        self._iniciar_listener()

    def _cambiar_engine(self):
        engine = self.sidebar.var("engine").get()
        self._listener.engine_offline = engine
        self.config.set("engine_offline", engine)
        if self._listener.modo_offline:
            if engine == "whisper":
                if not app.WHISPER_DISPONIBLE:
                    self.lbl_estado.config(text="  faster-whisper no instalado", fg=self.theme.colores["rojo"])
                    self.sidebar.var("engine").set("vosk")
                    return
                motor = WhisperEngine(self.sidebar.var("whisper_model").get())
                if not motor.cargar_modelo():
                    self.lbl_estado.config(text="  Error al cargar Whisper", fg=self.theme.colores["rojo"])
                    self.sidebar.var("engine").set("vosk")
                    return
                self._listener.motor = motor
            else:
                nombre = self.config.get("vosk_model", VOSK_MODELO_PREDET)
                motor = VoskEngine(nombre)
                motor.cargar_modelo()
                self._listener.motor = motor
            self._iniciar_listener()

    def _cambiar_modelo_whisper(self, event=None):
        self.config.set("whisper_model", self.sidebar.var("whisper_model").get())

    def _cambiar_modelo_vosk(self, event=None):
        nombre = self.sidebar.var("vosk_model").get()
        self.config.set("vosk_model", nombre)
        self._actualizar_estado_modelo()

    def _descargar_modelo(self):
        if not app.VOSK_DISPONIBLE:
            return
        nombre_modelo = self.config.get("vosk_model", VOSK_MODELO_PREDET)
        info = VOSK_MODELOS.get(nombre_modelo, VOSK_MODELOS["small"])
        self.sidebar.widget("btn_descargar").config(state="disabled", text="  Descargando...")
        self.sidebar.widget("lbl_modelo").config(text=f"  Descargando {info['nombre']}...", fg=self.theme.colores["subtexto"])
        self.root.update()
        motor = VoskEngine(nombre_modelo)
        threading.Thread(target=lambda: self._ejecutar_descarga(motor), daemon=True).start()

    def _ejecutar_descarga(self, motor):
        try:
            motor.descargar_modelo()
            self.root.after(0, lambda: self.sidebar.widget("lbl_modelo").config(text="  Modelo descargado correctamente", fg=self.theme.colores["verde"]))
            self.root.after(0, lambda: self.sidebar.widget("btn_descargar").pack_forget())
            self.root.after(0, lambda: self.lbl_estado.config(text="  Modelo Vosk listo", fg=self.theme.colores["verde"]))
            if self._listener.modo_offline and self._listener.engine_offline == "vosk":
                self._listener.motor = motor
                self._listener.motor.cargar_modelo()
        except Exception as e:
            self.root.after(0, lambda: self.sidebar.widget("lbl_modelo").config(text=f"  Error: {e}", fg=self.theme.colores["rojo"]))
        finally:
            self.root.after(0, lambda: self.sidebar.widget("btn_descargar").config(state="normal", text="  Descargar modelo"))

    def _actualizar_estado_modelo(self):
        c = self.theme.colores
        if app.WHISPER_DISPONIBLE and self.sidebar.var("engine").get() == "whisper":
            self.sidebar.widget("lbl_modelo").config(text=f'  Whisper ({self.sidebar.var("whisper_model").get()}) listo', fg=c["verde"])
            self.sidebar.widget("btn_descargar").pack_forget()
            return
        if not app.VOSK_DISPONIBLE:
            self.sidebar.widget("lbl_modelo").config(text="  Vosk no instalado. Corre: pip install vosk", fg=c["rojo"])
            self.sidebar.widget("btn_descargar").pack_forget()
            return
        if os.path.isdir(self._ruta_vosk_actual()):
            self.sidebar.widget("lbl_modelo").config(text="  Modelo Vosk listo", fg=c["verde"])
            self.sidebar.widget("btn_descargar").pack_forget()
        else:
            self.sidebar.widget("lbl_modelo").config(text="  Modelo no descargado", fg=c["rojo"])
            self.sidebar.widget("btn_descargar").pack(fill="x", padx=12, pady=(0, 3))

    # -- Dictation Control --

    def iniciar_dictado(self):
        if self.escuchando:
            return
        self.escuchando = True
        self._listener.escuchando = True
        self.sidebar.widget("btn_iniciar").config(state="disabled")
        self.sidebar.widget("btn_detener").config(state="normal")
        self._sesion_inicio = time.time()
        self._ultimo_break = time.time()
        self._alerta_sesion_larga_mostrada = False
        c = self.theme.colores
        modo = "offline" if self._listener.modo_offline else "online"
        self.lbl_estado.config(text=f"  Dictando ({modo})... habla con claridad", fg=c["verde"])
        self.lbl_mic.config(text=f"Microfono\nactivo ({modo})", fg=c["verde"])
        self._dibujar_mic(activo=True)
        self.feedback.dictado_iniciado()
        self._actualizar_tiempo_sesion()

    def detener_dictado(self):
        if not self.escuchando:
            return
        self.escuchando = False
        self._listener.escuchando = False
        self.sidebar.widget("btn_iniciar").config(state="normal")
        self.sidebar.widget("btn_detener").config(state="disabled")
        self._sesion_inicio = None
        c = self.theme.colores
        modo = "offline" if self._listener.modo_offline else "online"
        self.lbl_estado.config(text=f"   Dictado detenido ({modo})", fg=c["subtexto"])
        self.lbl_mic.config(text="Microfono\napagado", fg=c["rojo"])
        self._dibujar_mic(activo=False)
        self.feedback.dictado_detenido()
        self.lbl_tiempo_sesion.config(text="")

    def _actualizar_tiempo_sesion(self):
        if self._cerrando or not self.escuchando or self._sesion_inicio is None:
            return
        minutos = int((time.time() - self._sesion_inicio) / 60)
        segundos = int((time.time() - self._sesion_inicio) % 60)
        self.lbl_tiempo_sesion.config(text=f"Sesion: {minutos:02d}:{segundos:02d}")
        self.root.after(1000, self._actualizar_tiempo_sesion)

    def _dibujar_mic(self, activo=False):
        self.canvas_mic.delete("all")
        c = self.theme.colores
        color = c["verde"] if activo else c["rojo"]
        if activo:
            self.canvas_mic.create_oval(10, 10, 90, 90, outline=color, width=2)
        self.canvas_mic.create_rectangle(35, 20, 65, 60, fill=color, outline="", width=0)
        self.canvas_mic.create_oval(30, 45, 70, 65, fill=color, outline="", width=0)
        self.canvas_mic.create_line(50, 65, 50, 80, fill=color, width=3)
        self.canvas_mic.create_line(38, 80, 62, 80, fill=color, width=3)

    # -- Queue Processing --

    def _procesar_cola(self):
        if self._cerrando:
            return
        try:
            while True:
                tipo, dato = self.cola_texto.get_nowait()
                if tipo == "frase":
                    self._procesar_frase(dato)
                elif tipo == "info":
                    if dato == "listener_iniciado":
                        self.lbl_estado.config(text="  Escuchando...", fg=self.theme.colores["verde"])
                elif tipo == "comando":
                    self._procesar_comando_cola(dato)
                elif tipo == "error":
                    self.lbl_estado.config(text=dato, fg=self.theme.colores["rojo"])
                    self.feedback.error()
                    if "listener" in dato.lower():
                        self.detener_dictado()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._procesar_cola)

    def _procesar_comando_cola(self, dato):
        if dato == "fallback_offline":
            if app.VOSK_DISPONIBLE and os.path.isdir(self._ruta_vosk_actual()):
                self.lbl_estado.config(text="  Sin conexion, cambiando a modo offline...", fg=self.theme.colores["rojo"])
                self._listener.modo_offline = True
                self._listener.engine_offline = "vosk"
                self.sidebar.var("modo").set("offline")
                self.sidebar.var("engine").set("vosk")
                motor = VoskEngine()
                if motor.cargar_modelo():
                    self._listener.motor = motor
                    self._listener.iniciar()
                    self.root.after(500, self.iniciar_dictado)
                else:
                    self.lbl_estado.config(text="  No se pudo cargar modelo offline", fg=self.theme.colores["rojo"])
            else:
                self.lbl_estado.config(text="  Sin conexion y Vosk no disponible", fg=self.theme.colores["rojo"])
        elif dato == "iniciar_por_voz":
            if not self.escuchando:
                self.root.after(0, self.iniciar_dictado)
        elif dato.startswith("idioma_"):
            self.root.after(0, self._cambiar_idioma_por_comando, dato)
        elif dato == "listener_caido":
            self.lbl_estado.config(text="  Listener detenido inesperadamente", fg=self.theme.colores["rojo"])

    # -- Command Processing --

    def _procesar_frase(self, frase):
        self.lbl_ultima.config(text=f'"{frase}"')
        match_rep = re.match(r'^reemplazar\s+(.+?)\s+por\s+(.+)$', frase, re.IGNORECASE)
        if match_rep:
            self._reemplazar_texto(match_rep.group(1), match_rep.group(2))
            return
        match_cor_num = re.match(r'^corregir\s+(\d+)[\s]+(.+)$', frase, re.IGNORECASE)
        if match_cor_num:
            self._corregir_texto(match_cor_num.group(2), int(match_cor_num.group(1)))
            return
        match_cor = re.match(r'^corregir\s+(.+)$', frase, re.IGNORECASE)
        if match_cor:
            self._corregir_texto(match_cor.group(1))
            return
        for cmd, (tipo_accion, valor) in sorted(COMANDOS.items(), key=lambda x: -len(x[0])):
            if frase == cmd or frase.startswith(cmd + " "):
                texto_extra = frase[len(cmd):].strip() if frase != cmd else ""
                self._ejecutar_accion(tipo_accion, valor)
                if texto_extra:
                    self._insertar_texto(texto_extra)
                return
        self._insertar_texto(frase)

    def _ejecutar_accion(self, tipo, valor):
        if tipo == "insertar":
            contenido = self.texto.get("1.0", "end-1c")
            if valor in ".,:;?!" and contenido.endswith(" "):
                self.texto.delete("end-2c", "end-1c")
            self.texto.insert("end", valor + " ")
        elif tipo == "accion":
            getattr(self, f"_cmd_{valor}", lambda: None)()

    def _cmd_nueva_linea(self):
        self.texto.insert("end", "\n")

    def _cmd_nuevo_parrafo(self):
        self.texto.insert("end", "\n\n")

    def _cmd_mayusculas(self):
        self.mayusculas_siguiente = True

    def _cmd_borrar_ultima(self):
        contenido = self.texto.get("1.0", "end-1c")
        palabras = contenido.rstrip().rsplit(" ", 1)
        nuevo = palabras[0] + " " if len(palabras) > 1 else ""
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", nuevo)

    def _cmd_seleccionar_ultima(self):
        contenido = self.texto.get("1.0", "end-1c").rstrip()
        if not contenido:
            self.lbl_estado.config(text="  No hay texto", fg=self.theme.colores["rojo"])
            return
        palabras = contenido.rsplit(" ", 1)
        if len(palabras) > 1:
            idx = len(palabras[0]) + 1
        else:
            idx = 0
        self._seleccionar_texto(palabras[-1], idx)

    def _seleccionar_texto(self, texto, offset_chars):
        try:
            self.texto.tag_remove("sel", "1.0", "end")
            start = f"1.0 + {offset_chars} chars"
            end = f"1.0 + {offset_chars + len(texto)} chars"
            self.texto.tag_add("sel", start, end)
            self.texto.mark_set("insert", end)
            self.texto.see("insert")
        except tk.TclError:
            pass

    def _cmd_borrar_ultima_linea(self):
        contenido = self.texto.get("1.0", "end-1c")
        lineas = contenido.rsplit("\n", 1)
        nuevo = lineas[0] if len(lineas) > 1 else ""
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", nuevo)

    def _cmd_borrar_todo(self):
        self._borrar_todo()

    def _cmd_guardar(self):
        self.root.after(0, self.guardar)

    def _cmd_guardar_como(self):
        self.root.after(0, self.guardar_como)

    def _cmd_detener(self):
        self.root.after(0, self.detener_dictado)

    def _cmd_iniciar(self):
        self.root.after(0, self.iniciar_dictado)

    def _cmd_negrita(self):
        self._toggle_formato("bold")

    def _cmd_cursiva(self):
        self._toggle_formato("italic")

    def _cmd_subrayar(self):
        self._toggle_formato("underline")

    def _cmd_ir_inicio(self):
        self.texto.mark_set("insert", "1.0")
        self.texto.see("1.0")

    def _cmd_ir_final(self):
        self.texto.mark_set("insert", "end-1c")
        self.texto.see("end")

    def _cmd_seleccionar_todo(self):
        self.texto.tag_add("sel", "1.0", "end-1c")

    def _cmd_copiar(self):
        try:
            texto_sel = self.texto.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(texto_sel)
        except tk.TclError:
            pass

    def _cmd_pegar(self):
        try:
            texto_portapapeles = self.root.clipboard_get()
            self.texto.insert("insert", texto_portapapeles)
        except tk.TclError:
            pass

    def _cmd_exportar_docx(self):
        self.root.after(0, self._exportar_docx)

    def _cmd_exportar_pdf(self):
        self.root.after(0, self._exportar_pdf)

    def _cmd_idioma_es_AR(self):
        self._cambiar_idioma_por_comando("idioma_es_AR")

    def _cmd_idioma_es_ES(self):
        self._cambiar_idioma_por_comando("idioma_es_ES")

    def _cmd_idioma_en_US(self):
        self._cambiar_idioma_por_comando("idioma_en_US")

    def _cmd_idioma_pt_BR(self):
        self._cambiar_idioma_por_comando("idioma_pt_BR")

    def _cmd_idioma_fr_FR(self):
        self._cambiar_idioma_por_comando("idioma_fr_FR")

    def _cmd_idioma_de_DE(self):
        self._cambiar_idioma_por_comando("idioma_de_DE")

    def _cmd_idioma_it_IT(self):
        self._cambiar_idioma_por_comando("idioma_it_IT")

    def _cmd_abrir(self):
        self.root.after(0, self.abrir)

    def _cmd_nuevo_documento(self):
        self.root.after(0, self._nuevo_documento)

    def _cmd_exportar_txt(self):
        self.root.after(0, self.guardar_como)

    def _cmd_modo_online(self):
        self.root.after(0, lambda: self._cambiar_modo_voz("online"))

    def _cmd_modo_offline(self):
        self.root.after(0, lambda: self._cambiar_modo_voz("offline"))

    def _cmd_modo_whisper(self):
        self.root.after(0, self._cambiar_modo_voz_whisper)

    def _cmd_tema_oscuro(self):
        self.root.after(0, lambda: self._aplicar_tema_voz("oscuro"))

    def _cmd_tema_claro(self):
        self.root.after(0, lambda: self._aplicar_tema_voz("claro"))

    def _cmd_tema_azul(self):
        self.root.after(0, lambda: self._aplicar_tema_voz("alto_contraste"))

    def _cmd_tema_alto_contraste(self):
        self.root.after(0, lambda: self._aplicar_tema_voz("alto_contraste"))

    def _cmd_fuente_aumentar(self):
        self.root.after(0, lambda: self._cambiar_fuente_voz(+2))

    def _cmd_fuente_disminuir(self):
        self.root.after(0, lambda: self._cambiar_fuente_voz(-2))

    def _cmd_traducir(self):
        self.root.after(0, self._traducir_documento)

    def _cmd_traducir_en(self):
        self.root.after(0, lambda: self._traducir_a_idioma("en"))

    def _cmd_traducir_es(self):
        self.root.after(0, lambda: self._traducir_a_idioma("es"))

    def _cmd_traducir_fr(self):
        self.root.after(0, lambda: self._traducir_a_idioma("fr"))

    def _cmd_traducir_pt(self):
        self.root.after(0, lambda: self._traducir_a_idioma("pt"))

    def _cmd_traducir_de(self):
        self.root.after(0, lambda: self._traducir_a_idioma("de"))

    def _cmd_traducir_it(self):
        self.root.after(0, lambda: self._traducir_a_idioma("it"))

    def _cmd_transcribir_audio(self):
        self.root.after(0, self._transcribir_audio)

    def _cmd_ocr_imagen(self):
        self.root.after(0, self._extraer_texto_imagen)

    def _cmd_descargar_modelo(self):
        self.root.after(0, self._descargar_modelo)

    def _cmd_deshacer(self):
        try:
            self.texto.edit_undo()
        except Exception as e:
            print(f"[UI] Error al deshacer: {e}", file=sys.stderr)

    def _cmd_rehacer(self):
        try:
            self.texto.edit_redo()
        except Exception as e:
            print(f"[UI] Error al rehacer: {e}", file=sys.stderr)

    def _cmd_pausas_on(self):
        self.root.after(0, lambda: self._set_pausas(True))

    def _cmd_pausas_off(self):
        self.root.after(0, lambda: self._set_pausas(False))

    def _cmd_ayuda(self):
        self.root.after(0, self._mostrar_ayuda_voz)

    def _cmd_cerrar_ayuda(self):
        self.root.after(0, self._cerrar_ayuda)

    def _cmd_scroll_up(self):
        self.texto.yview_scroll(-3, "units")

    def _cmd_scroll_down(self):
        self.texto.yview_scroll(3, "units")

    def _cmd_scroll_page_up(self):
        self.texto.yview_scroll(-1, "pages")

    def _cmd_scroll_page_down(self):
        self.texto.yview_scroll(1, "pages")

    def _cmd_usar_vosk(self):
        self.root.after(0, lambda: self._cambiar_modo_voz("offline"))

    def _cmd_auto_save_on(self):
        self.root.after(0, lambda: self._toggle_auto_save_voz(True))

    def _cmd_auto_save_off(self):
        self.root.after(0, lambda: self._toggle_auto_save_voz(False))

    def _cmd_feedback_on(self):
        self.root.after(0, lambda: self._toggle_feedback_voz(True))

    def _cmd_feedback_off(self):
        self.root.after(0, lambda: self._toggle_feedback_voz(False))

    def _cmd_fuente_12(self):
        self.root.after(0, lambda: self._cambiar_fuente_voz_a(12))

    def _cmd_fuente_16(self):
        self.root.after(0, lambda: self._cambiar_fuente_voz_a(16))

    def _cmd_fuente_20(self):
        self.root.after(0, lambda: self._cambiar_fuente_voz_a(20))

    def _cmd_whisper_model_tiny(self):
        self.root.after(0, lambda: self._cambiar_modelo_whisper_voz("tiny"))

    def _cmd_whisper_model_base(self):
        self.root.after(0, lambda: self._cambiar_modelo_whisper_voz("base"))

    def _cmd_whisper_model_small(self):
        self.root.after(0, lambda: self._cambiar_modelo_whisper_voz("small"))

    def _cmd_whisper_model_medium(self):
        self.root.after(0, lambda: self._cambiar_modelo_whisper_voz("medium"))

    def _cmd_whisper_model_large(self):
        self.root.after(0, lambda: self._cambiar_modelo_whisper_voz("large-v3"))

    def _cambiar_idioma_por_comando(self, codigo):
        nombre, compatible = MAPA_IDIOMAS_COMANDO.get(codigo, ("Espanol (Argentina)", True))
        self.sidebar.var("idioma_dictado").set(nombre)
        self._cambiar_idioma_dictado()
        self._listener.idioma_dictado = self.idioma_dictado
        if not compatible and self._listener.modo_offline:
            self.sidebar.var("modo").set("online")
            self._listener.modo_offline = False
            self._cambiar_modo()
        elif compatible and not self._listener.modo_offline:
            self.lbl_estado.config(text=f"  Cambiado a offline para {nombre}", fg=self.theme.colores["verde"])
        self.feedback.comando_detectado()

    def _cambiar_modo_voz(self, modo):
        if modo == "online":
            self.sidebar.var("modo").set("online")
        else:
            self.sidebar.var("modo").set("offline")
        self._cambiar_modo()
        self.feedback.comando_detectado()

    def _cambiar_modo_voz_whisper(self):
        self.sidebar.var("modo").set("offline")
        self.sidebar.var("engine").set("whisper")
        self.config.set("engine_offline", "whisper")
        self._cambiar_modo()
        self.feedback.comando_detectado()

    def _aplicar_tema_voz(self, nombre):
        temas_disponibles = list(TEMAS.keys())
        coincidencia = next((t for t in temas_disponibles if nombre in t), None)
        if coincidencia:
            self.theme.aplicar(coincidencia)
            self.config.set("tema", coincidencia)
            self.sidebar.var("tema").set(coincidencia)
            self.lbl_estado.config(text=f"  Tema '{coincidencia}' aplicado", fg=self.theme.colores["verde"])
        else:
            self.lbl_estado.config(text=f"  Tema '{nombre}' no disponible", fg=self.theme.colores["rojo"])
        self.feedback.comando_detectado()

    def _cambiar_fuente_voz(self, delta):
        nuevo = max(8, min(36, self.theme.fuente_actual + delta))
        self._aplicar_fuente(nuevo)

    def _cambiar_fuente_voz_a(self, tam):
        self._aplicar_fuente(max(8, min(36, tam)))

    def _aplicar_fuente(self, nuevo):
        self.theme.actualizar_fuente(nuevo)
        sf = self.sidebar.widget("scale_fuente")
        if sf:
            sf.set(nuevo)
        ltf = self.sidebar.widget("lbl_tam_fuente")
        if ltf:
            ltf.config(text=f"Tamano fuente: {nuevo}")
        self.lbl_estado.config(text=f"  Fuente: {nuevo}pt", fg=self.theme.colores["verde"])
        self.feedback.comando_detectado()

    # -- Text Insertion / Formatting --

    def _insertar_texto(self, texto):
        if not texto:
            return
        try:
            if self.texto.tag_ranges("sel"):
                start = self.texto.index("sel.first")
                end = self.texto.index("sel.last")
                after = self.texto.get(end, f"{end} + 1 char")
                self.texto.delete(start, end)
                if after == " ":
                    self.texto.delete(start, f"{start} + 1 char")
                self.texto.insert(start, texto + " ")
                self.texto.tag_remove("sel", "1.0", "end")
                return
        except tk.TclError:
            pass
        if self.mayusculas_siguiente:
            texto = texto.capitalize()
            self.mayusculas_siguiente = False
        else:
            contenido = self.texto.get("1.0", "end-1c").rstrip()
            if not contenido or contenido.endswith((".", "?", "!")):
                texto = texto.capitalize()
        self.texto.insert("end", texto + " ")
        self.texto.see("end")

    def _toggle_formato(self, tag):
        TAGS_FONT = {"bold", "italic"}

        def recalcular(start, end):
            self.texto.tag_remove("bold_italic", start, end)
            idx = start
            while self.texto.compare(idx, "<", end):
                sig = self.texto.index(f"{idx}+1c")
                tags = set(self.texto.tag_names(idx))
                if "bold" in tags and "italic" in tags:
                    self.texto.tag_add("bold_italic", idx, sig)
                idx = sig

        try:
            if self.texto.tag_ranges("sel"):
                start = self.texto.index("sel.first")
                end = self.texto.index("sel.last")
                ranges = self.texto.tag_ranges(tag)
                covered = False
                if ranges:
                    covered = True
                    idx = start
                    while self.texto.compare(idx, "<", end):
                        sig = self.texto.index(f"{idx}+1c")
                        if tag not in self.texto.tag_names(idx):
                            covered = False
                            break
                        idx = sig
                if covered:
                    self.texto.tag_remove(tag, start, end)
                else:
                    self.texto.tag_add(tag, start, end)
                if tag in TAGS_FONT:
                    recalcular(start, end)
            else:
                self.texto.tag_add(tag, "insert", "insert+1c")
                if tag in TAGS_FONT:
                    recalcular("insert", "insert+1c")
        except tk.TclError:
            pass

    @staticmethod
    def _sin_acentos(s):
        import unicodedata
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').lower()

    def _reemplazar_texto(self, viejo, nuevo):
        contenido = self.texto.get("1.0", "end-1c")
        import re as _re
        buscar_esc = _re.escape(viejo.strip())
        patron = _re.sub(r'\s+', r'\\s+', buscar_esc, flags=_re.UNICODE)
        m = [match for match in _re.finditer(patron, contenido, _re.IGNORECASE)
             if self._sin_acentos(match.group()) == self._sin_acentos(viejo)]
        if not m:
            self.lbl_estado.config(text=f"  No se encontro '{viejo}'", fg=self.theme.colores["rojo"])
            self.feedback.error()
            return
        ultimo = m[-1]
        self.texto.delete(f"1.0 + {ultimo.start()} chars", f"1.0 + {ultimo.end()} chars")
        self.texto.insert(f"1.0 + {ultimo.start()} chars", nuevo)
        self.lbl_estado.config(text=f"  Reemplazado '{viejo}' por '{nuevo}'", fg=self.theme.colores["verde"])
        self.feedback.comando_detectado()

    def _corregir_texto(self, texto_buscar, ocurrencia=-1):
        contenido = self.texto.get("1.0", "end-1c")
        import re as _re
        buscar_esc = _re.escape(texto_buscar.strip())
        patron = _re.sub(r'\s+', r'\\s+', buscar_esc, flags=_re.UNICODE)
        matches = [m for m in _re.finditer(patron, contenido, _re.IGNORECASE)
                   if self._sin_acentos(m.group()) == self._sin_acentos(texto_buscar)]
        if not matches:
            self.lbl_estado.config(text=f"  No se encontro '{texto_buscar}'", fg=self.theme.colores["rojo"])
            self.feedback.error()
            return
        if ocurrencia == -1:
            m = matches[-1]
        else:
            m = matches[min(ocurrencia - 1, len(matches) - 1)]
        self._seleccionar_rango(m.start(), m.end(), texto_buscar)
        self.feedback.comando_detectado()

    def _seleccionar_rango(self, start, end, texto_label):
        self._ultima_correccion = (start, end, texto_label)
        self.texto.tag_remove("sel", "1.0", "end")
        self.texto.tag_add("sel", f"1.0 + {start} chars", f"1.0 + {end} chars")
        self.texto.mark_set("insert", f"1.0 + {end} chars")
        self.texto.see(f"1.0 + {start} chars")
        self.lbl_estado.config(text=f"  Seleccionado '{texto_label}'", fg=self.theme.colores["verde"])

    def _cmd_siguiente(self):
        if not hasattr(self, '_ultima_correccion'):
            self.lbl_estado.config(text="  Primero usa 'corregir [palabra]'", fg=self.theme.colores["rojo"])
            return
        start_anterior, _, texto_buscar = self._ultima_correccion
        contenido = self.texto.get("1.0", "end-1c")
        parte = contenido[:start_anterior]
        import re as _re
        buscar_esc = _re.escape(texto_buscar.strip())
        patron = _re.sub(r'\s+', r'\\s+', buscar_esc, flags=_re.UNICODE)
        matches = [m for m in _re.finditer(patron, parte, _re.IGNORECASE)
                   if self._sin_acentos(m.group()) == self._sin_acentos(texto_buscar)]
        if not matches:
            self.lbl_estado.config(text=f"  No hay mas '{texto_buscar}'", fg=self.theme.colores["rojo"])
            return
        m = matches[-1]
        self._seleccionar_rango(m.start(), m.end(), texto_buscar)

    # -- File Operations --

    def guardar(self):
        if not self.archivo_actual:
            self.guardar_como()
            return
        contenido = self.texto.get("1.0", "end-1c")
        try:
            self.file_service.guardar(self.archivo_actual, contenido)
            self.lbl_archivo.config(text=f"  Guardado: {os.path.basename(self.archivo_actual)}")
            self.lbl_estado.config(text=f"  Guardado en {self.archivo_actual}", fg=self.theme.colores["verde"])
            self.feedback.guardado()
        except Exception as e:
            self.lbl_estado.config(text=f"  Error al guardar: {e}", fg=self.theme.colores["rojo"])
            self.feedback.error()

    def guardar_como(self):
        nombre = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Documento Word", "*.docx"),
                       ("Documento PDF", "*.pdf"), ("Todos", "*.*")],
            initialfile=f"dictado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt")
        if nombre:
            ext = os.path.splitext(nombre)[1].lower()
            if ext == ".docx":
                self._exportar_docx(ruta=nombre)
                return
            elif ext == ".pdf":
                self._exportar_pdf(ruta=nombre)
                return
            self.archivo_actual = nombre
            self.guardar()

    def _exportar_docx(self, ruta=None):
        if not app.DOCX_DISPONIBLE:
            messagebox.showinfo("Exportar .docx", "python-docx no esta instalado.\nEjecuta: pip install python-docx")
            return
        if ruta is None:
            ruta = filedialog.asksaveasfilename(
                defaultextension=".docx", filetypes=[("Documento Word", "*.docx")],
                initialfile=f"dictado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.docx")
            if not ruta:
                return
        try:
            contenido = self.texto.get("1.0", "end-1c")
            self.file_service.exportar_docx(ruta, contenido, self.theme.fuente_actual)
            self.lbl_estado.config(text=f"  Exportado como DOCX", fg=self.theme.colores["verde"])
            self.feedback.guardado()
        except Exception as e:
            self.lbl_estado.config(text=f"  Error al exportar DOCX: {e}", fg=self.theme.colores["rojo"])
            self.feedback.error()

    def _exportar_pdf(self, ruta=None):
        if not app.PDF_DISPONIBLE:
            messagebox.showinfo("Exportar .pdf", "fpdf2 no esta instalado.\nEjecuta: pip install fpdf2")
            return
        if ruta is None:
            ruta = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("Documento PDF", "*.pdf")],
                initialfile=f"dictado_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
            if not ruta:
                return
        try:
            contenido = self.texto.get("1.0", "end-1c")
            self.file_service.exportar_pdf(ruta, contenido, self.theme.fuente_actual)
            self.lbl_estado.config(text=f"  Exportado como PDF", fg=self.theme.colores["verde"])
            self.feedback.guardado()
        except Exception as e:
            self.lbl_estado.config(text=f"  Error al exportar PDF: {e}", fg=self.theme.colores["rojo"])
            self.feedback.error()

    def abrir(self):
        nombre = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if nombre:
            try:
                contenido = self.file_service.abrir(nombre)
                self.texto.delete("1.0", "end")
                self.texto.insert("1.0", contenido)
                self.archivo_actual = nombre
                self.lbl_archivo.config(text=f"  {os.path.basename(nombre)}")
            except Exception as e:
                self.lbl_estado.config(text=f"  Error al abrir: {e}", fg=self.theme.colores["rojo"])
                self.feedback.error()

    def _borrar_todo(self):
        if messagebox.askyesno("Confirmar", "Borrar todo el contenido del documento?"):
            self.texto.delete("1.0", "end")

    def _nuevo_documento(self):
        contenido = self.texto.get("1.0", "end-1c").strip()
        if contenido:
            if not messagebox.askyesno("Nuevo documento", "Crear un documento nuevo? Se perdera el contenido no guardado."):
                return
        self.texto.delete("1.0", "end")
        self.archivo_actual = None
        self.lbl_archivo.config(text="  Sin titulo")
        self.lbl_estado.config(text="  Nuevo documento", fg=self.theme.colores["verde"])
        self.feedback.comando_detectado()

    # -- Services --

    def _traducir_documento(self):
        contenido = self.texto.get("1.0", "end-1c").strip()
        if not contenido:
            self.lbl_estado.config(text="  No hay texto para traducir", fg=self.theme.colores["rojo"])
            return
        self.lbl_estado.config(text="  Traduciendo...", fg=self.theme.colores["subtexto"])
        if not self._semaforo_tareas.acquire(blocking=False):
            self.lbl_estado.config(text="  Demasiadas tareas en segundo plano", fg=self.theme.colores["rojo"])
            return
        threading.Thread(target=self._ejecutar_traduccion, daemon=True).start()

    def _ejecutar_traduccion(self):
        try:
            contenido = self.texto.get("1.0", "end-1c").strip()
            if not contenido:
                return
            texto = self.translator.traducir(contenido, self.idioma_traduccion)
            self.root.after(0, lambda: self.texto.delete("1.0", "end"))
            self.root.after(0, lambda: self.texto.insert("1.0", texto))
            self.root.after(0, lambda: self.lbl_estado.config(text="  Traduccion lista", fg=self.theme.colores["verde"]))
        except Exception as e:
            self.root.after(0, lambda: self.lbl_estado.config(text=f"  Error al traducir: {e}", fg=self.theme.colores["rojo"]))
        finally:
            self._semaforo_tareas.release()

    def _traducir_a_idioma(self, lang):
        self.idioma_traduccion = lang
        cmb = self.sidebar.widget("cmb_idioma_trad")
        if cmb:
            nombre = MAPA_TRADUCCION_VOZ.get(lang, lang)
            valores = list(cmb["values"])
            coincidencia = next((v for v in valores if nombre in v), None)
            if coincidencia:
                self.sidebar.widget("cmb_idioma_trad").set(coincidencia)
        self._traducir_documento()

    def _transcribir_audio(self):
        nombre = filedialog.askopenfilename(
            title="Seleccionar archivo de audio",
            filetypes=[("Audio", "*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma"),
                       ("WAV", "*.wav"), ("MP3", "*.mp3"), ("M4A", "*.m4a"),
                       ("FLAC", "*.flac"), ("OGG", "*.ogg"), ("Todos", "*.*")])
        if not nombre:
            return
        self.sidebar.widget("btn_iniciar").config(state="disabled")
        self.lbl_estado.config(text="  Transcribiendo audio...", fg=self.theme.colores["subtexto"])
        self._mostrar_progreso("  Procesando audio...")
        if not self._semaforo_tareas.acquire(blocking=False):
            self.lbl_estado.config(text="  Demasiadas tareas en segundo plano", fg=self.theme.colores["rojo"])
            return
        threading.Thread(target=self._ejecutar_transcripcion, args=(nombre,), daemon=True).start()

    def _mostrar_progreso(self, texto):
        self._ventana_progreso = tk.Toplevel(self.root)
        self._ventana_progreso.title("Procesando")
        self._ventana_progreso.geometry("300x100")
        self._ventana_progreso.configure(bg=self.theme.colores["bg"])
        self._ventana_progreso.resizable(False, False)
        self._ventana_progreso.transient(self.root)
        try:
            self._ventana_progreso.grab_set()
        except tk.TclError:
            pass
        tk.Label(self._ventana_progreso, text=texto, font=("Segoe UI", 10),
                 bg=self.theme.colores["bg"], fg=self.theme.colores["verde"]).pack(pady=(15, 5))
        barra = ttk.Progressbar(self._ventana_progreso, mode="indeterminate", length=250)
        barra.pack(pady=5)
        barra.start(10)

    def _cerrar_progreso(self):
        if hasattr(self, "_ventana_progreso") and self._ventana_progreso:
            try:
                self._ventana_progreso.destroy()
            except Exception as e:
                print(f"[UI] Error al cerrar ventana de progreso: {e}", file=sys.stderr)
            self._ventana_progreso = None

    def _ejecutar_transcripcion(self, nombre):
        try:
            wav_path = convertir_a_wav(nombre)
            if wav_path is None:
                self.root.after(0, self._cerrar_progreso)
                return
            self._temp_wav = wav_path if wav_path != nombre else None
            if self._listener.modo_offline and self._listener.motor:
                texto = self._listener.motor.transcribir_archivo(wav_path, self.idioma_dictado)
            else:
                motor = GoogleEngine()
                texto = motor.transcribir_archivo(wav_path, self.idioma_dictado)
            self.root.after(0, self._cerrar_progreso)
            if texto.strip():
                self.root.after(0, lambda t=texto, n=nombre: self._insertar_texto_transcripcion(t, n))
            else:
                self.root.after(0, lambda: self.lbl_estado.config(text="  No se reconocio audio", fg=self.theme.colores["rojo"]))
        except Exception as e:
            self.root.after(0, self._cerrar_progreso)
            self.root.after(0, lambda: self.lbl_estado.config(text=f"  Error: {e}", fg=self.theme.colores["rojo"]))
        finally:
            self.root.after(0, lambda: self.sidebar.widget("btn_iniciar").config(state="normal"))
            self._semaforo_tareas.release()

    def _insertar_texto_transcripcion(self, texto, nombre_archivo):
        self.texto.insert("end", "\n")
        for parrafo in texto.split(". "):
            parrafo = parrafo.strip()
            if parrafo:
                self.texto.insert("end", parrafo.capitalize() + ".\n\n")
        self.lbl_ultima.config(text="  Transcripcion completada")
        self.lbl_estado.config(text=f"  Transcripcion insertada desde {os.path.basename(nombre_archivo)}", fg=self.theme.colores["verde"])
        self.texto.see("end")
        if self._temp_wav and os.path.exists(self._temp_wav):
            try:
                os.remove(self._temp_wav)
            except Exception as e:
                print(f"[UI] Error al eliminar WAV temporal: {e}", file=sys.stderr)
            self._temp_wav = None

    def _extraer_texto_imagen(self):
        nombre = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp"),
                       ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("BMP", "*.bmp"),
                       ("TIFF", "*.tiff *.tif"), ("WEBP", "*.webp"), ("Todos", "*.*")])
        if not nombre:
            return
        self.lbl_estado.config(text="  Extrayendo texto de imagen...", fg=self.theme.colores["subtexto"])
        self.sidebar.widget("btn_iniciar").config(state="disabled")
        self._mostrar_progreso("  Procesando imagen...")
        if not self._semaforo_tareas.acquire(blocking=False):
            self.lbl_estado.config(text="  Demasiadas tareas en segundo plano", fg=self.theme.colores["rojo"])
            return
        threading.Thread(target=self._ejecutar_ocr, args=(nombre,), daemon=True).start()

    def _ejecutar_ocr(self, nombre):
        try:
            texto = self.ocr_service.extraer_texto(nombre)
            self.root.after(0, self._cerrar_progreso)
            if texto.strip():
                self.root.after(0, lambda t=texto: self._insertar_texto_ocr(t))
            else:
                self.root.after(0, lambda: self.lbl_estado.config(text="  No se encontro texto en la imagen", fg=self.theme.colores["rojo"]))
        except Exception as e:
            self.root.after(0, self._cerrar_progreso)
            self.root.after(0, lambda: self.lbl_estado.config(text=f"  Error OCR: {e}", fg=self.theme.colores["rojo"]))
        finally:
            self.root.after(0, lambda: self.sidebar.widget("btn_iniciar").config(state="normal"))
            self._semaforo_tareas.release()

    def _insertar_texto_ocr(self, texto):
        self.texto.insert("end", "\n" + texto)
        self.texto.see("end")
        self.lbl_estado.config(text="  Texto extraido de imagen insertado", fg=self.theme.colores["verde"])

    # -- Settings --

    def _cambiar_tema(self):
        nombre = self.sidebar.var("tema").get()
        self.theme.aplicar(nombre)
        self.config.set("tema", nombre)

    def _cambiar_fuente_slider(self, valor):
        tam = int(float(valor))
        self.theme.actualizar_fuente(tam)
        ltf = self.sidebar.widget("lbl_tam_fuente")
        if ltf:
            ltf.config(text=f"Tamano fuente: {tam}")
        self.config.set("tamano_fuente", tam)

    def _cambiar_idioma_dictado(self, event=None):
        nombre = self.sidebar.var("idioma_dictado").get()
        self.idioma_dictado = CODIGOS_DICTADO.get(nombre, "es-AR")
        self._listener.idioma_dictado = self.idioma_dictado
        if not self.escuchando:
            self.lbl_estado.config(text=f"  Idioma: {nombre} ({self.idioma_dictado})", fg=self.theme.colores["subtexto"])

    def _cambiar_idioma_trad(self, event=None):
        nombre = self.sidebar.var("idioma_trad").get()
        self.idioma_traduccion = CODIGOS_TRADUCCION.get(nombre, "en")

    def _toggle_pausas(self):
        self.config.set("pausas_activas", self.sidebar.var("pausas").get())
        if self.sidebar.var("pausas").get():
            self._iniciar_temporizadores()

    def _toggle_auto_save(self):
        self.config.set("auto_guardar", self.sidebar.var("auto_save").get())
        if self.sidebar.var("auto_save").get():
            self._programar_auto_guardado()
        elif self._auto_save_after_id:
            self.root.after_cancel(self._auto_save_after_id)
            self._auto_save_after_id = None

    def _toggle_feedback(self):
        self.config.set("feedback_sonoro", self.sidebar.var("feedback").get())

    def _toggle_auto_save_voz(self, activo):
        self.sidebar.var("auto_save").set(activo)
        self.config.set("auto_guardar", activo)
        if activo:
            self._programar_auto_guardado()
            self.lbl_estado.config(text="  Auto-guardado activado", fg=self.theme.colores["verde"])
        else:
            if self._auto_save_after_id:
                self.root.after_cancel(self._auto_save_after_id)
                self._auto_save_after_id = None
            self.lbl_estado.config(text="  Auto-guardado desactivado", fg=self.theme.colores["subtexto"])
        self.feedback.comando_detectado()

    def _toggle_feedback_voz(self, activo):
        self.sidebar.var("feedback").set(activo)
        self.config.set("feedback_sonoro", activo)
        estado = "activado" if activo else "desactivado"
        self.lbl_estado.config(text=f"  Feedback sonoro {estado}", fg=self.theme.colores["verde"] if activo else self.theme.colores["subtexto"])
        self.feedback.comando_detectado()

    def _cambiar_modelo_whisper_voz(self, modelo):
        if modelo not in MODELOS_WHISPER_DISP:
            modelo = "base"
        self.sidebar.var("whisper_model").set(modelo)
        self.config.set("whisper_model", modelo)
        self.lbl_estado.config(text=f"  Modelo Whisper: {modelo}", fg=self.theme.colores["verde"])
        if self.escuchando and self._listener.modo_offline:
            self._cambiar_modo()
        self.feedback.comando_detectado()

    def _toggle_manos_libres(self):
        activo = self.sidebar.var("manos_libres").get()
        self.config.set("manos_libres", activo)
        if activo:
            self.root.after(500, self.iniciar_dictado)
            self.lbl_estado.config(text="  Modo manos libres activado", fg=self.theme.colores["verde"])
        else:
            self.detener_dictado()
            self.lbl_estado.config(text="  Modo manos libres desactivado", fg=self.theme.colores["subtexto"])

    def _set_pausas(self, activo):
        self.config.set("pausas_activas", activo)
        pv = self.sidebar.var("pausas")
        if pv:
            pv.set(activo)
        if activo:
            self._iniciar_temporizadores()
            self.lbl_estado.config(text="  Recordatorios de pausa activados", fg=self.theme.colores["verde"])
        else:
            self.lbl_estado.config(text="  Recordatorios de pausa desactivados", fg=self.theme.colores["subtexto"])
        self.feedback.comando_detectado()

    # -- Timers --

    def _iniciar_temporizadores(self):
        self._programar_auto_guardado()
        self._programar_verificacion_pausa()

    def _programar_auto_guardado(self):
        if self._auto_save_after_id:
            self.root.after_cancel(self._auto_save_after_id)
            self._auto_save_after_id = None
        if not self.config.get("auto_guardar", True):
            return
        try:
            intervalo = int(self.sidebar.widget("auto_save_spin").get()) * 60 * 1000
            self.config.set("intervalo_auto_guardar", int(self.sidebar.widget("auto_save_spin").get()))
        except Exception as e:
            print(f"[AutoSave] Error al leer intervalo, usando 5 min: {e}", file=sys.stderr)
            intervalo = 5 * 60 * 1000

        def auto_save():
            if not self.config.get("auto_guardar", True):
                return
            if self.archivo_actual and self.texto.get("1.0", "end-1c").strip():
                try:
                    with open(self.archivo_actual, "w", encoding="utf-8") as f:
                        f.write(self.texto.get("1.0", "end-1c"))
                except Exception as e:
                    print(f"[AutoSave] Error: {e}", file=sys.stderr)
            self._auto_save_after_id = self.root.after(intervalo, auto_save)
        auto_save()

    def _programar_verificacion_pausa(self):
        if self._break_check_after_id:
            self.root.after_cancel(self._break_check_after_id)
            self._break_check_after_id = None

        def verificar():
            if not self.config.get("pausas_activas", True):
                self._break_check_after_id = self.root.after(60000, verificar)
                return
            if self._sesion_inicio is not None:
                ahora = time.time()
                sesion_minutos = (ahora - self._sesion_inicio) / 60
                desde_ultimo = (ahora - self._ultimo_break) / 60 if self._ultimo_break > 0 else sesion_minutos
                if sesion_minutos >= 60 and not self._alerta_sesion_larga_mostrada:
                    self._alerta_sesion_larga_mostrada = True
                    self._mostrar_alerta_sesion_larga(sesion_minutos)
                if desde_ultimo >= self.config.get("intervalo_pausa", 20):
                    self._mostrar_recordatorio_pausa()
                    self._ultimo_break = ahora
            self._break_check_after_id = self.root.after(60000, verificar)
        verificar()

    # -- Alerts --

    def _mostrar_recordatorio_pausa(self):
        self.feedback.pausa_recordatorio()
        ventana = tk.Toplevel(self.root)
        ventana.title("  Pausa Activa")
        c = self.theme.colores
        ventana.configure(bg=c["bg"])
        ventana.geometry("420x260")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        try:
            ventana.grab_set()
        except tk.TclError:
            pass
        ventana.attributes("-topmost", True)
        x = self.root.winfo_x() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 260) // 2
        ventana.geometry(f"+{x}+{y}")
        tk.Label(ventana, text="   Tiempo de pausa activa", font=("Segoe UI", 16, "bold"),
                 bg=c["bg"], fg=c["verde"]).pack(pady=(20, 5))
        tk.Label(ventana, text="Mira algo a 20 pies (6 metros) durante 20 segundos\n"
                 "Parpadea conscientemente varias veces\n"
                 "Levantate y estira los brazos\n"
                 "Mueve las munecas suavemente",
                 font=("Segoe UI", 11), bg=c["bg"], fg=c["texto"], justify="left").pack(pady=10, padx=20)
        ventana.after(15000, lambda: ventana.winfo_exists() and ventana.destroy())
        tk.Button(ventana, text="   Cerrar (15s)", font=("Segoe UI", 11),
                  bg=c["acento"], fg=c["texto"], command=ventana.destroy,
                  relief="flat", pady=6, padx=20).pack(pady=10)

    def _mostrar_alerta_sesion_larga(self, minutos):
        ventana = tk.Toplevel(self.root)
        ventana.title("  Sesion Prolongada")
        c = self.theme.colores
        ventana.configure(bg=c["bg"])
        ventana.geometry("400x220")
        ventana.resizable(False, False)
        ventana.transient(self.root)
        try:
            ventana.grab_set()
        except tk.TclError:
            pass
        ventana.attributes("-topmost", True)
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 220) // 2
        ventana.geometry(f"+{x}+{y}")
        tk.Label(ventana, text="   Sesion de mas de 1 hora", font=("Segoe UI", 14, "bold"),
                 bg=c["bg"], fg=c["rojo"]).pack(pady=(20, 5))
        tk.Label(ventana, text=f"Llevas {int(minutos)} minutos de dictado continuo.\n"
                 "Tomate un descanso de 5-10 minutos para\n"
                 "evitar fatiga visual y tension muscular.",
                 font=("Segoe UI", 11), bg=c["bg"], fg=c["texto"], justify="center").pack(pady=10)
        tk.Button(ventana, text="Entendido", font=("Segoe UI", 11),
                  bg=c["acento"], fg=c["texto"], command=ventana.destroy,
                  relief="flat", pady=6, padx=20).pack(pady=10)

    # -- Help --

    def _mostrar_ayuda_voz(self):
        if hasattr(self, '_ayuda_ventana') and self._ayuda_ventana and self._ayuda_ventana.winfo_exists():
            self._ayuda_ventana.lift()
            return
        ventana = tk.Toplevel(self.root)
        self._ayuda_ventana = ventana
        ventana.title("Comandos de voz disponibles")
        ventana.configure(bg=self.theme.colores["bg"])
        ventana.geometry("560x600")
        try:
            ventana.grab_set()
        except tk.TclError:
            pass
        ventana.protocol("WM_DELETE_WINDOW", lambda: self._cerrar_ayuda(ventana))
        tk.Label(ventana, text="  Comandos de voz", font=("Segoe UI", 14, "bold"),
                 bg=self.theme.colores["bg"], fg=self.theme.colores["verde"]).pack(pady=(16, 4))
        tk.Label(ventana, text="Deci cualquiera de estos comandos mientras dictas:",
                 font=("Segoe UI", 10), bg=self.theme.colores["bg"],
                 fg=self.theme.colores["subtexto"]).pack(pady=(0, 10))
        frame = tk.Frame(ventana, bg=self.theme.colores["bg"])
        frame.pack(fill="both", expand=True, padx=16)
        scroll = tk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        lista = tk.Text(frame, font=("Consolas", 10), bg=self.theme.colores["texto_bg"],
                        fg=self.theme.colores["texto"], yscrollcommand=scroll.set,
                        wrap="word", relief="flat", padx=10, pady=8)
        lista.pack(fill="both", expand=True)
        scroll.config(command=lista.yview)
        categorias = {
            "Escritura": ["punto", "coma", "punto y coma", "dos puntos", "signo de pregunta",
                          "signo de exclamacion", "puntos suspensivos", "guion", "comillas",
                          "nueva linea", "nuevo parrafo", "mayusculas", "espacio", "tabulacion"],
            "Borrar": ["borrar ultima palabra", "borrar ultima linea", "borrar todo"],
            "Corregir": ["corregir [palabra]", "corregir [N] [palabra]", "seleccionar ultima palabra",
                        "siguiente", "siguiente ocurrencia",
                        "reemplazar [viejo] por [nuevo]"],
            "Dictado": ["iniciar dictado", "iniciar", "empezar", "detener", "parar", "stop", "pausar"],
            "Formato": ["negrita", "cursiva", "subrayar"],
            "Navegacion": ["ir al inicio", "ir al final", "seleccionar todo", "copiar", "pegar",
                           "deshacer", "rehacer", "desplazar arriba", "desplazar abajo",
                           "pagina arriba", "pagina abajo"],
            "Archivos": ["guardar", "guardar como", "abrir", "abrir archivo", "nuevo documento",
                         "exportar word", "exportar pdf", "exportar texto"],
            "Idioma dictado": ["lenguaje espanol", "lenguaje ingles", "lenguaje frances",
                               "lenguaje portugues", "lenguaje aleman", "lenguaje italiano"],
            "Traduccion": ["traducir", "traducir al ingles", "traducir al espanol",
                           "traducir al frances", "traducir al portugues",
                           "traducir al aleman", "traducir al italiano"],
            "Modo": ["modo online", "modo offline", "modo whisper", "usar vosk", "usar whisper"],
            "Apariencia": ["tema oscuro", "tema claro", "tema alto contraste",
                          "fuente mas grande", "fuente mas pequena",
                          "fuente normal", "fuente grande", "fuente muy grande"],
            "Whisper": ["modelo whisper tiny", "modelo whisper base", "modelo whisper small",
                        "modelo whisper medium", "modelo whisper large"],
            "Transcripcion": ["transcribir audio", "leer imagen", "texto de imagen"],
            "Ajustes": ["auto guardar activado", "auto guardar desactivado",
                        "feedback sonoro activado", "feedback sonoro desactivado",
                        "activar pausas", "desactivar pausas",
                        "descargar modelo"],
            "Otros": ["cerrar ayuda", "cerrar",
                      "ayuda", "mostrar comandos"],
        }
        for cat, cmds in categorias.items():
            lista.insert("end", f"\n{cat}\n", "cat")
            for cmd in cmds:
                lista.insert("end", f"   - {cmd}\n")
        lista.tag_config("cat", font=("Segoe UI", 10, "bold"), foreground=self.theme.colores["verde"])
        lista.config(state="disabled")
        tk.Button(ventana, text="Cerrar", command=lambda: self._cerrar_ayuda(ventana),
                  bg=self.theme.colores["acento"], fg=self.theme.colores["texto"],
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=6).pack(pady=12)

    def _cerrar_ayuda(self, ventana=None):
        v = ventana or getattr(self, '_ayuda_ventana', None)
        if v and v.winfo_exists():
            v.destroy()
        self._ayuda_ventana = None

    def _actualizar_contador(self, event=None):
        contenido = self.texto.get("1.0", "end-1c")
        palabras = len(contenido.split()) if contenido.strip() else 0
        self.lbl_palabras.config(text=f"Palabras: {palabras}")
        self.texto.edit_modified(False)
