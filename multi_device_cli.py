#!/usr/bin/env python3
"""
Simple Multi-Device Audio Player
Command-line interface for playing audio on all available devices simultaneously.
"""

import argparse
import sys
import os
from multi_device_audio import AudioDeviceManager


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="Play audio on all available devices simultaneously")
    parser.add_argument("file", nargs="?", help="Audio file to play")
    parser.add_argument("--list-devices", "-l", action="store_true", help="List all available audio devices")
    parser.add_argument("--test-devices", "-t", action="store_true", help="Test all devices with a test tone")
    parser.add_argument("--test-single", "-s", type=int, help="Test a specific device by index")
    parser.add_argument("--duration", "-d", type=float, default=2.0, help="Duration for test tone (default: 2.0 seconds)")
    parser.add_argument("--frequency", "-f", type=float, default=440.0, help="Frequency for test tone (default: 440.0 Hz)")
    
    args = parser.parse_args()
    
    # Create manager
    manager = AudioDeviceManager()
    
    # Discover devices
    print("Discovering audio devices...")
    devices = manager.discover_devices()
    
    if not devices:
        print("No audio devices found!")
        return 1
    
    # List devices
    if args.list_devices:
        print("\n=== Available Audio Devices ===")
        for device in devices:
            status = " (DEFAULT)" if device.is_default else ""
            print(f"  {device.index}: {device.name}{status}")
            print(f"      Channels: {device.max_output_channels}, Sample Rate: {device.default_samplerate}Hz")
        return 0
    
    # Test single device
    if args.test_single is not None:
        device_index = args.test_single
        device = next((d for d in devices if d.index == device_index), None)
        
        if not device:
            print(f"Device {device_index} not found!")
            return 1
        
        print(f"Testing device {device_index}: {device.name}")
        
        # Create test tone
        test_tone, sample_rate = manager.create_test_tone(
            duration=args.duration, 
            frequency=args.frequency
        )
        
        # Save to temporary file
        import tempfile
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, test_tone, sample_rate)
            temp_file_path = tmp_file.name
        
        try:
            success = manager.play_on_device(device_index, test_tone, sample_rate)
            if success:
                print(f"✓ Device {device_index} test passed")
            else:
                print(f"✗ Device {device_index} test failed")
        except Exception as e:
            print(f"✗ Device {device_index} test error: {e}")
        finally:
            # Clean up
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        return 0
    
    # Test all devices
    if args.test_devices:
        print("\nTesting all devices...")
        
        # Create test tone
        test_tone, sample_rate = manager.create_test_tone(
            duration=args.duration, 
            frequency=args.frequency
        )
        
        # Save to temporary file
        import tempfile
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, test_tone, sample_rate)
            temp_file_path = tmp_file.name
        
        try:
            results = manager.play_on_all_devices(temp_file_path)
            
            if results:
                print(f"\nTest tone played on {len(results)} devices")
                passed = sum(results.values())
                print(f"Results: {passed}/{len(results)} devices successful")
            else:
                print("Failed to play test tone on any device")
        except Exception as e:
            print(f"Error playing test tone: {e}")
        finally:
            # Clean up
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        return 0
    
    # Play audio file
    if args.file:
        if not os.path.exists(args.file):
            print(f"Audio file not found: {args.file}")
            return 1
        
        print(f"Playing '{args.file}' on all devices...")
        
        try:
            results = manager.play_on_all_devices(args.file)
            
            if results:
                passed = sum(results.values())
                print(f"Playback started on {passed}/{len(results)} devices")
                
                # Wait for playback to complete
                import time
                print("Press Ctrl+C to stop playback...")
                try:
                    while manager.is_playing:
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nStopping playback...")
                    manager.stop_all_playback()
            else:
                print("Failed to start playback on any device")
        except Exception as e:
            print(f"Error during playback: {e}")
        
        return 0
    
    # No action specified, show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
