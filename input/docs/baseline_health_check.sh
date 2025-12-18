#!/bin/bash

# Define the function
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
    sleep 150
}


health_check() {
  local min=$1
  local max=$2
  local tag=$3
  local dest_dir=$4
  local dataset_dir=$5
  echo "Health checking from ${min} to ${max} with tag ${tag} saving to ${dest_dir} using dataset ${dataset_dir}"
  if [ "$min" -gt "$max" ]; then
    echo "Error: min should be less than or equal to max."
    return 1
  fi
  for ((i = min; i <= max; i++)); do
    reboot_devices
    adb kill-server
    adb kill-server
    adb kill-server
    echo "Producing: dataset-${tag}-${i}"
    ./venv/bin/python start.py -m healthcheck -AS "${dataset_dir}" -o "${dest_dir}/dataset-${tag}-${i}" --recycle_emulator_with_kill --force  2>&1 | tee "/tmp/log-${tag}-${i}.log"
  done
}


# Check if exactly 5 arguments are provided
if [ $# -ne 5 ]; then
  echo "Usage: $0 <min> <max> <tag> <dest-dir> <dataset-dir>"
  exit 1
fi

# Call the create_files function with the provided arguments
health_check "$1" "$2" "$3" "$4" "$5"
