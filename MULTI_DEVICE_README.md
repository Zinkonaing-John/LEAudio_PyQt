# Multi-Device Audio Playback System

A Python project that allows you to play audio simultaneously across all available audio devices using the `sounddevice` library.

## Features

- **Multi-Device Playback**: Play audio on all available audio output devices simultaneously
- **Device Discovery**: Automatically detect and list all available audio devices
- **Device Testing**: Test individual devices or all devices with test tones
- **GUI Interface**: PyQt5-based graphical interface for easy control
- **Command-Line Interface**: Simple CLI for quick testing and automation
- **Real-time Status**: Monitor playback status on each device
- **Error Handling**: Robust error handling and device fallback

## Requirements

- Python 3.7+
- sounddevice
- soundfile
- numpy
- PyQt5 (for GUI)

## Installation

1. Install the required packages:
```bash
pip install sounddevice soundfile numpy PyQt5
```

2. Clone or download the project files

## Usage

### 1. GUI Interface (Recommended)

Run the graphical interface:
```bash
python multi_device_gui.py
```

Features:
- Select audio files to play
- View all available audio devices
- Test individual devices
- Play on all devices or selected devices
- Real-time status monitoring

### 2. Command-Line Interface

#### List all available devices:
```bash
python multi_device_cli.py --list-devices
```

#### Test all devices with a test tone:
```bash
python multi_device_cli.py --test-devices
```

#### Test a specific device:
```bash
python multi_device_cli.py --test-single 2
```

#### Play an audio file on all devices:
```bash
python multi_device_cli.py your_audio_file.wav
```

#### Custom test tone:
```bash
python multi_device_cli.py --test-devices --duration 5.0 --frequency 880.0
```

### 3. Demo Script

Run the demo to see the system in action:
```bash
python multi_device_demo.py
```

This will:
1. Discover all audio devices
2. Test each device
3. Create a demo audio file with a melody
4. Play the demo on all working devices

### 4. Programmatic Usage

```python
from multi_device_audio import AudioDeviceManager

# Create manager
manager = AudioDeviceManager()

# Discover devices
devices = manager.discover_devices()

# Test all devices
test_results = manager.test_all_devices()

# Play audio file on all devices
results = manager.play_on_all_devices("your_audio_file.wav")

# Stop all playback
manager.stop_all_playback()
```

## File Structure

- `multi_device_audio.py` - Core audio device management class
- `multi_device_gui.py` - PyQt5 graphical interface
- `multi_device_cli.py` - Command-line interface
- `multi_device_demo.py` - Demo script
- `README.md` - This file

## How It Works

1. **Device Discovery**: Uses `sounddevice.query_devices()` to find all available audio output devices
2. **Device Testing**: Tests each device by playing a short test tone to verify functionality
3. **Simultaneous Playback**: Uses threading to play audio on multiple devices concurrently
4. **Stream Management**: Creates separate `OutputStream` objects for each device
5. **Status Monitoring**: Provides real-time feedback on playback status

## Supported Audio Formats

- WAV files
- MP3 files (if supported by soundfile)
- FLAC files
- OGG files
- Any format supported by the `soundfile` library

## Troubleshooting

### No devices found
- Check that audio devices are properly connected
- Ensure audio drivers are installed
- Try running with administrator/sudo privileges

### Device test fails
- Check device permissions
- Verify the device is not being used by another application
- Try different sample rates or channel configurations

### Playback issues
- Ensure audio files are valid and not corrupted
- Check that devices support the audio format
- Verify sufficient system resources

## Example Use Cases

- **Multi-room audio**: Play music in different rooms simultaneously
- **Audio testing**: Test multiple audio outputs at once
- **Surround sound**: Create custom multi-channel audio setups
- **Audio distribution**: Distribute audio to multiple devices for events
- **Development testing**: Test audio applications across multiple devices

## Notes

- The system automatically handles different channel configurations (mono/stereo)
- Devices that fail tests are automatically excluded from playback
- Playback can be stopped at any time using Ctrl+C or the stop button
- The system is designed to be robust and handle device failures gracefully

## License

This project is open source and available under the MIT License.
