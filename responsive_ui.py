import sys
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QSizePolicy, QFrame,
    QScrollArea, QGridLayout, QSpacerItem
)
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush

class Signals(QObject):
    """Custom signals for thread-safe UI updates"""
    transcription_ready = pyqtSignal(str)
    translation_ready = pyqtSignal(str, str)
    set_status = pyqtSignal(str)
    set_button_enabled = pyqtSignal(bool)

class ResponsiveMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multilingual Speech Translator")
        self.setMinimumSize(400, 600)
        self.resize(1000, 700)
        
        # Initialize signals
        self.signals = Signals()
        self.target_languages = ['en', 'ja', 'zh-cn']
        self.selected_targets = ['en']  # Default to English
        
        # Initialize UI
        self.init_ui()
        self.connect_signals()
        
        # Set up responsive behavior
        self.setup_responsive_behavior()

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
        
        # To section
        self.create_to_section(parent_layout)
        
        # Additional translation outputs
        self.create_additional_outputs(parent_layout)
        
        # Replay audio button
        self.create_replay_button(parent_layout)

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
        self.english_card = self.create_translation_card("English", "🇺🇸", "Hello, how are you?")
        cards_layout.addWidget(self.english_card)
        
        # Add stretch for responsive spacing
        cards_layout.addStretch()
        
        # Japanese card
        self.japanese_card = self.create_translation_card("Japanese", "🇯🇵", "こんにちは、お元気ですか？")
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
        """Create the 'To' language selection section"""
        to_layout = QHBoxLayout()
        
        # To label
        to_label = QLabel("To:")
        to_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        to_label.setStyleSheet("color: #424242;")
        
        # Language selection pills
        self.create_language_pills(to_layout)
        
        to_layout.addWidget(to_label)
        to_layout.addLayout(self.create_language_pills(to_layout))
        to_layout.addStretch()
        
        parent_layout.addLayout(to_layout)

    def create_language_pills(self, parent_layout):
        """Create language selection pill buttons"""
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)
        
        languages = [
            ("English", "🇺🇸", "#4CAF50"),
            ("Japanese", "🇯🇵", "#FF5722"),
            ("Chinese", "🇨🇳", "#F44336")
        ]
        
        self.language_pills = []
        for lang, flag, color in languages:
            pill = QPushButton(f"{flag} {lang}")
            pill.setFont(QFont('Arial', 10))
            pill.setCheckable(True)
            pill.setStyleSheet(f"""
                QPushButton {{
                    background-color: #f5f5f5;
                    border-radius: 20px;
                    padding: 8px 15px;
                    color: #424242;
                    border: 2px solid transparent;
                }}
                QPushButton:checked {{
                    background-color: {color};
                    color: white;
                    border: 2px solid {color};
                }}
                QPushButton:hover {{
                    background-color: #e0e0e0;
                }}
            """)
            
            # Set English as default selected
            if lang == "English":
                pill.setChecked(True)
            
            pill.clicked.connect(lambda checked, lang=lang: self.toggle_language(lang, checked))
            pills_layout.addWidget(pill)
            self.language_pills.append(pill)
        
        return pills_layout

    def create_additional_outputs(self, parent_layout):
        """Create additional translation output cards"""
        additional_layout = QHBoxLayout()
        additional_layout.setSpacing(15)
        
        # Burmese card
        self.burmese_card = self.create_translation_card("Burmese", "🇲🇲", "မင်္ဂလာပါ၊ ဘယ်လိုနေလဲ?")
        additional_layout.addWidget(self.burmese_card)
        
        additional_layout.addStretch()
        
        # Vietnamese card
        self.vietnamese_card = self.create_translation_card("Vietnamese", "🇻🇳", "Xin chào, bạn khỏe không?")
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

    def setup_responsive_behavior(self):
        """Set up responsive behavior for different screen sizes"""
        # Timer for checking window size changes
        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self.handle_resize)
        self.resize_timer.setSingleShot(True)
        
        # Connect resize event
        self.resizeEvent = self.on_resize

    def on_resize(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        self.resize_timer.start(100)  # Debounce resize events

    def handle_resize(self):
        """Handle responsive layout changes"""
        width = self.width()
        
        # Adjust layout based on window width
        if width < 600:  # Mobile layout
            self.apply_mobile_layout()
        elif width < 900:  # Tablet layout
            self.apply_tablet_layout()
        else:  # Desktop layout
            self.apply_desktop_layout()

    def apply_mobile_layout(self):
        """Apply mobile-specific layout"""
        # Stack cards vertically
        for card in [self.english_card, self.japanese_card, self.burmese_card, self.vietnamese_card]:
            card.setFixedSize(300, 100)
        
        # Adjust language pills
        for pill in self.language_pills:
            pill.setFont(QFont('Arial', 9))

    def apply_tablet_layout(self):
        """Apply tablet-specific layout"""
        # Medium-sized cards
        for card in [self.english_card, self.japanese_card, self.burmese_card, self.vietnamese_card]:
            card.setFixedSize(180, 110)

    def apply_desktop_layout(self):
        """Apply desktop-specific layout"""
        # Full-sized cards
        for card in [self.english_card, self.japanese_card, self.burmese_card, self.vietnamese_card]:
            card.setFixedSize(200, 120)

    def toggle_language(self, language, checked):
        """Toggle language selection"""
        if checked:
            if language not in self.selected_targets:
                self.selected_targets.append(language)
        else:
            if language in self.selected_targets:
                self.selected_targets.remove(language)
        
        print(f"Selected languages: {self.selected_targets}")

    def start_recording(self):
        """Start recording process"""
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                border-radius: 50px;
                border: none;
                color: white;
            }
        """)
        self.mic_button.setText("🔴")
        
        # Simulate recording process
        QTimer.singleShot(3000, self.stop_recording)

    def stop_recording(self):
        """Stop recording process"""
        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                border-radius: 50px;
                border: none;
                color: white;
            }
        """)
        self.mic_button.setText("🎤")

    def replay_audio(self):
        """Replay audio functionality"""
        print("Replaying audio...")

    def connect_signals(self):
        """Connect custom signals"""
        # Connect signals for future functionality
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ResponsiveMainWindow()
    window.show()
    sys.exit(app.exec())
