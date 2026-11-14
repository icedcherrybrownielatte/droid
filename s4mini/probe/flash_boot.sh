#!/bin/bash
# usage: flash_boot.sh <image>   (Android adb root; writes the BOOT partition only; never recovery)
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
A=../../tools/platform-tools-dl/platform-tools/adb.exe
if [ "$($A get-state 2>/dev/null)" = device ]; then $A root >/dev/null 2>&1; sleep 3; fi; $A wait-for-device
$A push "$1" /data/local/tmp/boot_new.img >/dev/null
want=$(md5sum "$1" | cut -c1-32)
$A shell "dd if=/data/local/tmp/boot_new.img of=/dev/block/platform/msm_sdcc.1/by-name/boot bs=65536 2>/dev/null; sync; md5sum /dev/block/platform/msm_sdcc.1/by-name/boot" | cut -c1-32 | grep -q "$want" && echo "boot flashed OK ($want)" || { echo "VERIFY FAILED"; exit 1; }
