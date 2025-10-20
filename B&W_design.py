import sys
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QSizePolicy
)
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QSize
from PyQt5.QtGui import QFont, QIcon


class Signals(QObject):
    """Defines custom signals available from a worker thread."""
    transcription_ready = pyqtSignal(str) 
    translation_ready = pyqtSignal(str, str) 
    set_status = pyqtSignal(str) 
    set_button_enabled = pyqtSignal(bool) 


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Korean → Multilang Speech Translator (MCP)")
      
        self.setMinimumSize(400, 700)
        self.setStyleSheet(
            "QWidget { background-color: #f0f0f5; }"
            "QLabel { color: #333; }"
            "QPushButton { border-radius: 20px; padding: 10px; }"
        )
        self.signals = Signals()
        self.target_lang_code = 'en' # Default language
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- Top Bar (From/To) ---
        top_bar_layout = QHBoxLayout()
        # From Label
        from_label = QLabel("From: Korean")
        from_label.setFont(QFont('Arial', 12, QFont.Bold))
        # Toggle Switch Placeholder (using a text label for simplicity)
        toggle_placeholder = QLabel("🔄")
        toggle_placeholder.setFont(QFont('Arial', 18))

        # Language Selection Dropdown
        self.lang_box = QComboBox()
        self.lang_box.setFont(QFont('Arial', 12))
        self.lang_box.addItem("English")
        self.lang_box.addItem("Japanese")
        self.lang_box.addItem("Chinese")
        self.lang_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lang_box.currentIndexChanged.connect(self.update_language)
        
        top_bar_layout.addWidget(from_label)
        top_bar_layout.addStretch(1)
        top_bar_layout.addWidget(self.lang_box)

        # --- Recognized Korean Text Area ---
        self.orig_text = QTextEdit("Hello, how are you?") # Placeholder text
        self.orig_text.setReadOnly(True)
        self.orig_text.setFont(QFont('Arial', 16))
        self.orig_text.setStyleSheet(
            "QTextEdit { background-color: white; border: 1px solid #ddd; border-radius: 15px; padding: 15px; }"
        )
        self.orig_text.setFixedHeight(100)

        # --- Microphone/Record Button (Visual centerpiece) ---
        self.record_button = QPushButton()
        self.record_button.setIcon(QIcon('mic.png')) # Placeholder for a mic icon file
        self.record_button.setIconSize(QSize(60, 60))
        self.record_button.setFixedSize(100, 100)
        self.record_button.setStyleSheet(
            "QPushButton { background-color: white; border: 1px solid #333; border-radius: 50px; }"
            "QPushButton:pressed { background-color: #eee; }"
        )
        self.record_button.clicked.connect(self.start_stt_thread)
        
        mic_layout = QHBoxLayout()
        mic_layout.addStretch(1)
        mic_layout.addWidget(self.record_button)
        mic_layout.addStretch(1)

        # --- Translated Text Area ---
        self.trans_text = QTextEdit("Translation will appear here...")
        self.trans_text.setReadOnly(True)
        self.trans_text.setFont(QFont('Arial', 16))
        self.trans_text.setStyleSheet(
            "QTextEdit { background-color: white; border: 1px solid #ddd; border-radius: 15px; padding: 15px; color: #007aff; }"
        )
        self.trans_text.setFixedHeight(100)

        # --- Play Audio Button ---
        self.play_button = QPushButton("▶️ Replay Audio")
        self.play_button.setFont(QFont('Arial', 14))
        self.play_button.setStyleSheet(
            "QPushButton { background-color: #e0f7fa; border: none; border-radius: 15px; padding: 10px; color: #007aff; }"
        )
        self.play_button.clicked.connect(self.start_tts_thread)
        self.play_button.setEnabled(False) # Disabled until translation is ready

        # --- Status Label ---
        self.status_label = QLabel("Ready to record.")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont('Arial', 12)
        status_font.setItalic(True)
        self.status_label.setFont(status_font)

        # --- Add widgets to main layout ---
        main_layout.addLayout(top_bar_layout)
        main_layout.addWidget(QLabel("Korean Text:"))
        main_layout.addWidget(self.orig_text)
        main_layout.addLayout(mic_layout)
        main_layout.addWidget(QLabel("Translation:"))
        main_layout.addWidget(self.trans_text)
        main_layout.addWidget(self.play_button)
        main_layout.addWidget(self.status_label)
        main_layout.addStretch(1) # Pushes everything up

    def connect_signals(self):
        """Connects custom signals to their respective slots (UI update methods)."""
        self.signals.transcription_ready.connect(self.handle_transcription)
        self.signals.translation_ready.connect(self.handle_translation)
        self.signals.set_status.connect(self.status_label.setText)
        self.signals.set_button_enabled.connect(self.record_button.setEnabled)

    def update_language(self):
        """Updates the internal target language code based on the QComboBox selection."""
        # In a real app, you'd map "English" to "en", "Japanese" to "ja", etc.
        selected_lang = self.lang_box.currentText()
        if selected_lang == "English":
            self.target_lang_code = 'en'
        elif selected_lang == "Japanese":
            self.target_lang_code = 'ja'
        elif selected_lang == "Chinese":
            self.target_lang_code = 'zh-cn'
        self.status_label.setText(f"Target language set to: {selected_lang}")

    # --- 3. Threading Control Methods ---
    def start_stt_thread(self):
        """Starts the Speech-to-Text (Recording) process in a background thread."""
        self.record_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.orig_text.setPlainText("")
        self.trans_text.setPlainText("...Listening and Transcribing...")
        self.signals.set_status.emit("Recording...")

        stt_thread = threading.Thread(target=self.run_stt, daemon=True)
        stt_thread.start()

    def start_translation_thread(self, text):
        """Starts the Translation process in a background thread."""
        self.signals.set_status.emit("Translating...")
        
        trans_thread = threading.Thread(
            target=self.run_translation, 
            args=(text, self.target_lang_code), 
            daemon=True
        )
        trans_thread.start()

    def start_tts_thread(self):
        """Starts the Text-to-Speech (Playback) process in a background thread."""
        translated_text = self.trans_text.toPlainText().strip()
        if not translated_text or translated_text == "Translation will appear here...":
            self.signals.set_status.emit("Nothing to play.")
            return

        self.play_button.setEnabled(False)
        self.signals.set_status.emit("Playing audio...")

        tts_thread = threading.Thread(
            target=self.run_tts, 
            args=(translated_text, self.target_lang_code), 
            daemon=True
        )
        tts_thread.start()

    # --- 4. Worker Thread Functions (PLACEHOLDERS) ---
    def run_stt(self):
        """
        [PLACEHOLDER]
        1. Capture microphone audio.
        2. Use speech_recognition to get text (Google Web Speech).
        3. Emit the result.
        4. Re-enable button.
        """
        # --- MOCK LOGIC START ---
        import time
        time.sleep(3) # Simulate recording/processing time
        recognized_text = "안녕하세요, 잘 지내세요?" # Mock result
        # --- MOCK LOGIC END ---

        self.signals.transcription_ready.emit(recognized_text)
        self.signals.set_button_enabled.emit(True)

    def run_translation(self, text, target_lang):
        """
        [PLACEHOLDER]
        1. Use Google Translate / MyMemory API to translate 'text'.
        2. Emit the result.
        """
        # --- MOCK LOGIC START ---
        import time
        time.sleep(2) # Simulate API call time
        if target_lang == 'en':
            translated_text = "Hello, how are you doing?"
        elif target_lang == 'ja':
            translated_text = "こんにちは、お元気ですか？"
        else:
            translated_text = "你好，你怎么样？"
        # --- MOCK LOGIC END ---

        self.signals.translation_ready.emit(translated_text, target_lang)

    def run_tts(self, text, lang_code):
        """
        [PLACEHOLDER]
        1. Use gTTS to create an audio file from 'text'.
        2. Use pygame to play the audio file.
        3. Update status once finished.
        """
        # --- MOCK LOGIC START ---
        import time
        time.sleep(2) # Simulate TTS generation/playback time
        # --- MOCK LOGIC END ---
        
        self.signals.set_status.emit("Playback finished. Ready to record.")
        self.play_button.setEnabled(True)

    # --- 5. Signal Slot Handlers (UI Update) ---
    def handle_transcription(self, text):
        """Updates the Korean text area and starts translation."""
        self.orig_text.setPlainText(text)
        self.signals.set_status.emit("Transcription complete. Starting translation...")
        self.start_translation_thread(text)

    def handle_translation(self, translated_text, lang_code):
        """Updates the translated text area and enables playback."""
        self.trans_text.setPlainText(translated_text)
        self.play_button.setEnabled(True)
        self.signals.set_status.emit(f"Translation to {lang_code.upper()} complete. Ready to play.")


# --- 6. Application Bootstrap ---
if __name__ == '__main__':
    # Add a fallback for the missing mic.png icon in a real environment
    # import os
    # if not os.path.exists('mic.png'):
    #     print("Warning: 'mic.png' not found. Microphone icon will be missing.")
        
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())