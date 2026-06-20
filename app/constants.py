import os

RUTA_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MODELO_PEQUENO = os.path.join(RUTA_APP, "models", "vosk-model-small-es-0.42")
RUTA_MODELO_GRANDE = os.path.join(RUTA_APP, "models", "vosk-model-es-0.42")
RUTA_MODELO = RUTA_MODELO_PEQUENO

VOSK_MODELOS = {
    "small": {
        "ruta": RUTA_MODELO_PEQUENO,
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
        "nombre": "Pequeño (38 MB, rápido)",
    },
    "large": {
        "ruta": RUTA_MODELO_GRANDE,
        "url": "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip",
        "nombre": "Grande (1.2 GB, preciso)",
    },
}
VOSK_MODELO_PREDET = "small"

URL_MODELO = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"


def ruta_vosk(nombre_modelo=None):
    if nombre_modelo is None:
        nombre_modelo = VOSK_MODELO_PREDET
    info = VOSK_MODELOS.get(nombre_modelo, VOSK_MODELOS["small"])
    return info["ruta"]


def url_vosk(nombre_modelo=None):
    if nombre_modelo is None:
        nombre_modelo = VOSK_MODELO_PREDET
    info = VOSK_MODELOS.get(nombre_modelo, VOSK_MODELOS["small"])
    return info["url"]

MODELO_WHISPER_PREDET = "base"
MODELOS_WHISPER_DISP = ["tiny", "base", "small", "medium", "large-v3"]

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

