p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
a=s.index("void ios7m8930_mark(unsigned int n)")
b=s.index("}\nvoid ios7j1_stage",a)
new=r'''void ios7m8930_mark(unsigned int n)
{
 volatile unsigned char *fb=(volatile unsigned char *)0xC0000000u;
 static const unsigned char col[6][3]={{255,0,0},{0,255,0},{0,0,255},{255,255,0},{0,255,255},{255,0,255}};
 /* 40 bars per row, 13 px pitch, 10x14 px; row = n/40 at y=560+20*row */
 unsigned int x,y,xo=(n%40U)*13U,yo=560U+(n/40U)*20U;
 for(y=0;y<14;y++) for(x=0;x<10;x++){
  volatile unsigned char *p=fb+(yo+y)*1620U+(xo+x)*3U;
  p[0]=col[n%6][0]; p[1]=col[n%6][1]; p[2]=col[n%6][2];
 }
'''
s=s[:a]+new+s[b:]
open(p,"w").write(s); print("ok")
