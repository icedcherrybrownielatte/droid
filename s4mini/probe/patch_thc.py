import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/thread_call.c")
s = open(p).read()
a = "\t\t(*func)(param0, param1);\n"
assert a in s
b = "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n\t\t{ static unsigned thcn; extern void ios7m8930_hexN(unsigned int, unsigned int); thcn++; ios7m8930_hexN(22, (unsigned)func); ios7m8930_hexN(23, thcn); }\n#endif\n" + a
s = s.replace(a, b, 1)
open(p, "w").write(s)
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
s = s.replace(" ios7m8930_hexN(22, q[6] | (q[10] << 8)); ios7m8930_hexN(23, q[14]); }", " }", 1)
open(p, "w").write(s)
print("ok")
