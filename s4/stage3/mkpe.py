"""Build pexpert/arm/pe_exynos5410_ja3g.c in ~/xnu-s4 from the S4 mini PE (pe_msm8930_serrano.c),
replacing the MSM8930-specific parts with Exynos 5410 (Galaxy S4 GT-I9500) ones. Run inside WSL."""
import os
X = os.path.expanduser('~/xnu-s4/xnu')
src = open(X + '/pexpert/arm/pe_msm8930_serrano.c', newline='').read().replace(chr(13) + chr(10), chr(10)).split('\n')
L = lambda a, b: src[a - 1:b]          # 1-based inclusive line range


def find(text, start=1):
    for i in range(start - 1, len(src)):
        if src[i].startswith(text):
            return i + 1
    raise SystemExit('anchor not found: ' + text)


a_pix = find('static volatile unsigned int *j1_pixels;')
a_fbmap = find('static vm_offset_t j1_fb_map;')
a_font = find('static const unsigned short m8930_font[16]')
a_stage = find('void ios7j1_stage(unsigned int n)')
a_disp = find('/* Direct-FB backend')
a_vok = find('static int j1_video_ok(const boot_args *a)')
a_ckpt = find('void ios7j1_checkpoint(boot_args *a, unsigned int stage)')
a_touch = find('/* Touch power (mXT336S)')
a_rs = find("/* TWRP's ram_console (Samsung persistent_ram, 1 MB zone)")
a_end = max(i + 1 for i, l in enumerate(src) if l == '#endif')
assert a_pix < a_fbmap < a_font < a_stage < a_disp < a_vok < a_ckpt < a_touch < a_rs < a_end

HEAD = r'''/* Galaxy S4 GT-I9500 (Exynos 5410) PE, derived from the S4 mini PE (pe_msm8930_serrano.c): same
 * ios7j1_* / ios7m8930_* entry points so the shared iOS-port code is unchanged.
 * Panel: S-Boot leaves FIMD1 window 2 scanning out 0x67000000, 1080x1920, 4320 bytes/line, ARGB8888
 * (bytes B,G,R,A). The text console draws into a cached 540x960 BGRA shadow that is flushed 2x2 to the
 * panel a slice per timer tick. Persistent log: TWRP's ram_console, 2 MB zone at 0x60000000. */'''

FB = r'''static volatile unsigned int *j1_pixels;
/* 32bpp BGRA shadow (540x960) in cached kernel memory; ios7m8930_fb_flush() doubles it 2x2 into the
 * 1080x1920 ARGB8888 scanout a slice per timer tick. The name M8930_* is kept for the shared code. */
#define M8930_W 540U
#define M8930_H 960U
#define J5410_SCAN_PA    0x67000000U
#define J5410_SCAN_ROW   4320U
#define J5410_SCAN_BYTES (4320U * 1920U)
static unsigned int m8930_shadow[M8930_W*M8930_H] __attribute__((aligned(4096)));
static unsigned int m8930_scan_pa;
static vm_offset_t m8930_scan_map;
static unsigned int m8930_flush_row;
extern boolean_t pmap_initialized;
void ios7m8930_fb_flush(void);
static unsigned int m8930_force_all;
extern volatile int j1_panel_console_enabled;
extern uint64_t M8930_get_timebase(void);
void ios7m8930_fb_flush_all(void)
{
 m8930_force_all=1; ios7m8930_fb_flush(); ios7m8930_fb_flush(); m8930_force_all=0;
}
static int m8930_map_scan(void)
{
 if(m8930_scan_map) return 1;
 if(!m8930_scan_pa||!pmap_initialized) return 0;
 m8930_scan_map=ml_io_map(m8930_scan_pa,J5410_SCAN_BYTES);
 return m8930_scan_map!=0;
}
/* Dirty text lines (16 shadow rows each, 60 lines): only those are copied, at most 2 per call, because
 * the copy runs in the timer IRQ and the uncached panel writes are slow (a 240-row flush per tick left
 * threads ~no CPU). fast_putc marks lines dirty. */
unsigned long long m8930_dirty;
#define M8930_DIRTY(y) (m8930_dirty |= 1ULL << (((y) / 16U) & 63U))
static void m8930_copy_rows(unsigned int y0, unsigned int n)
{
 unsigned int y;
 for(y=y0;y<y0+n&&y<M8930_H;y++){
  const unsigned int *src=(const unsigned int *)j1_pixels+y*M8930_W; unsigned int x;
  volatile unsigned int *d0=(volatile unsigned int *)(m8930_scan_map+(2U*y)*J5410_SCAN_ROW);
  volatile unsigned int *d1=(volatile unsigned int *)(m8930_scan_map+(2U*y+1U)*J5410_SCAN_ROW);
  for(x=0;x<M8930_W;x++){ unsigned int p=src[x]; d0[2*x]=p; d0[2*x+1]=p; d1[2*x]=p; d1[2*x+1]=p; }
 }
}
void ios7m8930_fb_flush(void)
{
 unsigned int line,done=0;
 if(!m8930_scan_pa||!j1_pixels) return;
 if(!j1_panel_console_enabled && !m8930_force_all) return;
 if(!m8930_map_scan()) return;
 if(m8930_force_all){ m8930_copy_rows(0,M8930_H); m8930_dirty=0; return; }
 for(line=0;line<60U&&done<2U;line++){
  if(!(m8930_dirty&(1ULL<<line))) continue;
  m8930_dirty&=~(1ULL<<line);
  m8930_copy_rows(line*16U,16U); done++;
 }
 (void)m8930_flush_row;
}'''

