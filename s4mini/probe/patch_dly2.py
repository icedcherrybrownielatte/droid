import os
root = os.path.expanduser("~/xnu-j1/xnu")
p = root + "/osfmk/arm/rtclock.c"
s = open(p).read()
i = s.index("                ios7m8930_hexN(20, (unsigned int)now);")
j = s.index("\n", s.index("ios7m8930_hexN(22, (unsigned int)deadline)", i))
s = s[:i] + s[j+1:]
open(p,"w").write(s)
p = root + "/osfmk/kern/clock.c"
s = open(p).read()
a = "\t\tmachine_delay_until(interval, deadline);\n"
assert a in s
b = """#if defined(BOARD_CONFIG_MSM8930_SERRANO)
		{ extern void ios7m8930_hexN(unsigned int, unsigned int);
		  ios7m8930_hexN(20, ((unsigned)ml_delay_should_spin(interval) << 8) | ((unsigned)get_preemption_level() << 4) | (unsigned)ml_get_interrupts_enabled());
		  ios7m8930_hexN(21, (unsigned)interval); ios7m8930_hexN(22, (unsigned)(interval >> 32)); }
#endif
""" + a
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
