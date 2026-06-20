import threading
import time
import app


class FeedbackSonoro:
    def __init__(self, config_manager):
        self.config = config_manager
        self._tts_engine = None

    def _get_tts(self):
        if not app.TTS_DISPONIBLE:
            return None
        if self._tts_engine is None:
            try:
                import pyttsx3
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", 150)
                self._tts_engine.setProperty("volume", 0.8)
            except Exception as e:
                print(f"[TTS] Error al inicializar: {e}", file=sys.stderr)
                return None
        return self._tts_engine

    def _beep(self, frecuencia=800, duracion=150):
        if not self.config.get("feedback_sonoro", True):
            return
        if app.WINSOUND_DISPONIBLE:
            try:
                import winsound
                winsound.Beep(frecuencia, duracion)
                return
            except Exception as e:
                print(f"[Feedback] Error en Beep: {e}", file=sys.stderr)
        print('\a', end='', flush=True)

    def _hablar(self, texto):
        if not self.config.get("feedback_sonoro", True):
            return
        engine = self._get_tts()
        if engine:
            try:
                engine.say(texto)
                engine.runAndWait()
            except Exception as e:
                print(f"[TTS] Error al hablar: {e}", file=sys.stderr)
                self._beep()

    def dictado_iniciado(self):
        threading.Thread(target=self._secuencia_inicio, daemon=True).start()

    def _secuencia_inicio(self):
        self._beep(880, 120)
        time.sleep(0.08)
        self._beep(1100, 120)
        time.sleep(0.08)
        self._beep(1320, 200)

    def dictado_detenido(self):
        threading.Thread(target=self._secuencia_detener, daemon=True).start()

    def _secuencia_detener(self):
        self._beep(600, 200)
        time.sleep(0.1)
        self._beep(400, 200)

    def guardado(self):
        threading.Thread(target=self._secuencia_guardado, daemon=True).start()

    def _secuencia_guardado(self):
        self._beep(800, 100)
        self._beep(1000, 100)
        self._beep(1200, 150)

    def error(self):
        threading.Thread(target=self._secuencia_error, daemon=True).start()

    def _secuencia_error(self):
        self._beep(300, 200)
        self._beep(200, 300)

    def comando_detectado(self):
        self._beep(1000, 80)

    def pausa_recordatorio(self):
        threading.Thread(target=self._secuencia_pausa, daemon=True).start()

    def _secuencia_pausa(self):
        self._beep(500, 100)
        self._beep(500, 100)
        self._beep(500, 100)
