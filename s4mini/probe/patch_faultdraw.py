p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
draw=r'''
/* 3x5 hex font drawn at 4x scale into the scanout alias (works before arm_vm_init and, if the alias survives, after). */
static const unsigned short m8930_font[16]={
 0x7B6F,0x2C97,0x73E7,0x73CF,0x5BC9,0x79CF,0x79EF,0x7249,0x7BEF,0x7BCF,0x7BED,0x6BAE,0x7227,0x6B6E,0x79E7,0x79E4};
static void m8930_hexrow(unsigned int row,unsigned int v)
{
 volatile unsigned char *fb=(volatile unsigned char *)0xC0000000u;
 unsigned int d,gx,gy,sx,sy,xo,yo=600U+row*26U;
 for(d=0;d<8;d++){
  unsigned int nib=(v>>((7-d)*4))&15U, g=m8930_font[nib];
  xo=20U+d*16U;
  for(gy=0;gy<5;gy++) for(gx=0;gx<3;gx++){
   unsigned int on=(g>>(14-(gy*3+gx)))&1U;
   for(sy=0;sy<4;sy++) for(sx=0;sx<4;sx++){
    volatile unsigned char *p=fb+(yo+gy*4+sy)*1620U+(xo+gx*4+sx)*3U;
    p[0]=p[1]=p[2]=on?255:0;
   }
  }
 }
}
'''
s=s.replace("void ios7j1_stage(unsigned int n)",draw+"void ios7j1_stage(unsigned int n)",1)
# replace body of ios7j1_fault_report with a drawing version (keep signature)
a=s.index("void ios7j1_fault_report(unsigned int pc,unsigned int lr,unsigned int far,")
b=s.index("void ios7j1_fault_regs(",a)
newf=r'''void ios7j1_fault_report(unsigned int pc,unsigned int lr,unsigned int far,
                         unsigned int fsr,unsigned int cpsr,unsigned int reason)
{
 /* rows: pc, lr, far, fsr, cpsr, reason (first fault only, so the cause stays on screen) */
 if(j1_flt_n) return;
 j1_flt_n=1;
 m8930_hexrow(0,pc); m8930_hexrow(1,lr); m8930_hexrow(2,far);
 m8930_hexrow(3,fsr); m8930_hexrow(4,cpsr); m8930_hexrow(5,reason);
}
'''
s=s[:a]+newf+s[b:]
open(p,"w").write(s); print("ok")
