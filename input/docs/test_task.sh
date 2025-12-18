#!/bin/bash

# Define the function
reboot_devices() {
    echo "Killing emulators"
    adb -s emulator-5554 emu kill
    adb -s emulator-5556 emu kill
    adb -s emulator-5558 emu kill
    adb -s emulator-5560 emu kill
    adb -s emulator-5562 emu kill
}

reboot_devices() {
    echo "Killing emulators"
    adb -s emulator-5554 emu kill
    adb -s emulator-5556 emu kill
    adb -s emulator-5558 emu kill
    adb -s emulator-5560 emu kill
    adb -s emulator-5562 emu kill
    adb -s emulator-5564 emu kill
    adb -s emulator-5566 emu kill
    adb -s emulator-5568 emu kill
}

reboot_devices
adb kill-server
adb kill-server
adb kill-server
./venv/bin/python start.py -m healthcheck -AS /home/leandro/storage/dataset-test -o /home/leandro/storage/hc/dataset-test-hc-1 --recycle_emulator_with_kill --force
