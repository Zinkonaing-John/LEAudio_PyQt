#!/usr/bin/env python3
"""
Test Manual Stop Only
Test script to verify that multi-file playback doesn't auto-stop.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time

def create_short_test_audio_files():
    """Create very short test audio files."""
    files = []
    
    sample_rate = 44100
    duration = 2.0  # Very short duration
    
    tones = [
        (440, "A4_short"),
        (523, "C5_short"),
    ]
    
    for frequency, name in tones:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        stereo_tone = np.column_stack([tone, tone])
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, stereo_tone, sample_rate)
            files.append((tmp_file.name, name))
    
    return files

def test_manual_stop_only():
    """Test that multi-file playback doesn't auto-stop."""
    base_url = "http://localhost:5000"
    
    print("🛑 Testing Manual Stop Only (No Auto-Stop)")
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
    
    # Create short test files
    test_files = create_short_test_audio_files()
    print(f"   ✓ Created {len(test_files)} short test files (2 seconds each)")
    
    # Start playback
    print("\n2. Starting multi-file playback...")
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
            
            # Monitor for 5 seconds (longer than the 2-second files)
            print("\n3. Monitoring playback for 5 seconds (files are only 2 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 5:
                elapsed = time.time() - start_time
                
                # Check playback status
                try:
                    status_response = requests.get(f"{base_url}/api/playback-status")
                    status_data = status_response.json()
                    
                    if status_data['success']:
                        playing_devices = []
                        finished_devices = []
                        for device_id, status in status_data['devices'].items():
                            if status == 'Playing':
                                playing_devices.append(device_id)
                            elif status == 'Finished':
                                finished_devices.append(device_id)
                        
                        print(f"   ⏱️  {elapsed:.1f}s: {len(playing_devices)} playing, {len(finished_devices)} finished")
                        
                        # If all devices are finished but still running, that's good!
                        if len(finished_devices) == len(test_files) and len(playing_devices) == 0:
                            print(f"   ✅ All files finished playing but system still running (no auto-stop)")
                            break
                            
                    else:
                        print(f"   ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"   ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            # Now manually stop
            print("\n4. Manually stopping playback...")
            stop_response = requests.post(f"{base_url}/api/force-stop")
            stop_data = stop_response.json()
            
            if stop_data['success']:
                print("   ✅ Manual stop successful")
            else:
                print(f"   ✗ Manual stop failed: {stop_data['error']}")
                
        else:
            print(f"   ✗ Playback failed: {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Error during test: {e}")
    
    finally:
        # Clean up test files
        print("\n5. Cleaning up test files...")
        for file_path, name in test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        print("   ✓ Test files cleaned up")
    
    print("\n🎉 Manual stop test completed!")
    print("If you see 'All files finished playing but system still running', auto-stop is disabled! ✅")

if __name__ == "__main__":
    test_manual_stop_only()

