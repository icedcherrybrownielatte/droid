import os
root = os.path.expanduser("~/xnu-j1/xnu/")
nl = chr(92) + "n"
p = root + "osfmk/arm/cswitch.s"
s = open(p).read()
a = "    ldr     r8, [r12, MACHINE_THREAD_CPU_DATA]\n    ldr     r5, [r8, CPU_PENDING_AST]\n\n    cmp     r5, #0\n    beq     return_to_user\n"
assert a in s
b = "    ldr     r8, [r12, MACHINE_THREAD_CPU_DATA]\n    ldr     r5, [r8, CPU_PENDING_AST]\n#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    mov     r0, r5\n    mov     r1, r12\n    blx     _ios7m8930_tbr\n    LoadThreadRegister(r12)\n#endif\n\n    cmp     r5, #0\n    beq     return_to_user\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
p = root + "pexpert/arm/pe_msm8930_serrano.c"
s = open(p).read()
if "ios7m8930_tbr" not in s:
    s += '\n/* DEBUG: user-thread return path trace */\nextern int printf(const char *, ...);\nvoid ios7m8930_tbr(unsigned int pend, void *thr){ static unsigned n; if (n < 16U) { n++; printf("J1 tbr pend=%x thr=%p' + nl + '", pend, thr); } }\n'
open(p, "w").write(s)
p = root + "osfmk/kern/startup.c"
s = open(p).read()
a = "\tMARKI(528);\n"
assert a in s
s = s.replace(a, a + '\t{ extern int printf(const char *, ...); printf("J1 ks 528' + nl + '"); }\n', 1)
a = "\tMARKI(531);\n"
assert a in s
s = s.replace(a, a + '\t{ extern int printf(const char *, ...); printf("J1 ks 531' + nl + '"); }\n', 1)
open(p, "w").write(s)
print("ok")
