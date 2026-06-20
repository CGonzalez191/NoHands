"""
Lanzador por voz para NoHands
Escucha "nohands" en segundo plano y abre la aplicación.
"""

import os
import sys
import subprocess
import threading
import queue
import time
import json
import pathlib

RUTA_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")

RUTA_MODELO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "models", "vosk-model-small-es-0.42"
)

VOSK_DISPONIBLE = False
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    import sounddevice as sd
    VOSK_DISPONIBLE = True
except ImportError:
    pass

# winsound solo existe en Windows; fallback multiplataforma con campana de terminal
SONIDO_DISPONIBLE = False
try:
    import winsound
    SONIDO_DISPONIBLE = True
except ImportError:
    pass

PALABRAS_ACTIVACION = ["nohands", "no hands", "no-hand", "iniciar nohands", "abrir nohands", "hola nohands"]
PALABRAS_ACTIVACION_FONETICA = ["no hans", "now hans", "no ans", "now and", "no hand", "no ands", "no han", "non"]
# Lista definida una sola vez (eliminado duplicado)
PALABRAS_APAGADO = ["cerrar nohands", "adiós nohands", "salir", "detener nohands"]

LOCK = threading.Lock()
proceso_app = None
_evento_salida = threading.Event()   # señaliza al hilo principal que debe terminar


def beep(frecuencia=800, duracion=150):
    if SONIDO_DISPONIBLE:
        try:
            winsound.Beep(frecuencia, duracion)
            return
        except Exception:
            pass
    # Fallback multiplataforma
    print('\a', end='', flush=True)


def beep_confirmacion():
    beep(800, 100)
    time.sleep(0.1)
    beep(1000, 150)


def beep_error():
    beep(300, 200)
    beep(200, 300)


def abrir_app():
    global proceso_app
    with LOCK:
        if proceso_app is not None and proceso_app.poll() is None:
            return
        try:
            proceso_app = subprocess.Popen(
                [sys.executable, RUTA_APP],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            beep_confirmacion()
            print("🔊 NoHands iniciada — lanzador detenido")
            # Señalizar al hilo principal para salir limpiamente
            # (sys.exit() en un hilo no-principal solo termina ese hilo, no el proceso)
            _evento_salida.set()
        except Exception as e:
            beep_error()
            print(f"❌ Error al abrir NoHands: {e}")


def cerrar_app():
    global proceso_app
    with LOCK:
        if proceso_app is not None and proceso_app.poll() is None:
            try:
                proceso_app.terminate()
                proceso_app.wait(timeout=3)
            except Exception:
                try:
                    proceso_app.kill()
                except Exception:
                    pass
            proceso_app = None
            beep(400, 200)
            beep(600, 200)
            print("🔇 NoHands cerrada")


def contiene_activacion(texto):
    texto = texto.lower().strip()
    for p in PALABRAS_ACTIVACION:
        if p in texto:
            return True
    for p in PALABRAS_ACTIVACION_FONETICA:
        if p in texto:
            return True
    return False


def contiene_apagado(texto):
    texto = texto.lower().strip()
    for p in PALABRAS_APAGADO:
        if p in texto:
            return True
    return False


def bucle_escucha():
    if not VOSK_DISPONIBLE:
        print("❌ Vosk no está instalado. Ejecutá: pip install vosk sounddevice")
        return

    if not os.path.isdir(RUTA_MODELO):
        print(f"❌ Modelo Vosk no encontrado en: {RUTA_MODELO}")
        print("   Abrí NoHands manualmente y descargá el modelo desde el panel.")
        return

    try:
        SetLogLevel(-1)
        modelo = Model(RUTA_MODELO)
        rec = KaldiRecognizer(modelo, 16000)
    except Exception as e:
        print(f"❌ Error al cargar modelo Vosk: {e}")
        return

    q_audio = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        q_audio.put(bytes(indata))

    print("🎤 Escuchando... Decí 'NoHands' para abrir la aplicación")
    print("   Decí 'cerrar NoHands' para cerrarla")
    print("   Presioná Ctrl+C para salir")
    beep(600, 100)
    beep(800, 100)

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000,
                               dtype="int16", channels=1,
                               callback=callback):
            while not _evento_salida.is_set():
                # Timeout de 0.5 s para poder revisar _evento_salida periódicamente
                try:
                    data = q_audio.get(timeout=0.5)
                except queue.Empty:
                    continue
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        print(f"  → {text}")
                        if contiene_activacion(text):
                            print("📢 Activación detectada")
                            abrir_app()
                        if contiene_apagado(text):
                            print("📢 Apagado detectado")
                            cerrar_app()
    except KeyboardInterrupt:
        pass
    finally:
        cerrar_app()
        print("👋 Lanzador detenido")


def main():
    if not VOSK_DISPONIBLE:
        print("⚠️  Vosk no disponible. Abriendo NoHands directamente...")
        abrir_app()
        return

    hilo = threading.Thread(target=bucle_escucha, daemon=True)
    hilo.start()

    try:
        # Esperar hasta que el hilo termine o _evento_salida se active
        while hilo.is_alive() and not _evento_salida.is_set():
            hilo.join(1)
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")
    finally:
        _evento_salida.set()   # asegura que bucle_escucha salga si sigue corriendo


if __name__ == "__main__":
    main()
