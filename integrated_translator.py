import sys
import os
import tempfile
import threading
import requests
import time
import queue
from gtts import gTTS
import pygame
import pyaudio
import wave
import numpy as np
import speech_recognition as sr

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QSizePolicy, QFrame,
    QScrollArea, QGridLayout, QSpacerItem, QProgressBar, QCheckBox
)
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush

class Signals(QObject):
    """Custom signals for thread-safe UI updates"""
    transcription_ready = pyqtSignal(str)
    translation_ready = pyqtSignal(str, str)
    set_status = pyqtSignal(str)
    set_button_enabled = pyqtSignal(bool)
    tts_ready = pyqtSignal(str, str)
    all_translations_done = pyqtSignal()

class ToggleSwitch(QWidget):
    """Custom toggle switch widget"""
    toggled = pyqtSignal(bool)
    
    def __init__(self, text="", icon="", parent=None):
        super().__init__(parent)
        self.text = text
        self.icon = icon
        self.checked = False
        self.animation = None
        self.setFixedSize(140, 35)
        
        # Colors
        self.bg_color_off = QColor(220, 220, 220)
        self.bg_color_on = QColor(76, 175, 80)
        self.thumb_color = QColor(255, 255, 255)
        
        # Animation properties
        self.thumb_position = 3
        self.target_position = 3
        self.background_opacity = 0.3
        self.target_opacity = 0.3
        
        # Language icons mapping
        self.language_icons = {
            "Japanese": "🇯🇵",
            "Chinese": "🇨🇳", 
            "Vietnamese": "🇻🇳",
            "English": "🇺🇸",
            "Korean": "🇰🇷"
        }
        
    def setChecked(self, checked):
        if self.checked != checked:
            self.checked = checked
            self.target_position = 29 if checked else 3
            self.target_opacity = 1.0 if checked else 0.3
            self.start_animation()
            self.toggled.emit(checked)
            
    def isChecked(self):
        return self.checked
        
    def start_animation(self):
        if self.animation:
            self.animation.stop()
            
        self.animation = QPropertyAnimation(self, b"thumb_position")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self.animation.setStartValue(self.thumb_position)
        self.animation.setEndValue(self.target_position)
        self.animation.valueChanged.connect(self.update)
        self.animation.finished.connect(self.on_animation_finished)
        
        self.bg_animation = QPropertyAnimation(self, b"background_opacity")
        self.bg_animation.setDuration(300)
        self.bg_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.bg_animation.setStartValue(self.background_opacity)
        self.bg_animation.setEndValue(self.target_opacity)
        self.bg_animation.valueChanged.connect(self.update)
        
        self.animation.start()
        self.bg_animation.start()
        
    def on_animation_finished(self):
        self.thumb_position = self.target_position
        self.background_opacity = self.target_opacity
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw toggle button background
        toggle_bg_color = self.bg_color_on if self.checked else self.bg_color_off
        toggle_bg_color.setAlphaF(self.background_opacity)
        painter.setBrush(toggle_bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(3, 5, 55, 24, 14, 14)
        
        # Draw thumb
        thumb_size = 18
        thumb_rect = QRect(int(self.thumb_position), 8, thumb_size, thumb_size)
        
        painter.setBrush(self.thumb_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(thumb_rect)
        
        # Draw text and icon
        if self.text:
            icon_text = self.language_icons.get(self.text, "")
            painter.setPen(QColor(100, 100, 100))
            painter.setFont(QFont('Arial', 10))
            painter.drawText(65, 20, f"{icon_text} {self.text}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.checked)

class IntegratedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multilingual Speech Translator")
        self.setMinimumSize(400, 600)
        self.resize(1000, 700)
        
        # Initialize signals
        self.signals = Signals()
        self.target_languages = ['en', 'ja', 'zh-cn', 'vi']
        self.selected_targets = ['en']  # Default to English
        
        # Initialize audio components
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.audio_frames = []
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize pygame for audio playback
        pygame.mixer.init()
        
        # Initialize UI
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initialize the main UI components"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with gradient background
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Apply gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
            }
        """)
        
        # Create the main content container
        self.create_main_container(main_layout)

    def create_main_container(self, parent_layout):
        """Create the main content container with responsive design"""
        # Main container frame
        container_frame = QFrame()
        container_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 20px;
                border: none;
            }
        """)
        
        container_layout = QVBoxLayout(container_frame)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(25)
        
        # Create responsive layout
        self.create_responsive_layout(container_layout)
        
        parent_layout.addWidget(container_frame)

    def create_responsive_layout(self, parent_layout):
        """Create responsive layout that adapts to screen size"""
        # From section
        self.create_from_section(parent_layout)
        
        # Translation cards section
        self.create_translation_cards_section(parent_layout)
        
        # Microphone section
        self.create_microphone_section(parent_layout)
        
        # To section with toggle switches
        self.create_to_section(parent_layout)
        
        # Additional translation outputs
        self.create_additional_outputs(parent_layout)
        
        # Replay audio button
        self.create_replay_button(parent_layout)
        
        # Status section
        self.create_status_section(parent_layout)

    def create_from_section(self, parent_layout):
        """Create the 'From' language selection section"""
        from_layout = QHBoxLayout()
        
        # From label
        from_label = QLabel("From:")
        from_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        from_label.setStyleSheet("color: #424242;")
        
        # Source language display
        self.source_lang_label = QLabel("Korean 🇰🇷")
        self.source_lang_label.setFont(QFont('Arial', 12))
        self.source_lang_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border-radius: 15px;
                padding: 8px 15px;
                color: #424242;
            }
        """)
        
        from_layout.addWidget(from_label)
        from_layout.addWidget(self.source_lang_label)
        from_layout.addStretch()
        
        parent_layout.addLayout(from_layout)

    def create_translation_cards_section(self, parent_layout):
        """Create the translation output cards"""
        # Create a horizontal layout for cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        # English card
        self.english_card = self.create_translation_card("English", "🇺🇸", "Translation will appear here...")
        cards_layout.addWidget(self.english_card)
        
        # Add stretch for responsive spacing
        cards_layout.addStretch()
        
        # Japanese card
        self.japanese_card = self.create_translation_card("Japanese", "🇯🇵", "Translation will appear here...")
        cards_layout.addWidget(self.japanese_card)
        
        parent_layout.addLayout(cards_layout)

    def create_translation_card(self, language, flag, text):
        """Create a translation output card"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 15px;
                border: 1px solid #e0e0e0;
                padding: 15px;
            }
        """)
        card.setFixedSize(200, 120)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(8)
        
        # Language header
        header_layout = QHBoxLayout()
        flag_label = QLabel(flag)
        flag_label.setFont(QFont('Arial', 16))
        
        lang_label = QLabel(language)
        lang_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        lang_label.setStyleSheet("color: #424242;")
        
        header_layout.addWidget(flag_label)
        header_layout.addWidget(lang_label)
        header_layout.addStretch()
        
        # Text content
        text_label = QLabel(text)
        text_label.setFont(QFont('Arial', 11))
        text_label.setStyleSheet("color: #666;")
        text_label.setWordWrap(True)
        text_label.setObjectName(f"{language.lower()}_text")
        
        card_layout.addLayout(header_layout)
        card_layout.addWidget(text_label)
        
        return card

    def create_microphone_section(self, parent_layout):
        """Create the central microphone button section"""
        mic_layout = QHBoxLayout()
        mic_layout.addStretch()
        
        # Microphone button
        self.mic_button = QPushButton()
        self.mic_button.setFixedSize(100, 100)
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                border-radius: 50px;
                border: none;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        
        # Set microphone icon (using Unicode for now)
        self.mic_button.setText("🎤")
        self.mic_button.setFont(QFont('Arial', 30))
        
        self.mic_button.clicked.connect(self.start_recording)
        
        mic_layout.addWidget(self.mic_button)
        mic_layout.addStretch()
        
        parent_layout.addLayout(mic_layout)

    def create_to_section(self, parent_layout):
        """Create the 'To' language selection section with toggle switches"""
        to_layout = QHBoxLayout()
        
        # To label
        to_label = QLabel("To:")
        to_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        to_label.setStyleSheet("color: #424242;")
        
        to_layout.addWidget(to_label)
        
        # Create toggle switches for each language
        languages = [
            ("English", "en"),
            ("Japanese", "ja"),
            ("Chinese", "zh-cn"),
            ("Vietnamese", "vi")
        ]
        
        self.toggle_switches = {}
        for lang_name, lang_code in languages:
            toggle = ToggleSwitch(text=lang_name)
            toggle.toggled.connect(lambda checked, code=lang_code: self.toggle_language(code, checked))
            
            # Set English as default selected
            if lang_code == 'en':
                toggle.setChecked(True)
            
            to_layout.addWidget(toggle)
            self.toggle_switches[lang_code] = toggle
        
        to_layout.addStretch()
        parent_layout.addLayout(to_layout)

    def create_additional_outputs(self, parent_layout):
        """Create additional translation output cards"""
        additional_layout = QHBoxLayout()
        additional_layout.setSpacing(15)
        
        # Chinese card
        self.chinese_card = self.create_translation_card("Chinese", "🇨🇳", "Translation will appear here...")
        additional_layout.addWidget(self.chinese_card)
        
        additional_layout.addStretch()
        
        # Vietnamese card
        self.vietnamese_card = self.create_translation_card("Vietnamese", "🇻🇳", "Translation will appear here...")
        additional_layout.addWidget(self.vietnamese_card)
        
        parent_layout.addLayout(additional_layout)

    def create_replay_button(self, parent_layout):
        """Create the replay audio button"""
        replay_layout = QHBoxLayout()
        replay_layout.addStretch()
        
        self.replay_button = QPushButton("🔊 Replay Audio")
        self.replay_button.setFont(QFont('Arial', 12))
        self.replay_button.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                border-radius: 15px;
                padding: 10px 20px;
                color: #1976D2;
                border: none;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
            QPushButton:pressed {
                background-color: #90caf9;
            }
        """)
        self.replay_button.clicked.connect(self.replay_audio)
        
        replay_layout.addWidget(self.replay_button)
        replay_layout.addStretch()
        
        parent_layout.addLayout(replay_layout)

    def create_status_section(self, parent_layout):
        """Create status section"""
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready to record")
        self.status_label.setFont(QFont('Arial', 12))
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_layout.addWidget(self.status_label)
        parent_layout.addLayout(status_layout)

    def toggle_language(self, language_code, checked):
        """Toggle language selection"""
        if checked:
            if language_code not in self.selected_targets:
                self.selected_targets.append(language_code)
        else:
            if language_code in self.selected_targets:
                self.selected_targets.remove(language_code)
        
        print(f"Selected languages: {self.selected_targets}")

    def start_recording(self):
        """Start recording process"""
        if self.is_recording:
            self.stop_recording()
            return
            
        self.is_recording = True
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                border-radius: 50px;
                border: none;
                color: white;
            }
        """)
        self.mic_button.setText("🔴")
        self.status_label.setText("Recording... Speak now!")
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self.record_audio, daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        """Stop recording process"""
        self.is_recording = False
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                border-radius: 50px;
                border: none;
                color: white;
            }
        """)
        self.mic_button.setText("🎤")
        self.status_label.setText("Processing...")

    def record_audio(self):
        """Record audio using speech recognition"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                self.status_label.setText("Listening...")
                
                # Record for up to 5 seconds or until silence
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                self.status_label.setText("Processing speech...")
                
                # Recognize speech
                try:
                    text = self.recognizer.recognize_google(audio, language='ko-KR')  # Korean
                    self.signals.transcription_ready.emit(text)
                except sr.UnknownValueError:
                    self.signals.set_status.emit("Could not understand audio")
                except sr.RequestError as e:
                    self.signals.set_status.emit(f"Error: {e}")
                    
        except Exception as e:
            self.signals.set_status.emit(f"Recording error: {e}")
        finally:
            self.stop_recording()

    def translate_text(self, text):
        """Translate text to selected languages"""
        for lang_code in self.selected_targets:
            threading.Thread(
                target=self.translate_to_language,
                args=(text, lang_code),
                daemon=True
            ).start()

    def translate_to_language(self, text, target_lang):
        """Translate text to a specific language"""
        try:
            # Using MyMemory API for translation
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text,
                'langpair': f'ko|{target_lang}'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['responseStatus'] == 200:
                translated_text = data['responseData']['translatedText']
                self.signals.translation_ready.emit(translated_text, target_lang)
            else:
                self.signals.set_status.emit(f"Translation error for {target_lang}")
                
        except Exception as e:
            self.signals.set_status.emit(f"Translation error: {e}")

    def replay_audio(self):
        """Replay audio functionality"""
        self.status_label.setText("Playing audio...")
        # This would play the last translated text
        # For now, just show a message
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready to record"))

    def connect_signals(self):
        """Connect custom signals"""
        self.signals.transcription_ready.connect(self.handle_transcription)
        self.signals.translation_ready.connect(self.handle_translation)
        self.signals.set_status.connect(self.status_label.setText)
        self.signals.set_button_enabled.connect(self.mic_button.setEnabled)

    def handle_transcription(self, text):
        """Handle transcribed text"""
        # Update source text display
        self.source_lang_label.setText(f"Korean 🇰🇷: {text}")
        
        # Start translation
        self.translate_text(text)
        self.status_label.setText("Translating...")

    def handle_translation(self, translated_text, lang_code):
        """Handle translated text"""
        # Update the appropriate card based on language code
        lang_mapping = {
            'en': 'english',
            'ja': 'japanese', 
            'zh-cn': 'chinese',
            'vi': 'vietnamese'
        }
        
        if lang_code in lang_mapping:
            card_name = lang_mapping[lang_code]
            # Find the text label in the corresponding card
            text_widget = self.findChild(QLabel, f"{card_name}_text")
            if text_widget:
                text_widget.setText(translated_text)
        
        self.status_label.setText("Translation complete!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = IntegratedMainWindow()
    window.show()
    sys.exit(app.exec())
