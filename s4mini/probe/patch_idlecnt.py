import os
NL = chr(92) + "n"
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/sched_prim.c")
s = open(p).read()
a = "\t\tmachine_idle();\n"
assert s.count(a) == 1
s = s.replace(a, "\t\tios7m8930_idle_n++;\n" + a, 1)
# global near sched_tick definition
a2 = "unsigned\tsched_tick;\n"
assert a2 in s
s = s.replace(a2, a2 + "unsigned\tios7m8930_idle_n;\t/* DEBUG: idle-loop iterations */\n", 1)
a3 = 'printf("J1W sched_tick=%u '
assert a3 in s
s = s.replace(a3, '{ static unsigned last_idle; printf("J1W idle +%u@NL@", ios7m8930_idle_n - last_idle); last_idle = ios7m8930_idle_n; } printf("J1W sched_tick=%u '.replace("@NL@", NL), 1)
open(p, "w").write(s)
print("ok")
