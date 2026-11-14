import os
p = os.path.expanduser("~/xnu-j1/xnu/iokit/Kernel/IOService.cpp")
s = open(p).read()
i = s.index("        if (pn == 1) { unsigned q[20]; ios7m8930_sched_stats(q);")
j = s.index("\n", i)
b = '        { static int pk_done; if (pn == 1 && !pk_done) { extern unsigned int ios7m8930_dbg[16]; pk_done = 1; printf("PK jobs=%d/%u cfg=%d wt=%d dbg=%u %u %u %u\n", gOutstandingJobs, gJobsRun, gNumConfigThreads, gNumWaitingThreads, ios7m8930_dbg[0], ios7m8930_dbg[1], ios7m8930_dbg[2], ios7m8930_dbg[3]); } }'
s = s[:i] + b + s[j:]
open(p, "w").write(s)
print("ok")
