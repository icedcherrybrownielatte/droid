p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
s=s.replace("static volatile unsigned int *j1_pixels;","""static volatile unsigned int *j1_pixels;
/* 32bpp BGRA shadow framebuffer in cached kernel memory; ios7m8930_fb_flush() converts it to the
 * bootloader's 24bpp RGB888 scanout buffer (540x960, stride 1620) a slice per timer tick. */
#define M8930_W 540U
#define M8930_H 960U
static unsigned int m8930_shadow[M8930_W*M8930_H] __attribute__((aligned(4096)));
static unsigned int m8930_scan_pa;
static vm_offset_t m8930_scan_map;
static unsigned int m8930_flush_row;
extern boolean_t pmap_initialized;
void ios7m8930_fb_flush(void)
{
 unsigned int y,n;
 if(!m8930_scan_pa||!j1_pixels) return;
 if(!m8930_scan_map){
  if(!pmap_initialized) return;
  m8930_scan_map=ml_io_map(m8930_scan_pa,0x180000);
  if(!m8930_scan_map) return;
 }
 for(n=0;n<60;n++){
  const unsigned char *src; volatile unsigned int *dst; unsigned int x;
  y=m8930_flush_row; if(++m8930_flush_row>=M8930_H) m8930_flush_row=0;
  src=(const unsigned char *)j1_pixels+y*(M8930_W*4U);
  dst=(volatile unsigned int *)(m8930_scan_map+y*1620U);
  for(x=0;x<M8930_W;x+=4){
   /* 4 BGRA pixels -> 12 bytes R,G,B */
   unsigned int a=(unsigned int)src[2]|((unsigned int)src[1]<<8)|((unsigned int)src[0]<<16)|((unsigned int)src[6]<<24);
   unsigned int b=(unsigned int)src[5]|((unsigned int)src[4]<<8)|((unsigned int)src[10]<<16)|((unsigned int)src[9]<<24);
   unsigned int c=(unsigned int)src[8]|((unsigned int)src[14]<<8)|((unsigned int)src[13]<<16)|((unsigned int)src[12]<<24);
   dst[0]=a; dst[1]=b; dst[2]=c; dst+=3; src+=16;
  }
 }
}""",1)
# stage 6: remember scanout, use shadow as pixels
s=s.replace("  j1_fb_physical=a->Video.v_baseAddr;\n  j1_pixels=(volatile unsigned int *)j1_fb_physical;","  m8930_scan_pa=a->Video.v_baseAddr;\n  j1_fb_physical=m8930_scan_pa;\n  j1_pixels=(volatile unsigned int *)m8930_shadow;",1)
s=s.replace(" fb=ml_io_map(j1_fb_physical,2073600);\n"," fb=(vm_offset_t)m8930_shadow;\n",1)
s=s.replace("cv.v_baseAddr=j1_fb_physical|1U;","cv.v_baseAddr=(unsigned int)m8930_shadow;",1)
# fast putc remap: keep shadow
s=s.replace("        vm_offset_t nfb = ml_io_map(j1_fb_physical, 2073600);\n        if (nfb) { j1_pixels = (volatile unsigned int *)nfb; fb = j1_pixels; }","        /* shadow framebuffer lives in kernel memory: nothing to remap */",1)
open(p,"w").write(s)
p="/home/user/xnu-j1/xnu/pexpert/arm/msm8930_timer.c"; s=open(p).read()
s=s.replace("extern void rtclock_intr(arm_saved_state_t *regs);","extern void rtclock_intr(arm_saved_state_t *regs);\nextern void ios7m8930_fb_flush(void);",1)
s=s.replace("\t\trtclock_intr((arm_saved_state_t *)context);","\t\trtclock_intr((arm_saved_state_t *)context);\n\t\tios7m8930_fb_flush();",1)
open(p,"w").write(s)
