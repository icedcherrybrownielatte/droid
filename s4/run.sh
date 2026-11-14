#!/bin/bash
# S4: flash stage3/boot_xnu.img, boot it, pull last_kmsg into stage3/lastk<N>.txt. A return in < 100 s is
# uniLoader's safety bounce (stale marker): reboot once more. Usage: run.sh <N>
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1
A=../tools/platform-tools-dl/platform-tools/adb.exe
S=4d0023254b106097
waitback() { local t0=$1 i; sleep 10; for i in $(seq 1 160); do $A devices | grep -q "$S	recovery" && break; sleep 3; [ $((i % 20)) -eq 0 ] && { $A kill-server >/dev/null 2>&1; $A start-server >/dev/null 2>&1; }; done; echo $(( $(date +%s) - t0 )); }
NOREBOOT=1 bash flash_boot.sh stage3/boot_xnu.img || exit 1
for try in 1 2; do
  T0=$(date +%s); $A -s $S reboot; DT=$(waitback $T0)
  echo "try $try: back after $DT s"
  [ "$DT" -ge 100 ] && break
done
sleep 3
$A -s $S shell 'echo 0 > /sys/class/backlight/panel/brightness; echo 1 > /sys/class/graphics/fb0/blank; cat /proc/last_kmsg' > stage3/lastk$1.txt
wc -c stage3/lastk$1.txt
