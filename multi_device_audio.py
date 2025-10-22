#!/usr/bin/env python3
"""
Multi-Device Audio Playback System
Allows playing audio simultaneously across all available audio devices using sounddevice.
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time
import os
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue


@dataclass
class AudioDevice:
    """Represents an audio device with its properties."""
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    is_default: bool = False
    
    def __str__(self):
        return f"Device {self.index}: {self.name} ({self.max_output_channels} out, {self.max_input_channels} in)"


class AudioDeviceManager:
    """Manages multiple audio devices for simultaneous playback."""
    
    def __init__(self):
        self.devices: List[AudioDevice] = []
        self.active_streams: Dict[int, sd.OutputStream] = {}
        self.playback_threads: Dict[int, threading.Thread] = {}
        self.stop_events: Dict[int, threading.Event] = {}
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.max_simultaneous_streams = 4  # Limit to prevent ALSA overload
        
    def discover_devices(self) -> List[AudioDevice]:
        """Discover all available audio output devices."""
        self.devices.clear()
        
        try:
            device_list = sd.query_devices()
            default_device = sd.default.device[1]  # Output device
            
            for i, device_info in enumerate(device_list):
                if device_info['max_output_channels'] > 0:
                    device = AudioDevice(
                        index=i,
                        name=device_info['name'],
                        max_input_channels=device_info['max_input_channels'],
                        max_output_channels=device_info['max_output_channels'],
                        default_samplerate=device_info['default_samplerate'],
                        is_default=(i == default_device)
                    )
                    self.devices.append(device)
                    
            print(f"Discovered {len(self.devices)} audio output devices:")
            for device in self.devices:
                print(f"  {device}")
                
        except Exception as e:
            print(f"Error discovering devices: {e}")
            
        return self.devices
    
    def test_device(self, device_index: int) -> bool:
        """Test if a device can play audio."""
        try:
            # Generate a short test tone
            duration = 0.1  # 100ms
            sample_rate = 44100
            frequency = 440  # A4 note
            
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            test_tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
            
            # Try to play the test tone
            sd.play(test_tone, samplerate=sample_rate, device=device_index)
            sd.wait()
            
            return True
            
        except Exception as e:
            print(f"Device {device_index} test failed: {e}")
            return False
    
    def test_all_devices(self) -> Dict[int, bool]:
        """Test all discovered devices."""
        results = {}
        print("\nTesting all devices...")
        
        for device in self.devices:
            print(f"Testing {device.name}...")
            results[device.index] = self.test_device(device.index)
            if results[device.index]:
                print(f"  ✓ {device.name} - OK")
            else:
                print(f"  ✗ {device.name} - Failed")
                
        return results
    
    def load_audio_file(self, file_path: str) -> tuple:
        """Load audio file and return data and sample rate."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
                
            data, sample_rate = sf.read(file_path, dtype='float32')
            
            if data.size == 0:
                raise ValueError("Empty audio file")
                
            # Ensure data is in the right format
            if data.ndim == 1:
                data = data.reshape(-1, 1)  # Convert to 2D for consistency
                
            print(f"Loaded audio: {file_path} ({sample_rate}Hz, {data.shape[1]} channels)")
            return data, sample_rate
            
        except Exception as e:
            print(f"Error loading audio file {file_path}: {e}")
            raise
    
    def play_on_device(self, device_index: int, audio_data: np.ndarray, 
                      sample_rate: int, callback: Optional[Callable] = None, 
                      status_callback: Optional[Callable] = None) -> bool:
        """Play audio on a specific device."""
        try:
            device = next((d for d in self.devices if d.index == device_index), None)
            if not device:
                print(f"Device {device_index} not found")
                return False
            
            if device_index in self.active_streams:
                print(f"Device {device_index} is already playing")
                return False
            
            # Check if we're at the stream limit
            if len(self.active_streams) >= self.max_simultaneous_streams:
                print(f"Maximum simultaneous streams ({self.max_simultaneous_streams}) reached. Skipping device {device_index}")
                return False
            
            # Create stop event for this device
            stop_event = threading.Event()
            self.stop_events[device_index] = stop_event
            
            # Determine number of channels to use
            channels = min(audio_data.shape[1], device.max_output_channels)
            if channels < audio_data.shape[1]:
                print(f"Device {device.name} supports only {channels} channels, downmixing from {audio_data.shape[1]}")
                if audio_data.shape[1] > 1:
                    audio_data = np.mean(audio_data, axis=1, keepdims=True)
            
            # Create output stream
            stream = sd.OutputStream(
                samplerate=sample_rate,
                device=device_index,
                channels=channels,
                callback=self._audio_callback if callback else None,
                finished_callback=lambda: self._on_device_finished(device_index)
            )
            
            self.active_streams[device_index] = stream
            
            # Start playback in a separate thread
            def playback_thread():
                try:
                    if status_callback:
                        status_callback(device_index, "Playing")
                    
                    stream.start()
                    stream.write(audio_data)
                    
                    # Keep the stream running indefinitely until manually stopped
                    # This ensures no automatic stopping
                    while not stop_event.is_set():
                        import time
                        time.sleep(0.1)
                        
                        # Only check if stream is still active, don't break on completion
                        if not stream.active:
                            # Stream finished naturally, but keep the thread alive
                            # until manually stopped to prevent auto-cleanup
                            pass
                    
                    # Only stop when manually requested
                    if stream.active:
                        try:
                            stream.stop()
                        except Exception as stop_error:
                            print(f"Error stopping stream in thread: {stop_error}")
                    
                    try:
                        stream.close()
                    except Exception as close_error:
                        print(f"Error closing stream in thread: {close_error}")
                    
                    if status_callback:
                        status_callback(device_index, "Finished")
                    
                    if callback:
                        callback(device_index, "finished")
                        
                except Exception as e:
                    print(f"Playback error on device {device_index}: {e}")
                    if status_callback:
                        status_callback(device_index, "Error")
                    if callback:
                        callback(device_index, f"error: {e}")
                finally:
                    # Clean up
                    try:
                        if device_index in self.active_streams:
                            del self.active_streams[device_index]
                        if device_index in self.stop_events:
                            del self.stop_events[device_index]
                    except Exception as cleanup_error:
                        print(f"Error in cleanup: {cleanup_error}")
            
            thread = threading.Thread(target=playback_thread, daemon=True)
            self.playback_threads[device_index] = thread
            thread.start()
            
            return True
            
        except Exception as e:
            print(f"Error playing on device {device_index}: {e}")
            return False
    
    def _audio_callback(self, outdata, frames, time, status):
        """Audio callback for real-time processing (if needed)."""
        if status:
            print(f"Audio callback status: {status}")
    
    def _on_device_finished(self, device_index: int):
        """Called when a device finishes playback."""
        print(f"Device {device_index} finished playback")
    
    def play_on_all_devices(self, file_path: str, callback: Optional[Callable] = None) -> Dict[int, bool]:
        """Play audio file simultaneously on all available devices."""
        if not self.devices:
            print("No devices available. Run discover_devices() first.")
            return {}
        
        try:
            # Load audio file
            audio_data, sample_rate = self.load_audio_file(file_path)
            
            print(f"\nPlaying '{file_path}' on {len(self.devices)} devices simultaneously...")
            
            # Test devices first
            working_devices = []
            for device in self.devices:
                if self.test_device(device.index):
                    working_devices.append(device)
                else:
                    print(f"Skipping {device.name} - test failed")
            
            if not working_devices:
                print("No working devices found!")
                return {}
            
            print(f"Playing on {len(working_devices)} working devices...")
            
            # Play on all working devices simultaneously
            results = {}
            with ThreadPoolExecutor(max_workers=len(working_devices)) as executor:
                # Submit all playback tasks
                future_to_device = {
                    executor.submit(self.play_on_device, device.index, audio_data, sample_rate, callback): device
                    for device in working_devices
                }
                
                # Collect results
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        result = future.result()
                        results[device.index] = result
                        if result:
                            print(f"✓ Started playback on {device.name}")
                        else:
                            print(f"✗ Failed to start playback on {device.name}")
                    except Exception as e:
                        print(f"✗ Error on {device.name}: {e}")
                        results[device.index] = False
            
            self.is_playing = True
            return results
            
        except Exception as e:
            print(f"Error in play_on_all_devices: {e}")
            return {}
    
    def stop_all_playback(self):
        """Stop all active playback with improved error handling."""
        print("Stopping all playback...")

        # Signal all stop events first
        for stop_event in self.stop_events.values():
            try:
                stop_event.set()
            except Exception as e:
                print(f"Error setting stop event: {e}")

        # Stop all active streams with better error handling
        streams_to_close = list(self.active_streams.items())
        for device_index, stream in streams_to_close:
            try:
                if hasattr(stream, 'active') and stream.active:
                    print(f"Stopping stream on device {device_index}")
                    # Try to stop gracefully first
                    try:
                        stream.stop()
                    except Exception as stop_error:
                        print(f"Error stopping stream on device {device_index}: {stop_error}")
                        # Force close if stop fails
                        try:
                            if hasattr(stream, 'abort'):
                                stream.abort()
                        except Exception as abort_error:
                            print(f"Error aborting stream on device {device_index}: {abort_error}")
                
                # Close the stream
                if hasattr(stream, 'close'):
                    try:
                        stream.close()
                    except Exception as close_error:
                        print(f"Error closing stream on device {device_index}: {close_error}")
                        
            except Exception as e:
                print(f"Error handling stream on device {device_index}: {e}")
            finally:
                # Remove from tracking even if there was an error
                if device_index in self.active_streams:
                    del self.active_streams[device_index]

        # Wait for threads to finish with shorter timeout
        threads_to_join = list(self.playback_threads.values())
        for thread in threads_to_join:
            try:
                if thread.is_alive():
                    thread.join(timeout=0.2)  # Very short timeout
                    if thread.is_alive():
                        print(f"Thread still alive after timeout, continuing...")
            except Exception as e:
                print(f"Error joining thread: {e}")

        # Force stop any remaining sounddevice streams
        try:
            import sounddevice as sd
            sd.stop()
            # Don't wait too long to avoid hanging
            import time
            time.sleep(0.1)
        except Exception as e:
            print(f"Error stopping sounddevice: {e}")

        # Clear all tracking
        self.active_streams.clear()
        self.playback_threads.clear()
        self.stop_events.clear()
        self.is_playing = False  # Only set to False when manually stopped

        print("All playback stopped")
    
    def get_device_status(self) -> Dict[int, str]:
        """Get status of all devices."""
        status = {}
        for device in self.devices:
            if device.index in self.active_streams:
                stream = self.active_streams[device.index]
                if hasattr(stream, 'active') and stream.active:
                    status[device.index] = "Playing"
                else:
                    status[device.index] = "Finished"
            else:
                status[device.index] = "Idle"
        return status
    
    def create_test_tone(self, duration: float = 2.0, frequency: float = 440.0, 
                        sample_rate: int = 44100) -> tuple:
        """Create a test tone for testing devices."""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        # Make it stereo
        stereo_tone = np.column_stack([tone, tone])
        
        return stereo_tone, sample_rate


