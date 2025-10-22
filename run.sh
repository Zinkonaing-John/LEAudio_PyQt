#!/bin/bash
# Run script for LEAudio PyQt application
# This script runs the application with proper Python and display setup

cd /home/zinko/Documents/LEAudio_PyQt

# Check if DISPLAY is set, if not try to set it
if [ -z "$DISPLAY" ]; then
    echo "No DISPLAY set. Trying to start Xvfb..."
    # Try to start a virtual display
    export DISPLAY=:99
    Xvfb :99 -screen 0 1024x768x24 &
    XVFB_PID=$!
    sleep 2
    echo "Started Xvfb with PID $XVFB_PID"
fi

# Use system Python (not 3.13) to access PyQt5
/usr/bin/python3 main.py

# Clean up Xvfb if we started it
if [ ! -z "$XVFB_PID" ]; then
    kill $XVFB_PID 2>/dev/null
fi
