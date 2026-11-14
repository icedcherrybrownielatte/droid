set -e
cd /mnt/c/Users/User/Desktop/Droid/s4mini/probe
CF="-marm -march=armv7-a -mfloat-abi=soft -O1 -ffreestanding -nostdlib -fno-builtin -fno-stack-protector -fno-tree-loop-distribute-patterns -Wall"
G=arm-linux-gnueabi
# --- test build (QEMU virt) ---
$G-gcc -c -marm fake.S -o fake.o; $G-objcopy -O binary -j .text fake.o fake.bin
sed 's/0x80208000/0x40108000/' probe.ld > t.ld
$G-gcc $CF -DZSIZE=$(stat -c %s fake.bin) -DRAMB=0x40100000u -DMDP=0x50000000u -DSPTOP='"0x40103ff0"' -T t.ld -o t.elf probe.c 2>&1 | grep -v build-id || true
$G-objcopy -O binary t.elf t.bin; cat t.bin fake.bin > t_full.bin
python3 - <<PY
a=open("atags.bin","rb").read()
b=open("boot.bin","rb").read().ljust(0xF0100,b"\0")+a
b=b.ljust(0xF8000,b"\0")+open("t_full.bin","rb").read()
open("img.bin","wb").write(b)
PY
# --- real build ---
$G-gcc $CF -DZSIZE=$(stat -c %s zImage) -DSPTOP='"0x80203ff0"' -T probe.ld -o probe.elf probe.c 2>&1 | grep -v build-id || true
$G-objcopy -O binary probe.elf probe.bin
