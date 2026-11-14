import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/sched_prim.c")
s = open(p).read()
a = "\tthread_dispatch(thread, self);\n\n\tself->continuation = self->parameter = NULL;\n"
assert a in s
nl = chr(92) + "n"
b = '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n\t{ static unsigned tcn; extern void printf(const char *, ...); if (tcn < 40U) { tcn++; printf("J1 tc %p cont=%p' + nl + '", self, continuation); } }\n#endif\n' + a
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
