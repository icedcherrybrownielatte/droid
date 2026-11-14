p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
a=s.index("#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* identity sections for the scanout")
b=s.index("#endif\n",a)+len("#endif\n")
clean='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
    /* identity sections for the scanout, written after the SDRAM map loop so they survive */
    LoadConstantToReg(0x88100000, r7)
    mov     r7, r7, lsr#20
    add     r5, r4, r7, lsl#2
    LoadConstantToReg(0x88100402, r8)
    str     r8, [r5]
    LoadConstantToReg(0x88200402, r8)
    str     r8, [r5, #4]
#endif
'''
s=s[:a]+clean+s[b:]
open(p,"w").write(s); print("ok")