FONT = r'''/* Debug hex rows straight into the panel (only once the scanout is mapped). 3x5 font, 8x scale. */
static const unsigned short m8930_font[16]={
 0x7B6F,0x2C97,0x73E7,0x73CF,0x5BC9,0x79CF,0x79EF,0x7249,0x7BEF,0x7BCF,0x7BED,0x6BAE,0x7227,0x6B6E,0x79E7,0x79E4};
static void m8930_hexrow(unsigned int row,unsigned int v)
{
 volatile unsigned int *fb;
 unsigned int d,gx,gy,sx,sy,xo,yo=1200U+row*44U;
 /* only while a panic forces the panel: these rows are drawn from hot paths (IRQ exit draws two),
  * and ~8k uncached pixel writes per row made every interrupt ~17 ms late */
 if(!m8930_scan_map||row>15U||!m8930_force_all) return;
 fb=(volatile unsigned int *)m8930_scan_map;
 for(d=0;d<8;d++){
  unsigned int nib=(v>>((7-d)*4))&15U, g=m8930_font[nib];
  xo=760U+d*32U;
  for(gy=0;gy<5;gy++) for(gx=0;gx<3;gx++){
   unsigned int on=(g>>(14-(gy*3+gx)))&1U;
   for(sy=0;sy<8;sy++) for(sx=0;sx<8;sx++)
    fb[(yo+gy*8+sy)*(J5410_SCAN_ROW/4U)+xo+gx*8+sx]=on?0xFF505050U:0xFF000000U;
  }
 }
}
/* Progress markers of the shared code (IOService matching, config threads, ...): logged to ram_console as
 * "[n]" when the value changes, so TWRP's last_kmsg shows where things stopped. */
static void j1_seclog_putc(char c);
void ios7m8930_mark(unsigned int n)
{
 static unsigned int last=~0U;
 char b[12]; int k=0;
 if(n==last||n>=1000U) return;	/* skip the per-tick scheduler/AST markers */
 last=n;
 do { b[k++]=(char)('0'+n%10U); n/=10U; } while(n&&k<10);
 j1_seclog_putc('[');
 while(k) j1_seclog_putc(b[--k]);
 j1_seclog_putc(']');
}
'''

