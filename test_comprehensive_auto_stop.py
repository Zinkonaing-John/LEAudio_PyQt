#!/usr/bin/env python3
"""
Comprehensive Auto-Stop Test
Test to see exactly what happens in the browser when audio finishes.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time
import json

def create_test_audio_file(duration=5.0):
    """Create a test audio file with specified duration."""
    sample_rate = 44100
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # A4 note
    stereo_tone = np.column_stack([tone, tone])
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, stereo_tone, sample_rate)
        return tmp_file.name

def test_comprehensive_auto_stop():
    """Comprehensive test to identify auto-stop behavior."""
    base_url = "http://localhost:5000"
    
    print("🔍 Comprehensive Auto-Stop Test")
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
    
    # Test 1: Single-file playback with longer monitoring
    print("\n2. Testing Single-File Playback (Extended Monitoring)")
    test_file = create_test_audio_file(4.0)  # 4-second file
    print(f"   ✓ Created 4-second test file")
    
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
            
            # Monitor for 10 seconds (much longer than the 4-second file)
            print("   ⏱️  Monitoring for 10 seconds (file is only 4 seconds)...")
            start_time = time.time()
            last_status = None
            
            while time.time() - start_time < 10:
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
                        
                        current_status = f"{len(playing_devices)} playing, {len(finished_devices)} finished, {len(idle_devices)} idle"
                        is_playing = status_data.get('is_playing', False)
                        
                        # Only print if status changed
                        if current_status != last_status:
                            print(f"     {elapsed:.1f}s: {current_status} | is_playing: {is_playing}")
                            last_status = current_status
                        
                        # Check for auto-stop indicators
                        if not is_playing and elapsed > 5.0:
                            print(f"     ⚠️  AUTO-STOP DETECTED at {elapsed:.1f}s!")
                            print(f"     📊 Status: {current_status}")
                            print(f"     🔍 This indicates the system auto-stopped!")
                            break
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(0.5)  # Check more frequently
            
            # Final status check
            print("   🔍 Final status check...")
            try:
                status_response = requests.get(f"{base_url}/api/playback-status")
                status_data = status_response.json()
                
                if status_data['success']:
                    is_playing = status_data.get('is_playing', False)
                    print(f"   📊 Final is_playing status: {is_playing}")
                    
                    if not is_playing:
                        print("   ⚠️  SYSTEM AUTO-STOPPED!")
                        print("   🔍 The system automatically stopped playback")
                    else:
                        print("   ✅ System still reports as playing (no auto-stop)")
                        
            except Exception as e:
                print(f"   ✗ Error checking final status: {e}")
            
            # Manually stop
            print("   ⏹️  Manually stopping...")
            stop_response = requests.post(f"{base_url}/api/stop-playback", 
                                       json={'playback_id': playback_id})
            stop_data = stop_response.json()
            
            if stop_data['success']:
                print("   ✅ Manual stop successful")
            else:
                print(f"   ✗ Manual stop failed: {stop_data['error']}")
                
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
    
    print("\n🎯 Analysis:")
    print("If you see 'AUTO-STOP DETECTED' or 'SYSTEM AUTO-STOPPED',")
    print("then the system is indeed auto-stopping when audio finishes.")
    print("This would indicate a bug in the audio manager or web server.")

if __name__ == "__main__":
    test_comprehensive_auto_stop()

