import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/arm/machine_routines_asm.s")
s = open(p).read()
a = "    /* See if first we have power saving enabled. */\n"
assert a in s
b = "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* DEBUG: no WFI on this port yet (suspect lost wakeups) - busy idle */\n    bx      lr\n#endif\n" + a
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
