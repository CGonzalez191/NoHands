import io
import json
import os
import queue
import sys
import tempfile
import threading
import urllib.request
import wave as wav_mod
import zipfile

import app
from app.constants import ruta_vosk, url_vosk, VOSK_MODELO_PREDET


class EngineBase:
    nombre = "base"

    def cargar_modelo(self):
        return True

    def descargar_modelo(self):
        pass

    def transcribir_chunk(self, chunk, idioma):
        return ""

    def transcribir_archivo(self, ruta, idioma):
        return ""

    def estado(self):
        return "desconocido"


class GoogleEngine(EngineBase):
    nombre = "google"

    def __init__(self):
        import speech_recognition as sr
        self.reconocedor = sr.Recognizer()
        self.reconocedor.pause_threshold = 0.8
        self.reconocedor.energy_threshold = 300

    def transcribir_chunk(self, chunk, idioma):
        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            with wav_mod.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(bytes(chunk))
            import speech_recognition as sr
            with sr.AudioFile(wav_path) as source:
                audio = self.reconocedor.record(source)
            return self.reconocedor.recognize_google(audio, language=idioma).lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return "__FALLBACK_OFFLINE__"
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except Exception as e:
                    print(f"[Vosk] Error al eliminar WAV temporal: {e}", file=sys.stderr)

    def transcribir_archivo(self, ruta, idioma):
        import speech_recognition as sr
        with sr.AudioFile(ruta) as source:
            audio = self.reconocedor.record(source)
        return self.reconocedor.recognize_google(audio, language=idioma)


