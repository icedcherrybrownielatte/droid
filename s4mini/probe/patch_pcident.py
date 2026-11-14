p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
old="    LoadConstantToReg(0x88200402, r8)\n    str     r8, [r5, #4]\n#endif\n"
assert old in s
new='''    LoadConstantToReg(0x88200402, r8)
    str     r8, [r5, #4]
    /* The SDRAM linear map (VA 0x80000000+) covers VA index 0xA61..: it just overwrote the identity
     * section of the code we are executing from (PA 0xA61xxxxx). Put it back (and the next one). */
    mov     r7, pc, lsr#20
    add     r5, r4, r7, lsl#2
    mov     r7, r7, lsl#20
    orr     r8, r7, r6
    str     r8, [r5]
    add     r7, r7, #0x100000
    orr     r8, r7, r6
    str     r8, [r5, #4]
#endif
'''
s=s.replace(old,new,1)
open(p,"w").write(s); print("ok")
