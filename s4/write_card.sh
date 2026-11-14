#!/bin/bash
# S4 GT-I9500: back up SYSTEM (mmcblk0p20) to backup/SYSTEM.img.gz, then write ../ipsw_x/card.img into it and verify.
# User chose SYSTEM p20 for the iOS disk image (2026-11-14). Never touches RECOVERY.
set -e
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1
A=../tools/platform-tools-dl/platform-tools/adb.exe
S=4d0023254b106097
IMG=../ipsw_x/card.img
TGT=$($A -s $S shell "readlink -f /dev/block/platform/dw_mmc.0/by-name/SYSTEM" | tr -d '\r')
[ "$TGT" = "/dev/block/mmcblk0p20" ] || { echo "SYSTEM resolves to '$TGT' - abort"; exit 1; }
$A -s $S shell "umount /system 2>/dev/null; umount /system_root 2>/dev/null; true"
if [ ! -s backup/SYSTEM.img.gz ]; then
  echo "backing up $TGT ..."
  $A -s $S exec-out "dd if=$TGT bs=4194304 2>/dev/null" | gzip -1 > backup/SYSTEM.img.gz.part
  mv backup/SYSTEM.img.gz.part backup/SYSTEM.img.gz
  ls -la backup/SYSTEM.img.gz
fi
SZ=$(stat -c %s $IMG); WANT=$(md5sum $IMG | cut -c1-32)
echo "pushing card.img ($SZ bytes, md5 $WANT) ..."
$A -s $S push $IMG /data/local/tmp/card.img
GOT=$($A -s $S shell "md5sum /data/local/tmp/card.img" | cut -c1-32)
[ "$GOT" = "$WANT" ] || { echo "push md5 mismatch $GOT"; exit 2; }
echo "writing $TGT ..."
$A -s $S shell "dd if=/data/local/tmp/card.img of=$TGT bs=4194304 2>&1 | tail -1; sync"
GOT=$($A -s $S shell "dd if=$TGT bs=$((SZ/16)) count=16 2>/dev/null | md5sum" | cut -c1-32)
[ "$GOT" = "$WANT" ] || { echo "PARTITION VERIFY FAILED $GOT"; exit 3; }
$A -s $S shell "rm /data/local/tmp/card.img"
echo "CARD_OK $TGT md5 $WANT"
