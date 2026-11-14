p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
macro='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
/* White bar n (5x8 px) at y=930 in the bootloader scanout; clobbers r1-r3. */
.macro MSM_MARK n
    LoadConstantToReg((0x88100000 + 930*1620 + (\n)*32), r2)
    mvn     r3, #0
    mov     r1, #8
.Lmsmmark\@:
    str     r3, [r2]
    str     r3, [r2, #4]
    str     r3, [r2, #8]
    str     r3, [r2, #12]
    add     r2, r2, #1620
    subs    r1, r1, #1
    bne     .Lmsmmark\@
.endm
#else
.macro MSM_MARK n
.endm
#endif

'''
s=s.replace("EnterARM(_start)\n",macro+"EnterARM(_start)\n",1)
s=s.replace("    cpsid   if\n\n    /* If MMU is initialized","    cpsid   if\n    MSM_MARK 0\n\n    /* If MMU is initialized",1)
s=s.replace("    /* Start MMU. */\n","    MSM_MARK 1\n    /* Start MMU. */\n",1)
s=s.replace("fix_boot_args_hack_for_bootkit:\n","fix_boot_args_hack_for_bootkit:\n    MSM_MARK 2\n",1)
s=s.replace("    /* Boot to ARM init. */\n    bx      lr\n","    MSM_MARK 3\n    /* Boot to ARM init. */\n    bx      lr\n",1)
open(p,"w").write(s); print(s.count("MSM_MARK"))
