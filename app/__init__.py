import sys

WINSOUND_DISPONIBLE = False
try:
    import winsound
    WINSOUND_DISPONIBLE = True
except ImportError:
    pass

sd = None
try:
    import sounddevice as sd
except ImportError:
    pass

VOSK_DISPONIBLE = False
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_DISPONIBLE = True
except ImportError:
    pass

WHISPER_DISPONIBLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_DISPONIBLE = True
except ImportError:
    pass

OCR_DISPONIBLE = False
try:
    import easyocr
    OCR_DISPONIBLE = True
except ImportError:
    pass

DOCX_DISPONIBLE = False
try:
    from docx import Document
    from docx.shared import Pt
    DOCX_DISPONIBLE = True
except ImportError:
    pass

PDF_DISPONIBLE = False
try:
    from fpdf import FPDF
    PDF_DISPONIBLE = True
except ImportError:
    pass

TTS_DISPONIBLE = False
try:
    import pyttsx3
    TTS_DISPONIBLE = True
except ImportError:
    pass
