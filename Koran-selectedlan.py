# save as stt_translate_pyqt.py
import sys
import os
import tempfile
import threading
import requests
from gtts import gTTS
import pygame

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject

import speech_recognition as sr


# Simple signals helper

class Signals(QObject):
    transcription_ready = pyqtSignal(str)
    translation_ready = pyqtSignal(str)
    set_status = pyqtSignal(str)

signals = Signals()


# Config / language map (LibreTranslate + gTTS use ISO codes)
# You can expand this map to whatever you need.

LANGS = {
    "English": "en",
    "Korean": "ko",
    "Vietnamese": "vi",
    "Burmese": "my",
    "Khmer": "km",
    "Chinese (Simplified)": "zh",
    "Japanese": "ja",
    "French": "fr",
    "Spanish": "es"
}

# helper to map for Google recognizer language tags
RECOGNIZER_LANG_TAG = {
    "ko": "ko-KR",
    "en": "en-US",
    "vi": "vi-VN",
    "my": "my-MM",   # might not be supported by recognizer
    "km": "km-KH",   # might not be supported
    "zh": "zh-CN",
    "ja": "ja-JP",
    "fr": "fr-FR",
    "es": "es-ES"
}

# Translation endpoints
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# -----------------
# Worker functions (run in background threads)
# -----------------
def do_record_and_transcribe(source_lang_code="ko"):
    """Record from microphone (single phrase) and transcribe using Google's web recognizer."""
    signals.set_status.emit("Listening...")
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=8, phrase_time_limit=12)
        except Exception as e:
            signals.set_status.emit(f"Recording error: {e}")
            signals.transcription_ready.emit("")
            return

    signals.set_status.emit("Transcribing...")
    # recognizer language tag (e.g., ko-KR)
    lang_tag = RECOGNIZER_LANG_TAG.get(source_lang_code, "ko-KR")
    try:
        text = r.recognize_google(audio, language=lang_tag)
        signals.transcription_ready.emit(text)
        signals.set_status.emit("Transcription done.")
    except sr.UnknownValueError:
        signals.set_status.emit("Could not understand audio.")
        signals.transcription_ready.emit("")
    except sr.RequestError as e:
        signals.set_status.emit(f"STT request error: {e}")
        signals.transcription_ready.emit("")

def do_translate(text, source_code, target_code):
    signals.set_status.emit("Translating...")
    if not text:
        signals.set_status.emit("Nothing to translate.")
        signals.translation_ready.emit("")
        return
    
    # Try Google Translate first
    try:
        params = {
            "client": "gtx",
            "sl": source_code,
            "tl": target_code,
            "dt": "t",
            "q": text
        }
        resp = requests.get(GOOGLE_TRANSLATE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and len(data) > 0 and len(data[0]) > 0:
            translated = data[0][0][0]
            signals.translation_ready.emit(translated)
            signals.set_status.emit("Translation done.")
            return
    except Exception as e:
        signals.set_status.emit(f"Google Translate failed: {e}, trying fallback...")
    
    # Fallback to MyMemory API
    try:
        params = {
            "q": text,
            "langpair": f"{source_code}|{target_code}"
        }
        resp = requests.get(MYMEMORY_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        if translated:
            signals.translation_ready.emit(translated)
            signals.set_status.emit("Translation done.")
        else:
            signals.set_status.emit("Translation failed.")
            signals.translation_ready.emit("")
    except Exception as e:
        signals.set_status.emit(f"Translation error: {e}")
        signals.translation_ready.emit("")

def do_tts_play(text, target_code):
    if not text:
        signals.set_status.emit("Nothing to play.")
        return
    signals.set_status.emit("Generating speech...")
    try:
        # gTTS language uses short ISO codes (en, ko, vi, ...)
        tts = gTTS(text=text, lang=target_code)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.close()
        tts.save(tmp.name)
        signals.set_status.emit("Playing audio...")
        
        # Initialize pygame mixer and play the audio
        pygame.mixer.init()
        pygame.mixer.music.load(tmp.name)
        pygame.mixer.music.play()
        
        # Wait for the music to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        try:
            os.remove(tmp.name)
        except:
            pass
        signals.set_status.emit("Done.")
    except Exception as e:
        signals.set_status.emit(f"TTS error: {e}")

# -----------------
# Main Window
# -----------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Korean → Multilang Speech Translator (MCP)")
        self.setMinimumSize(600, 480)
        layout = QVBoxLayout()

        # status
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # controls: target language selector + buttons
        controls = QHBoxLayout()
        self.lang_box = QComboBox()
        for name in LANGS.keys():
            if name == "Korean":
                continue  # target shouldn't be Korean by default
            self.lang_box.addItem(name)
        controls.addWidget(QLabel("Target:"))
        controls.addWidget(self.lang_box)

        self.record_button = QPushButton("Record (Korean)")
        self.record_button.clicked.connect(self.on_record_clicked)
        controls.addWidget(self.record_button)

        self.play_button = QPushButton("Play Translation")
        self.play_button.clicked.connect(self.on_play_clicked)
        controls.addWidget(self.play_button)

        layout.addLayout(controls)

        # text areas
        layout.addWidget(QLabel("Recognized (Korean):"))
        self.orig_text = QTextEdit()
        self.orig_text.setReadOnly(False)
        layout.addWidget(self.orig_text)

        layout.addWidget(QLabel("Translated:"))
        self.trans_text = QTextEdit()
        self.trans_text.setReadOnly(True)
        layout.addWidget(self.trans_text)

        self.setLayout(layout)

        # wire signals
        signals.transcription_ready.connect(self.on_transcription_ready)
        signals.translation_ready.connect(self.on_translation_ready)
        signals.set_status.connect(self.on_status)

    def on_status(self, s):
        self.status_label.setText(s)

    def on_record_clicked(self):
        # disable button while recording
        self.record_button.setEnabled(False)
        self.status_label.setText("Starting...")
        # Record & transcribe in background
        t = threading.Thread(target=self.background_record_and_translate, daemon=True)
        t.start()

    def background_record_and_translate(self):
        # 1) STT (assume source = Korean)
        do_record_and_transcribe(source_lang_code="ko")
        # transcription_ready signal will trigger translation below

    def on_transcription_ready(self, text):
        self.orig_text.setPlainText(text)
        # after transcription, call translation
        target_name = self.lang_box.currentText()
        target_code = LANGS.get(target_name, "en")
        # run translation in background thread
        t = threading.Thread(target=do_translate, args=(text, "ko", target_code), daemon=True)
        t.start()
        # re-enable record button
        self.record_button.setEnabled(True)

    def on_translation_ready(self, translated):
        self.trans_text.setPlainText(translated)

    def on_play_clicked(self):
        translated = self.trans_text.toPlainText().strip()
        if not translated:
            self.status_label.setText("No translated text to play.")
            return
        target_name = self.lang_box.currentText()
        target_code = LANGS.get(target_name, "en")
        t = threading.Thread(target=do_tts_play, args=(translated, target_code), daemon=True)
        t.start()

# -----------------
# Run
# -----------------
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
