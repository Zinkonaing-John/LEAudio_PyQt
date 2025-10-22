#!/usr/bin/env python3
"""
Debug Auto-Stop Issue
Test script to identify exactly why the system is auto-stopping.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time
import json

def create_short_test_audio_file():
    """Create a very short test audio file."""
    sample_rate = 44100
    duration = 3.0  # 3 seconds
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # A4 note
    stereo_tone = np.column_stack([tone, tone])
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, stereo_tone, sample_rate)
        return tmp_file.name

def debug_auto_stop():
    """Debug why the system is auto-stopping."""
    base_url = "http://localhost:5000"
    
    print("🔍 Debugging Auto-Stop Issue")
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
    
    # Test 1: Single-file playback
    print("\n2. Testing Single-File Playback Auto-Stop")
    test_file = create_short_test_audio_file()
    print(f"   ✓ Created 3-second test file")
    
    try:
        # Start single-file playback
        print("   🎵 Starting single-file playback...")
        with open(test_file, 'rb') as f:
            files = {'file': ('test.wav', f, 'audio/wav')}
            response = requests.post(f"{base_url}/api/play-all", files=files)
        
        data = response.json()
        
        if data['success']:
            playback_id = data['playback_id']
            print(f"   ✓ Single-file playback started on {data['devices_playing']} devices")
            print(f"   📋 Playback ID: {playback_id}")
            
            # Monitor for 6 seconds (longer than the 3-second file)
            print("   ⏱️  Monitoring for 6 seconds (file is only 3 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 6:
                elapsed = time.time() - start_time
                
                # Check playback status
                try:
                    status_response = requests.get(f"{base_url}/api/playback-status")
                    status_data = status_response.json()
                    
                    if status_data['success']:
                        playing_devices = []
                        finished_devices = []
                        idle_devices = []
                        
                        for device_id, status in status_data['devices'].items():
                            if status == 'Playing':
                                playing_devices.append(device_id)
                            elif status == 'Finished':
                                finished_devices.append(device_id)
                            elif status == 'Idle':
                                idle_devices.append(device_id)
                        
                        print(f"     {elapsed:.1f}s: {len(playing_devices)} playing, {len(finished_devices)} finished, {len(idle_devices)} idle")
                        print(f"     📊 is_playing: {status_data.get('is_playing', 'N/A')}")
                        
                        # Check if playback ID still exists
                        try:
                            # Try to get playback info (this might fail if auto-cleaned)
                            # We can't directly check active_playbacks, but we can infer from behavior
                            pass
                        except:
                            pass
                        
                        # If all devices are finished but system still running, that's good!
                        if len(finished_devices) > 0 and elapsed > 3.5:
                            print(f"     ✅ Single-file finished but system still running (no auto-stop)")
                            break
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            # Check if playback is still active
            print("   🔍 Checking if playback is still active...")
            try:
                status_response = requests.get(f"{base_url}/api/playback-status")
                status_data = status_response.json()
                
                if status_data['success']:
                    is_playing = status_data.get('is_playing', False)
                    print(f"   📊 Final is_playing status: {is_playing}")
                    
                    if not is_playing:
                        print("   ⚠️  System reports not playing - this might indicate auto-stop!")
                    else:
                        print("   ✅ System still reports as playing")
                        
            except Exception as e:
                print(f"   ✗ Error checking final status: {e}")
            
            # Manually stop single-file playback
            print("   ⏹️  Manually stopping single-file playback...")
            stop_response = requests.post(f"{base_url}/api/stop-playback", 
                                       json={'playback_id': playback_id})
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
    print("\n3. Testing Multi-File Playback Auto-Stop")
    
    # Create short test files
    test_files = []
    tones = [(440, "A4"), (523, "C5")]
    
    for frequency, name in tones:
        sample_rate = 44100
        duration = 3.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        stereo_tone = np.column_stack([tone, tone])
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, stereo_tone, sample_rate)
            test_files.append((tmp_file.name, name))
    
    print(f"   ✓ Created {len(test_files)} short test files (3 seconds each)")
    
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
            playback_id = data['playback_id']
            print(f"   ✓ Multi-file playback started on {data['devices_playing']} devices")
            print(f"   📋 Playback ID: {playback_id}")
            
            # Monitor for 6 seconds (longer than the 3-second files)
            print("   ⏱️  Monitoring for 6 seconds (files are only 3 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 6:
                elapsed = time.time() - start_time
                
                # Check playback status
                try:
                    status_response = requests.get(f"{base_url}/api/playback-status")
                    status_data = status_response.json()
                    
                    if status_data['success']:
                        playing_devices = []
                        finished_devices = []
                        idle_devices = []
                        
                        for device_id, status in status_data['devices'].items():
                            if status == 'Playing':
                                playing_devices.append(device_id)
                            elif status == 'Finished':
                                finished_devices.append(device_id)
                            elif status == 'Idle':
                                idle_devices.append(device_id)
                        
                        print(f"     {elapsed:.1f}s: {len(playing_devices)} playing, {len(finished_devices)} finished, {len(idle_devices)} idle")
                        print(f"     📊 is_playing: {status_data.get('is_playing', 'N/A')}")
                        
                        # If all devices are finished but system still running, that's good!
                        if len(finished_devices) == len(test_files) and elapsed > 3.5:
                            print(f"     ✅ Multi-file finished but system still running (no auto-stop)")
                            break
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            # Check if playback is still active
            print("   🔍 Checking if playback is still active...")
            try:
                status_response = requests.get(f"{base_url}/api/playback-status")
                status_data = status_response.json()
                
                if status_data['success']:
                    is_playing = status_data.get('is_playing', False)
                    print(f"   📊 Final is_playing status: {is_playing}")
                    
                    if not is_playing:
                        print("   ⚠️  System reports not playing - this might indicate auto-stop!")
                    else:
                        print("   ✅ System still reports as playing")
                        
            except Exception as e:
                print(f"   ✗ Error checking final status: {e}")
            
            # Manually stop multi-file playback
            print("   ⏹️  Manually stopping multi-file playback...")
            stop_response = requests.post(f"{base_url}/api/stop-playback", 
                                       json={'playback_id': playback_id})
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
    
    print("\n🎯 Debug Analysis:")
    print("If you see 'System reports not playing' after files finish,")
    print("that indicates the system is auto-stopping when streams finish.")
    print("The issue is likely in the audio manager's stream completion logic.")

if __name__ == "__main__":
    debug_auto_stop()

