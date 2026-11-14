import os
p = os.path.expanduser("~/xnu-j1/xnu/iokit/Kernel/IOService.cpp")
s = open(p).read()
a = "        IOLockLock( gJobsLock );\n        IOLockSleep( gJobsLock, (void *) &pn, THREAD_UNINT );\t/* never woken: park forever */\n        IOLockUnlock( gJobsLock );\n"
assert a in s
b = "        assert_wait( (event_t) &pn, THREAD_UNINT );\t/* never woken: park forever */\n        thread_block( THREAD_CONTINUE_NULL );\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
