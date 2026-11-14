import os
NL = chr(92) + "n"
p = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/kern_exec.c")
s = open(p).read()
a = '\tprintf("J1 spawn %s err=%d' + NL + '", (imgp->ip_strings ? imgp->ip_strings : "?"), error);\n'
assert a in s
b = '\t{ char j1path[96]; size_t j1len = 0; if (copyinstr(uap->path, j1path, sizeof(j1path), &j1len) != 0) strlcpy(j1path, "?", sizeof(j1path));\n\t  printf("J1 spawn %s err=%d' + NL + '", j1path, error); }\n'
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