class VoskEngine(EngineBase):
    nombre = "vosk"

    def __init__(self, nombre_modelo=None):
        self.modelo = None
        self.rec = None
        self.nombre_modelo = nombre_modelo or VOSK_MODELO_PREDET

    def _ruta(self):
        return ruta_vosk(self.nombre_modelo)

    def _url(self):
        return url_vosk(self.nombre_modelo)

    def cargar_modelo(self):
        if not app.VOSK_DISPONIBLE:
            return False
        if self.modelo is not None:
            return True
        ruta = self._ruta()
        if not os.path.isdir(ruta):
            return False
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            SetLogLevel(-1)
            self.modelo = Model(ruta)
            self.rec = KaldiRecognizer(self.modelo, 16000)
            return True
        except Exception as e:
            print(f"[Vosk] Error al cargar modelo: {e}", file=sys.stderr)
            self.modelo = None
            self.rec = None
            return False

    def transcribir_chunk(self, chunk, idioma):
        if self.rec is None:
            return None
        if self.rec.AcceptWaveform(bytes(chunk)):
            try:
                result = json.loads(self.rec.Result())
                text = result.get("text", "").strip()
                return text if text else None
            except json.JSONDecodeError:
                return None
        return None

    def transcribir_archivo(self, ruta, idioma):
        import wave
        from vosk import KaldiRecognizer
        if self.modelo is None:
            return ""
        try:
            with wave.open(ruta, "rb") as wf:
                rec = KaldiRecognizer(self.modelo, wf.getframerate())
                texto_parts = []
                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    if rec.AcceptWaveform(data):
                        try:
                            result = json.loads(rec.Result())
                            text = result.get("text", "").strip()
                            if text:
                                texto_parts.append(text)
                        except json.JSONDecodeError:
                            continue
                try:
                    result = json.loads(rec.FinalResult())
                    text = result.get("text", "").strip()
                    if text:
                        texto_parts.append(text)
                except json.JSONDecodeError:
                    pass
            return " ".join(texto_parts)
        except wave.Error as e:
            raise RuntimeError(f"Error al leer archivo de audio: {e}")
        except FileNotFoundError as e:
            raise RuntimeError(f"Archivo no encontrado: {e}")

    def estado(self):
        ruta = self._ruta()
        if self.modelo is not None:
            return "listo"
        if os.path.isdir(ruta):
            return "no_cargado"
        return "no_descargado"

    def descargar_modelo(self):
        if not app.VOSK_DISPONIBLE:
            return
        ruta = self._ruta()
        zip_path = ruta + ".zip"
        urllib.request.urlretrieve(self._url(), zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(os.path.dirname(ruta))
        os.remove(zip_path)
        self.cargar_modelo()


class WhisperEngine(EngineBase):
    nombre = "whisper"

    def __init__(self, nombre_modelo="base"):
        self.modelo = None
        self.nombre_modelo = nombre_modelo
        self._ultimo_texto = ""

    @property
    def modelo_id(self):
        return self.nombre_modelo

    @modelo_id.setter
    def modelo_id(self, valor):
        if valor != self.nombre_modelo:
            self.nombre_modelo = valor
            self.modelo = None

    def cargar_modelo(self):
        if not app.WHISPER_DISPONIBLE:
            return False
        if self.modelo is not None:
            return True
        try:
            self.modelo = app.WhisperModel(self.nombre_modelo, device="cpu", compute_type="int8")
            return True
        except Exception as e:
            print(f"[Whisper] Error al cargar modelo: {e}", file=sys.stderr)
            self.modelo = None
            return False

    def _wav_bytes(self, chunk):
        buf = io.BytesIO()
        with wav_mod.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(chunk)
        buf.seek(0)
        return buf

    def transcribir_chunk(self, chunk, idioma):
        if self.modelo is None:
            return None
        try:
            buf = self._wav_bytes(chunk)
            segments, _ = self.modelo.transcribe(buf, language=idioma.split("-")[0])
            texto = " ".join(s.text.strip() for s in segments).strip()
            if not texto:
                return None
            if texto != self._ultimo_texto and not texto.startswith(self._ultimo_texto):
                nuevo = texto
            elif len(texto) > len(self._ultimo_texto):
                nuevo = texto[len(self._ultimo_texto):].strip()
            else:
                return None
            self._ultimo_texto = texto
            return nuevo if nuevo else None
        except Exception as e:
            print(f"[Whisper] Error en transcribir_chunk: {e}", file=sys.stderr)
            return None

    def transcribir_simple(self, chunk, idioma):
        if self.modelo is None:
            return None
        try:
            buf = self._wav_bytes(chunk)
            segments, _ = self.modelo.transcribe(buf, language=idioma.split("-")[0])
            texto = " ".join(s.text.strip() for s in segments).strip()
            return texto if texto else None
        except Exception as e:
            print(f"[Whisper] Error en transcribir_simple: {e}", file=sys.stderr)
            return None

    def transcribir_archivo(self, ruta, idioma):
        if self.modelo is None:
            return ""
        segments, _ = self.modelo.transcribe(ruta, language=idioma.split("-")[0])
        return " ".join(s.text.strip() for s in segments)

    def estado(self):
        if self.modelo is not None:
            return "listo"
        return "no_cargado"

    def reset(self):
        self._ultimo_texto = ""


class Listener:
    TAMANO_CHUNK = 160000
    MAX_HILOS_TRANSCRIPCION = 4

    def __init__(self, cola_texto, config_manager):
        self.cola_texto = cola_texto
        self.config = config_manager
        self.activo = False
        self._listener_id = 0
        self._lock = threading.Lock()
        self._hilo = None
        self._semaforo_hilos = threading.BoundedSemaphore(self.MAX_HILOS_TRANSCRIPCION)

        self.escuchando = False
        self.modo_offline = False
        self.engine_offline = "vosk"
        self.idioma_dictado = "es-AR"
        self._motor = None

        self._buffer = bytearray()
        self._buffer_online = bytearray()
        self._motor_google = GoogleEngine()

    @property
    def motor(self):
        return self._motor

    @motor.setter
    def motor(self, valor):
        self._motor = valor

    def iniciar(self):
        self.detener()
        self._buffer = bytearray()
        self._buffer_online = bytearray()
        if self._motor:
            self._motor.reset() if hasattr(self._motor, 'reset') else None
        with self._lock:
            self.activo = True
            mi_id = self._listener_id
        self._iniciar_stream(mi_id)

    def _iniciar_stream(self, mi_id):
        q_audio = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            q_audio.put(bytes(indata))

        def sigo():
            return self.activo and self._listener_id == mi_id

        def hilo():
            if app.sd is None:
                self.cola_texto.put(("error", "  sounddevice no instalado"))
                return
            try:
                with app.sd.RawInputStream(samplerate=16000, blocksize=8000,
                                           dtype="int16", channels=1, callback=callback):
                    self.cola_texto.put(("info", "listener_iniciado"))
                    while sigo():
                        try:
                            data = q_audio.get(timeout=0.5)
                        except queue.Empty:
                            continue
                        if not sigo():
                            break
                        self._procesar_chunk(data)
            except Exception as e:
                self.cola_texto.put(("error", f"  Error en listener: {e}"))
            finally:
                if sigo():
                    self.cola_texto.put(("comando", "listener_caido"))

        self._hilo = threading.Thread(target=hilo, daemon=True)
        self._hilo.start()

    def _procesar_chunk(self, data):
        if self.modo_offline:
            if self._motor and self._motor.nombre == "whisper":
                self._buffer.extend(data)
                if len(self._buffer) >= self.TAMANO_CHUNK:
                    chunk = bytes(self._buffer)
                    self._buffer = bytearray()
                    if self._semaforo_hilos.acquire(blocking=False):
                        if self.escuchando:
                            threading.Thread(
                                target=self._transcribir_whisper_chunk,
                                args=(chunk,), daemon=True
                            ).start()
                        else:
                            threading.Thread(
                                target=self._transcribir_whisper_simple,
                                args=(chunk,), daemon=True
                            ).start()
            elif self._motor and self._motor.nombre == "vosk":
                texto = self._motor.transcribir_chunk(data, self.idioma_dictado)
                if texto:
                    if self.escuchando:
                        self.cola_texto.put(("frase", texto))
                    else:
                        self._verificar_comando_iniciar(texto)
        else:
            self._buffer_online.extend(data)
            if len(self._buffer_online) >= 32000:
                chunk = bytes(self._buffer_online)
                self._buffer_online = bytearray()
                if self._semaforo_hilos.acquire(blocking=False):
                    threading.Thread(
                        target=self._transcribir_online_chunk,
                        args=(chunk,), daemon=True
                    ).start()

    def _transcribir_online_chunk(self, chunk):
        try:
            texto = self._motor_google.transcribir_chunk(chunk, self.idioma_dictado)
            if texto == "__FALLBACK_OFFLINE__":
                self.cola_texto.put(("comando", "fallback_offline"))
            elif texto:
                if self.escuchando:
                    self.cola_texto.put(("frase", texto))
                else:
                    self._verificar_comando_iniciar(texto)
        finally:
            self._semaforo_hilos.release()

    def _transcribir_whisper_chunk(self, chunk):
        try:
            texto = self._motor.transcribir_chunk(chunk, self.idioma_dictado)
            if texto:
                self.cola_texto.put(("frase", texto))
        except Exception as e:
            if self.escuchando:
                self.cola_texto.put(("error", f"  Whisper: {e}"))
        finally:
            self._semaforo_hilos.release()

    def _transcribir_whisper_simple(self, chunk):
        try:
            texto = self._motor.transcribir_simple(chunk, self.idioma_dictado)
            if texto:
                self._verificar_comando_iniciar(texto)
        except Exception as e:
            print(f"[Whisper] Error en hilo simple: {e}", file=sys.stderr)
        finally:
            self._semaforo_hilos.release()

    def _verificar_comando_iniciar(self, frase):
        frase_lower = frase.lower().strip()
        for cmd in ["iniciar dictado", "iniciar", "empezar"]:
            if cmd in frase_lower:
                self.cola_texto.put(("comando", "iniciar_por_voz"))
                return
        for nombre, codigo in [
            ("lenguaje español españa", "idioma_es_ES"),
            ("lenguaje español", "idioma_es_AR"),
            ("lenguaje inglés", "idioma_en_US"),
            ("lenguaje portugués", "idioma_pt_BR"),
            ("lenguaje francés", "idioma_fr_FR"),
            ("lenguaje alemán", "idioma_de_DE"),
            ("lenguaje italiano", "idioma_it_IT"),
        ]:
            if nombre in frase_lower:
                self.cola_texto.put(("comando", codigo))
                return
        wake_cmds = [
            "ayuda", "mostrar comandos", "lista de comandos",
            "modo online", "modo en línea", "modo offline", "modo sin internet",
            "modo local", "modo whisper",
            "tema oscuro", "tema claro", "tema azul",
            "activar pausas", "desactivar pausas",
            "modo oscuro", "modo claro",
        ]
        for cmd in wake_cmds:
            if cmd in frase_lower:
                self.cola_texto.put(("comando", "iniciar_por_voz"))
                self.cola_texto.put(("frase", frase))
                return

    def detener(self):
        with self._lock:
            self.activo = False
            self._listener_id += 1
        if self._hilo and self._hilo.is_alive():
            self._hilo.join(timeout=3)
        self._hilo = None
        self._buffer = bytearray()
        self._buffer_online = bytearray()
        if self._motor and hasattr(self._motor, 'reset'):
            self._motor.reset()


def convertir_a_wav(ruta):
    if ruta.lower().endswith(".wav"):
        return ruta
    try:
        from pydub import AudioSegment
        import shutil, glob
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            candidates = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            ]
            winget_base = os.path.expandvars(
                r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
            if os.path.isdir(winget_base):
                pattern = os.path.join(winget_base, "Gyan.FFmpeg*", "**", "ffmpeg.exe")
                candidates = list(glob.glob(pattern, recursive=True)) + candidates
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
        raise RuntimeError(f"No se pudo convertir el audio: {e}")
