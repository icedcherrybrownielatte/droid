import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/debug.c")
s = open(p).read()
a = "\t\t\tios7m8930_fb_flush_all();\n\t\t}\n\t}\n#endif\n"
assert a in s
b = "\t\t\tios7m8930_fb_flush_all();\n\t\t\t{\t/* DEBUG: hold the panic text on screen ~70 s (pet WDT), then let it bite -> TWRP */\n\t\t\t\tvolatile unsigned long long spin;\n\t\t\t\tfor (spin = 0; spin < 12000000000ULL; spin++) { *(volatile unsigned int *)0x0208A038u = 1; if (!(spin & 0xfffffULL)) ios7m8930_fb_flush_all(); }\n\t\t\t}\n\t\t}\n\t}\n#endif\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