COMANDOS = {
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
    "nueva línea":              ("accion", "nueva_linea"),
    "nuevo párrafo":            ("accion", "nuevo_parrafo"),
    "espacio":                  ("insertar", " "),
    "mayúsculas":               ("accion", "mayusculas"),
    "borrar última palabra":    ("accion", "borrar_ultima"),
    "borrar última línea":      ("accion", "borrar_ultima_linea"),
    "borrar todo":              ("accion", "borrar_todo"),
    "guardar":                  ("accion", "guardar"),
    "guardar como":             ("accion", "guardar_como"),
    "detener":                  ("accion", "detener"),
    "parar":                    ("accion", "detener"),
    "stop":                     ("accion", "detener"),
    "pausar":                   ("accion", "detener"),
    "iniciar dictado":          ("accion", "iniciar"),
    "iniciar":                  ("accion", "iniciar"),
    "empezar":                  ("accion", "iniciar"),
    "negrita":                  ("accion", "negrita"),
    "cursiva":                  ("accion", "cursiva"),
    "subrayar":                 ("accion", "subrayar"),
    "ir al inicio":             ("accion", "ir_inicio"),
    "ir al final":              ("accion", "ir_final"),
    "seleccionar todo":         ("accion", "seleccionar_todo"),
    "copiar":                   ("accion", "copiar"),
    "pegar":                    ("accion", "pegar"),
    "exportar word":            ("accion", "exportar_docx"),
    "exportar docx":            ("accion", "exportar_docx"),
    "exportar pdf":             ("accion", "exportar_pdf"),
    "lenguaje español":         ("accion", "idioma_es_AR"),
    "lenguaje español españa":  ("accion", "idioma_es_ES"),
    "lenguaje inglés":          ("accion", "idioma_en_US"),
    "lenguaje portugués":       ("accion", "idioma_pt_BR"),
    "lenguaje francés":         ("accion", "idioma_fr_FR"),
    "lenguaje alemán":          ("accion", "idioma_de_DE"),
    "lenguaje italiano":        ("accion", "idioma_it_IT"),
    "abrir archivo":            ("accion", "abrir"),
    "abrir documento":          ("accion", "abrir"),
    "abrir":                    ("accion", "abrir"),
    "nuevo documento":          ("accion", "nuevo_documento"),
    "nuevo":                    ("accion", "nuevo_documento"),
    "exportar texto":           ("accion", "exportar_txt"),
    "guardar texto":            ("accion", "exportar_txt"),
    "modo online":              ("accion", "modo_online"),
    "modo en línea":            ("accion", "modo_online"),
    "modo offline":             ("accion", "modo_offline"),
    "modo sin internet":        ("accion", "modo_offline"),
    "modo local":               ("accion", "modo_offline"),
    "modo whisper":             ("accion", "modo_whisper"),
    "tema oscuro":              ("accion", "tema_oscuro"),
    "tema claro":               ("accion", "tema_claro"),
    "tema azul":                ("accion", "tema_azul"),
    "modo oscuro":              ("accion", "tema_oscuro"),
    "modo claro":               ("accion", "tema_claro"),
    "fuente más grande":        ("accion", "fuente_aumentar"),
    "letra más grande":         ("accion", "fuente_aumentar"),
    "aumentar fuente":          ("accion", "fuente_aumentar"),
    "fuente más pequeña":       ("accion", "fuente_disminuir"),
    "letra más pequeña":        ("accion", "fuente_disminuir"),
    "disminuir fuente":         ("accion", "fuente_disminuir"),
    "traducir":                 ("accion", "traducir"),
    "traducir al inglés":       ("accion", "traducir_en"),
    "traducir al español":      ("accion", "traducir_es"),
    "traducir al francés":      ("accion", "traducir_fr"),
    "traducir al portugués":    ("accion", "traducir_pt"),
    "traducir al alemán":       ("accion", "traducir_de"),
    "traducir al italiano":     ("accion", "traducir_it"),
    "transcribir audio":        ("accion", "transcribir_audio"),
    "transcribir archivo":      ("accion", "transcribir_audio"),
    "extraer texto imagen":     ("accion", "ocr_imagen"),
    "leer imagen":              ("accion", "ocr_imagen"),
    "texto de imagen":          ("accion", "ocr_imagen"),
    "descargar modelo":         ("accion", "descargar_modelo"),
    "instalar modelo":          ("accion", "descargar_modelo"),
    "deshacer":                 ("accion", "deshacer"),
    "rehacer":                  ("accion", "rehacer"),
    "activar pausas":           ("accion", "pausas_on"),
    "desactivar pausas":        ("accion", "pausas_off"),
    "ayuda":                    ("accion", "ayuda"),
    "mostrar comandos":         ("accion", "ayuda"),
    "lista de comandos":        ("accion", "ayuda"),
    "qué puedo decir":          ("accion", "ayuda"),

    # Unaccented fallbacks
    "interrogacion":            ("insertar", "?"),
    "admiracion":               ("insertar", "!"),
    "guion":                    ("insertar", " - "),
    "nueva linea":              ("accion", "nueva_linea"),
    "nuevo parrafo":            ("accion", "nuevo_parrafo"),
    "mayusculas":               ("accion", "mayusculas"),
    "borrar ultima palabra":    ("accion", "borrar_ultima"),
    "borrar ultima linea":      ("accion", "borrar_ultima_linea"),
    "lenguaje espanol":         ("accion", "idioma_es_AR"),
    "lenguaje espanol espana":  ("accion", "idioma_es_ES"),
    "lenguaje ingles":          ("accion", "idioma_en_US"),
    "lenguaje portugues":       ("accion", "idioma_pt_BR"),
    "lenguaje frances":         ("accion", "idioma_fr_FR"),
    "lenguaje aleman":          ("accion", "idioma_de_DE"),
    "lenguaje italiano":        ("accion", "idioma_it_IT"),
    "traducir al ingles":       ("accion", "traducir_en"),
    "traducir al espanol":      ("accion", "traducir_es"),
    "traducir al frances":      ("accion", "traducir_fr"),
    "traducir al portugues":    ("accion", "traducir_pt"),
    "traducir al aleman":       ("accion", "traducir_de"),
    "traducir al italiano":     ("accion", "traducir_it"),
    "fuente mas grande":        ("accion", "fuente_aumentar"),
    "letra mas grande":         ("accion", "fuente_aumentar"),
    "aumentar fuente":          ("accion", "fuente_aumentar"),
    "fuente mas pequena":       ("accion", "fuente_disminuir"),
    "letra mas pequena":        ("accion", "fuente_disminuir"),
    "disminuir fuente":         ("accion", "fuente_disminuir"),

    # New commands: navigation
    "tabulación":               ("insertar", "\t"),
    "tabulacion":               ("insertar", "\t"),
    "desplazar arriba":         ("accion", "scroll_up"),
    "scroll up":                ("accion", "scroll_up"),
    "desplazar abajo":          ("accion", "scroll_down"),
    "scroll down":              ("accion", "scroll_down"),
    "subir":                    ("accion", "scroll_up"),
    "bajar":                    ("accion", "scroll_down"),
    "página arriba":            ("accion", "scroll_page_up"),
    "página abajo":             ("accion", "scroll_page_down"),
    "pagina arriba":            ("accion", "scroll_page_up"),
    "pagina abajo":             ("accion", "scroll_page_down"),

    # New commands: settings
    "usar vosk":                ("accion", "usar_vosk"),
    "usar whisper":             ("accion", "modo_whisper"),
    "tema alto contraste":      ("accion", "tema_alto_contraste"),
    "alto contraste":           ("accion", "tema_alto_contraste"),
    "auto guardar activado":    ("accion", "auto_save_on"),
    "auto guardar desactivado": ("accion", "auto_save_off"),
    "auto guardar on":          ("accion", "auto_save_on"),
    "auto guardar off":         ("accion", "auto_save_off"),
    "feedback sonoro activado": ("accion", "feedback_on"),
    "feedback sonoro desactivado":("accion", "feedback_off"),
    "cerrar ayuda":             ("accion", "cerrar_ayuda"),
    "cerrar":                   ("accion", "cerrar_ayuda"),

    # Font presets
    "fuente normal":            ("accion", "fuente_12"),
    "fuente grande":            ("accion", "fuente_16"),
    "fuente muy grande":        ("accion", "fuente_20"),

    # Whisper model selection
    "modelo whisper tiny":      ("accion", "whisper_model_tiny"),
    "modelo whisper base":      ("accion", "whisper_model_base"),
    "modelo whisper small":     ("accion", "whisper_model_small"),
    "modelo whisper medium":    ("accion", "whisper_model_medium"),
    "modelo whisper large":     ("accion", "whisper_model_large"),

    "siguiente":                ("accion", "siguiente"),
    "siguiente ocurrencia":     ("accion", "siguiente"),

    "seleccionar última palabra": ("accion", "seleccionar_ultima"),
    "seleccionar ultima palabra": ("accion", "seleccionar_ultima"),
}

