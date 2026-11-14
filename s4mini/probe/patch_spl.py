import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/arm/machine_routines_asm.s")
s = open(p).read()
a = "EnterARM(ml_set_interrupts_enabled)\n    mrs     r2, cpsr\n"
assert a in s
b = """EnterARM(ml_set_interrupts_enabled)
#if defined(BOARD_CONFIG_MSM8930_SERRANO)
    /* DEBUG: show last caller that masked (row 19) / unmasked (row 18) interrupts */
    stmfd   sp!,{r0-r3,r12,lr}
    mov     r1, lr
    cmp     r0, #0
    moveq   r0, #19
    movne   r0, #18
    blx     _ios7m8930_hexN
    ldmfd   sp!,{r0-r3,r12,lr}
#endif
    mrs     r2, cpsr
"""
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
