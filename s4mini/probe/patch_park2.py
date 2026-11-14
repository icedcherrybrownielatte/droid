import os
p = os.path.expanduser("~/xnu-j1/xnu/iokit/Kernel/IOService.cpp")
s = open(p).read()
a = "        IOSleep(60000);\n"
assert a in s
b = "        IOLockLock( gJobsLock );\n        IOLockSleep( gJobsLock, (void *) &pn, THREAD_UNINT );\t/* never woken: park forever */\n        IOLockUnlock( gJobsLock );\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
