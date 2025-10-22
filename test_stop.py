#!/usr/bin/env python3
"""
Test Stop Functionality
Simple script to test the improved stop functionality.
"""

import requests
import time
import json

def test_stop_functionality():
    """Test the stop functionality."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Stop Functionality")
    print("=" * 40)
    
    # Test 1: Start test tone
    print("1. Starting test tone...")
    try:
        response = requests.post(f"{base_url}/api/test-tone", 
                               json={"duration": 10.0, "frequency": 440.0})
        data = response.json()
        
        if data['success']:
            print(f"   ✓ Test tone started on {data['devices_playing']} devices")
        else:
            print(f"   ✗ Failed to start test tone: {data['error']}")
            return
    except Exception as e:
        print(f"   ✗ Error starting test tone: {e}")
        return
    
    # Wait a bit
    print("2. Playing for 3 seconds...")
    time.sleep(3)
    
    # Test 2: Stop with regular stop
    print("3. Testing regular stop...")
    try:
        response = requests.post(f"{base_url}/api/stop-playback", 
                               json={"playback_id": "test"})
        data = response.json()
        
        if data['success']:
            print("   ✓ Regular stop successful")
        else:
            print(f"   ⚠ Regular stop failed: {data['error']}")
    except Exception as e:
        print(f"   ⚠ Regular stop error: {e}")
    
    # Wait a bit
    time.sleep(1)
    
    # Test 3: Force stop
    print("4. Testing force stop...")
    try:
        response = requests.post(f"{base_url}/api/force-stop")
        data = response.json()
        
        if data['success']:
            print("   ✓ Force stop successful")
        else:
            print(f"   ✗ Force stop failed: {data['error']}")
    except Exception as e:
        print(f"   ✗ Force stop error: {e}")
    
    # Test 4: Check device status
    print("5. Checking device status...")
    try:
        response = requests.get(f"{base_url}/api/playback-status")
        data = response.json()
        
        if data['success']:
            print(f"   ✓ Playback status: {data['is_playing']}")
            for device_id, status in data['devices'].items():
                print(f"     Device {device_id}: {status}")
        else:
            print(f"   ✗ Failed to get status: {data['error']}")
    except Exception as e:
        print(f"   ✗ Status check error: {e}")
    
    print("\n🎉 Stop functionality test completed!")

if __name__ == "__main__":
    test_stop_functionality()