DISP = r'''/* Direct-FB backend: GUI frames (IOMobileFramebuffer swaps) go straight to the panel. */
static uint64_t j1_graphics_seq=1;
/* Panel text console (fast_putc): active during boot, handed to the GUI after its first frames. */
volatile int j1_panel_console_enabled=1;
static unsigned long long m8930_last_present;
unsigned int ios7j1_present_count;
unsigned long long ios7m8930_last_present_tb(void);
unsigned long long ios7m8930_last_present_tb(void){ return m8930_last_present; }
int ios7j1_display_ready(void)
{
 return m8930_scan_pa && j1_pixels && !j1_fatal_active;
}
/* Source: half-resolution 540x960 BGRA (row >= 2160); each pixel is doubled 2x2 into the 1080x1920
 * ARGB8888 panel (same byte order, plain word copies). */
int ios7j1_display_present(const uint8_t *px,uint32_t bytes,uint32_t row,
                           uint32_t fmt,uint64_t *seq)
{
 unsigned int y;
 if(!px||!seq) return 0;
 if(!(fmt==0x42475241U||fmt==0x52474241U)) return 0;
 if(row<2160U||bytes<row*960U) return 0;
 if(!ios7j1_display_ready()) return 0;
 if(!m8930_map_scan()) return 0;
 m8930_last_present=M8930_get_timebase();
 for(y=0;y<960U;y++){
  const unsigned int *s=(const unsigned int *)(px+(uint64_t)y*row);
  volatile unsigned int *d0=(volatile unsigned int *)(m8930_scan_map+(2U*y)*J5410_SCAN_ROW);
  volatile unsigned int *d1=(volatile unsigned int *)(m8930_scan_map+(2U*y+1U)*J5410_SCAN_ROW);
  unsigned int x;
  for(x=0;x<540U;x++){ unsigned int p=s[x]|0xFF000000U; d0[2*x]=p; d0[2*x+1]=p; d1[2*x]=p; d1[2*x+1]=p; }
 }
 *seq=j1_graphics_seq++;
 if(!j1_graphics_seq) j1_graphics_seq=1;
 if(ios7j1_present_count++<3) printf("J1 present #%u fmt%x row%u\n",ios7j1_present_count,fmt,row);
 if(ios7j1_present_count>=2) j1_panel_console_enabled=0;
 return 1;
}
int ios7j1_display_completed(uint64_t s){ return s && s<j1_graphics_seq; }
'''

VOK = r'''static int j1_video_ok(const boot_args *a)
{
 unsigned long long ramend=(unsigned long long)a->physBase+a->memSize;
 /* uniLoader-s4 (ja3g_xnu_defconfig): XNU RAM 0x68000000 + 0x38000000, clear of sec_log (0x46000000),
  * the watchdog marker (0x5FF00000), ram_console (0x60000000) and the scanout (0x67000000). */
 return a->Revision==1 && a->Version==2 && a->virtBase==0x80000000U &&
  a->physBase==0x68000000U && a->memSize==0x38000000U &&
  a->topOfKernelData>=a->physBase && !(a->topOfKernelData&0x3fffU) &&
  (unsigned long long)a->topOfKernelData+0x220000U<=ramend &&
  a->Video.v_width==1080 && a->Video.v_height==1920 &&
  a->Video.v_rowBytes==4320 && a->Video.v_depth==32 &&
  a->Video.v_baseAddr==J5410_SCAN_PA;
}
'''

