from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer, QPoint, pyqtProperty
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QTextEdit, QFrame, QScrollArea, QComboBox
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QFontMetrics
import sys
import os
import tempfile
import threading
import requests
import time
from gtts import gTTS
import pygame
import pyaudio
import wave
import numpy as np
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf


class Signals(QtCore.QObject):
    """Custom signals for thread-safe UI updates."""
    transcription_ready = QtCore.pyqtSignal(str)
    translation_ready = QtCore.pyqtSignal(str, str)
    tts_ready = QtCore.pyqtSignal(str, str)
    set_status = QtCore.pyqtSignal(str)
    all_translations_done = QtCore.pyqtSignal()


class LanguageButton(QPushButton):
    """Modern pill-shaped language selection button."""
    def __init__(self, text, flag_emoji="", parent=None):
        super().__init__(parent)
        self.text = text
        self.flag_emoji = flag_emoji
        self.is_selected = False
        
        self.setText(f"{self.flag_emoji} {self.text}")
        self.setCheckable(True)
        self.setMinimumHeight(40)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton[selected="true"] {
                background-color: #87CEEB;
                border: 2px solid #4682B4;
                color: white;
            }
            QPushButton[selected="true"]:hover {
                background-color: #7BB3D9;
            }
            QPushButton[selected="false"] {
                background-color: #f0f0f0;
                border: 2px solid #e0e0e0;
                color: #333333;
            }
            QPushButton[selected="false"]:hover {
                background-color: #e8e8e8;
            }
        """)
    
    def setSelected(self, selected):
        """Set selection state and update display"""
        self.is_selected = selected
        self.setChecked(selected)

       
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class MicrophoneButton(QPushButton):
    """Animated microphone button with a pulsing ring effect."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("🎤")
        self.setFixedSize(100, 100)
        self.setCheckable(True)
        self.is_recording = False
        self._ring_radius = 0
        
        
        self.setStyleSheet("""
            QPushButton {
                background-color: #87CEEB; 
                border: none;
                border-radius: 50px;
                font-size: 36px;
                color: white;
            }
            QPushButton:hover {
                background-color: #7BB3D9;
            }
            QPushButton:pressed {
                background-color: #6BA3C9;
            }
            QPushButton:checked {
                background-color: #FF6B6B;
            }
        """)
        
       
        self.ring_animation = QPropertyAnimation(self, b"ring_radius")
        self.ring_animation.setDuration(1500)
        self.ring_animation.setStartValue(0)
        self.ring_animation.setEndValue(40)
        self.ring_animation.setLoopCount(-1)
        self.ring_animation.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(int)
    def ring_radius(self):
        return self._ring_radius

    @ring_radius.setter
    def ring_radius(self, radius):
        self._ring_radius = radius
        self.update()

    def paintEvent(self, event):
        if self.is_recording:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            center = self.rect().center()
            
            
            opacity = 1.0 - (self._ring_radius / 40.0)
            
            ring_color = QColor(255, 107, 107, int(200 * opacity))
            painter.setBrush(ring_color)
            painter.setPen(Qt.NoPen)
            
            
            painter.drawEllipse(center, self._ring_radius, self._ring_radius)

       
        super().paintEvent(event)

    def setRecording(self, recording):
        self.is_recording = recording
        self.setChecked(recording)
        if recording:
            self.ring_animation.start()
        else:
            self.ring_animation.stop()
            self._ring_radius = 0
            self.update()


