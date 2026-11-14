import os
NL = chr(92) + "n"
p = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/kern_exec.c")
s = open(p).read()
a = '\tif (0) kprintf("J1EXEC activate=%d spawn=%d' + NL + '", error,\n\t\t(imgp->ip_flags & IMGPF_SPAWN) ? 1 : 0);\n'
i = s.index("posix_spawn(proc_t ap, struct posix_spawn_args *uap, int32_t *retval)")
j = s.index(a, i)
b = a + '\tprintf("J1 spawn %s err=%d' + NL + '", (imgp->ip_strings ? imgp->ip_strings : "?"), error);\n'
s = s[:j] + b + s[j + len(a):]
open(p, "w").write(s)

p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
a = "\t\tios7m8930_hexN(17, 0x40000000U|m_irqs);\n"
assert a in s
s = s.replace(a, a + "\t\t{ extern int nprocs; ios7m8930_hexN(20, 0xC0DE0000U | (unsigned)nprocs); }\n", 1)
open(p, "w").write(s)
print("ok")
