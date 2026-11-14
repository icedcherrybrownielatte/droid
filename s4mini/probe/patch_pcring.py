import os
NL = chr(92) + "n"
root = os.path.expanduser("~/xnu-j1/xnu/")

p = root + "pexpert/arm/msm8930_timer.c"
s = open(p).read()
assert "ios7m8930_pcring" not in s
a = "void M8930_handle_interrupt(void *context)\n{\n"
assert a in s
s = s.replace(a, """/* DEBUG: ring of interrupted PCs/LRs (sampled at timer ticks) for CPU-hog hunting */
unsigned int ios7m8930_pcring[16], ios7m8930_lrring[16], ios7m8930_pcidx;
""" + a + """	{ arm_saved_state_t *ss = (arm_saved_state_t *)context;
	  unsigned int k = ios7m8930_pcidx++ & 15U; ios7m8930_pcring[k] = ss->pc; ios7m8930_lrring[k] = ss->lr; }
""", 1)
open(p, "w").write(s)

p = root + "osfmk/kern/sched_prim.c"
s = open(p).read()
a = "\tif (task == TASK_NULL) return;\n"
assert a in s
s = s.replace(a, a + """	{ extern unsigned int ios7m8930_pcring[16], ios7m8930_lrring[16], ios7m8930_pcidx; unsigned k, i = ios7m8930_pcidx;
	  printf("J1W pcs:");
	  for (k = 0; k < 8; k++) printf(" %08x/%08x", ios7m8930_pcring[(i - 1 - k) & 15U], ios7m8930_lrring[(i - 1 - k) & 15U]);
	  printf("@NL@"); }
""".replace("@NL@", NL), 1)
open(p, "w").write(s)
print("ok")
