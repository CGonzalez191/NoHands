import json
import pathlib
import sys

CONFIG_DIR = pathlib.Path.home() / ".nohands"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigManager:
    def __init__(self):
        self.config = self._cargar()

    def _cargar(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Config] Error al cargar config: {e}", file=sys.stderr)
        return self._predeterminados()

    def _predeterminados(self):
        return {
            "tema": "oscuro",
            "tamano_fuente": 12,
            "auto_guardar": True,
            "intervalo_auto_guardar": 5,
            "pausas_activas": True,
            "intervalo_pausa": 20,
            "feedback_sonoro": True,
            "alto_contraste": False,
            "engine_offline": "vosk",
            "whisper_model": "base",
            "manos_libres": False,
            "vosk_model": "small",
        }

    def get(self, clave, predeterminado=None):
        return self.config.get(clave, predeterminado)

    def set(self, clave, valor):
        self.config[clave] = valor
        self._guardar()

    def _guardar(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[Config] Error al guardar config: {e}", file=sys.stderr)
