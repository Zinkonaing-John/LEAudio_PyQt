#!/usr/bin/env python3
"""
Multi-Device Audio Playback GUI
PyQt5 interface for playing audio simultaneously across all available devices.
"""

import sys
import os
import tempfile
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                           QTextEdit, QFrame, QScrollArea, QComboBox, 
                           QFileDialog, QProgressBar, QCheckBox, QSlider,
                           QGroupBox, QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush
import soundfile as sf
import numpy as np
from multi_device_audio import AudioDeviceManager


class AudioPlaybackWorker(QThread):
    """Worker thread for audio playback operations."""
    
    device_status_changed = pyqtSignal(int, str)  # device_index, status
    playback_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, manager, file_path, selected_devices=None):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.selected_devices = selected_devices or []
    
    def run(self):
        """Run the audio playback."""
        try:
            if self.selected_devices:
                # Play on selected devices only
                audio_data, sample_rate = self.manager.load_audio_file(self.file_path)
                
                for device_index in self.selected_devices:
                    if device_index in [d.index for d in self.manager.devices]:
                        self.device_status_changed.emit(device_index, "Starting...")
                        success = self.manager.play_on_device(
                            device_index, audio_data, sample_rate, 
                            self._playback_callback
                        )
                        if not success:
                            self.device_status_changed.emit(device_index, "Failed")
            else:
                # Play on all devices
                self.manager.play_on_all_devices(self.file_path, self._playback_callback)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _playback_callback(self, device_index, status):
        """Callback for device playback status."""
        self.device_status_changed.emit(device_index, status)


class DeviceStatusWidget(QFrame):
    """Widget showing status of a single audio device."""
    
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.status = "Idle"
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the device status UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Device name
        self.name_label = QLabel(self.device.name)
        self.name_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        # Device info
        info_text = f"Index: {self.device.index}\n"
        info_text += f"Channels: {self.device.max_output_channels}\n"
        info_text += f"Sample Rate: {self.device.default_samplerate}Hz"
        if self.device.is_default:
            info_text += "\n(DEFAULT)"
        
        self.info_label = QLabel(info_text)
        self.info_label.setFont(QFont("Arial", 9))
        self.info_label.setStyleSheet("color: #666;")
        layout.addWidget(self.info_label)
        
        # Status indicator
        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Test button
        self.test_button = QPushButton("Test")
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.test_button)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid #ddd;
                border-radius: 8px;
                margin: 2px;
            }
        """)
    
    def update_status(self, status):
        """Update the device status."""
        self.status = status
        
        # Update status label with appropriate color
        if status == "Playing":
            color = "#4CAF50"  # Green
        elif status == "Starting...":
            color = "#FF9800"  # Orange
        elif status == "Failed" or "error" in status.lower():
            color = "#F44336"  # Red
        else:
            color = "#9E9E9E"  # Gray
        
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border: 1px solid {color};
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }}
        """)


