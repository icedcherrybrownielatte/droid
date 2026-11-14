import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
a = "\tw = ml_set_interrupts_enabled(FALSE);\n\tv = dgt_get_count();\n\tml_set_interrupts_enabled(w);\n\treturn v;\n"
assert a in s
b = "\tw = ml_set_interrupts_enabled(FALSE);\n\tv = dgt_get_count();\n\t{ static unsigned int tbn; ++tbn; ios7m8930_hexN(20, (unsigned int)v); ios7m8930_hexN(21, tbn); }\n\tml_set_interrupts_enabled(w);\n\treturn v;\n"
s = s.replace(a, b, 1)
if "void ios7m8930_hexN(unsigned int" not in s.split("static unsigned int m_irqs")[0]:
    s = s.replace("static unsigned int m_irqs;", "extern void ios7m8930_hexN(unsigned int row, unsigned int v);\nstatic unsigned int m_irqs;", 1)
open(p,"w").write(s)
print("ok")
