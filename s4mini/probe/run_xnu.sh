#!/bin/bash
# Boot the XNU test image (recovery partition) from Android and photograph the screen.
cd "$(dirname "$0")/.."
A=tools/platform-tools-dl/platform-tools/adb.exe
$A reboot recovery
bash probe/shot.sh recon/cam/xnu_shot.png ${1:-25}
