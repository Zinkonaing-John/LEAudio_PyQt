#!/usr/bin/env python3
"""
Multi-Device Audio Launcher
Simple launcher script for the multi-device audio system.
"""

import sys
import os
import subprocess


def main():
    """Main launcher function."""
    print("=== Multi-Device Audio System ===")
    print("Choose an option:")
    print("1. GUI Interface (Recommended)")
    print("2. Command Line Interface")
    print("3. Demo Script")
    print("4. List Devices")
    print("5. Test All Devices")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (0-5): ").strip()
            
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                print("Starting GUI interface...")
                subprocess.run([sys.executable, "multi_device_gui.py"])
            elif choice == "2":
                print("Starting CLI interface...")
                print("Usage examples:")
                print("  python multi_device_cli.py --list-devices")
                print("  python multi_device_cli.py --test-devices")
                print("  python multi_device_cli.py your_audio_file.wav")
                break
            elif choice == "3":
                print("Running demo script...")
                subprocess.run([sys.executable, "multi_device_demo.py"])
            elif choice == "4":
                print("Listing devices...")
                subprocess.run([sys.executable, "multi_device_cli.py", "--list-devices"])
            elif choice == "5":
                print("Testing all devices...")
                subprocess.run([sys.executable, "multi_device_cli.py", "--test-devices"])
            else:
                print("Invalid choice. Please enter 0-5.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