TOUCH = r'''/* Touch (Synaptics RMI4 on i2c-0, addr 0x20) and buttons (gpio-keys) are not ported yet: report nothing. */
unsigned int ios7j1_mxt_msgs, ios7j1_mxt_reports, ios7j1_mxt_errs, ios7j1_mxt_last, ios7j1_mxt_polls, ios7j1_mxt_chg;
unsigned int ios7j1_mxt_hid, ios7j1_mxt_noopen, ios7j1_mxt_nopkt;
unsigned int ios7j1_key_home, ios7j1_key_power, ios7j1_key_events;
int ios7j1_mxt_read(unsigned int reg, unsigned char *buf, unsigned int len);
int ios7j1_mxt_read(unsigned int reg, unsigned char *buf, unsigned int len) { (void)reg; (void)buf; (void)len; return -9; }
void ios7j1_touch_power(void);
void ios7j1_touch_power(void) { }
void ios7j1_touch_i2c_probe(void);
void ios7j1_touch_i2c_probe(void) { }
void ios7j1_touch_i2c_report(void);
void ios7j1_touch_i2c_report(void) { printf("J1I touch: not ported on ja3g\n"); }
void ios7j1_touch_power_report(void);
void ios7j1_touch_power_report(void) { }
void ios7j1_touch_probe(void);
void ios7j1_touch_probe(void) { }
int ios7j1_mxt_init(void);
int ios7j1_mxt_init(void) { return -1; }
int ios7j1_mxt_poll(unsigned int *x, unsigned int *y, unsigned int *down);
int ios7j1_mxt_poll(unsigned int *x, unsigned int *y, unsigned int *down) { (void)x; (void)y; (void)down; return 0; }
int ios7j1_buttons_read(unsigned int *home, unsigned int *power);
int ios7j1_buttons_read(unsigned int *home, unsigned int *power) { *home = 0; *power = 0; return -1; }
'''

out = [HEAD, '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)']
out += [l for l in L(6, a_pix - 1) if l != '#include "msm8930_timer.h"'] + ['#include "msm8930_timer.h"']
out += [FB]
out += L(a_fbmap, a_font - 1)
out += [FONT]
out += L(a_stage, a_disp - 1)
out += [DISP]
out += [VOK]
mid = '\n'.join(L(a_ckpt, a_touch - 1))
tail = '\n'.join(L(a_rs, len(src)))

def rep(s, old, new, n=1):
    assert s.count(old) == n, (old, s.count(old))
    return s.replace(old, new)

# checkpoint / SocSupport / console constants
mid = rep(mid, 'h->machine==0x8930U', 'h->machine==0x5410U')
mid = rep(mid, 'j1_default_handoff.machine=0x8930U;', 'j1_default_handoff.machine=0x5410U;')
mid = rep(mid, 'j1_default_handoff.disp_physical=0x88100000U;', 'j1_default_handoff.disp_physical=J5410_SCAN_PA;')
mid = rep(mid, 'j1_default_handoff.dma_stride=2160; j1_default_handoff.dma_xy=0;', 'j1_default_handoff.dma_stride=4320; j1_default_handoff.dma_xy=0;')
mid = rep(mid, 'j1_default_handoff.width=540; j1_default_handoff.height=960;', 'j1_default_handoff.width=1080; j1_default_handoff.height=1920;')
mid = rep(mid, 'j1_default_handoff.row_bytes=2160;', 'j1_default_handoff.row_bytes=4320;')
mid = rep(mid, 'j1_default_handoff.framebuffer_bytes=2073600;', 'j1_default_handoff.framebuffer_bytes=J5410_SCAN_BYTES;')
mid = rep(mid, '-0xA6100000U+0x80000000U', '-0x68000000U+0x80000000U', 3)
mid = rep(mid, 'PE_state.video.v_rowBytes=1080;PE_state.video.v_width=200;\n PE_state.video.v_height=300;',
          'PE_state.video.v_rowBytes=2160;PE_state.video.v_width=540;\n PE_state.video.v_height=960;')
mid = rep(mid, 'cv.v_offset=0; cv.v_length=480U*1080U;\n  cv.v_width=200; cv.v_height=300; cv.v_rowBytes=1080;',
          'cv.v_offset=0; cv.v_length=960U*2160U;\n  cv.v_width=540; cv.v_height=960; cv.v_rowBytes=2160;')
mid = rep(mid, '#define J1F_FB_W 270U\n#define J1F_FB_H 480U', '#define J1F_FB_W 540U\n#define J1F_FB_H 960U')
mid = rep(mid, 'volatile unsigned int *row = fb + (y + yy) * 270U;\n        for (x = 0; x < 270; x++)',
          'volatile unsigned int *row = fb + (y + yy) * 540U;\n        for (x = 0; x < 540; x++)')
