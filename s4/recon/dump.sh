#!/bin/bash
# S4 GT-I9500 hardware recon over adb (read-only). Device pinned by serial.
cd "$(dirname "$0")"
A=../../tools/platform-tools-dl/platform-tools/adb.exe
S=4d0023254b106097
export MSYS_NO_PATHCONV=1
run() { timeout 60 $A -s $S shell "$2" > "$1.txt" 2>&1; echo "$1 $(wc -c < "$1.txt")"; }
run getprop "getprop"
run cpuinfo "cat /proc/cpuinfo"
run iomem "cat /proc/iomem"
run interrupts "cat /proc/interrupts"
run cmdline "cat /proc/cmdline"
run uname "uname -a"
run meminfo "cat /proc/meminfo"
run byname "ls -l /dev/block/platform/*/by-name/ /dev/block/by-name/ 2>/dev/null"
run partitions "cat /proc/partitions"
run dmesg "dmesg"
run fb0 "for f in name virtual_size bits_per_pixel stride modes; do echo \$f: \$(cat /sys/class/graphics/fb0/\$f 2>/dev/null); done"
run input "cat /proc/bus/input/devices"
run i2c "for d in /sys/bus/i2c/devices/*; do echo \$d \$(cat \$d/name 2>/dev/null); done"
run config "zcat /proc/config.gz"
run lastkmsg "cat /proc/last_kmsg 2>/dev/null; ls -la /sys/fs/pstore 2>/dev/null"
run devtree "ls /proc/device-tree 2>/dev/null | head; ls /sys/firmware 2>/dev/null"
run gpio "cat /sys/kernel/debug/gpio 2>/dev/null | head -400"
run clk "cat /sys/kernel/debug/clock/clock_summary 2>/dev/null | head -300; ls /sys/kernel/debug 2>/dev/null"
run regulators "for r in /sys/class/regulator/regulator.*; do echo \$r \$(cat \$r/name 2>/dev/null) \$(cat \$r/state 2>/dev/null) \$(cat \$r/microvolts 2>/dev/null); done"
run backlight "ls /sys/class/backlight /sys/class/lcd 2>/dev/null; cat /sys/class/backlight/*/brightness /sys/class/backlight/*/max_brightness 2>/dev/null; cat /sys/class/lcd/*/lcd_type 2>/dev/null"
run cpufreq "for c in /sys/devices/system/cpu/cpu*/cpufreq; do echo \$c \$(cat \$c/scaling_cur_freq \$c/cpuinfo_max_freq 2>/dev/null); done; cat /sys/devices/system/cpu/online"
