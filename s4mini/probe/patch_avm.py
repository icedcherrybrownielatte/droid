p="/home/user/xnu-j1/xnu/osfmk/arm/arm_vm_init.c"; s=open(p).read()
hdr='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
extern void ios7m8930_mark(unsigned int n);
#define MARKV(n) ios7m8930_mark(n)
#else
#define MARKV(n) do{}while(0)
#endif
'''
i=s.index("void arm_vm_init(uint32_t mem_limit, boot_args * args)")
s=s[:i]+hdr+s[i:]
reps=[("    cpu_ttb = gTopOfKernel + L1_SIZE;\n    bzero((void*)phys_to_virt(cpu_ttb), L1_SIZE);","    MARKV(100);\n    cpu_ttb = gTopOfKernel + L1_SIZE;\n    bzero((void*)phys_to_virt(cpu_ttb), L1_SIZE);\n    MARKV(101);"),
("    identityBaseVA = gVirtBase;","    MARKV(102);\n    identityBaseVA = gVirtBase;"),
("    vectp = (vm_offset_t *)addr_to_tte(phys_to_virt(cpu_ttb), VECTORS_BASE);","    MARKV(103);\n    vectp = (vm_offset_t *)addr_to_tte(phys_to_virt(cpu_ttb), VECTORS_BASE);"),
("    set_mmu_ttb(cpu_ttb);\n    set_mmu_ttb_alt(cpu_ttb);","    MARKV(104);\n    set_mmu_ttb(cpu_ttb);\n    set_mmu_ttb_alt(cpu_ttb);\n    MARKV(105);"),
("    pmap_bootstrap(gMemSize, (vm_offset_t *) & bootstrap_addr, 0);","    MARKV(106);\n    pmap_bootstrap(gMemSize, (vm_offset_t *) & bootstrap_addr, 0);\n    MARKV(107);")]
for o,n in reps:
    assert o in s,o
    s=s.replace(o,n,1)
open(p,"w").write(s); print("ok")
