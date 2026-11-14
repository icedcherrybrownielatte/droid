import os
root = os.path.expanduser("~/xnu-j1/xnu")
p = root + "/pexpert/arm/pe_msm8930_serrano.c"
s = open(p).read()
if "ios7m8930_irqret" not in s:
    s += "\n/* DEBUG: show the frame an IRQ is about to return to (pc, cpsr) */\nvoid ios7m8930_irqret(unsigned int *f){ m8930_hexrow(13,f[15]); m8930_hexrow(14,f[16]); }\n"
open(p, "w").write(s)

p = root + "/osfmk/arm/traps_lo.s"
s = open(p).read()
a = "restart_kernel_execution:\n"
assert a in s
if "_ios7m8930_irqret" not in s:
    s = s.replace(a, a + "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    mov     r0, r5\n    blx     _ios7m8930_irqret\n#endif\n", 1)
open(p, "w").write(s)

p = root + "/osfmk/kern/ast.c"
s = open(p).read()
a = "\tios7m8930_hexN(13,((unsigned)reasons<<16)|(unsigned)*myast);\n"
if a in s:
    s = s.replace(a, "", 1)
open(p, "w").write(s)

p = root + "/pexpert/arm/msm8930_timer.c"
s = open(p).read()
i = s.find("\t\t{ extern void ios7m8930_hexN(unsigned int,unsigned int); uint32_t *cx=")
if i >= 0:
    j = s.index("\n", i)
    s = s[:i] + s[j+1:]
open(p, "w").write(s)
print("irqret patched")
