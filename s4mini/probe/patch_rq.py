import os
p = os.path.expanduser("~/xnu-j1/xnu/iokit/Kernel/IOService.cpp")
s = open(p).read()
a = "        IOSleep(20);\n        ios7m8930_fb_flush_all();\n"
assert a in s
nl = chr(92) + "n"
b = '        { static unsigned rqn; if ((pn % 150) == 2 && rqn < 8) { unsigned q[20]; rqn++; ios7m8930_sched_stats(q); printf("RQ cnt=%u hq=%u pri=%u st=%x ks=%u cont=%x act=%u pst=%u' + nl + '", q[0], q[1], q[8], q[9], q[10], q[11], q[12], q[6]); } }\n' + a
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
