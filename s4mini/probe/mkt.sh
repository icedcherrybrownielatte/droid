set -e
cd /mnt/c/Users/User/Desktop/Droid/s4mini/probe
arm-linux-gnueabi-gcc -c -marm fake.S -o fake.o
arm-linux-gnueabi-objcopy -O binary -j .text fake.o fake.bin
ZS=$(stat -c %s fake.bin)
sed 's/0x80208000/0x40008000/' probe.ld > t.ld
arm-linux-gnueabi-gcc -marm -march=armv7-a -O1 -ffreestanding -nostdlib -fno-builtin -fno-stack-protector -fno-tree-loop-distribute-patterns -DZSIZE=$ZS -DRAMB=0x40000000u -DMDP=0x08000000u -T t.ld -o t.elf probe.c 2>/dev/null
arm-linux-gnueabi-objcopy -O binary t.elf t.bin
cat t.bin fake.bin > t_full.bin
# atags at 0x40000100: CORE, MEM, CMDLINE(old, long), NONE
python3 - <<'PY'
import struct
old=b"androidboot.hardware=qcom user_debug=22 cordon=26cc284c connie=GT-I9190_OPEN sec_log=0x80000@0x88400008 sec_debug.enable=0 loglevel=4\0"
old+=b"\0"*((-len(old))%4)
t=struct.pack('<II',2,0x54410001)+struct.pack('<IIII',4,0x54410002,0x10000000,0x40000000)
t+=struct.pack('<II',2+len(old)//4,0x54410009)+old+struct.pack('<II',0,0)
open('/mnt/c/Users/User/Desktop/Droid/s4mini/probe/atags.bin','wb').write(t)
PY
