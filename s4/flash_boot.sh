#!/bin/bash
# S4 GT-I9500: flash a boot image into BOOT (mmcblk0p9) ONLY, verify, reboot, and time the return to TWRP.
# Usage: flash_boot.sh <boot.img> [max_wait_s]
# Safety: device pinned by serial; refuses unless by-name/BOOT resolves to mmcblk0p9; never touches RECOVERY.
set -e
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1
A=../tools/platform-tools-dl/platform-tools/adb.exe
S=4d0023254b106097
IMG="$1"; WAIT="${2:-240}"
[ -f "$IMG" ] || { echo "no image $IMG"; exit 1; }
[ "$(stat -c %s "$IMG")" -le 8388608 ] || { echo "image > 8 MiB"; exit 1; }
$A -s $S get-state >/dev/null 2>&1 || { echo "S4 $S not connected"; exit 1; }
MODE=$($A devices | grep $S | awk '{print $2}')
echo "S4 state: $MODE"
TGT=$($A -s $S shell "readlink -f /dev/block/platform/dw_mmc.0/by-name/BOOT" | tr -d '\r')
[ "$TGT" = "/dev/block/mmcblk0p9" ] || { echo "BOOT resolves to '$TGT', expected /dev/block/mmcblk0p9 - abort"; exit 1; }
$A -s $S push "$IMG" /data/local/tmp/s4boot.img >/dev/null 2>&1 || $A -s $S push "$IMG" /tmp/s4boot.img >/dev/null
SRC=/data/local/tmp/s4boot.img; $A -s $S shell "[ -f $SRC ]" || SRC=/tmp/s4boot.img
$A -s $S shell "dd if=/dev/zero of=$TGT bs=1048576 count=8 2>/dev/null; dd if=$SRC of=$TGT bs=1048576 2>/dev/null; sync"
SZ=$(stat -c %s "$IMG")
GOT=$($A -s $S shell "dd if=$TGT bs=$SZ count=1 2>/dev/null | md5sum" | cut -c1-32)
WANT=$(md5sum "$IMG" | cut -c1-32)
[ "$GOT" = "$WANT" ] || { echo "FLASH VERIFY FAILED $GOT != $WANT"; exit 2; }
echo "flashed $IMG ($SZ bytes) md5 $WANT"
[ -n "$NOREBOOT" ] && exit 0
T0=$(date +%s)
$A -s $S reboot
sleep 8
for i in $(seq 1 $((WAIT / 3))); do
  st=$($A devices | grep $S | awk '{print $2}')
  if [ -n "$st" ]; then echo "back after $(( $(date +%s) - T0 )) s in state: $st"; sleep 4; $A -s $S shell "echo 0 > /sys/class/backlight/panel/brightness; echo 1 > /sys/class/graphics/fb0/blank" >/dev/null 2>&1; echo "screen blanked"; exit 0; fi
  sleep 3
  [ $((i % 20)) -eq 0 ] && { $A kill-server >/dev/null 2>&1; $A start-server >/dev/null 2>&1; }   # stale adb server missed the device once
done
echo "NOT BACK after $WAIT s"; exit 3