# ram_console: 2 MB zone at 0x60000000, ring 1 MB; continue after uniLoader's text
mid = rep(mid, '#define J1_SECLOG_PA   0x8fe00000U', '#define J1_SECLOG_PA   0x60000000U\n#define J1_SECLOG_ZONE 0x200000U')
mid = rep(mid, '#define J1_SECLOG_SIZE 0x4B000U', '#define J1_SECLOG_SIZE 0x100000U')
mid = rep(mid, '#define J1_MARK_OFF 0x60000U', '#define J1_MARK_OFF 0x180000U')
mid = rep(mid, 'ml_io_map(J1_SECLOG_PA, 0x100000U);', 'ml_io_map(J1_SECLOG_PA, J1_SECLOG_ZONE);')
mid = rep(mid, '''        if (ok) {
            j1_seclog_idx = mk[1];
            boots = mk[2] + 1;
        } else {
            j1_seclog_idx = 0;''', '''        if (ok) {
            j1_seclog_idx = mk[1];
            boots = mk[2] + 1;
        } else {
            /* uniLoader logged first (header {DBGC, start, size}): append after its text */
            volatile unsigned int *hd = (volatile unsigned int *)j1_seclog;
            j1_seclog_idx = (hd[0] == 0x43474244U && hd[2] < J1_SECLOG_SIZE - 0x10000U) ? hd[2] : 0;''')
tail = rep(tail, 'j1_seclog[0x100000U - 16U + i] = par[i];', 'j1_seclog[J1_SECLOG_ZONE - 16U + i] = par[i];')
tail = rep(tail, "/* TWRP's ram_console (Samsung persistent_ram, 1 MB zone)", "/* TWRP's ram_console (Samsung persistent_ram, 2 MB zone on the S4)")
# fast console: 540x960 shadow, dim grey text (OLED)
tail = rep(tail, 'unsigned int i, n = 270U * 480U;', 'unsigned int i, n = 540U * 960U;')
tail = rep(tail, 'if (j1f_cy + 16 > 480) j1f_cy = 0;', 'if (j1f_cy + 16 > 960) j1f_cy = 0;', 2)
tail = rep(tail, 'fb + (j1f_cy + y) * 270U + j1f_cx;', 'fb + (j1f_cy + y) * 540U + j1f_cx;')
tail = rep(tail, 'if (bits & (1U << x)) row[x] = 0xFFFFFFFFU;', 'if (bits & (1U << x)) row[x] = 0xFF909090U;')
tail = rep(tail, 'if (j1f_cx + 8 > 270) {', 'if (j1f_cx + 8 > 540) {')
# dirty-line tracking for the IRQ-time flush
tail = rep(tail, '        j1f_cx += 8;\n', '        M8930_DIRTY(j1f_cy);\n        j1f_cx += 8;\n')
tail = rep(tail, '        j1f_wiped = 1;\n', '        j1f_wiped = 1;\n        m8930_dirty = (1ULL << 60) - 1ULL;\n')
mid = rep(mid, 'static void j1f_blank_line(volatile unsigned int *fb, unsigned int y)\n{\n    unsigned int x, yy;\n',
          'static void j1f_blank_line(volatile unsigned int *fb, unsigned int y)\n{\n    unsigned int x, yy;\n    M8930_DIRTY(y);\n')
# the S4 mini file closes its #if before the hex helpers: close ours at the very end instead
tl = tail.split('\n')
last_endif = max(i for i, l in enumerate(tl) if l == '#endif')
del tl[last_endif]
tail = '\n'.join(tl).rstrip('\n') + '\n#endif /* BOARD_CONFIG_EXYNOS5410_JA3G */\n'

text = '\n'.join(out) + '\n' + mid + '\n' + TOUCH + tail
for bad in ('0x88100000', '0xA6100000', '0x8fe00000', '0x30000000', 'j1_tlmm', 'j1_ssbi'):
    if bad in text:
        print('WARNING leftover', bad, [i + 1 for i, l in enumerate(text.split('\n')) if bad in l][:5])
open(X + '/pexpert/arm/pe_exynos5410_ja3g.c', 'w', newline='').write(text)
print('pe_exynos5410_ja3g.c', len(text.split('\n')), 'lines')
