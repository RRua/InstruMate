#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <emulator-serial> <package-list-file>"
    exit 1
fi
EMULATOR_SERIAL=$1
PACKAGE_LIST_FILE=$2
if [ ! -f "$PACKAGE_LIST_FILE" ]; then
    echo "Error: Package list file '$PACKAGE_LIST_FILE' not found."
    exit 1
fi
while IFS= read -r pkg_name || [[ -n "$pkg_name" ]]; do
    if [[ -z "$pkg_name" || "$pkg_name" == \#* ]]; then
        continue
    fi
    #echo "Uninstalling package: $pkg_name"
    echo adb -s "$EMULATOR_SERIAL" uninstall "$pkg_name"
    #adb -s "$EMULATOR_SERIAL" uninstall "$pkg_name"
done < "$PACKAGE_LIST_FILE"
#echo "Uninstallation process completed."
