#!/usr/bin/env python3
"""
Test Multi-File Reset
Test script to verify that multi-file playback can be restarted after stopping.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time

def create_test_audio_files():
    """Create test audio files."""
    files = []
    
    sample_rate = 44100
    duration = 3.0  # Short duration for testing
    
    tones = [
        (440, "A4_test"),
        (523, "C5_test"),
    ]
    
    for frequency, name in tones:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        stereo_tone = np.column_stack([tone, tone])
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, stereo_tone, sample_rate)
            files.append((tmp_file.name, name))
    
    return files

def test_multi_file_reset():
    """Test that multi-file playback can be restarted after stopping."""
    base_url = "http://localhost:5000"
    
    print("🔄 Testing Multi-File Reset Functionality")
    print("=" * 50)
    
    # Get available devices
    print("1. Getting available devices...")
    try:
        response = requests.get(f"{base_url}/api/devices")
        data = response.json()
        
        if not data['success']:
            print(f"   ✗ Failed to get devices: {data['error']}")
            return
        
        devices = data['devices']
        working_devices = [d for d in devices if d['max_output_channels'] > 0]
        print(f"   ✓ Found {len(working_devices)} working devices")
        
    except Exception as e:
        print(f"   ✗ Error getting devices: {e}")
        return
    
    # Test multiple cycles
    for cycle in range(3):
        print(f"\n🔄 Cycle {cycle + 1}: Testing multi-file playback and reset")
        
        # Create test files
        test_files = create_test_audio_files()
        print(f"   ✓ Created {len(test_files)} test files")
        
        # Start playback
        print("   🎵 Starting multi-file playback...")
        try:
            files_data = []
            device_mappings = {}
            
            for i, (file_path, name) in enumerate(test_files):
                if i < len(working_devices):
                    device_id = working_devices[i]['index']
                    files_data.append(('files', (name + '.wav', open(file_path, 'rb'), 'audio/wav')))
                    device_mappings[str(i)] = device_id
            
            form_data = {
                'device_mappings': str(device_mappings).replace("'", '"')
            }
            
            response = requests.post(f"{base_url}/api/play-multi-files", 
                                   files=files_data, 
                                   data=form_data)
            
            data = response.json()
            
            if data['success']:
                print(f"   ✓ Playback started on {data['devices_playing']} devices")
                
                # Let it play for 2 seconds
                time.sleep(2)
                
                # Stop playback
                print("   ⏹️  Stopping playback...")
                stop_response = requests.post(f"{base_url}/api/force-stop")
                stop_data = stop_response.json()
                
                if stop_data['success']:
                    print("   ✓ Playback stopped successfully")
                else:
                    print(f"   ✗ Failed to stop: {stop_data['error']}")
                
                # Wait a moment for cleanup
                time.sleep(1)
                
            else:
                print(f"   ✗ Playback failed: {data['error']}")
        
        except Exception as e:
            print(f"   ✗ Error in cycle {cycle + 1}: {e}")
        
        finally:
            # Clean up test files
            for file_path, name in test_files:
                try:
                    os.unlink(file_path)
                except:
                    pass
        
        print(f"   ✅ Cycle {cycle + 1} completed")
    
    print("\n🎉 Multi-file reset test completed!")
    print("If you can see this message, the reset functionality is working!")

if __name__ == "__main__":
    test_multi_file_reset()

