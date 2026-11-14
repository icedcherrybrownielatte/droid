import os
p = os.path.expanduser("~/xnu-j1/xnu/bsd/conf/param.c")
s = open(p).read()
a = "#define\tNPROC (20 + 16 * MAXUSERS)\n"
assert a in s
b = "#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n#define\tNPROC 532\t/* iOS 7 launchd starts far more than 52 processes (MAXUSERS 2) */\n#else\n" + a + "#endif\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
