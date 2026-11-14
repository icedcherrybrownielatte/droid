#!/bin/bash
# Writes the probe image to the boot partition (only boot; recovery untouched). Needs adb root.
set -e
export MSYS_NO_PATHCONV=1
A=../../tools/platform-tools-dl/platform-tools/adb.exe
B=/dev/block/platform/msm_sdcc.1/by-name/boot
cd "$(dirname "$0")"
$A root >/dev/null; sleep 3; $A wait-for-device
$A push boot_xnu.img /data/local/tmp/boot_xnu.img
want=$(sha256sum boot_xnu.img | cut -d' ' -f1)
have=$($A shell sha256sum /data/local/tmp/boot_xnu.img | cut -d' ' -f1)
[ "$want" = "$have" ] || { echo "push checksum mismatch"; exit 1; }
$A shell "dd if=/data/local/tmp/boot_xnu.img of=$B bs=65536 && sync"
echo "flashed; verify then reboot:"
$A shell "md5sum $B /data/local/tmp/boot_xnu.img"