TEMAS = {
    "oscuro": {
        "bg": "#1a1a2e",
        "panel": "#16213e",
        "acento": "#0f3460",
        "verde": "#4ecca3",
        "rojo": "#e94560",
        "texto": "#eaeaea",
        "subtexto": "#8892b0",
        "texto_bg": "#0d1b2a",
        "entrada_bg": "#0d1b2a",
        "barra_inferior": "#0d1b2a",
        "btn_activo": "#1a4a7a",
    },
    "claro": {
        "bg": "#f0f2f5",
        "panel": "#ffffff",
        "acento": "#d0d7de",
        "verde": "#1a7d36",
        "rojo": "#c62828",
        "texto": "#1a1a2e",
        "subtexto": "#57606a",
        "texto_bg": "#ffffff",
        "entrada_bg": "#ffffff",
        "barra_inferior": "#e8eaed",
        "btn_activo": "#b0b8c1",
    },
    "alto_contraste": {
        "bg": "#000000",
        "panel": "#000000",
        "acento": "#333333",
        "verde": "#00ff41",
        "rojo": "#ff0000",
        "texto": "#ffffff",
        "subtexto": "#ffff00",
        "texto_bg": "#000000",
        "entrada_bg": "#000000",
        "barra_inferior": "#111111",
        "btn_activo": "#444444",
    },
}

TEMA_NOMBRES = {
    "oscuro": "  Oscuro",
    "claro": "  Claro",
    "alto_contraste": "  Alto Contraste",
}

MAPA_IDIOMAS_COMANDO = {
    "idioma_es_AR": ("Español (Argentina)", True),
    "idioma_es_ES": ("Español (España)", True),
    "idioma_en_US": ("English (US)", False),
    "idioma_pt_BR": ("Português (Brasil)", False),
    "idioma_fr_FR": ("Français", False),
    "idioma_de_DE": ("Deutsch", False),
    "idioma_it_IT": ("Italiano", False),
}

MAPA_TRADUCCION_VOZ = {
    "en": "Inglés", "es": "Español", "fr": "Francés",
    "pt": "Portugués", "de": "Alemán", "it": "Italiano",
}
