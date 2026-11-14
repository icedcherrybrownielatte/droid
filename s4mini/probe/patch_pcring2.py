import os
NL = chr(92) + "n"
root = os.path.expanduser("~/xnu-j1/xnu/")

p = root + "pexpert/arm/msm8930_timer.c"
s = open(p).read()
a = "unsigned int ios7m8930_pcring[16], ios7m8930_lrring[16], ios7m8930_pcidx;\n"
assert a in s
s = s.replace(a, a + "void *ios7m8930_thring[16];\nextern void *current_thread(void);\n", 1)
a = "ios7m8930_lrring[k] = ss->lr; }"
assert a in s
s = s.replace(a, "ios7m8930_lrring[k] = ss->lr; ios7m8930_thring[k] = current_thread(); }", 1)
open(p, "w").write(s)

p = root + "osfmk/kern/sched_prim.c"
s = open(p).read()
old_start = s.index("\t{ extern unsigned int ios7m8930_pcring[16]")
old_end = s.index("}\n", s.index('printf("\\n");', old_start)) + 2
new = """	{ extern unsigned int ios7m8930_pcring[16], ios7m8930_lrring[16], ios7m8930_pcidx; extern void *ios7m8930_thring[16];
	  extern void *get_bsdtask_info(task_t); extern int proc_pid(void *); extern char *proc_name_address(void *);
	  unsigned k, i = ios7m8930_pcidx;
	  for (k = 0; k < 6; k++) { unsigned j = (i - 1 - k) & 15U; thread_t t = (thread_t)ios7m8930_thring[j]; void *bp = NULL;
	    if (t && t->task && t->task != kernel_task) bp = get_bsdtask_info(t->task);
	    printf("J1P %08x/%08x %d %s p%d@NL@", ios7m8930_pcring[j], ios7m8930_lrring[j],
	           bp ? proc_pid(bp) : 0, bp ? proc_name_address(bp) : "k", t ? (int)t->sched_pri : -1); } }
""".replace("@NL@", NL)
s = s[:old_start] + new + s[old_end:]
open(p, "w").write(s)
print("ok")
