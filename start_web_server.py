#!/usr/bin/env python3
"""
Start Multi-Device Audio Web Server
Simple script to start the Flask web server for the multi-device audio system.
"""

import os
import sys
import webbrowser
import time
import threading
from web_server import app, audio_manager


def open_browser():
    """Open browser after a short delay."""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')


def main():
    """Main function to start the web server."""
    print("=" * 60)
    print("🎵 Multi-Device Audio Web Server")
    print("=" * 60)
    print()
    
    # Initialize audio manager
    print("Initializing audio system...")
    try:
        devices = audio_manager.discover_devices()
        print(f"✓ Found {len(devices)} audio devices")
        
        # Test devices
        print("Testing devices...")
        test_results = audio_manager.test_all_devices()
        working_devices = sum(test_results.values())
        print(f"✓ {working_devices}/{len(devices)} devices are working")
        
    except Exception as e:
        print(f"⚠️  Warning: Audio initialization error: {e}")
    
    print()
    print("Starting web server...")
    print("🌐 Server will be available at: http://localhost:5000")
    print("📱 You can also access it from other devices on your network")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        # Start Flask server
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        print("Goodbye! 👋")


if __name__ == "__main__":
    main()
