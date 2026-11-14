import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
i = s.index("{ static unsigned int tbn;")
j = s.index("}", s.index("ios7m8930_hexN(20", i)) + 1
b = "{ static unsigned int tbn; unsigned int *f = (unsigned int *)__builtin_frame_address(0); unsigned int ret[6]; int k; for (k = 0; k < 6; k++) { ret[k] = 0; if (f && !((unsigned int)f & 3U) && (unsigned int)f > 0x80000000U) { ret[k] = f[1]; f = (unsigned int *)f[0]; } else f = 0; } ++tbn; ios7m8930_hexN(21, tbn); ios7m8930_hexN(20, ret[3]); ios7m8930_hexN(22, ret[4]); ios7m8930_hexN(23, ret[5]); }"
s = s[:i] + b + s[j:]
open(p,"w").write(s)
print("ok")
