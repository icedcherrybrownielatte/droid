import os
p = os.path.expanduser("~/xnu-j1/xnu/pexpert/arm/msm8930_timer.c")
s = open(p).read()
def rep(a,b):
    global s
    assert a in s, a
    s = s.replace(a,b,1)
rep("\t++m_irqs;\n\tif (!controller_ready", "\t++m_irqs;\n\tios7m8930_hexN(17, 0x10000000U|m_irqs);\n\tif (!controller_ready")
rep("\t\twr(m_gic_cpu, GIC_CPU_EOI, ack);\n\t\tdrain();\n\t\t(void)dgt", "\t\twr(m_gic_cpu, GIC_CPU_EOI, ack);\n\t\tdrain();\n\t\tios7m8930_hexN(17, 0x20000000U|m_irqs);\n\t\t(void)dgt")
rep("\t\t\tuint32_t gen = arm_gen;\n", "\t\t\tuint32_t gen = arm_gen;\n\t\t\tios7m8930_hexN(17, 0x30000000U|m_irqs);\n")
rep("\t\tios7m8930_fb_flush();\n\t\tios7m8930_hex10(m_irqs);\n\t\t/* DEBUG", "\t\tios7m8930_hexN(17, 0x40000000U|m_irqs);\n\t\tios7m8930_fb_flush();\n\t\tios7m8930_hex10(m_irqs);\n\t\t/* DEBUG")
open(p,"w").write(s)
print("ok")