class DeviceSelector(QComboBox):
    """Device selection dropdown for each language."""
    def __init__(self, language, parent=None):
        super().__init__(parent)
        self.language = language
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                color: #333;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.9);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 5px;
            }
        """)
        
        # Populate with available devices
        self.populate_devices()
    
    def populate_devices(self):
        """Populate the dropdown with available audio devices."""
        self.clear()
        self.addItem("Default Device", "default")
        
        for device_name in discovered_audio_device_ids:
            self.addItem(device_name, device_name)
    
    def get_selected_device(self):
        """Get the currently selected device name."""
        return self.currentData()


class TranslationCard(QFrame):
    """Individual translation output card"""
    
    def __init__(self, language, flag_emoji="", parent=None):
        super().__init__(parent)
        self.language = language
        self.flag_emoji = flag_emoji
        
       
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self.flag_label = QLabel(flag_emoji)
        self.flag_label.setFont(QFont("Arial", 20))
        self.flag_label.setFixedSize(40, 40)
        self.flag_label.setAlignment(Qt.AlignCenter)
        self.flag_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
        """)
        
        self.language_label = QLabel(language)
        self.language_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.language_label.setStyleSheet("""
            QLabel {
                color: #333333;
                background-color: transparent;
                border: none;
            }
        """)
        
        
        header_layout.addWidget(self.flag_label, alignment=Qt.AlignVCenter)
        header_layout.addWidget(self.language_label)
        header_layout.addStretch()
        
        
        self.channel_indicator = QLabel()
        self.channel_indicator.setFixedSize(90, 24)
        self.channel_indicator.setAlignment(Qt.AlignCenter)
        self.channel_indicator.setStyleSheet("""
            QLabel {
                background-color: #2E8B57; /* SeaGreen */
                color: white;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.channel_indicator.setVisible(False)
        header_layout.addWidget(self.channel_indicator)
        
        # Add device selector
        self.device_selector = DeviceSelector(language)
        self.device_selector.setVisible(False)
        header_layout.addWidget(self.device_selector)
        
       
        self.text_area = QTextEdit()
        self.text_area.setMaximumHeight(100)
        self.text_area.setPlaceholderText("the translation will appear here")
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.6);
                border: 2px solid rgba(255, 255, 255, 0.8);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                color: #333;
                font-weight: 500;
            }
            QTextEdit:focus {
                background-color: rgba(255, 255, 255, 0.8);
                border: 2px solid rgba(100, 150, 255, 0.8);
            }
        """)
       
        self.text_area.style().unpolish(self.text_area)
        self.text_area.style().polish(self.text_area)
        
       
        self.play_button = QPushButton("▶️ Play")
        self.play_button.setFixedSize(80, 30)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #87CEEB;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7BB3D9; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.play_button.setEnabled(False)
        
        
        layout.addLayout(header_layout)
        layout.addWidget(self.text_area)
        
        
        # Set the layout
        card_bottom_layout = QHBoxLayout()
        card_bottom_layout.addStretch()
        card_bottom_layout.addWidget(self.play_button)
        layout.addLayout(card_bottom_layout)
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
            }
        """)

    def set_channel_indicator(self, channel_number):
        """Shows the channel indicator with the given number."""
        self.channel_indicator.setText(f"🟢 CHANNEL {channel_number}")
        self.channel_indicator.setVisible(True)

    def clear_channel_indicator(self):
        """Hides the channel indicator."""
        self.channel_indicator.setVisible(False)
    
    def show_device_selector(self):
        """Shows the device selector dropdown."""
        self.device_selector.setVisible(True)
    
    def hide_device_selector(self):
        """Hides the device selector dropdown."""
        self.device_selector.setVisible(False)
    
    def get_selected_device(self):
        """Gets the currently selected device from the dropdown."""
        return self.device_selector.get_selected_device()




TARGET_LANGS = {
    "English": "en",
    "Japanese": "ja",
    "Chinese": "zh-cn", 
    "Vietnamese": "vi"
}

# VAD Settings
VAD_ENERGY_THRESHOLD = 500
VAD_CHUNK_SIZE = 1024

# Translation endpoints
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# ===== MULTI-CHANNEL AUDIO CONFIGURATION =====
# Define the names (or parts of names) of the target audio output devices.
# The application will search for these and map them to device IDs dynamically.
# Use a separate script with `list_audio_devices()` to find the exact names.
TARGET_AUDIO_DEVICE_NAMES = [
    "USB Audio Device", # Example for first slave device
    "Built-in Output"   # Example for second slave device
]

# This will be populated at runtime with the discovered device IDs.
discovered_audio_device_ids = []
# A lock to prevent multiple threads from trying to use pygame.mixer at once

def calculate_energy(audio_data):
    """Calculate energy of audio frame for VAD"""
    return np.sum(np.frombuffer(audio_data, dtype=np.int16) ** 2) / len(audio_data)

def list_audio_devices():
    """Helper function to print all available audio output devices."""
    print("--- Available Audio Output Devices (from sounddevice) ---")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            print(f"Device {i}: {device['name']} (Output channels: {device['max_output_channels']})")
    return devices

def find_all_output_devices():
    """Finds all available audio output devices."""
    global discovered_audio_device_ids
    devices = sd.query_devices()
    
    # Clear previous findings
    discovered_audio_device_ids.clear()
    
    # Find all output devices
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            device_name = device['name']
            discovered_audio_device_ids.append(device_name)
            print(f"Found output device: {device_name}")
    
    return discovered_audio_device_ids

def find_audio_device_ids_by_name():
    """Legacy function - now redirects to find_all_output_devices."""
    return find_all_output_devices()

def do_record_with_vad(signals):
    """Record with Voice Activity Detection - stops after 1.5s of silence"""
    signals.set_status.emit("Listening...")
    
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=VAD_CHUNK_SIZE)
        frames, last_voice_time, voice_detected = [], time.time(), False
        
        while True:
            data = stream.read(VAD_CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)
            energy = calculate_energy(data)
            
            if energy > VAD_ENERGY_THRESHOLD:
                last_voice_time = time.time()
                if not voice_detected:
                    voice_detected = True
                    signals.set_status.emit("Voice detected...")
            elif voice_detected and (time.time() - last_voice_time > 1.5):
                signals.set_status.emit("Silence detected, processing...")
                break
        
        stream.stop_stream()
        stream.close()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
            with wave.open(temp_wav.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(b''.join(frames))
            
            signals.set_status.emit("Transcribing...")
            r = sr.Recognizer()
            with sr.AudioFile(temp_wav.name) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language="ko-KR")
            signals.transcription_ready.emit(text)
        os.unlink(temp_wav.name)
            
    except Exception as e:
        signals.set_status.emit(f"Error: {e}")
        signals.transcription_ready.emit("")
    finally:
        p.terminate()

def do_translate(text, target_code, signals):
    try:
        params = {"client": "gtx", "sl": "ko", "tl": target_code, "dt": "t", "q": text}
        resp = requests.get(GOOGLE_TRANSLATE_URL, params=params, timeout=5)
        translated = resp.json()[0][0][0]
        signals.translation_ready.emit(translated, target_code)
    except Exception:
        try: # Fallback
            params = {"q": text, "langpair": f"ko|{target_code}"}
            resp = requests.get(MYMEMORY_URL, params=params, timeout=5)
            translated = resp.json().get("responseData", {}).get("translatedText", "Translation failed")
            signals.translation_ready.emit(translated, target_code)
        except Exception as e:
            signals.translation_ready.emit(f"Error: {e}", target_code)

def do_tts(text, target_code, audio_file, signals):
    try:
        tts = gTTS(text=text, lang=target_code)
        tts.save(audio_file)
        signals.tts_ready.emit(audio_file, target_code)
    except Exception as e:
        print(f"TTS error for {target_code}: {e}")
        signals.tts_ready.emit("", target_code)

def play_audio_on_device(audio_file, device_name=None):
    """Plays an audio file on a specific device using sounddevice."""
    try:
        data, fs = sf.read(audio_file, dtype='float32')
        sd.play(data, fs, device=device_name)
        sd.wait()  # Wait for the sound to finish playing
    except Exception as e:
        print(f"Error playing audio on device '{device_name}': {e}")

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 750)
        MainWindow.setMinimumSize(380, 650)
        MainWindow.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        MainWindow.setWindowTitle("Modern Translation App")
        
        # --- Backend State ---
        self.signals = Signals()
        self.pending_translations = 0
        self.translations = {}
        self.audio_files_map = {}
        self.channel_assignments = {} # Maps target_code to a device_id

        # Find and map audio devices by name
        find_all_output_devices()

        # Connect signals
        self.signals.transcription_ready.connect(self.on_transcription_ready)
        self.signals.translation_ready.connect(self.on_translation_ready)
        self.signals.tts_ready.connect(self.on_tts_ready)
        
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
      
        self.centralwidget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E3F2FD, stop:1 #BBDEFB);
            }
        """)
        
        main_layout = QVBoxLayout(self.centralwidget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # --- Title ---
        title_label = QLabel("Multi-Language Translator")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #1976D2;
                padding: 10px;
                background-color: transparent;
            }
        """)
        main_layout.addWidget(title_label)
        
        # --- Source Language & Text ---
        source_layout = QHBoxLayout()
        self.source_language_button = LanguageButton("Korean", "🇰🇷")
        self.source_language_button.setSelected(True)
        self.source_language_button.setCheckable(False) # Not a toggle
        source_layout.addWidget(self.source_language_button)

        self.recorded_text_field = QTextEdit()
        self.recorded_text_field.setPlaceholderText("Recorded text will appear here...")
        self.recorded_text_field.setFixedHeight(50)
        self.recorded_text_field.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 10px; padding: 8px; font-size: 14px; color: #333;
            }
        """)
        source_layout.addWidget(self.recorded_text_field, 1) # Add stretch factor
        main_layout.addLayout(source_layout)

        # --- Microphone Button ---
        mic_layout = QHBoxLayout()
        mic_layout.addStretch()
        self.mic_button = MicrophoneButton()
        self.mic_button.clicked.connect(self.toggleRecording)
        mic_layout.addWidget(self.mic_button)
        mic_layout.addStretch()
        main_layout.addLayout(mic_layout)

        # --- Target Language Selection ---
        target_lang_label = QLabel("Translate To:")
        target_lang_label.setFont(QFont("Arial", 14, QFont.Bold))
        target_lang_label.setStyleSheet("background: transparent; color: #333;")
        main_layout.addWidget(target_lang_label)

        self.target_languages_layout = QGridLayout()
        self.target_languages_layout.setSpacing(10)
        main_layout.addLayout(self.target_languages_layout)

        self.to_buttons = []
        languages_to = [("English", "🇺🇸"), ("Japanese", "🇯🇵"), ("Chinese", "🇨🇳"), ("Vietnamese", "🇻🇳")]
        for i, (lang, flag) in enumerate(languages_to):
            btn = LanguageButton(lang, flag)
            btn.clicked.connect(lambda checked, b=btn: self.selectToLanguage(b))
            self.to_buttons.append(btn)
            self.target_languages_layout.addWidget(btn, 0, i)
        self.to_buttons[0].setSelected(True)


        # --- Translation Cards ---
        self.createTranslationArea(main_layout)
        
        # --- Status Label ---
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background: transparent; color: #444; font-style: italic;")
        main_layout.addWidget(self.status_label)
        self.signals.set_status.connect(self.status_label.setText)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def createTranslationArea(self, main_layout):
        # Add a status label for when no languages are selected
        self.no_cards_label = QLabel("Select one or more languages to see translations.")
        self.no_cards_label.setAlignment(Qt.AlignCenter)
        self.no_cards_label.setStyleSheet("background: transparent; color: #666; font-style: italic;")
        """Create the main translation area with cards"""
        self.translation_area_widget = QWidget() # A container for the cards
        self.translation_layout = QGridLayout()
        self.translation_layout.setSpacing(10)
        self.translation_area_widget.setLayout(self.translation_layout)
        main_layout.addWidget(self.translation_area_widget)
        main_layout.addStretch(1) # Pushes cards up
        
        self.translation_cards = {
            "English": TranslationCard("English", "🇺🇸"),
            "Japanese": TranslationCard("Japanese", "🇯🇵"),
            "Chinese": TranslationCard("Chinese", "🇨🇳"), # Name must match TARGET_LANGS
            "Vietnamese": TranslationCard("Vietnamese", "🇻🇳")
        }
        
        # Add all cards to the layout initially and hide them
        for card in self.translation_cards.values():
            self.translation_layout.addWidget(card)
            card.hide()

        # Initially update the visible cards
        self.updateVisibleCards()
        
    def selectToLanguage(self, button):
        """Handle to language selection - multiple can be selected"""
        button.setSelected(not button.is_selected)
        self.updateVisibleCards()

    def updateVisibleCards(self):
        """Clear and repopulate the translation layout based on selected languages."""
        selected_buttons = [btn for btn in self.to_buttons if btn.is_selected]

        if not selected_buttons:
            # Hide all cards and show the placeholder label
            for card in self.translation_cards.values():
                card.hide()
            self.no_cards_label.show()
            return
        
        # Hide the placeholder label
        self.no_cards_label.hide()

        # Iterate through all buttons and show/hide cards accordingly
        visible_card_count = 0
        for button in self.to_buttons:
            card = self.translation_cards.get(button.text) # Use clean name
            if card and button.is_selected:
                card.show()
                card.show_device_selector()  # Show device selector when card is visible
                # Re-add to layout to manage position
                row, col = visible_card_count // 2, visible_card_count % 2
                self.translation_layout.addWidget(card, row, col)
                visible_card_count += 1
            elif card:
                card.hide()
                card.hide_device_selector()  # Hide device selector when card is hidden

    def toggleRecording(self):
        is_recording = self.mic_button.isChecked()
        self.mic_button.setRecording(is_recording)
        if is_recording:
            # Clear previous state
            self.recorded_text_field.clear()
            self.translations.clear()
            self.audio_files_map.clear()
            for card in self.translation_cards.values():
                card.text_area.clear()
                card.clear_channel_indicator()
                card.play_button.setEnabled(False)
                card.hide_device_selector()
            
            # Start recording in a background thread
            threading.Thread(target=do_record_with_vad, args=(self.signals,), daemon=True).start()
        else:
            # This part is now handled by the recording thread stopping
            self.signals.set_status.emit("Recording stopped manually.")

    def on_transcription_ready(self, text):
        """Handle transcribed text from the worker."""
        self.mic_button.setRecording(False) # Stop animation
        self.recorded_text_field.setPlainText(text)
        
        if not text:
            self.signals.set_status.emit("Could not understand audio. Please try again.")
            return

        selected_langs = {name: code for name, code in TARGET_LANGS.items() if self.translation_cards[name].isVisible()}
        self.pending_translations = len(selected_langs)

        if self.pending_translations == 0:
            self.signals.set_status.emit("No target languages selected.")
            return

        self.signals.set_status.emit(f"Translating to {self.pending_translations} language(s)...")
        for name, code in selected_langs.items():
            threading.Thread(target=do_translate, args=(text, code, self.signals), daemon=True).start()

    def on_translation_ready(self, translated_text, target_code):
        """Handle translated text for a specific language."""
        self.translations[target_code] = translated_text
        
        # Find the card and update it
        for name, code in TARGET_LANGS.items():
            if code == target_code:
                card = self.translation_cards.get(name)
                if card:
                    card.text_area.setPlainText(translated_text)
                    # Generate TTS for this translation
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{code}.mp3")
                    tmp.close()
                    threading.Thread(target=do_tts, args=(translated_text, code, tmp.name, self.signals), daemon=True).start()
                break

    def on_tts_ready(self, audio_file, target_code):
        """Handle generated TTS file."""
        if not audio_file:
            return

        self.audio_files_map[target_code] = audio_file

        # --- Get device assignment from UI ---
        # The device will be determined when the user selects it from the dropdown

        for name, code in TARGET_LANGS.items():
            if code == target_code:
                card = self.translation_cards.get(name)
                if card:
                    card.play_button.setEnabled(True)
                    # Disconnect previous signals to prevent multiple plays
                    try:
                        card.play_button.clicked.disconnect()
                    except TypeError: # No signals connected
                        pass
                    # Show device selector and update channel indicator
                    card.show_device_selector()
                    selected_device = card.get_selected_device()
                    if selected_device and selected_device != "default":
                        try:
                            channel_num = discovered_audio_device_ids.index(selected_device) + 1
                            card.set_channel_indicator(channel_num)
                        except ValueError:
                            # Device not found in list, use default
                            card.clear_channel_indicator()
                    card.play_button.clicked.connect(lambda _, tc=target_code: self.play_translation(tc))
                    
                    # --- AUTOPLAY ---
                    self.play_translation(target_code)
                break

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Modern Translation App"))


    def play_translation(self, target_code):
        """Plays the audio for a given language on its selected device."""
        audio_file = self.audio_files_map.get(target_code)
        
        # Get the selected device from the UI
        device_name = None
        for name, code in TARGET_LANGS.items():
            if code == target_code:
                card = self.translation_cards.get(name)
                if card:
                    device_name = card.get_selected_device()
                    break

        if audio_file and os.path.exists(audio_file):
            if device_name == "default":
                device_name = None  # Use default system device
            self.status_label.setText(f"Playing {target_code} on device: {device_name or 'Default'}...")
            # Run playback in a thread to not freeze the UI
            threading.Thread(target=play_audio_on_device, args=(audio_file, device_name), daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())