#!/usr/bin/env python3
"""
Browser Simulation Test
Simulate what happens when a user interacts with the web interface.
"""

import requests
import tempfile
import os
import numpy as np
import soundfile as sf
import time
import json

def create_test_audio_file(duration=3.0):
    """Create a test audio file with specified duration."""
    sample_rate = 44100
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # A4 note
    stereo_tone = np.column_stack([tone, tone])
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        sf.write(tmp_file.name, stereo_tone, sample_rate)
        return tmp_file.name

def simulate_browser_behavior():
    """Simulate browser behavior to see if there's auto-stopping."""
    base_url = "http://localhost:5000"
    
    print("🌐 Browser Simulation Test")
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
    
    # Test 1: Single-file playback with frequent status checks (like browser polling)
    print("\n2. Simulating Single-File Playback (Browser-like polling)")
    test_file = create_test_audio_file(3.0)  # 3-second file
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
            
            # Simulate browser polling every 1 second for 8 seconds
            print("   ⏱️  Simulating browser polling for 8 seconds...")
            start_time = time.time()
            
            for i in range(8):
                elapsed = time.time() - start_time
                
                # Check playback status (like browser would)
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
                        
                        # Check if system auto-stopped
                        if not is_playing and elapsed > 3.5:
                            print(f"     ⚠️  SYSTEM AUTO-STOPPED at {elapsed:.1f}s!")
                            print(f"     🔍 This would explain the user's experience!")
                            break
                            
                    else:
                        print(f"     ⚠️  {elapsed:.1f}s: Status check failed")
                        
                except Exception as e:
                    print(f"     ⚠️  {elapsed:.1f}s: Status error: {e}")
                
                time.sleep(1)  # Poll every second like browser
            
            # Final check
            print("   🔍 Final status check...")
            try:
                status_response = requests.get(f"{base_url}/api/playback-status")
                status_data = status_response.json()
                
                if status_data['success']:
                    is_playing = status_data.get('is_playing', False)
                    print(f"   📊 Final is_playing status: {is_playing}")
                    
                    if not is_playing:
                        print("   ⚠️  SYSTEM AUTO-STOPPED!")
                        print("   🔍 This confirms the auto-stop issue!")
                    else:
                        print("   ✅ System still reports as playing")
                        
            except Exception as e:
                print(f"   ✗ Error checking final status: {e}")
            
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
    
    except Exception as e:
        print(f"   ✗ Error during single-file test: {e}")
    
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass
    
    print("\n🎯 Browser Simulation Analysis:")
    print("If you see 'SYSTEM AUTO-STOPPED', then the issue is confirmed.")
    print("If not, the issue might be browser-specific or UI-related.")

if __name__ == "__main__":
    simulate_browser_behavior()

