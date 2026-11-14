import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/clock.c")
s = open(p).read()
a = "ios7m8930_hexN(21, (unsigned)interval); ios7m8930_hexN(22, (unsigned)(interval >> 32)); }"
assert a in s
b = "ios7m8930_hexN(21, (unsigned)interval);\n\t\t  { unsigned int *f = (unsigned int *)__builtin_frame_address(0); unsigned int r[5]; int k; static const unsigned rows[5] = {22,23,15,16,17}; for (k = 0; k < 5; k++) { r[k] = 0; if (f && !((unsigned int)f & 3U) && (unsigned int)f > 0x80000000U) { r[k] = f[1]; f = (unsigned int *)f[0]; } else f = 0; } for (k = 1; k < 5; k++) ios7m8930_hexN(rows[k-1], r[k]); } }"
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
