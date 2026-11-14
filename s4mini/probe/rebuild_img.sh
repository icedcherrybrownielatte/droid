#!/bin/bash
# Rebuild kernel->uniloader->rec_xnu.img from the WSL trees, flash to recovery partition (needs Android adb root) and boot it.
set -e
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"
A=../../tools/platform-tools-dl/platform-tools/adb.exe
wsl -d Ubuntu -e bash -lc 'cd ~/xnu-j1/xnu && export B=$HOME/cctools/bin PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc HOST_CC=$HOME/cctools/bin/hostcc && . SETUP/setup.sh && make TARGET_CONFIGS="release arm MSM8930_SERRANO" MAKEJOBS=-j8 SDKROOT=$HOME/sdk/ios7 >~/xnu-build-last.log 2>&1; test -f BUILD/obj/RELEASE_ARM_MSM8930_SERRANO/mach_kernel && cp BUILD/obj/RELEASE_ARM_MSM8930_SERRANO/mach_kernel ~/uniloader/blob/Image && cd ~/uniloader && export ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- && make -j8 >/dev/null 2>&1 && cp uniLoader /mnt/c/Users/User/Desktop/Droid/s4mini/probe/uniLoader_xnu.bin'
python3 - <<'PY'
import struct,hashlib
d=open('../backup/recovery.img','rb').read(); hdr=bytearray(d[:2048]); page=2048
pad=lambda b: b+b'\0'*((-len(b))%page)
k=open('uniLoader_xnu.bin','rb').read(); r=b'\0'*2048
struct.pack_into('<I',hdr,8,len(k)); struct.pack_into('<I',hdr,16,len(r))
sha=hashlib.sha1()
for b in (k,r,b''): sha.update(b); sha.update(struct.pack('<I',len(b)))
hdr[576:608]=sha.digest().ljust(32,b'\0')
img=bytes(hdr)+pad(k)+pad(r)+b'SEANDROIDENFORCE'
assert len(img)<=10*1024*1024
open('rec_xnu.img','wb').write(img.ljust(10*1024*1024,b'\0'))
PY
$A root >/dev/null; sleep 3; $A wait-for-device
$A push rec_xnu.img /data/local/tmp/rec_xnu.img >/dev/null
$A shell "dd if=/data/local/tmp/rec_xnu.img of=/dev/block/platform/msm_sdcc.1/by-name/recovery bs=65536 2>/dev/null && sync && md5sum /dev/block/platform/msm_sdcc.1/by-name/recovery /data/local/tmp/rec_xnu.img"
