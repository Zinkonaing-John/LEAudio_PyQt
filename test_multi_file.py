#!/usr/bin/env python3
"""
Multi-File Audio Test
Test script to demonstrate playing different songs on different devices.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf

def create_test_audio_files():
    """Create test audio files with different tones."""
    files = []
    
    # Create different test tones
    sample_rate = 44100
    duration = 3.0
    
    tones = [
        (440, "A4_tone"),      # A4 note
        (523, "C5_tone"),      # C5 note  
        (659, "E5_tone"),      # E5 note
        (784, "G5_tone"),      # G5 note
    ]
    
    for frequency, name in tones:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        # Make it stereo
        stereo_tone = np.column_stack([tone, tone])
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, stereo_tone, sample_rate)
            files.append((tmp_file.name, name))
    
    return files

def test_multi_file_playback():
    """Test multi-file playback functionality."""
    base_url = "http://localhost:5000"
    
    print("🎵 Testing Multi-File Playback")
    print("=" * 40)
    
    # Get available devices
    print("1. Getting available devices...")
    try:
        response = requests.get(f"{base_url}/api/devices")
        data = response.json()
        
        if not data['success']:
            print(f"   ✗ Failed to get devices: {data['error']}")
            return
        
        devices = data['devices']
        print(f"   ✓ Found {len(devices)} devices")
        
        # Filter working devices (skip devices with 0 output channels)
        working_devices = [d for d in devices if d['max_output_channels'] > 0]
        print(f"   ✓ {len(working_devices)} devices have output capability")
        
    except Exception as e:
        print(f"   ✗ Error getting devices: {e}")
        return
    
    # Create test audio files
    print("\n2. Creating test audio files...")
    try:
        test_files = create_test_audio_files()
        print(f"   ✓ Created {len(test_files)} test audio files")
    except Exception as e:
        print(f"   ✗ Error creating test files: {e}")
        return
    
    # Test multi-file playback
    print("\n3. Testing multi-file playback...")
    try:
        # Prepare form data
        files_data = []
        device_mappings = {}
        
        # Assign files to devices (up to 4 devices)
        for i, (file_path, name) in enumerate(test_files):
            if i < len(working_devices):
                device_id = working_devices[i]['index']
                files_data.append(('files', (name + '.wav', open(file_path, 'rb'), 'audio/wav')))
                device_mappings[str(i)] = device_id
                print(f"   📁 {name} → Device {device_id} ({working_devices[i]['name']})")
        
        if not files_data:
            print("   ✗ No files to play")
            return
        
        # Send request
        form_data = {
            'device_mappings': str(device_mappings).replace("'", '"')
        }
        
        response = requests.post(f"{base_url}/api/play-multi-files", 
                               files=files_data, 
                               data=form_data)
        
        data = response.json()
        
        if data['success']:
            print(f"   ✓ Multi-file playback started successfully!")
            print(f"   ✓ Playing on {data['devices_playing']}/{data['total_devices']} devices")
            
            # Show results for each device
            for device_id, result in data['results'].items():
                if result['success']:
                    print(f"     ✓ Device {device_id}: Playing {result['filename']}")
                else:
                    print(f"     ✗ Device {device_id}: Failed - {result.get('error', 'Unknown error')}")
        else:
            print(f"   ✗ Multi-file playback failed: {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Error during multi-file playback: {e}")
    
    finally:
        # Clean up test files
        print("\n4. Cleaning up test files...")
        for file_path, name in test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        print("   ✓ Test files cleaned up")
    
    print("\n🎉 Multi-file playback test completed!")

if __name__ == "__main__":
    test_multi_file_playback()

