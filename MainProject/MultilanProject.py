# stt_translator_ui.py
import sys, os, tempfile, threading, requests, time, queue
from gtts import gTTS
import pygame
import pyaudio
import wave
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QTextEdit, QLabel, QCheckBox, QFrame, QGroupBox,
    QProgressBar, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPixmap, QIcon
import speech_recognition as sr

# ----------------- signals
class Signals(QObject):
    transcription_ready = pyqtSignal(str)
    set_status = pyqtSignal(str)
    translation_ready = pyqtSignal(str, str) 
    tts_ready = pyqtSignal(str, str)  
    all_translations_done = pyqtSignal()
signals = Signals()

# ----------------- Custom Toggle Switch Widget
class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    
    def __init__(self, text="", icon="", parent=None):
        super().__init__(parent)
        self.text = text
        self.icon = icon
        self.checked = False
        self.animation = None
        self.setFixedSize(140, 35)
        self.setMinimumSize(140, 35)
        
        # Colors
        self.bg_color_off = QColor(220, 220, 220)
        self.bg_color_on = QColor(76, 175, 80)
        self.thumb_color = QColor(255, 255, 255)
        self.text_color_off = QColor(120, 120, 120)
        self.text_color_on = QColor(255, 255, 255)
        self.icon_color_off = QColor(100, 100, 100)
        self.icon_color_on = QColor(255, 255, 255)
        
        # Animation properties
        self.thumb_position = 3  # Start position (off state)
        self.target_position = 3
        self.background_opacity = 0.3
        self.target_opacity = 0.3
        
        # Toggle button dimensions (fixed on left side)
        self.toggle_width = 55
        self.toggle_height = 24
        self.toggle_x = 3
        self.toggle_y = 5
        
        # Text area positioning (right side with proper spacing)
        self.text_area_x = 65
        
        # Language icons mapping
        self.language_icons = {
            "Japanese": "🇯🇵",
            "Chinese": "🇨🇳", 
            "Vietnamese": "🇻🇳",
            "English": "🇺🇸"
        }
        
    def setChecked(self, checked):
        if self.checked != checked:
            self.checked = checked
            self.target_position = 29 if checked else 3  # Move to right side of longer toggle button
            self.target_opacity = 1.0 if checked else 0.3
            self.start_animation()
            self.toggled.emit(checked)
            
    def isChecked(self):
        return self.checked
        
    def start_animation(self):
        if self.animation:
            self.animation.stop()
            
        # Create animation for thumb position
        self.animation = QPropertyAnimation(self, b"thumb_position")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.setStartValue(self.thumb_position)
        self.animation.setEndValue(self.target_position)
        self.animation.valueChanged.connect(self.update)
        self.animation.finished.connect(self.on_animation_finished)
        
        # Background opacity animation
        self.bg_animation = QPropertyAnimation(self, b"background_opacity")
        self.bg_animation.setDuration(300)
        self.bg_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.bg_animation.setStartValue(self.background_opacity)
        self.bg_animation.setEndValue(self.target_opacity)
        self.bg_animation.valueChanged.connect(self.update)
        
        self.animation.start()
        self.bg_animation.start()
        
    def on_animation_finished(self):
        # Ensure final position is set correctly
        self.thumb_position = self.target_position
        self.background_opacity = self.target_opacity
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw toggle button background (fixed on left side)
        toggle_bg_color = self.bg_color_on if self.checked else self.bg_color_off
        toggle_bg_color.setAlphaF(self.background_opacity)
        painter.setBrush(toggle_bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.toggle_x, self.toggle_y, self.toggle_width, self.toggle_height, 14, 14)
        
        # Draw toggle button border
        toggle_border_color = QColor(200, 200, 200) if not self.checked else QColor(76, 175, 80)
        painter.setPen(toggle_border_color)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.toggle_x, self.toggle_y, self.toggle_width, self.toggle_height, 14, 14)
        
        # Draw thumb with shadow effect (inside smaller toggle button)
        thumb_size = 18
        thumb_rect = QRect(int(self.thumb_position), self.toggle_y + 3, thumb_size, thumb_size)
        
        # Shadow
        shadow_rect = QRect(thumb_rect.x() + 1, thumb_rect.y() + 1, thumb_size, thumb_size)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(shadow_rect)
        
        # Thumb
        painter.setBrush(self.thumb_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(thumb_rect)
        
        # Draw icon and text (fixed on right side with proper spacing)
        if self.text:
            # Get icon for this language
            icon_text = self.language_icons.get(self.text, "")
            
            # Position icon and text side by side on the right, centered vertically with toggle
            icon_x = self.text_area_x
            text_x = self.text_area_x + 25  # Space for icon
            
            # Calculate vertical center to align with toggle button
            toggle_center_y = self.toggle_y + (self.toggle_height // 2)
            
            # Draw icon (proportional to toggle button size)
            if icon_text:
                painter.setPen(self.icon_color_off)
                font = QFont()
                font.setPointSize(16)  # Proportional to toggle button height
                painter.setFont(font)
                painter.drawText(icon_x, toggle_center_y + 6, icon_text)
            
            # Draw text (proportional to toggle button size)
            painter.setPen(self.text_color_off)
            font = QFont()
            font.setPointSize(10)  # Proportional to toggle button height
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(text_x, toggle_center_y + 6, self.text)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self.checked)
            
    def get_thumb_position(self):
        return self.thumb_position
        
    def set_thumb_position(self, value):
        self.thumb_position = value
        self.update()
        
    def get_background_opacity(self):
        return self.background_opacity
        
    def set_background_opacity(self, value):
        self.background_opacity = value
        self.update()

# ----------------- Config
TARGET_LANGS = {
    "Japanese": "ja",
    "Chinese": "zh",
    "Vietnamese": "vi",
    "English": "en"
}

# VAD Settings
VAD_SILENCE_TIMEOUT = 1.5  # Stop recording after 3 seconds of silence
VAD_ENERGY_THRESHOLD = 500  # Energy threshold for voice detection
VAD_FRAME_DURATION = 0.1   # Frame duration in seconds
VAD_CHUNK_SIZE = 1024      # Audio chunk size

# Translation endpoints
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# ----------------- Workers
def calculate_energy(audio_data):
    """Calculate energy of audio frame for VAD"""
    return np.sum(np.frombuffer(audio_data, dtype=np.int16) ** 2) / len(audio_data)

def do_record_with_vad():
    """Record with Voice Activity Detection - stops after 3s of silence"""
    signals.set_status.emit("Recording... (speak now)")
    
    # Audio configuration
    CHUNK = VAD_CHUNK_SIZE
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        frames = []
        last_voice_time = time.time()
        recording = True
        voice_detected = False
        
        while recording:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Calculate energy for VAD
            energy = calculate_energy(data)
            
            # Check if voice is detected
            if energy > VAD_ENERGY_THRESHOLD:
                last_voice_time = time.time()
                if not voice_detected:
                    voice_detected = True
                    signals.set_status.emit("Voice detected... (keep speaking)")
            else:
                # Check if we've been silent too long
                silence_duration = time.time() - last_voice_time
                if voice_detected and silence_duration > 1.5:  # Fixed 3 seconds
                    recording = False
                    signals.set_status.emit("Silence detected, processing...")
                elif voice_detected:
                    # Show countdown
                    remaining = 1.5 - silence_duration
                    if remaining > 0:
                        signals.set_status.emit(f"Silence detected... stopping in {remaining:.1f}s")
        
        stream.stop_stream()
        stream.close()
        
        if len(frames) > 0:
            # Convert frames to audio data
            audio_data = b''.join(frames)
            
            # Create temporary WAV file
            temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            with wave.open(temp_wav.name, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(audio_data)
            
            # Transcribe the audio
            signals.set_status.emit("Transcribing...")
            r = sr.Recognizer()
            try:
                with sr.AudioFile(temp_wav.name) as source:
                    audio = r.record(source)
                text = r.recognize_google(audio, language="ko-KR", show_all=False)
                signals.transcription_ready.emit(text)
                signals.set_status.emit("Transcription done.")
            except Exception as e:
                signals.set_status.emit(f"STT error: {e}")
                signals.transcription_ready.emit("")
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_wav.name)
                except:
                    pass
        else:
            signals.set_status.emit("No audio recorded")
            signals.transcription_ready.emit("")
            
    except Exception as e:
        signals.set_status.emit(f"Recording error: {e}")
        signals.transcription_ready.emit("")
    finally:
        p.terminate()


def do_translate(text, target_code):
    try:
        translated = ""
        # Try Google API (no-key quick endpoint)
        try:
            params = {
                "client": "gtx",
                "sl": "ko",
                "tl": target_code,
                "dt": "t",
                "q": text
            }
            resp = requests.get(GOOGLE_TRANSLATE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0 and len(data[0]) > 0:
                translated = data[0][0][0]
        except Exception:
            # Fallback to MyMemory
            try:
                params = {"q": text, "langpair": f"ko|{target_code}"}
                resp = requests.get(MYMEMORY_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                translated = data.get("responseData", {}).get("translatedText", "")
            except Exception:
                translated = "Translation failed"

        signals.translation_ready.emit(translated, target_code)
    except Exception as e:
        signals.translation_ready.emit(f"Error: {e}", target_code)

def do_tts(text, target_code, audio_file):
    try:
        if text and text != "Translation failed" and not text.startswith("Error:"):
            tts = gTTS(text=text, lang=target_code)
            tts.save(audio_file)
            signals.tts_ready.emit(audio_file, target_code)
        else:
            signals.tts_ready.emit("", target_code)
    except Exception as e:
        print(f"TTS error for {target_code}: {e}")
        signals.tts_ready.emit("", target_code)

def play_all_audio(audio_files):
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        sounds = []
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                sound = pygame.mixer.Sound(audio_file)
                sounds.append((sound, audio_file))
                sound.play()

        if sounds:
            pygame.time.wait(100)
            # wait while any are playing
            while any(sound.get_num_channels() > 0 for (sound, _) in sounds):
                pygame.time.wait(100)

        # cleanup
        for (_, audio_file) in sounds:
            try:
                os.remove(audio_file)
            except:
                pass
    except Exception as e:
        print(f"Audio playback error (simul): {e}")
        for audio_file in audio_files:
            try:
                os.remove(audio_file)
            except:
                pass

def play_single_audio_file(audio_file):
    """Play one file (non-blocking)"""
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        if os.path.exists(audio_file):
            sound = pygame.mixer.Sound(audio_file)
            sound.play()
    except Exception as e:
        print(f"Audio single playback error: {e}")

# ----------------- Main Window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌏 Korean Multi-Language Speech Translator")
        self.setMinimumSize(1000, 700)
        self.load_stylesheet()

        # state trackers
        self.pending_translations = 0
        self.audio_files = []            # list used for simultaneous play
        self.audio_files_map = {}        # code -> path (for Play buttons)
        self.translations = {}           # code -> text
        self.trans_boxes = {}            # language name -> QTextEdit
        self.play_buttons = {}           # language name -> QPushButton

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Controls
        control_section = self.create_control_section()
        main_layout.addWidget(control_section)

        # Content area with splitter
        content_splitter = QSplitter(Qt.Horizontal)

        left_panel = self.create_input_panel()
        content_splitter.addWidget(left_panel)

        right_panel = self.create_output_panel()
        content_splitter.addWidget(right_panel)

        content_splitter.setSizes([400, 600])
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(content_splitter)

        # Status bar
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)

        self.setLayout(main_layout)

        # connect signals
        signals.transcription_ready.connect(self.on_transcription_ready)
        signals.set_status.connect(self.on_status)
        signals.translation_ready.connect(self.on_translation_ready)
        signals.tts_ready.connect(self.on_tts_ready)
        signals.all_translations_done.connect(self.on_all_translations_done)

    def load_stylesheet(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            css_file = os.path.join(script_dir, 'styles.css')
            with open(css_file, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            print("styles.css not found — continuing without it.")
        except Exception as e:
            print(f"Error loading styles.css: {e}")

    def create_header(self):
        header_frame = QFrame()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Korean Multi-Language Speech Translator")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("Speak in Korean, get instant translations with audio playback")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)

        header_frame.setLayout(header_layout)
        return header_frame

    def create_control_section(self):
        control_group = QGroupBox()
        control_group.setTitle("")  
        control_layout = QVBoxLayout()

        # central mic button row
        mic_row = QHBoxLayout()
        mic_row.addStretch()

        self.record_button = QPushButton("🎤")
        self.record_button.setObjectName("micButton")
        self.record_button.setToolTip("Click to start recording Korean speech")
        self.record_button.clicked.connect(self.on_record_clicked)
        mic_row.addWidget(self.record_button)
        
        mic_row.addStretch()
        control_layout.addLayout(mic_row)



        # language toggles row
        toggles_row = QHBoxLayout()
        toggles_row.setSpacing(30)
        toggles_row.setContentsMargins(80, 10, 80, 10)

        self.toggle_switches = {}
        for name in TARGET_LANGS:
            toggle = ToggleSwitch(name)
            toggle.setObjectName(f"toggle_{name}")
            toggle.toggled.connect(lambda checked, n=name: self.on_language_toggled(n, checked))
            self.toggle_switches[name] = toggle
            toggles_row.addWidget(toggle, alignment=Qt.AlignCenter)

        control_layout.addLayout(toggles_row)
        control_group.setLayout(control_layout)
        return control_group

    def create_input_panel(self):
        input_group = QGroupBox("Recognized Korean Speech")
        input_layout = QVBoxLayout()

        self.orig_text = QTextEdit()
        self.orig_text.setPlaceholderText("Press mic and start speaking...")
        self.orig_text.setMaximumHeight(240)
        input_layout.addWidget(self.orig_text)

        self.status_small = QLabel("Ready to record")
        self.status_small.setObjectName("statusSmall")
        input_layout.addWidget(self.status_small)

        input_group.setLayout(input_layout)
        return input_group

    def create_output_panel(self):
        output_group = QGroupBox("Output - Translations")
        output_layout = QGridLayout()
        output_layout.setSpacing(16)
        output_layout.setContentsMargins(10, 10, 10, 10)

        flag_map = {
            "Japanese": "🇯🇵",
            "Chinese": "🇨🇳",
            "Vietnamese": "🇻🇳",
            "English": "🇺🇸"
        }

        # positions 2x2
        positions = [
            (0, 0, "Japanese"),
            (0, 1, "Chinese"),
            (1, 0, "Vietnamese"),
            (1, 1, "English")
        ]

        for row, col, name in positions:
            card = QFrame()
            card.setObjectName(f"card_{name}")
            card.setFrameStyle(QFrame.NoFrame)
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(8)

            lbl = QLabel(f"{flag_map.get(name)}  {name}")
            lbl.setObjectName(f"lbl_{name}")
            lbl.setAlignment(Qt.AlignLeft)
            card_layout.addWidget(lbl)

            box = QTextEdit()
            box.setReadOnly(True)
            box.setPlaceholderText(f"Translation in {name} will appear here...")
            box.setFixedHeight(100)
            self.trans_boxes[name] = box
            card_layout.addWidget(box)

            # play again button
            play_btn = QPushButton("🎧 Play Again")
            play_btn.setObjectName(f"play_{name}")
            play_btn.setEnabled(False)
            # connect to play handler
            play_btn.clicked.connect(lambda checked, n=name: self.on_play_again(n))
            self.play_buttons[name] = play_btn
            card_layout.addWidget(play_btn, alignment=Qt.AlignLeft)

            card.setLayout(card_layout)
            output_layout.addWidget(card, row, col)

        output_group.setLayout(output_layout)
        return output_group

    def create_status_bar(self):
        status_frame = QFrame()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(8, 8, 8, 8)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(16)
        status_layout.addWidget(self.progress_bar)

        status_frame.setLayout(status_layout)
        return status_frame

    # --- signal handlers
    
    def on_language_toggled(self, language_name, checked):
        """Handle language toggle switch changes"""
        # This method can be used for any additional logic when toggles change
        # The main logic is already handled in on_transcription_ready
        pass

    def on_status(self, s):
        self.status_label.setText(s)
        self.status_small.setText(s)
        if any(k in s for k in ("Listening", "Transcribing", "Translating", "Generating speech")):
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setVisible(False)

    def on_record_clicked(self):
        # clear previous UI state for neatness
        self.orig_text.clear()
        for b in self.play_buttons.values():
            b.setEnabled(False)
        # Clear all translation text boxes
        for box in self.trans_boxes.values():
            box.clear()
        self.audio_files_map.clear()
        self.translations.clear()
        self.pending_translations = 0
        
        # Set recording state with red background
        self.record_button.setEnabled(False)
        self.record_button.setText("🎤 Recording...")
        self.record_button.setStyleSheet("""
            QPushButton#micButton {
                background-color: #d13438;
                color: white;
                border-radius: 50px;
                padding: 20px;
                min-width: 100px;
                min-height: 100px;
                font-size: 40px;
                border: 3px solid #d13438;
                font-weight: bold;
            }
        """)
        
        # Use VAD for automatic 3-second silence detection
        threading.Thread(target=do_record_with_vad, daemon=True).start()


    def on_transcription_ready(self, text):
        self.orig_text.setPlainText(text)
        # Reset button to normal state
        self.record_button.setText("🎤")
        self.record_button.setEnabled(True)
        self.record_button.setStyleSheet("")  # Reset to default CSS
        
        if not text:
            return

        # prepare for translations
        selected = []
        for name, code in TARGET_LANGS.items():
            if self.toggle_switches[name].isChecked():
                selected.append((name, code))
                self.pending_translations += 1

        if not selected:
            self.record_button.setEnabled(True)
            return

        # start translation threads
        for name, code in selected:
            threading.Thread(target=do_translate, args=(text, code), daemon=True).start()

        self.record_button.setEnabled(True)

    def on_translation_ready(self, translated_text, target_code):
        # map code -> name, update UI
        for name, code in TARGET_LANGS.items():
            if code == target_code:
                self.trans_boxes[name].setPlainText(translated_text)
                self.translations[code] = translated_text
                break

        self.pending_translations -= 1
        if self.pending_translations == 0:
            # start TTS generation
            self.start_tts_generation()

    def start_tts_generation(self):
        self.pending_translations = len(self.translations)
        self.audio_files = []
        # create TTS threads for each translation
        for code, text in self.translations.items():
            if text and text != "Translation failed" and not text.startswith("Error:"):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{code}.mp3")
                tmp.close()
                self.audio_files.append(tmp.name)
                # store placeholder in map until tts_ready
                self.audio_files_map[code] = ""
                threading.Thread(target=do_tts, args=(text, code, tmp.name), daemon=True).start()
            else:
                self.pending_translations -= 1

        if self.pending_translations == 0:
            signals.all_translations_done.emit()

    def on_tts_ready(self, audio_file, target_code):
        # store file path for this language code
        if audio_file:
            self.audio_files_map[target_code] = audio_file
            # enable corresponding play button
            for name, code in TARGET_LANGS.items():
                if code == target_code:
                    btn = self.play_buttons.get(name)
                    if btn:
                        btn.setEnabled(True)
                    break
        else:
            # tts failed for this language
            self.audio_files_map[target_code] = ""
        self.pending_translations -= 1
        if self.pending_translations == 0:
            signals.all_translations_done.emit()

    def on_all_translations_done(self):
        # if we have audio files for simultaneous playback, start it (optional)
        files_for_simul = [f for f in self.audio_files if os.path.exists(f)]
        if files_for_simul:
            threading.Thread(target=play_all_audio, args=(files_for_simul,), daemon=True).start()

    # Play Again handler (single language)
    def on_play_again(self, language_name):
        code = TARGET_LANGS.get(language_name)
        if not code:
            return
        audio_file = self.audio_files_map.get(code)
        if audio_file and os.path.exists(audio_file):
            threading.Thread(target=play_single_audio_file, args=(audio_file,), daemon=True).start()
        else:
            # If TTS is not available (maybe user toggled late), attempt to generate TTS right now
            text = self.translations.get(code, "")
            if text:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{code}.mp3")
                tmp.close()
                # generate now (blocking TTS in background)
                threading.Thread(target=self._generate_and_play_now, args=(text, code, tmp.name), daemon=True).start()


    def _generate_and_play_now(self, text, code, tmpfile):
        do_tts(text, code, tmpfile)
        if os.path.exists(tmpfile):
            play_single_audio_file(tmpfile)
            try:
                import time
                time.sleep(1)
                os.remove(tmpfile)
            except:
                pass

# ----------------- Run
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
