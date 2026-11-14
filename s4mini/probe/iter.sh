#!/bin/bash
# Full iteration (phone must be in TWRP):  rebuild XNU -> LZ4 -> uniloader -> boot img -> flash boot -> reboot -> photo -> wait for TWRP.
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
A=../../tools/platform-tools-dl/platform-tools/adb.exe
P=/dev/block/platform/msm_sdcc.1/by-name
wsl -d Ubuntu -e bash -lc 'cd ~/xnu-j1/xnu && export B=$HOME/cctools/bin PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc HOST_CC=$HOME/cctools/bin/hostcc && . SETUP/setup.sh && make TARGET_CONFIGS="release arm MSM8930_SERRANO" MAKEJOBS=-j8 SDKROOT=$HOME/sdk/ios7 >~/xnu-build-last.log 2>&1; if grep -qE ": error|Undefined symbols" ~/xnu-build-last.log; then grep -E ": error|Undefined symbols" -A2 ~/xnu-build-last.log | head -12; echo BUILD_FAILED; exit 3; fi; cd /mnt/c/Users/User/Desktop/Droid/s4mini/probe && cp ~/xnu-j1/xnu/BUILD/obj/RELEASE_ARM_MSM8930_SERRANO/mach_kernel mk_cur && cp mk_cur mk_strip && arm-apple-darwin11-strip -S -x mk_strip && python3 mklz4.py mk_strip mk_strip.lz4 && cd ~/uniloader && cp /mnt/c/Users/User/Desktop/Droid/s4mini/probe/mk_strip.lz4 blob/Image && touch arch/arm/start.S && export ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- && make -j8 >/dev/null 2>&1 && cp uniLoader /mnt/c/Users/User/Desktop/Droid/s4mini/probe/uniLoader_recfb.bin'
# refuse to flash a kernel identical to the last flashed one (an edit that did not apply); FORCE=1 overrides
# fingerprint of the sources (the kernel binary embeds its build time, so its md5 always changes)
NEWSUM=$(wsl -d Ubuntu -e bash -c 'for d in ~/xnu-j1/xnu ~/uniloader; do cd $d && git diff HEAD && git ls-files -o --exclude-standard | grep -v -E "^BUILD/|\.o$|\.d$" | sort | xargs -r cat; done | md5sum' | cut -c1-32)
if [ -z "$FORCE" ] && [ -f last_flashed_kernel.md5 ] && [ "$NEWSUM" = "$(cat last_flashed_kernel.md5)" ]; then echo "NO_CHANGE: kernel identical to last flashed build, not flashing (FORCE=1 to override)"; exit 4; fi
python3 pack_boot.py uniLoader_recfb.bin boot_recfb.img >/dev/null
$A push boot_recfb.img /data/local/tmp/b.img >/dev/null
$A shell "dd if=/data/local/tmp/b.img of=$P/boot bs=65536 2>/dev/null; sync; md5sum $P/boot" | cut -c1-32 > /tmp/flashed.md5
[ "$(cat /tmp/flashed.md5)" = "$(md5sum boot_recfb.img | cut -c1-32)" ] || { echo "FLASH VERIFY FAILED"; exit 1; }
echo "$NEWSUM" > last_flashed_kernel.md5
$A reboot
sleep ${1:-14}
# photo / wait phase ends early as soon as the phone is back in TWRP (adb "recovery")
intwrp() { $A devices | grep -q recovery; }
if [ -z "$NOSNAP" ]; then (cd ../../iphonecontrol && timeout 60 python cleandcim.py 2>&1 | tail -3); for n in $(seq 1 ${2:-1}); do intwrp && break; (cd ../../iphonecontrol && python snap.py --out photos 2>&1 | tail -1); [ $n -lt ${2:-1} ] && sleep ${3:-6}; done; else for n in $(seq 1 $(( ${2:-1} * ${3:-6} / 5 ))); do intwrp && break; sleep 5; done; fi
for i in $(seq 1 40); do sleep 5; $A devices | grep -q recovery && { echo "back in TWRP"; break; }; done
