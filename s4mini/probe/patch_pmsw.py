import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/arm/pmap.c")
s = open(p).read()
a = """        if (pmap_asid_ncpus) {
            pmap_asid_activate(new_pmap, cpu_number());
        }
        current_cpu_datap()->user_pmap = new_pmap;
        arm_set_context_id(new_pmap->pm_asid & 0xFF);
        arm_context_switch(new_pmap->pm_l1_phys);
"""
assert a in s
b = """#if defined(BOARD_CONFIG_MSM8930_SERRANO)
        { extern void ios7m8930_hexN(unsigned int, unsigned int);
          ios7m8930_hexN(20, 0x5A000001U); ios7m8930_hexN(21, (unsigned)new_pmap->pm_l1_phys); ios7m8930_hexN(22, (unsigned)new_pmap->pm_asid);
        if (pmap_asid_ncpus) {
            pmap_asid_activate(new_pmap, cpu_number());
        }
          ios7m8930_hexN(20, 0x5A000002U); ios7m8930_hexN(22, (unsigned)new_pmap->pm_asid);
        current_cpu_datap()->user_pmap = new_pmap;
        arm_set_context_id(new_pmap->pm_asid & 0xFF);
          ios7m8930_hexN(20, 0x5A000003U);
        arm_context_switch(new_pmap->pm_l1_phys);
          ios7m8930_hexN(20, 0x5A000004U); }
#else
""" + a + "#endif\n"
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("ok")
