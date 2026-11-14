import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/arm/machine_routines_asm.s")
s = open(p).read()
a = "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* DEBUG: no WFI on this port yet (suspect lost wakeups) - busy idle */\n    bx      lr\n#endif\n"
assert a in s
s = s.replace(a, "", 1)
open(p, "w").write(s)
print("ok")
