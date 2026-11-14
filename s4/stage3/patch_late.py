"""One-off: measure timer interrupt lateness (exynos5410_timer.c)."""
NL = chr(92) + 'n'
p = 'exynos5410_timer.c'
s = open(p, newline='').read()


def rep(o, n):
    global s
    assert s.count(o) == 1, (o[:60], s.count(o))
    s = s.replace(o, n)


rep("unsigned int j5410_tstat[5] = { 0, 0, ~0U, 0, 0 };",
    "unsigned int j5410_tstat[8] = { 0, 0, ~0U, 0, 0, 0, 0, 0 };\t/* [5] late total, [6] late max, [7] early count */")
rep("\tuint64_t h0 = timebase_ready ? mct_count() : 0;\n",
    "\tuint64_t h0 = timebase_ready ? mct_count() : 0;\n"
    "\tif (armed) { if (h0 >= m_deadline) { uint32_t l = (uint32_t)(h0 - m_deadline); j5410_tstat[5] += l; if (l > j5410_tstat[6]) j5410_tstat[6] = l; } else j5410_tstat[7]++; }\n")
rep('\t\t\tprintf("J5410 timer arms=',
    '\t\t\tprintf("J5410 timer late avg=%u us max=%u us early=%u' + NL + '", m_irqs ? j5410_tstat[5] / m_irqs / 24U : 0U, j5410_tstat[6] / 24U, j5410_tstat[7]);\n'
    '\t\t\tprintf("J5410 timer arms=')
open(p, 'w', newline='').write(s)
print('ok')
