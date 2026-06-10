# 🎙 NoHands

**Asistente de dictado, transcripción de audio, OCR y traducción** diseñado para personas con discapacidad o lesiones en las manos.

## ✨ Funcionalidades

- **Dictado por voz** — online (Google Speech) u offline (Vosk)
- **Transcripción de audio** — WAV, MP3, M4A, FLAC, OGG, AAC, WMA
- **OCR** — extrae texto de imágenes (fotos de libros, documentos, etc.)
- **Traducción** — traduce el documento a 7 idiomas
- **Comandos de voz** — "punto", "coma", "nueva línea", "guardar", "detener", etc.
- **Multilenguaje** — 10 idiomas para dictado online

## 📦 Requisitos

- **Python 3.9+**
- **FFmpeg** (para transcripción de audio multi-formato)
- **Conexión a internet** solo para: dictado online, traducción, y primera descarga de modelos

## 🚀 Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/tuusuario/nohands.git
cd nohands
```

### 2. Instalar FFmpeg (Windows)

```bash
winget install Gyan.FFmpeg.Essentials
```

> También puede descargarlo manualmente de [ffmpeg.org](https://ffmpeg.org) y agregar la carpeta `bin` al PATH del sistema.

### 3. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

> **Nota:** En Linux adicionalmente necesitará:
> ```bash
> sudo apt-get install portaudio19-dev python3-pyaudio
> ```

### 4. Descargar modelo Vosk (para dictado offline)

Desde la aplicación: haga clic en **"📥 Descargar modelo"** en el panel lateral.

O manualmente:

```bash
mkdir models
curl -L -o models/model.zip https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
# En PowerShell:
# Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip" -OutFile "models\model.zip"
```

```bash
cd models
unzip model.zip
# En PowerShell: Expand-Archive -Path model.zip -DestinationPath .
```

### 5. Ejecutar

```bash
python redactor_por_voz.py
```

## 🧠 Primer uso

- **Dictado online**: seleccione "Online (Google)" y presione **"▶ Iniciar Dictado"**
- **Dictado offline**: seleccione "Offline (Vosk)" (requiere modelo descargado)
- **Transcribir audio**: haga clic en **"📂 Transcribir Audio…"** y seleccione un archivo
- **OCR**: haga clic en **"📸 Extraer texto de imagen…"** y seleccione una imagen
  - La primera vez descargará automáticamente los modelos de EasyOCR (~100-200MB)
- **Traducir**: escriba o transcriba texto, seleccione idioma y presione **"🌐 Traducir documento"**

## 🎤 Comandos de voz

Mientras dicta puede decir:

| Comando | Acción |
|---|---|
| "punto" | `.` |
| "coma" | `,` |
| "punto y coma" | `;` |
| "dos puntos" | `:` |
| "signo de pregunta" / "interrogación" | `?` |
| "signo de exclamación" / "admiración" | `!` |
| "nueva línea" / "nuevo párrafo" | salto de línea |
| "borrar última palabra" | borra la última palabra |
| "borrar todo" | limpia el documento |
| "guardar" | guarda el archivo |
| "detener" / "parar" / "stop" | pausa el dictado |

## 📁 Archivos del proyecto

```
nohands/
├── redactor_por_voz.py   → Aplicación principal
├── requirements.txt       → Dependencias de Python
├── models/                → Modelos Vosk (descargar)
├── .gitignore
└── README.md
```

## 🌐 Idiomas disponibles

**Dictado online:** Español (Argentina/España), Inglés (US/UK), Portugués, Francés, Alemán, Italiano, Japonés, Chino

**Traducción:** Inglés, Portugués, Francés, Alemán, Italiano, Japonés, Chino

**OCR:** 80+ idiomas (EasyOCR)

## ⚙️ Funciones sin internet

| Función | Offline |
|---|---|
| Dictado (Vosk) | ✅ |
| Transcripción de audio (modo offline) | ✅ |
| OCR (EasyOCR) | ✅ |
| Editar / Guardar / Abrir | ✅ |
| Dictado (Google) | ❌ |
| Traducción | ❌ |
| Descargar modelos | ❌ |
