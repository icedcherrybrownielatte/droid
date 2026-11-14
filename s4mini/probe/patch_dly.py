import os
root = os.path.expanduser("~/xnu-j1/xnu")
p = root + "/pexpert/arm/msm8930_timer.c"
s = open(p).read()
i = s.index("\t{ static unsigned int tbn;")
j = s.index("\n", i)
s = s[:i] + s[j+1:]
open(p,"w").write(s)
p = root + "/osfmk/arm/rtclock.c"
s = open(p).read()
a = "    do {\n        cpu_pause();\n        now = mach_absolute_time();\n    } while (now < deadline);\n"
assert a in s
b = """#if defined(BOARD_CONFIG_MSM8930_SERRANO)
    {
        extern void ios7m8930_hexN(unsigned int, unsigned int);
        unsigned int spins = 0;
        do {
            cpu_pause();
            now = mach_absolute_time();
            if (!(++spins & 0x3ffU)) {
                ios7m8930_hexN(20, (unsigned int)now); ios7m8930_hexN(21, (unsigned int)(now >> 32));
                ios7m8930_hexN(22, (unsigned int)deadline); ios7m8930_hexN(23, (unsigned int)(deadline >> 32));
            }
        } while (now < deadline);
    }
#else
""" + a + "#endif\n"
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
