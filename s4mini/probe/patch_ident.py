p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
# generic macro with base
mb='''.macro MSM_MARKB idx, base
    LoadConstantToReg(((\base) + 500*1620 + (\idx)*48), r2)
    mvn     r3, #0
    mov     r1, #16
.Lmsmmarkb\@:
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
    bne     .Lmsmmarkb\@
.endm
'''
s=s.replace("#else\n.macro MSM_MARK idx\n.endm\n.macro MSM_MARKV idx\n.endm\n#endif",mb+"#else\n.macro MSM_MARK idx\n.endm\n.macro MSM_MARKV idx\n.endm\n.macro MSM_MARKB idx, base\n.endm\n#endif",1)
# move identity sections AFTER the SDRAM map loop: add block before MSM_MARK 1
ident='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
    /* identity sections for the scanout (written after the SDRAM map loop so they survive) */
    LoadConstantToReg(0x402, r2)
    LoadConstantToReg(0x88100000, r7)
    mov     r5, r4
    add     r5, r5, #0x2000
    add     r5, r5, #0x400
    add     r5, r5, #0x400
    add     r5, r5, #0x400
    add     r5, r5, #0x400
    add     r5, r5, #0x4
    orr     r8, r7, r2
    LoadConstantToReg(0x88100000, r7)
    mov     r7, r7, lsr#20
    add     r5, r4, r7, lsl#2
    orr     r8, r8, #0
    LoadConstantToReg(0x88100402, r8)
    str     r8, [r5]
    LoadConstantToReg(0x88200402, r8)
    str     r8, [r5, #4]
#endif
'''
s=s.replace("    MSM_MARK 1\n    /* Page-table","%s    MSM_MARK 1\n    /* Page-table"%ident,1)
s=s.replace("    isb     sy\n\n    /*\n     * Hopefully, if we got here","    isb     sy\n    MSM_MARKB 2, 0x88100000\n\n    /*\n     * Hopefully, if we got here",1)
s=s.replace("fix_boot_args_hack_for_bootkit:\n    MSM_MARKV 2\n","fix_boot_args_hack_for_bootkit:\n    MSM_MARKB 3, 0x88100000\n    MSM_MARKB 4, 0xC0000000\n",1)
s=s.replace("    MSM_MARKV 3\n    /* Boot to ARM init. */","    MSM_MARKB 5, 0x88100000\n    /* Boot to ARM init. */",1)
open(p,"w").write(s); print(s.count("MSM_MARKB"))
