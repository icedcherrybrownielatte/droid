import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/sched_prim.c")
s = open(p).read()
a = "\tif (thread != THREAD_NULL)\n\t\t(void)spllo();\n\n TLOG(1, \"thread_continue: calling call_continuation"
assert a in s
b = "\tif (thread != THREAD_NULL)\n\t\t(void)spllo();\n#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n\telse\n\t\t(void)spllo();\t/* new kernel threads must not start with IRQs masked */\n#endif\n\n TLOG(1, \"thread_continue: calling call_continuation"
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
