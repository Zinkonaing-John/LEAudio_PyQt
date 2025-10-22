# Multi-Device Audio Web Interface

A modern HTML-based web interface for playing audio simultaneously across all available audio devices using sounddevice.

## 🌟 Features

- **Modern Web UI**: Beautiful, responsive HTML interface that works on any device
- **Multi-Device Playback**: Play audio on all available audio output devices simultaneously
- **Drag & Drop**: Easy file upload with drag and drop support
- **Real-time Status**: Live updates of device status and playback progress
- **Device Testing**: Test individual devices or all devices with test tones
- **Cross-Platform**: Works on any device with a web browser
- **Mobile Friendly**: Responsive design that works on phones and tablets

## 🚀 Quick Start

### 1. Start the Web Server
```bash
python start_web_server.py
```

### 2. Open Your Browser
The server will automatically open your browser to: `http://localhost:5000`

### 3. Use the Interface
- **Upload Audio**: Drag and drop or click to select an audio file
- **Play on All Devices**: Click "Play Audio" to play on all devices simultaneously
- **Test Devices**: Use "Test Tone" to test all devices
- **Individual Control**: Test or play on specific devices

## 📁 Files

- `web_ui.html` - The main HTML interface
- `web_server.py` - Flask web server with API endpoints
- `start_web_server.py` - Simple startup script
- `multi_device_audio.py` - Core audio management (shared with CLI version)

## 🎯 How to Use

### Web Interface Features

1. **File Upload**
   - Drag and drop audio files onto the upload area
   - Or click to browse and select files
   - Supports: WAV, MP3, FLAC, OGG, M4A, AAC, WMA

2. **Device Management**
   - View all available audio devices
   - See device information (channels, sample rate, etc.)
   - Test individual devices
   - Play audio on specific devices

3. **Playback Controls**
   - Play on all devices simultaneously
   - Stop all playback
   - Play test tones
   - Refresh device list

4. **Real-time Status**
   - Live device status updates
   - Playback progress indicator
   - Success/error notifications

### API Endpoints

The web server provides these REST API endpoints:

- `GET /api/devices` - Get list of available devices
- `POST /api/test-device` - Test a specific device
- `POST /api/test-tone` - Play test tone on all devices
- `POST /api/play-device` - Play audio on specific device
- `POST /api/play-all` - Play audio on all devices
- `POST /api/stop-playback` - Stop all playback
- `GET /api/playback-status` - Get current playback status

## 🌐 Network Access

The server runs on `0.0.0.0:5000`, which means:
- **Local access**: `http://localhost:5000`
- **Network access**: `http://YOUR_IP:5000` (accessible from other devices on your network)

To find your IP address:
```bash
# Linux/Mac
ip addr show | grep inet
# or
ifconfig | grep inet

# Windows
ipconfig
```

## 📱 Mobile Access

You can access the web interface from any device on your network:
1. Find your computer's IP address
2. Open a browser on your phone/tablet
3. Go to `http://YOUR_IP:5000`
4. Control audio playback from your mobile device!

## 🎵 Supported Audio Formats

- **WAV** - Uncompressed audio
- **MP3** - Compressed audio
- **FLAC** - Lossless compressed audio
- **OGG** - Open source audio format
- **M4A** - Apple audio format
- **AAC** - Advanced Audio Coding
- **WMA** - Windows Media Audio

## 🔧 Technical Details

### Architecture
- **Frontend**: Pure HTML/CSS/JavaScript (no frameworks needed)
- **Backend**: Flask web server
- **Audio Engine**: sounddevice library
- **File Handling**: Temporary file uploads with automatic cleanup

### Browser Compatibility
- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers

### Security Notes
- File uploads are limited to 100MB
- Temporary files are automatically cleaned up
- Server runs in development mode (not for production)

## 🐛 Troubleshooting

### Server Won't Start
- Check if port 5000 is already in use
- Ensure all dependencies are installed
- Check audio device permissions

### No Audio Devices Found
- Verify audio devices are connected
- Check audio drivers are installed
- Try running with administrator/sudo privileges

### Playback Issues
- Ensure audio files are valid and not corrupted
- Check that devices support the audio format
- Verify sufficient system resources

### Browser Issues
- Clear browser cache
- Try a different browser
- Check JavaScript is enabled

## 🎉 Example Use Cases

- **Multi-room Audio**: Play music in different rooms simultaneously
- **Audio Testing**: Test multiple audio outputs at once
- **Surround Sound**: Create custom multi-channel audio setups
- **Audio Distribution**: Distribute audio to multiple devices for events
- **Mobile Control**: Control audio playback from your phone
- **Remote Access**: Control audio from any device on your network

## 🔄 Updates and Maintenance

The web interface automatically:
- Refreshes device status every second during playback
- Cleans up temporary files every 5 minutes
- Handles device failures gracefully
- Provides real-time error feedback

## 📞 Support

If you encounter issues:
1. Check the browser console for JavaScript errors
2. Check the server logs for backend errors
3. Verify audio devices are working with the CLI version
4. Ensure all dependencies are properly installed

---

**Enjoy your multi-device audio experience! 🎵**
