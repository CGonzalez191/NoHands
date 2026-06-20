# NoHands

**Asistente de dictado por voz, transcripción, OCR y traducción** diseñado para personas con discapacidad o lesiones en las manos.

Todo se controla por voz: dictar, editar, navegar, cambiar ajustes y más.

## Funcionalidades

- **Dictado por voz** — Online (Google Speech) u offline (Vosk o faster-whisper)
- **Reconocimiento offline** — Vosk (rápido, modelos pequeño o grande) o Whisper tiny/base/small/medium/large-v3 (más preciso)
- **Modo manos libres** — El micrófono se activa solo al abrir la app
- **Comandos de voz** — 150+ comandos: puntuación, edición, formato (negrita, cursiva, subrayar), navegación (scroll, inicio/fin), portapapeles, guardar, cambiar tema, ajustar fuente, cambiar motor, y más
- **Transcripción de audio** — WAV, MP3, M4A, FLAC, OGG, AAC, WMA
- **OCR** — Extrae texto de imágenes (EasyOCR, 80+ idiomas)
- **Traducción** — Traduce el documento a 7 idiomas
- **Exportación** — .txt, .docx (Word), .pdf
- **Temas visuales** — Oscuro, Claro, Alto Contraste
- **Control de fuente** — Slider de tamaño (8-36)
- **Pausas activas** — Recordatorio 20-20-20 cada 20 min, alerta de sesión prolongada (>1h)
- **Auto-guardado** — Intervalo configurable (1-60 min)
- **Feedback sonoro** — Confirmaciones por beeps
- **Configuración persistente** — Los ajustes se guardan en `~/.nohands/config.json`

## Requisitos

- **Python 3.9+** — Descargar de [python.org](https://python.org) (marcar "Add to PATH" al instalar)
- **FFmpeg** — Solo para transcripción de audio multi-formato (opcional)
- **Conexión a internet** — Solo para dictado online, traducción, y primera descarga de modelos

## Instalación paso a paso

### 1. Descomprimir el zip

Extraiga todo el contenido del zip en una carpeta, por ejemplo `C:\NoHands`.

### 2. Abrir terminal en la carpeta

```bash
cd ruta/donde/descomprimiste/NoHands
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

> **Tip:** Si usa varias apps de Python, cree un entorno virtual primero:
> ```bash
> python -m venv venv
> venv\Scripts\activate    # Windows
> pip install -r requirements.txt
> ```

### 4. FFmpeg (opcional, para transcribir audios .mp3, .m4a, etc.)

```bash
winget install Gyan.FFmpeg.Essentials
```

O descargue de [ffmpeg.org](https://ffmpeg.org) y agregue la carpeta `bin` al PATH.

### 5. Ejecutar

```bash
python main.py
```

O haga doble clic en `iniciar_nohands.vbs` (Windows) para ejecución silenciosa sin terminal.

## Primer uso

| Acción | Cómo hacerlo |
|--------|-------------|
| Dictar | Seleccione Online/Offline/Whisper y presione **Iniciar Dictado** |
| Comandos | Diga "mostrar comandos" para ver la lista completa |
| Manos libres | Active el checkbox en el panel lateral |
| Transcribir audio | Presione **Transcribir Audio…** y seleccione un archivo |
| OCR | Presione **Extraer texto de imagen…** y seleccione una imagen |
| Traducir | Seleccione idioma y presione **Traducir documento** |
| Exportar | Use **Exportar .docx** o **Exportar .pdf** |

## Comandos de voz principales

| Categoría | Ejemplos |
|-----------|----------|
| Puntuación | punto, coma, punto y coma, dos puntos, signo de pregunta, exclamación |
| Edición | negrita, cursiva, subrayar, copiar, pegar, borrar ultima palabra, seleccionar todo |
| Navegación | ir al inicio/fin, desplazar arriba/abajo, pagina arriba/abajo |
| Corrección | corregir [palabra], corregir [N] [palabra], siguiente, siguiente ocurrencia, reemplazar [X] por [Y], seleccionar ultima palabra |
| Archivo | guardar, guardar como, abrir, nuevo documento, exportar |
| Motor | modo online, modo offline, modo whisper, usar vosk, usar whisper |
| Tema | tema oscuro/claro/alto contraste |
| Fuente | fuente normal (12), grande (16), muy grande (20) |
| Whisper | modelo whisper tiny/base/small/medium/large |
| Ajustes | auto guardar activado/desactivado, feedback sonoro activado/desactivado, pausas activadas/desactivadas |
| Otros | ayuda, cerrar ayuda, cerrar, tabulacion, deshacer, rehacer |

## Idiomas

**Dictado online:** Español (AR/ES), Inglés (US/UK), Portugués, Francés, Alemán, Italiano, Japonés, Chino

**Traducción:** Inglés, Portugués, Francés, Alemán, Italiano, Japonés, Chino

**OCR:** 80+ idiomas (EasyOCR)

## Configuración

Archivo `~/.nohands/config.json` con ajustes persistentes:
- Tema, tamaño de fuente, auto-guardado, pausas activas, feedback sonoro
- Engine offline (vosk/whisper), modelo Whisper, modelo Vosk (small/large)
- Modo manos libres

## Funciones sin internet

| Función | Offline |
|---------|---------|
| Dictado (Vosk/Whisper) | ✅ |
| Transcripción de audio | ✅ |
| OCR (EasyOCR) | ✅ |
| Editar / Guardar / Abrir | ✅ |
| Exportar .txt / .docx / .pdf | ✅ |
| Dictado (Google) | ❌ |
| Traducción | ❌ |
| Descargar modelos | ❌ |