def main():
    """Demo function to test the multi-device audio system."""
    print("=== Multi-Device Audio Playback Demo ===\n")
    
    # Create manager
    manager = AudioDeviceManager()
    
    # Discover devices
    devices = manager.discover_devices()
    if not devices:
        print("No audio devices found!")
        return
    
    # Test all devices
    test_results = manager.test_all_devices()
    working_devices = [d for d in devices if test_results.get(d.index, False)]
    
    if not working_devices:
        print("No working devices found!")
        return
    
    print(f"\nFound {len(working_devices)} working devices")
    
    # Create a test tone
    print("\nCreating test tone...")
    test_tone, sample_rate = manager.create_test_tone(duration=3.0, frequency=440.0)
    
    # Save test tone to file
    test_file = "/tmp/test_tone.wav"
    sf.write(test_file, test_tone, sample_rate)
    print(f"Test tone saved to: {test_file}")
    
    # Play on all devices
    print("\nPlaying test tone on all devices...")
    
    def playback_callback(device_index, status):
        device_name = next(d.name for d in devices if d.index == device_index)
        print(f"Device {device_index} ({device_name}): {status}")
    
    results = manager.play_on_all_devices(test_file, callback=playback_callback)
    
    # Wait for playback to complete
    print("\nWaiting for playback to complete...")
    time.sleep(4)
    
    # Show final status
    print("\nFinal device status:")
    status = manager.get_device_status()
    for device in devices:
        print(f"  {device.name}: {status.get(device.index, 'Unknown')}")
    
    # Clean up
    manager.stop_all_playback()
    
    # Remove test file
    try:
        os.remove(test_file)
    except:
        pass
    
    print("\nDemo completed!")


if __name__ == "__main__":
    main()
