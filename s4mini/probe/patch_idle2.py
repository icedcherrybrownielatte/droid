import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/arm/machine_routines_asm.s")
s = open(p).read()
a = "    /* See if first we have power saving enabled. */\n"
assert a in s and "busy idle" not in s
b = "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* DEBUG: WFI wakeups look lost on this port; busy idle with IRQs open instead */\n    cpsie   i\n    nop\n    nop\n    nop\n    nop\n    bx      lr\n#endif\n" + a
s = s.replace(a, b, 1)
open(p, "w").write(s)
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
i = s.index("\t\t{ extern void ios7m8930_sched_stats(unsigned *);")
j = s.index("\n", i)
s = s[:i] + s[j+1:]
open(p, "w").write(s)
print("ok")
