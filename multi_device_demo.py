#!/usr/bin/env python3
"""
Multi-Device Audio Demo
Demonstrates playing audio simultaneously on all available devices.
"""

import os
import sys
import tempfile
import time
from multi_device_audio import AudioDeviceManager
import soundfile as sf
import numpy as np


def create_demo_audio():
    """Create a demo audio file with multiple tones."""
    sample_rate = 44100
    duration = 3.0
    
    # Create a sequence of tones
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create a melody: C-E-G-C (frequencies in Hz)
    frequencies = [261.63, 329.63, 392.00, 523.25]  # C4, E4, G4, C5
    note_duration = duration / len(frequencies)
    
    audio = np.zeros_like(t)
    
    for i, freq in enumerate(frequencies):
        start_idx = int(i * note_duration * sample_rate)
        end_idx = int((i + 1) * note_duration * sample_rate)
        
        note_t = t[start_idx:end_idx]
        note_audio = np.sin(2 * np.pi * freq * note_t)
        
        # Add envelope to avoid clicks
        envelope = np.exp(-note_t * 2)  # Exponential decay
        note_audio *= envelope
        
        audio[start_idx:end_idx] = note_audio
    
    # Make it stereo
    stereo_audio = np.column_stack([audio, audio])
    
    return stereo_audio, sample_rate


def main():
    """Main demo function."""
    print("=== Multi-Device Audio Demo ===\n")
    
    # Create manager
    manager = AudioDeviceManager()
    
    # Discover devices
    print("1. Discovering audio devices...")
    devices = manager.discover_devices()
    
    if not devices:
        print("No audio devices found!")
        return
    
    print(f"Found {len(devices)} audio devices\n")
    
    # Test all devices
    print("2. Testing all devices...")
    test_results = manager.test_all_devices()
    working_devices = [d for d in devices if test_results.get(d.index, False)]
    
    if not working_devices:
        print("No working devices found!")
        return
    
    print(f"Found {len(working_devices)} working devices\n")
    
    # Create demo audio
    print("3. Creating demo audio...")
    demo_audio, sample_rate = create_demo_audio()
    
    # Save demo audio to temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, demo_audio, sample_rate)
        demo_file = tmp_file.name
    
    print(f"Demo audio saved to: {demo_file}\n")
    
    try:
        # Play demo audio on all devices
        print("4. Playing demo audio on all devices...")
        
        def playback_callback(device_index, status):
            device_name = next(d.name for d in devices if d.index == device_index)
            print(f"  Device {device_index} ({device_name}): {status}")
        
        results = manager.play_on_all_devices(demo_file, callback=playback_callback)
        
        if results:
            successful_devices = sum(results.values())
            print(f"\nPlayback started on {successful_devices}/{len(results)} devices")
            
            # Wait for playback to complete
            print("\nPlaying... (Press Ctrl+C to stop early)")
            try:
                while manager.is_playing:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nStopping playback...")
                manager.stop_all_playback()
            
            print("\nDemo completed!")
        else:
            print("Failed to start playback on any device")
    
    except Exception as e:
        print(f"Error during demo: {e}")
    
    finally:
        # Clean up
        manager.stop_all_playback()
        try:
            os.unlink(demo_file)
        except:
            pass


if __name__ == "__main__":
    main()
