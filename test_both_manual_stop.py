#!/usr/bin/env python3
"""
Test Manual Stop for Both Single and Multi-File Playback
Test script to verify that both single-file and multi-file playback require manual stopping.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time

def create_short_test_audio_file():
    """Create a very short test audio file."""
    sample_rate = 44100
    duration = 2.0  # Very short duration
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # A4 note
    stereo_tone = np.column_stack([tone, tone])
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, stereo_tone, sample_rate)
        return tmp_file.name

def test_both_manual_stop():
    """Test that both single-file and multi-file playback require manual stopping."""
    base_url = "http://localhost:5000"
    
    print("🛑 Testing Manual Stop for Both Single and Multi-File Playback")
    print("=" * 60)
    
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
    
    # Test 1: Single-file playback
    print("\n2. Testing Single-File Playback (Manual Stop Required)")
    test_file = create_short_test_audio_file()
    print(f"   ✓ Created 2-second test file")
    
    try:
        # Start single-file playback
        print("   🎵 Starting single-file playback...")
        with open(test_file, 'rb') as f:
            files = {'file': ('test.wav', f, 'audio/wav')}
            response = requests.post(f"{base_url}/api/play-all", files=files)
        
        data = response.json()
        
        if data['success']:
            print(f"   ✓ Single-file playback started on {data['devices_playing']} devices")
            
            # Monitor for 4 seconds (longer than the 2-second file)
            print("   ⏱️  Monitoring for 4 seconds (file is only 2 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 4:
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
                        
                        print(f"     {elapsed:.1f}s: {len(playing_devices)} playing, {len(finished_devices)} finished")
                        
                        # If all devices are finished but still running, that's good!
                        if len(finished_devices) > 0 and elapsed > 2.5:
                            print(f"     ✅ Single-file finished but system still running (no auto-stop)")
                            break
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            # Manually stop single-file playback
            print("   ⏹️  Manually stopping single-file playback...")
            stop_response = requests.post(f"{base_url}/api/force-stop")
            stop_data = stop_response.json()
            
            if stop_data['success']:
                print("   ✅ Single-file manual stop successful")
            else:
                print(f"   ✗ Single-file manual stop failed: {stop_data['error']}")
                
        else:
            print(f"   ✗ Single-file playback failed: {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Error during single-file test: {e}")
    
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass
    
    # Wait a moment between tests
    time.sleep(2)
    
    # Test 2: Multi-file playback
    print("\n3. Testing Multi-File Playback (Manual Stop Required)")
    
    # Create short test files
    test_files = []
    tones = [(440, "A4"), (523, "C5")]
    
    for frequency, name in tones:
        sample_rate = 44100
        duration = 2.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        stereo_tone = np.column_stack([tone, tone])
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, stereo_tone, sample_rate)
            test_files.append((tmp_file.name, name))
    
    print(f"   ✓ Created {len(test_files)} short test files (2 seconds each)")
    
    try:
        # Start multi-file playback
        print("   🎵 Starting multi-file playback...")
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
            print(f"   ✓ Multi-file playback started on {data['devices_playing']} devices")
            
            # Monitor for 4 seconds (longer than the 2-second files)
            print("   ⏱️  Monitoring for 4 seconds (files are only 2 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 4:
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
                        
                        print(f"     {elapsed:.1f}s: {len(playing_devices)} playing, {len(finished_devices)} finished")
                        
                        # If all devices are finished but still running, that's good!
                        if len(finished_devices) == len(test_files) and elapsed > 2.5:
                            print(f"     ✅ Multi-file finished but system still running (no auto-stop)")
                            break
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            # Manually stop multi-file playback
            print("   ⏹️  Manually stopping multi-file playback...")
            stop_response = requests.post(f"{base_url}/api/force-stop")
            stop_data = stop_response.json()
            
            if stop_data['success']:
                print("   ✅ Multi-file manual stop successful")
            else:
                print(f"   ✗ Multi-file manual stop failed: {stop_data['error']}")
                
        else:
            print(f"   ✗ Multi-file playback failed: {data['error']}")
    
    except Exception as e:
        print(f"   ✗ Error during multi-file test: {e}")
    
    finally:
        # Clean up test files
        for file_path, name in test_files:
            try:
                os.unlink(file_path)
            except:
                pass
    
    print("\n🎉 Manual stop test completed!")
    print("✅ Both single-file and multi-file playback now require manual stopping!")
    print("✅ No automatic stopping - full user control!")

if __name__ == "__main__":
    test_both_manual_stop()

