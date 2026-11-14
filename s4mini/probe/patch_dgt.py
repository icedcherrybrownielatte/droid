import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
a = "\tdo { a = rd(m_tmr, DGT_COUNT_VAL); b = rd(m_tmr, DGT_COUNT_VAL); } while (a != b);\n"
assert a in s
b = "\t/* Two reads can never be identical if an MMIO read takes longer than one 6.75 MHz tick, so accept\n\t * reads that agree within a few ticks (bounded retries) instead of requiring equality. */\n\t{ unsigned int tries = 0; do { a = rd(m_tmr, DGT_COUNT_VAL); b = rd(m_tmr, DGT_COUNT_VAL); } while ((uint32_t)(b - a) > 8U && ++tries < 16U); }\n"
s = s.replace(a, b, 1)
open(p,"w").write(s)
print("ok")
