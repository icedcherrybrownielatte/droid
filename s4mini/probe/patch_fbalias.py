import re
X="/home/user/xnu-j1/xnu/"
p=X+"osfmk/arm/locore.s"; s=open(p).read()
# 1) replace identity maps of 0x88100000/0x88200000 by VA alias 0xC0000000/0xC0100000
a=s.index("    LoadConstantToReg(0x402, r2)\n    LoadConstantToReg(0x88100000, r7)")
b=s.index("    LoadConstantToReg(0x02000000, r7)",a)
new='''    LoadConstantToReg(0x402, r2)
    /* VA 0xC0000000/0xC0100000 -> PA 0x88100000/0x88200000 (the PA range collides with the kernel linear map VA) */
    LoadConstantToReg(0x88100000, r7)
    orr     r8, r7, r2
    add     r5, r4, #0x3000
    str     r8, [r5]
    LoadConstantToReg(0x88200000, r7)
    orr     r8, r7, r2
    str     r8, [r5, #4]
'''
s=s[:a]+new+s[b:]
# 2) virtual-address mark macro for after the MMU is on
mv='''.macro MSM_MARKV idx
    LoadConstantToReg((0xC0000000 + 500*1620 + (\idx)*48), r2)
    mvn     r3, #0
    mov     r1, #16
.Lmsmmarkv\@:
    str     r3, [r2]
    str     r3, [r2, #4]
    str     r3, [r2, #8]
    str     r3, [r2, #12]
    str     r3, [r2, #16]
    str     r3, [r2, #20]
    str     r3, [r2, #24]
    str     r3, [r2, #28]
    add     r2, r2, #0x600
    add     r2, r2, #0x54
    subs    r1, r1, #1
    bne     .Lmsmmarkv\@
.endm
'''
s=s.replace("#else\n.macro MSM_MARK idx\n.endm\n#endif",mv+"#else\n.macro MSM_MARK idx\n.endm\n.macro MSM_MARKV idx\n.endm\n#endif",1)
s=s.replace("fix_boot_args_hack_for_bootkit:\n    MSM_MARK 2\n","fix_boot_args_hack_for_bootkit:\n    MSM_MARKV 2\n",1)
s=s.replace("    MSM_MARK 3\n    /* Boot to ARM init. */","    MSM_MARKV 3\n    /* Boot to ARM init. */",1)
open(p,"w").write(s)
# 3) arm_vm_init: seed alias sections instead of 0x881/0x882
p=X+"osfmk/arm/arm_vm_init.c"; s=open(p).read()
s=s.replace("        l1[0x881] = 0x88100000u | 0xC02;\n        l1[0x882] = 0x88200000u | 0xC02;\n","        l1[0xC00] = 0x88100000u | 0xC02;\n        l1[0xC01] = 0x88200000u | 0xC02;\n",1)
open(p,"w").write(s)
# 4) C markers use the alias
p=X+"pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
s=s.replace("volatile unsigned char *fb=(volatile unsigned char *)0x88100000u;\n static const unsigned char col","volatile unsigned char *fb=(volatile unsigned char *)0xC0000000u;\n static const unsigned char col",1)
open(p,"w").write(s)
print("ok")
