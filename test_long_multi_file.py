#!/usr/bin/env python3
"""
Long Multi-File Audio Test
Test script to verify that multi-file playback doesn't stop after 5 seconds.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time

def create_long_test_audio_files():
    """Create longer test audio files."""
    files = []
    
    # Create longer test tones (10 seconds each)
    sample_rate = 44100
    duration = 10.0  # 10 seconds
    
    tones = [
        (440, "A4_long"),      # A4 note
        (523, "C5_long"),      # C5 note  
        (659, "E5_long"),      # E5 note
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

def test_long_multi_file_playback():
    """Test long multi-file playback to verify no 5-second timeout."""
    base_url = "http://localhost:5000"
    
    print("🎵 Testing Long Multi-File Playback (10 seconds)")
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
    
    # Create longer test audio files
    print("\n2. Creating 10-second test audio files...")
    try:
        test_files = create_long_test_audio_files()
        print(f"   ✓ Created {len(test_files)} long test audio files")
    except Exception as e:
        print(f"   ✗ Error creating test files: {e}")
        return
    
    # Test multi-file playback
    print("\n3. Starting long multi-file playback...")
    try:
        # Prepare form data
        files_data = []
        device_mappings = {}
        
        # Assign files to devices
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
            print(f"   ✓ Long multi-file playback started!")
            print(f"   ✓ Playing on {data['devices_playing']}/{data['total_devices']} devices")
            
            # Monitor playback for 12 seconds (longer than the files)
            print("\n4. Monitoring playback for 12 seconds...")
            start_time = time.time()
            
            while time.time() - start_time < 12:
                elapsed = time.time() - start_time
                
                # Check playback status
                try:
                    status_response = requests.get(f"{base_url}/api/playback-status")
                    status_data = status_response.json()
                    
                    if status_data['success']:
                        playing_devices = []
                        for device_id, status in status_data['devices'].items():
                            if status == 'Playing':
                                playing_devices.append(device_id)
                        
                        if playing_devices:
                            print(f"   ⏱️  {elapsed:.1f}s: {len(playing_devices)} devices still playing")
                        else:
                            print(f"   ⏱️  {elapsed:.1f}s: All devices stopped")
                            break
                    else:
                        print(f"   ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"   ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            final_time = time.time() - start_time
            print(f"\n   ✅ Playback completed after {final_time:.1f} seconds")
            
            if final_time >= 9.5:  # Should be close to 10 seconds
                print("   🎉 SUCCESS: Multi-file playback ran for full duration!")
            else:
                print("   ⚠️  WARNING: Playback stopped early (possible timeout issue)")
                
        else:
            print(f"   ✗ Multi-file playback failed: {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Error during multi-file playback: {e}")
    
    finally:
        # Clean up test files
        print("\n5. Cleaning up test files...")
        for file_path, name in test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        print("   ✓ Test files cleaned up")
    
    print("\n🎉 Long multi-file playback test completed!")

if __name__ == "__main__":
    test_long_multi_file_playback()

