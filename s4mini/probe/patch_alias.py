import os
root = os.path.expanduser("~/xnu-j1/xnu/")
p = root + "pexpert/arm/pe_msm8930_serrano.c"
s = open(p).read()
old = " volatile unsigned char *fb=(volatile unsigned char *)0x30000000u;\n"
assert s.count(old) == 2
new = " /* the low 0x30000000 alias lives in TTBR0 space and vanishes once a user pmap is active: prefer the kernel mapping */\n volatile unsigned char *fb=(volatile unsigned char *)(m8930_scan_map ? m8930_scan_map : 0x30000000u);\n"
s = s.replace(old, new)
open(p, "w").write(s)
p = root + "osfmk/arm/pmap.c"
s = open(p).read()
i = s.index("#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n        { extern void ios7m8930_hexN(unsigned int, unsigned int);\n          ios7m8930_hexN(20, 0x5A000001U)")
j = s.index("#else\n", i) + len("#else\n")
k = s.index("#endif\n", j)
s = s[:i] + s[j:k] + s[k+len("#endif\n"):]
open(p, "w").write(s)
print("ok")
