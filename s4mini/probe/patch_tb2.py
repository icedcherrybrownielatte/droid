import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
a = "{ static unsigned int tbn; ++tbn; ios7m8930_hexN(20, (unsigned int)v); ios7m8930_hexN(21, tbn); }"
assert a in s
b = "{ static unsigned int tbn; unsigned int *fp0 = (unsigned int *)__builtin_frame_address(0); unsigned int *fp1 = (unsigned int *)fp0[0]; ++tbn; ios7m8930_hexN(21, tbn); ios7m8930_hexN(22, (unsigned int)__builtin_return_address(0)); ios7m8930_hexN(23, fp1 ? fp1[1] : 0); ios7m8930_hexN(20, fp1 && fp1[0] ? ((unsigned int *)fp1[0])[1] : 0); }"
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
