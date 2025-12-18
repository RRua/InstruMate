#!/bin/bash

# Function to kill the adb server
kill_adb_server() {
    echo "$(date): Killing ADB server..."
    adb kill-server
}

# Infinite loop to run the command every 2 hours
while true; do
    kill_adb_server
    sleep 2h  # Wait for 2 hours
done
