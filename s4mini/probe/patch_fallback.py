import re
U="/home/user/uniloader/"
# Kconfig
p=U+"Kconfig"; s=open(p).read()
s=s.replace("config SELFTEST_CHAIN","""config SERRANO_FALLBACK
	bool "S4 mini: watchdog fallback to stock Android kernel (blob/ramdisk)"
	default n
	help
	  First boot sets a RAM flag and arms the MSM watchdog, then runs the payload. If the payload
	  hangs the watchdog resets the SoC; the next boot sees the flag and chain-loads the stock
	  Linux zImage embedded as the ramdisk blob, so Android comes back without button combos.

config FALLBACK_TEST_HANG
	bool "Fallback test: arm watchdog then hang instead of booting XNU"
	depends on SERRANO_FALLBACK
	default n

config SELFTEST_CHAIN""",1)
open(p,"w").write(s)
# start.S
p=U+"arch/arm/start.S"; s=open(p).read()
s=s.replace("#ifdef CONFIG_SELFTEST_CHAIN\n\t/* keep bootloader","#if defined(CONFIG_SELFTEST_CHAIN) || defined(CONFIG_SERRANO_FALLBACK)\n\t/* keep bootloader",1)
open(p,"w").write(s)
# main.c
p=U+"main/main.c"; s=open(p).read()
fb=r'''#ifdef CONFIG_SERRANO_FALLBACK
#define FB_FLAG		((volatile unsigned int *)0x80203fd0)
#define FB_MAGIC	0x584E5550
#define WDT_BASE	0x0208A038u
#define WDT_RST		0x00
#define WDT_EN		0x08
#define WDT_BARK	0x14
#define WDT_BITE	0x24
#define WDT_HZ		32768u
static void wdt_write(unsigned int off, unsigned int v)
{
	*(volatile unsigned int *)(WDT_BASE + off) = v;
}
static void fallback_to_android(void *zimage)
{
	extern unsigned long ramdisk_size;
	unsigned int *sv = (unsigned int *)0x80203ff8;
	unsigned int *s = (unsigned int *)zimage, *d = (unsigned int *)0x81800000, i;
	unsigned int sz = (unsigned int)ramdisk_size;
	volatile unsigned int w;

	wdt_write(WDT_EN, 0);
	printk(KERN_INFO, "fallback: previous XNU attempt did not finish -> Android (%u bytes)\n", sz);
	for (w = 0; w < 0x01000000; w++)
		;
	for (i = 0; i < (sz + 3) / 4; i++)
		d[i] = s[i];
	((void (*)(unsigned, unsigned, unsigned))0x81800000)(0, sv[0], sv[1]);
}
#endif

'''
s=s.replace("extern void fb_mark_asm(unsigned int byte_off, unsigned int color);\n","extern void fb_mark_asm(unsigned int byte_off, unsigned int color);\n\n"+fb,1)
s=s.replace("\tprint_splash();\n","""\tprint_splash();

#ifdef CONFIG_SERRANO_FALLBACK
	if (*FB_FLAG == FB_MAGIC) {
		*FB_FLAG = 0;
		fallback_to_android(ramdisk);
	}
	*FB_FLAG = FB_MAGIC;
	wdt_write(WDT_EN, 0);
	wdt_write(WDT_BARK, 20 * WDT_HZ);
	wdt_write(WDT_BITE, 23 * WDT_HZ);
	wdt_write(WDT_RST, 1);
	wdt_write(WDT_EN, 1);
	printk(KERN_INFO, "fallback: watchdog armed (23 s), flag set\n");
#ifdef CONFIG_FALLBACK_TEST_HANG
	printk(KERN_INFO, "fallback: TEST - hanging now, expect reset then Android\n");
	for (;;)
		;
#endif
#endif
""",1)
s=s.replace("\tboot_kernel(dt, kernel, ramdisk);\n","""#ifdef CONFIG_SERRANO_FALLBACK
	boot_kernel(dt, kernel, (void *)0);
#else
	boot_kernel(dt, kernel, ramdisk);
#endif
""",1)
open(p,"w").write(s)
# XNU timer: pet watchdog
p="/home/user/xnu-j1/xnu/pexpert/arm/msm8930_timer.c"; s=open(p).read()
if "0x0208A038" not in s:
    s=s.replace("\t\tios7m8930_fb_flush();","\t\tios7m8930_fb_flush();\n\t\t*(volatile uint32_t *)0x0208A038u = 1;\t/* pet the MSM watchdog armed by uniLoader */",1)
open(p,"w").write(s)
print("ok")
