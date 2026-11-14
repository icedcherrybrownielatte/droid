import os
p = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/bsd_init.c")
s = open(p).read()
a = "#define MARKI(n) ios7m8930_mark(n)\n"
assert a in s
nl = chr(92) + "n"
b = '#define MARKI(n) do { ios7m8930_mark(n); if ((n) >= 740) printf("J1 stage %d' + nl + '", (int)(n)); } while (0)\n'
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