class MultiDeviceAudioGUI(QMainWindow):
    """Main GUI for multi-device audio playback."""
    
    def __init__(self):
        super().__init__()
        self.manager = AudioDeviceManager()
        self.device_widgets = {}
        self.playback_worker = None
        self.current_file = None
        
        self.setup_ui()
        self.discover_devices()
        
    def setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Multi-Device Audio Playback")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Multi-Device Audio Playback System")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1976D2; padding: 10px;")
        main_layout.addWidget(title)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Controls
        left_panel = self.create_control_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Device status
        right_panel = self.create_device_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 800])
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
    def create_control_panel(self):
        """Create the control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # File selection group
        file_group = QGroupBox("Audio File")
        file_layout = QVBoxLayout(file_group)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                min-height: 40px;
            }
        """)
        file_layout.addWidget(self.file_label)
        
        self.select_file_button = QPushButton("Select Audio File")
        self.select_file_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.select_file_button.clicked.connect(self.select_audio_file)
        file_layout.addWidget(self.select_file_button)
        
        layout.addWidget(file_group)
        
        # Playback controls group
        playback_group = QGroupBox("Playback Controls")
        playback_layout = QVBoxLayout(playback_group)
        
        # Device selection
        device_selection_layout = QHBoxLayout()
        device_selection_layout.addWidget(QLabel("Play on:"))
        
        self.play_all_checkbox = QCheckBox("All Devices")
        self.play_all_checkbox.setChecked(True)
        self.play_all_checkbox.stateChanged.connect(self.on_device_selection_changed)
        device_selection_layout.addWidget(self.play_all_checkbox)
        
        self.play_selected_checkbox = QCheckBox("Selected Devices")
        self.play_selected_checkbox.stateChanged.connect(self.on_device_selection_changed)
        device_selection_layout.addWidget(self.play_selected_checkbox)
        
        playback_layout.addLayout(device_selection_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.play_button = QPushButton("▶ Play")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.play_button.clicked.connect(self.start_playback)
        self.play_button.setEnabled(False)
        button_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_button.clicked.connect(self.stop_playback)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        playback_layout.addLayout(button_layout)
        
        # Test tone controls
        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("Test Tone:"))
        
        self.test_button = QPushButton("Play Test Tone")
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.test_button.clicked.connect(self.play_test_tone)
        test_layout.addWidget(self.test_button)
        
        playback_layout.addLayout(test_layout)
        
        layout.addWidget(playback_group)
        
        # Device management group
        device_group = QGroupBox("Device Management")
        device_layout = QVBoxLayout(device_group)
        
        self.refresh_button = QPushButton("Refresh Devices")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.refresh_button.clicked.connect(self.discover_devices)
        device_layout.addWidget(self.refresh_button)
        
        self.test_all_button = QPushButton("Test All Devices")
        self.test_all_button.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        self.test_all_button.clicked.connect(self.test_all_devices)
        device_layout.addWidget(self.test_all_button)
        
        layout.addWidget(device_group)
        
        layout.addStretch()
        return panel
    
    def create_device_panel(self):
        """Create the device status panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Panel title
        title = QLabel("Audio Devices")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: #333; padding: 5px;")
        layout.addWidget(title)
        
        # Scroll area for device widgets
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.device_container = QWidget()
        self.device_layout = QGridLayout(self.device_container)
        self.device_layout.setSpacing(10)
        
        scroll_area.setWidget(self.device_container)
        layout.addWidget(scroll_area)
        
        return panel
    
    def discover_devices(self):
        """Discover and display audio devices."""
        self.status_bar.showMessage("Discovering audio devices...")
        
        # Clear existing widgets
        for widget in self.device_widgets.values():
            widget.deleteLater()
        self.device_widgets.clear()
        
        # Discover devices
        devices = self.manager.discover_devices()
        
        if not devices:
            self.status_bar.showMessage("No audio devices found")
            return
        
        # Create device widgets
        for i, device in enumerate(devices):
            widget = DeviceStatusWidget(device)
            widget.test_button.clicked.connect(
                lambda checked, idx=device.index: self.test_single_device(idx)
            )
            
            row, col = i // 2, i % 2
            self.device_layout.addWidget(widget, row, col)
            self.device_widgets[device.index] = widget
        
        self.status_bar.showMessage(f"Found {len(devices)} audio devices")
        
        # Update device selection checkboxes
        self.update_device_selection_ui()
    
    def update_device_selection_ui(self):
        """Update the device selection UI."""
        # This would be used if we implement individual device selection
        pass
    
    def select_audio_file(self):
        """Select an audio file for playback."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;All Files (*)"
        )
        
        if file_path:
            self.current_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.setText(f"Selected: {filename}")
            self.play_button.setEnabled(True)
            self.status_bar.showMessage(f"Selected file: {filename}")
    
    def on_device_selection_changed(self):
        """Handle device selection checkbox changes."""
        if self.play_all_checkbox.isChecked():
            self.play_selected_checkbox.setChecked(False)
        elif self.play_selected_checkbox.isChecked():
            self.play_all_checkbox.setChecked(False)
    
    def start_playback(self):
        """Start audio playback."""
        if not self.current_file:
            self.status_bar.showMessage("No audio file selected")
            return
        
        if not self.manager.devices:
            self.status_bar.showMessage("No audio devices available")
            return
        
        # Determine which devices to use
        selected_devices = []
        if self.play_selected_checkbox.isChecked():
            # Get selected devices (would need to implement device selection UI)
            selected_devices = [d.index for d in self.manager.devices]
        
        # Start playback worker
        self.playback_worker = AudioPlaybackWorker(
            self.manager, self.current_file, selected_devices
        )
        self.playback_worker.device_status_changed.connect(self.update_device_status)
        self.playback_worker.playback_finished.connect(self.on_playback_finished)
        self.playback_worker.error_occurred.connect(self.on_error)
        
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_bar.showMessage("Starting playback...")
        
        self.playback_worker.start()
    
    def stop_playback(self):
        """Stop audio playback."""
        self.manager.stop_all_playback()
        
        if self.playback_worker and self.playback_worker.isRunning():
            self.playback_worker.terminate()
            self.playback_worker.wait()
        
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("Playback stopped")
        
        # Reset all device statuses
        for widget in self.device_widgets.values():
            widget.update_status("Idle")
    
    def update_device_status(self, device_index, status):
        """Update the status of a specific device."""
        if device_index in self.device_widgets:
            self.device_widgets[device_index].update_status(status)
    
    def on_playback_finished(self):
        """Handle playback finished."""
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("Playback completed")
    
    def on_error(self, error_message):
        """Handle errors."""
        self.status_bar.showMessage(f"Error: {error_message}")
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def test_single_device(self, device_index):
        """Test a single device."""
        if device_index in self.device_widgets:
            self.device_widgets[device_index].update_status("Testing...")
        
        # Create test tone
        test_tone, sample_rate = self.manager.create_test_tone(duration=1.0)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, test_tone, sample_rate)
            temp_file_path = tmp_file.name
        
        try:
            # Test the device
            success = self.manager.test_device(device_index)
            if success:
                self.update_device_status(device_index, "Test Passed")
                self.status_bar.showMessage(f"Device {device_index} test passed")
            else:
                self.update_device_status(device_index, "Test Failed")
                self.status_bar.showMessage(f"Device {device_index} test failed")
        except Exception as e:
            self.update_device_status(device_index, f"Error: {e}")
            self.status_bar.showMessage(f"Device {device_index} test error: {e}")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def test_all_devices(self):
        """Test all devices."""
        self.status_bar.showMessage("Testing all devices...")
        
        # Update all device statuses to testing
        for widget in self.device_widgets.values():
            widget.update_status("Testing...")
        
        # Run tests
        test_results = self.manager.test_all_devices()
        
        # Update statuses based on results
        for device_index, success in test_results.items():
            if device_index in self.device_widgets:
                if success:
                    self.device_widgets[device_index].update_status("Test Passed")
                else:
                    self.device_widgets[device_index].update_status("Test Failed")
        
        passed = sum(test_results.values())
        total = len(test_results)
        self.status_bar.showMessage(f"Device tests completed: {passed}/{total} passed")
    
    def play_test_tone(self):
        """Play test tone on all devices."""
        if not self.manager.devices:
            self.status_bar.showMessage("No audio devices available")
            return
        
        # Create test tone
        test_tone, sample_rate = self.manager.create_test_tone(duration=2.0)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, test_tone, sample_rate)
            temp_file_path = tmp_file.name
        
        try:
            # Play on all devices
            results = self.manager.play_on_all_devices(temp_file_path)
            
            if results:
                self.status_bar.showMessage("Playing test tone on all devices...")
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # Set up timer to re-enable controls after test tone
                QTimer.singleShot(3000, self.on_test_tone_finished)
            else:
                self.status_bar.showMessage("Failed to play test tone")
                
        except Exception as e:
            self.status_bar.showMessage(f"Error playing test tone: {e}")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def on_test_tone_finished(self):
        """Handle test tone playback finished."""
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("Test tone completed")
        
        # Reset device statuses
        for widget in self.device_widgets.values():
            widget.update_status("Idle")


def main():
    """Main function to run the GUI."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MultiDeviceAudioGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
