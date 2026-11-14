#!/bin/bash
# Run while the phone is in TWRP recovery (adb). Restores stock boot, puts the XNU test image in the RECOVERY partition.
# After that: normal boot = Android; `adb reboot recovery` = XNU test. Original recovery: ../backup/recovery.img
set -e
export MSYS_NO_PATHCONV=1
A=../../tools/platform-tools-dl/platform-tools/adb.exe
P=/dev/block/platform/msm_sdcc.1/by-name
cd "$(dirname "$0")"
$A push ../backup/boot.img /data/local/tmp/boot_orig.img
$A push rec_xnu.img /data/local/tmp/rec_xnu.img
$A shell "dd if=/data/local/tmp/boot_orig.img of=$P/boot bs=65536 && dd if=/data/local/tmp/rec_xnu.img of=$P/recovery bs=65536 && sync"
$A shell "md5sum $P/boot /data/local/tmp/boot_orig.img $P/recovery /data/local/tmp/rec_xnu.img"
