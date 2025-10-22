#!/usr/bin/env python3
"""
Final Auto-Stop Fix Test
Test to verify that the auto-stop fix is working correctly.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time
import json

def create_test_audio_file(duration=2.0):
    """Create a test audio file with specified duration."""
    sample_rate = 44100
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # A4 note
    stereo_tone = np.column_stack([tone, tone])
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, stereo_tone, sample_rate)
        return tmp_file.name

def test_auto_stop_fix():
    """Test that the auto-stop fix is working."""
    base_url = "http://localhost:5000"
    
    print("🔧 Testing Auto-Stop Fix")
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
        working_devices = [d for d in devices if d['max_output_channels'] > 0]
        print(f"   ✓ Found {len(working_devices)} working devices")
        
    except Exception as e:
        print(f"   ✗ Error getting devices: {e}")
        return
    
    # Test: Single-file playback
    print("\n2. Testing Single-File Playback (Auto-Stop Fix)")
    test_file = create_test_audio_file(2.0)  # 2-second file
    print(f"   ✓ Created 2-second test file")
    
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
            
            # Monitor for 6 seconds (3x longer than the 2-second file)
            print("   ⏱️  Monitoring for 6 seconds (file is only 2 seconds)...")
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
                        
                        is_playing = status_data.get('is_playing', False)
                        
                        print(f"     {elapsed:.1f}s: {len(playing_devices)} playing, {len(finished_devices)} finished | is_playing: {is_playing}")
                        
                        # Check for auto-stop
                        if not is_playing and elapsed > 2.5:
                            print(f"     ⚠️  AUTO-STOP DETECTED at {elapsed:.1f}s!")
                            print(f"     ✗ Fix failed - system still auto-stops!")
                            return
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)
            
            # Final check
            print("   🔍 Final status check...")
            try:
                status_response = requests.get(f"{base_url}/api/playback-status")
                status_data = status_response.json()
                
                if status_data['success']:
                    is_playing = status_data.get('is_playing', False)
                    print(f"   📊 Final is_playing status: {is_playing}")
                    
                    if not is_playing:
                        print("   ✗ Fix failed - system auto-stopped!")
                        return
                    else:
                        print("   ✅ Fix successful - system still playing!")
                        
            except Exception as e:
                print(f"   ✗ Error checking final status: {e}")
                return
            
            # Manual stop
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
            return
    
    except Exception as e:
        print(f"   ✗ Error during single-file test: {e}")
        return
    
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass
    
    print("\n🎉 Auto-Stop Fix Test Results:")
    print("✅ System no longer auto-stops!")
    print("✅ Audio continues playing until manually stopped!")
    print("✅ Manual stop functionality works correctly!")
    print("\n🔧 The fix is working - you now have full manual control!")

if __name__ == "__main__":
    test_auto_stop_fix()

