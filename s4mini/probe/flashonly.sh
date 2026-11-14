#!/bin/bash
# Full iteration (phone must be in TWRP):  rebuild XNU -> LZ4 -> uniloader -> boot img -> flash boot -> reboot -> photo -> wait for TWRP.
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
A=../../tools/platform-tools-dl/platform-tools/adb.exe
P=/dev/block/platform/msm_sdcc.1/by-name
wsl -d Ubuntu -e bash -lc 'cd ~/xnu-j1/xnu && export B=$HOME/cctools/bin PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc HOST_CC=$HOME/cctools/bin/hostcc && . SETUP/setup.sh && make TARGET_CONFIGS="release arm MSM8930_SERRANO" MAKEJOBS=-j8 SDKROOT=$HOME/sdk/ios7 >~/xnu-build-last.log 2>&1; if grep -qE ": error|Undefined symbols" ~/xnu-build-last.log; then grep -E ": error|Undefined symbols" -A2 ~/xnu-build-last.log | head -12; echo BUILD_FAILED; exit 3; fi; cd /mnt/c/Users/User/Desktop/Droid/s4mini/probe && cp ~/xnu-j1/xnu/BUILD/obj/RELEASE_ARM_MSM8930_SERRANO/mach_kernel mk_cur && cp mk_cur mk_strip && arm-apple-darwin11-strip -S -x mk_strip && python3 mklz4.py mk_strip mk_strip.lz4 && cd ~/uniloader && cp /mnt/c/Users/User/Desktop/Droid/s4mini/probe/mk_strip.lz4 blob/Image && touch arch/arm/start.S && export ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- && make -j8 >/dev/null 2>&1 && cp uniLoader /mnt/c/Users/User/Desktop/Droid/s4mini/probe/uniLoader_recfb.bin'
python3 pack_boot.py uniLoader_recfb.bin boot_recfb.img >/dev/null
$A push boot_recfb.img /data/local/tmp/b.img >/dev/null
$A shell "dd if=/data/local/tmp/b.img of=$P/boot bs=65536 2>/dev/null; sync; md5sum $P/boot" | cut -c1-32 > /tmp/flashed.md5
[ "$(cat /tmp/flashed.md5)" = "$(md5sum boot_recfb.img | cut -c1-32)" ] || { echo "FLASH VERIFY FAILED"; exit 1; }
$A reboot
echo FLASHED_OK
