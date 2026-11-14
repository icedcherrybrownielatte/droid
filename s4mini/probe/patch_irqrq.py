import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
a = "\t\tios7m8930_hexN(17, 0x40000000U|m_irqs);\n"
assert a in s
b = a + "\t\t{ extern void ios7m8930_sched_stats(unsigned *); unsigned q[20]; ios7m8930_sched_stats(q); ios7m8930_hexN(15, q[0]); ios7m8930_hexN(16, (q[8] << 16) | (q[12] & 0xffffU)); ios7m8930_hexN(20, q[9]); ios7m8930_hexN(21, q[11]); ios7m8930_hexN(22, q[6] | (q[10] << 8)); ios7m8930_hexN(23, q[14]); }\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
