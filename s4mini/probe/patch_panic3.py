import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/debug.c")
s = open(p).read()
a = " if (!(spin & 0xfffffULL)) ios7m8930_fb_flush_all();"
assert a in s
s = s.replace(a, "", 1)
a = "\t\t\tprintf(\"\n\");\n\t\t\tios7m8930_fb_flush_all();\n"
assert a in s, "flush"
s = s.replace(a, "\t\t\tprintf(\"\n\");\n", 1)
open(p, "w").write(s)
print("ok")
