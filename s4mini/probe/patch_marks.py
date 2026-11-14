import re
X="/home/user/xnu-j1/xnu/"
# 1) locore.s: J1 block only for J1, add MSM block
p=X+"osfmk/arm/locore.s"; s=open(p).read()
old="#if defined(BOARD_CONFIG_EXYNOS3475_J1XLTE) || defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* J1: identity-map S3C UART"
assert old in s
s=s.replace(old,"#if defined(BOARD_CONFIG_EXYNOS3475_J1XLTE)\n    /* J1: identity-map S3C UART",1)
msm='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
    /* S4 mini: identity-map the bootloader scanout (2 MB @0x88100000) and the
     * qGIC/timer block (1 MB @0x02000000) with strongly-ordered sections. */
    LoadConstantToReg(0x402, r2)
    LoadConstantToReg(0x88100000, r7)
    mov     r7, r7, lsr#20
    add     r5, r4, r7, lsl#2
    mov     r7, r7, lsl#20
    orr     r8, r7, r2
    str     r8, [r5]
    LoadConstantToReg(0x88200000, r7)
    mov     r7, r7, lsr#20
    add     r5, r4, r7, lsl#2
    mov     r7, r7, lsl#20
    orr     r8, r7, r2
    str     r8, [r5]
    LoadConstantToReg(0x02000000, r7)
    mov     r7, r7, lsr#20
    add     r5, r4, r7, lsl#2
    mov     r7, r7, lsl#20
    orr     r8, r7, r2
    str     r8, [r5]
#endif

    mov     r7, pc, lsr#20
    add     r5, r4, r7, lsl#2   /* Make the TTE offset */
'''
s=s.replace("\n    mov     r7, pc, lsr#20\n    add     r5, r4, r7, lsl#2   /* Make the TTE offset */\n","\n"+msm,1)
open(p,"w").write(s)
# 2) arm_vm_init.c: MSM seed block
p=X+"osfmk/arm/arm_vm_init.c"; s=open(p).read()
s=s.replace("#if defined(BOARD_CONFIG_EXYNOS3475_J1XLTE) || defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* Seed the new tables","#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    {\n        volatile unsigned int *l1 = (volatile unsigned int *)phys_to_virt(cpu_ttb);\n        l1[0x881] = 0x88100000u | 0xC02;\n        l1[0x882] = 0x88200000u | 0xC02;\n        l1[0x020] = 0x02000000u | 0xC02;\n    }\n#endif\n#if defined(BOARD_CONFIG_EXYNOS3475_J1XLTE)\n    /* Seed the new tables",1)
open(p,"w").write(s)
# 3) arm_init.c: marks
p=X+"osfmk/arm/arm_init.c"; s=open(p).read()
s=s.replace("void arm_init(boot_args * args)\n{","#if defined(BOARD_CONFIG_MSM8930_SERRANO)\nextern void ios7m8930_mark(unsigned int n);\n#define MARK(n) ios7m8930_mark(n)\n#else\n#define MARK(n) do{}while(0)\n#endif\nvoid arm_init(boot_args * args)\n{",1)
for needle,n in [("    bootProcessor = cpu_processor_alloc(TRUE);",1),("    cpu_bootstrap();",2),("    thread_bootstrap();",3),("    cpu_init();",4),("    processor_bootstrap();",5),("    PE_init_platform(FALSE, (void *) args);",6),("    PE_init_kprintf(FALSE);",7),("    arm_vm_init(maxMem, args);",8),("    kernel_early_bootstrap();",9),("    PE_init_platform(TRUE, (void *) args);",10)]:
    assert needle in s, needle
    s=s.replace(needle,"    MARK(%d);\n%s\n    MARK(%d);"%(n*2-1,needle,n*2),1)
open(p,"w").write(s)
# 4) pe file: mark function + stage hook
p=X+"pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
s=s.replace("void ios7j1_stage(unsigned int n)\n{\n (void)n;\n}","""/* Progress bars painted straight into the bootloader scanout (identity-mapped early): bar n = 24x12 px
 * at x=n*26, y=940.  Colour cycles so adjacent bars are distinguishable. */
void ios7m8930_mark(unsigned int n)
{
 volatile unsigned char *fb=(volatile unsigned char *)0x88100000u;
 static const unsigned char col[6][3]={{255,0,0},{0,255,0},{0,0,255},{255,255,0},{0,255,255},{255,0,255}};
 unsigned int x,y,xo=(n%40U)*26U,yo=900U+(n/40U)*14U;
 for(y=0;y<12;y++) for(x=0;x<24;x++){
  volatile unsigned char *p=fb+(yo+y)*1620U+(xo+x)*3U;
  p[0]=col[n%6][0]; p[1]=col[n%6][1]; p[2]=col[n%6][2];
 }
}
void ios7j1_stage(unsigned int n)
{
 ios7m8930_mark(40U+n);
}""",1)
s=s.replace(" if(stage==6){\n  if(!j1_video_ok(a)) ios7j1_final_boundary(1);"," ios7m8930_mark(60U+stage);\n if(stage==6){\n  if(!j1_video_ok(a)) ios7j1_final_boundary(1);",1)
open(p,"w").write(s)
print("ok")
