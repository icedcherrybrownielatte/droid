import os
root = os.path.expanduser("~/xnu-j1/xnu/bsd/kern/")
NL = chr(92) + "n"

p = root + "kern_xxx.c"
s = open(p).read()
assert "J1 REBOOT" not in s
a = "\tAUDIT_ARG(cmd, uap->opt);\n"
assert a in s
b = a + """#if defined(BOARD_CONFIG_MSM8930_SERRANO)
	{	/* DEBUG: show who asks for a reboot and hold the system instead, so the console can be read */
		static int j1_hold;
		printf("J1 REBOOT requested by pid %d (%s) opt=0x%x@NL@", p->p_pid, p->p_comm, uap->opt);
		while (1) (void)tsleep(&j1_hold, PWAIT, "j1hold", hz);
	}
#endif
""".replace("@NL@", NL)
s = s.replace(a, b, 1)
open(p, "w").write(s)

p = root + "kern_exit.c"
s = open(p).read()
assert "J1 exit" not in s
i = s.index("proc_exit(proc_t p)\n")
j = s.index("{\n", i) + 2
# insert after the local declarations: find first blank line after the opening brace
k = s.index("\n\n", j) + 1
ins = """#if defined(BOARD_CONFIG_MSM8930_SERRANO)
	printf("J1 exit pid %d (%s) xstat=0x%x@NL@", p->p_pid, p->p_comm, (unsigned)p->p_xstat);
#endif
""".replace("@NL@", NL)
s = s[:k] + ins + s[k:]
open(p, "w").write(s)

p = root + "kern_exec.c"
s = open(p).read()
if "J1 exec ok" not in s:
    a = "\tif (error)\n\t\tpanic(\"Process 1 exec of %s failed, errno %d\","
    # leave init path alone; log every successful exec at the end of execve instead
    pass
open(p, "w").write(s)
print("ok")
