p="/home/user/xnu-j1/xnu/osfmk/arm/arm_vm_init.c"; s=open(p).read()
reps=[("    flush_mmu_tlb();\n\n    /*\n     * Set settings for pmap.","    MARKV(108);\n    flush_mmu_tlb();\n    MARKV(109);\n\n    /*\n     * Set settings for pmap."),
("    kernel_pmap->pm_l1_virt = phys_to_virt(cpu_ttb);\n","    kernel_pmap->pm_l1_virt = phys_to_virt(cpu_ttb);\n    MARKV(110);\n"),
("    etext = (vm_offset_t) sectTEXTB + sectSizeTEXT;","    MARKV(111);\n    etext = (vm_offset_t) sectTEXTB + sectSizeTEXT;"),
("    vm_kernel_slide = (gVirtBase - VM_KERNEL_BASE_ADDRESS);","    MARKV(112);\n    vm_kernel_slide = (gVirtBase - VM_KERNEL_BASE_ADDRESS);"),
("    sectCONSTB = (vm_offset_t) sectDCONST->addr;","    MARKV(113);\n    sectCONSTB = (vm_offset_t) sectDCONST->addr;\n    MARKV(114);")]
for o,n in reps:
    assert o in s,o
    s=s.replace(o,n,1)
open(p,"w").write(s); print("ok")
