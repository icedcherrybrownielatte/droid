import os
root = os.path.expanduser("~/xnu-j1/xnu/")

# timer driver: own kernel mapping of the WDT block + helper
p = root + "pexpert/arm/msm8930_timer.c"
s = open(p).read()
a = "\tm_tmr = ml_io_map(M8930_TMR_PA, M8930_IO_BYTES);\n"
assert a in s
s = s.replace(a, a + "\tm_wdt = ml_io_map(0x0208A000U, 0x1000U);\n", 1)
a = "static vm_offset_t m_tmr, m_gic_dist, m_gic_cpu;\n"
assert a in s
s = s.replace(a, a + """static vm_offset_t m_wdt;
/* Pet uniLoader's WDT through a kernel mapping. The early identity mapping of 0x02000000 lives in
 * TTBR0 space and disappears as soon as a user pmap is active (it used to abort the IRQ handler). */
void ios7m8930_pet_wdt(void)
{
	if (m_wdt) *(volatile uint32_t *)(m_wdt + 0x38U) = 1;
}
""", 1)
a = "*(volatile uint32_t *)0x0208A038u = 1;"
assert a in s
s = s.replace(a, "ios7m8930_pet_wdt();", 1)
open(p, "w").write(s)

for rel in ("osfmk/kern/debug.c", "osfmk/arm/trap.c"):
    p = root + rel
    s = open(p).read()
    a = "*(volatile unsigned int *)0x0208A038u = 1;"
    assert a in s, rel
    s = s.replace(a, "{ extern void ios7m8930_pet_wdt(void); ios7m8930_pet_wdt(); }", 1)
    open(p, "w").write(s)
print("ok")
