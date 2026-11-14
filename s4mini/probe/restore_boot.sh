#!/bin/bash
# Restores the original boot partition from the verified backup.
set -e
export MSYS_NO_PATHCONV=1
A=../../tools/platform-tools-dl/platform-tools/adb.exe
B=/dev/block/platform/msm_sdcc.1/by-name/boot
cd "$(dirname "$0")"
$A wait-for-device
$A push ../backup/boot.img /data/local/tmp/boot_orig.img
$A shell "dd if=/data/local/tmp/boot_orig.img of=$B bs=65536 && sync"
$A shell "md5sum $B /data/local/tmp/boot_orig.img"
