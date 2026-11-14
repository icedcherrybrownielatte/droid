import os
NL = chr(92) + "n"
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/sched_prim.c")
s = open(p).read()
a = "\tif (task == TASK_NULL) return;\n\ttask_lock(task);\n"
assert a in s
b = "\tif (task == TASK_NULL) return;\n\t{ unsigned q[20]; ios7m8930_sched_stats(q); printf(\"J1W sched_tick=%u rq=%u hq=%d headpri=%u headcont=%08x act=%u@NL@\", (unsigned)sched_tick, q[0], (int)q[1], q[8], q[11], q[12]); }\n\ttask_lock(task);\n".replace("@NL@", NL)
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
