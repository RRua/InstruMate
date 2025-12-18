#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <emulator_name>"
    exit 1
fi

EMULATOR_NAME="$1"
# -no-window
while true; do
    echo "Starting emulator $EMULATOR_NAME..."
    emulator -avd "$EMULATOR_NAME" -no-snapshot-save -no-snapshot-load -snapshot start-snap
    echo "Emulator $EMULATOR_NAME has stopped. Restarting..."
    sleep 5
done