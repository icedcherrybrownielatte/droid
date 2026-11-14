import os
NL = chr(92) + "n"
root = os.path.expanduser("~/xnu-j1/xnu/")

# osfmk side: dump the threads of a task (needs thread/task internals)
p = root + "osfmk/kern/sched_prim.c"
s = open(p).read()
assert "ios7m8930_dump_task" not in s
s += """
/* DEBUG: print every thread of a task with its scheduling/wait state */
void ios7m8930_dump_task(task_t task, int pid);
void ios7m8930_dump_task(task_t task, int pid)
{
	thread_t th;
	int n = 0;
	if (task == TASK_NULL) return;
	task_lock(task);
	queue_iterate(&task->threads, th, thread_t, task_threads) {
		printf("J1W pid%d t%d st=%x pri=%d ev=%08x cont=%08x wr=%d susp=%d@NL@", pid, n,
		       (unsigned)th->state, (int)th->sched_pri, (unsigned)th->wait_event,
		       (unsigned)(uintptr_t)th->continuation, (int)th->wait_result, (int)th->suspend_count);
		if (++n >= 8) break;
	}
	task_unlock(task);
}
""".replace("@NL@", NL)
open(p, "w").write(s)

# bsd side: watcher thread started right after the init process is bootstrapped
p = root + "bsd/kern/bsd_init.c"
s = open(p).read()
assert "j1_watch_thread" not in s
a = "\tbsd_utaskbootstrap();\n"
assert a in s
watcher = """
#if defined(BOARD_CONFIG_MSM8930_SERRANO)
/* DEBUG: every 10 s print what launchd's threads are waiting on */
extern void ios7m8930_dump_task(task_t task, int pid);
static void j1_watch_thread(__unused void *arg, __unused wait_result_t wr)
{
	int round;
	for (round = 0; round < 30; round++) {
		IOSleep(10000);
		if (initproc != PROC_NULL) {
			printf("J1W round %d nprocs=%d@NL@", round, nprocs);
			ios7m8930_dump_task(initproc->task, 1);
		}
	}
}
#endif
""".replace("@NL@", NL)
# put the helper before bsd_init()
i = s.index("\nbsd_init(void)")
j = s.rfind("\n", 0, i - 1)
s = s[:j] + watcher + s[j:]
s = s.replace(a, a + "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n\t{ thread_t j1w; if (kernel_thread_start(j1_watch_thread, NULL, &j1w) == KERN_SUCCESS) thread_deallocate(j1w); }\n#endif\n", 1)
open(p, "w").write(s)
print("ok")
