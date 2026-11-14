import os
p = os.path.expanduser("~/xnu-j1/xnu/iokit/Kernel/IOService.cpp")
s = open(p).read()
bad = "dbg=%u %u %u %u\n\", gOutstandingJobs"
assert bad in s
s = s.replace(bad, "dbg=%u %u %u %u\" \"\n\", gOutstandingJobs", 1)
open(p, "w").write(s)
print("ok")
