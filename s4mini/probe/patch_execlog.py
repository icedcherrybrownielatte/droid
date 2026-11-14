import os, re
root = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/")
NL = chr(92) + "n"

# silence the old step-by-step J1EXEC traces (they flood the console)
for name in ("kern_exec.c", "kern_credential.c"):
    p = root + name
    s = open(p).read()
    s2 = re.sub(r'kprintf\("J1EXEC ', 'if (0) kprintf("J1EXEC ', s)
    open(p, "w").write(s2)

p = root + "kern_exec.c"
s = open(p).read()
a = '\tif (0) kprintf("J1EXEC execve return err=%d' + NL + '", error);\n'
assert a in s, "anchor"
b = a + '\tprintf("J1 exec pid %d (%s) err=%d' + NL + '", p->p_pid, p->p_comm, error);\n'
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
