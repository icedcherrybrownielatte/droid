import os
p = os.path.expanduser("~/xnu-j1/xnu/iokit/Kernel/IOService.cpp")
s = open(p).read()
i = s.index("        { static unsigned rqn;")
j = s.index("        IOSleep(20);\n        ios7m8930_fb_flush_all();\n", i)
k = j + len("        IOSleep(20);\n        ios7m8930_fb_flush_all();\n")
s = s[:i] + "        IOSleep(60000);\n" + s[k:]
open(p, "w").write(s)
print("ok")
