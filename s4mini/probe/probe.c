/* Probe: dump MDP4 scanout registers into the kernel cmdline ("fbp=..."),
 * then chain-load the stock zImage unchanged. Read-only on hardware. */
typedef unsigned int u32;
#define RD(a) (*(volatile u32 *)(a))
#ifndef RAMB
#define RAMB 0x80200000u
#endif
#ifndef MDP
#define MDP 0x05100000u
#endif
#define ZDST (RAMB+0x1600000u)
#define TAGS_NEW ((u32 *)(RAMB+0x1000u))
#define CMDBUF ((char *)(RAMB+0x3000u))
#define TAG_CORE 0x54410001u
#define TAG_CMDLINE 0x54410009u

static const u32 offs[] = {
	0x00000, 0x10000, 0x10004,
	0x20000, 0x20010, 0x20040, 0x30000, 0x30010, 0x30040,
	0x40000, 0x40010, 0x40040, 0x50000, 0x50010, 0x50040,
	0x90000, 0x90004, 0x90008, 0x9000c,
};
static const char *skip[] = { "cordon=", "connie=", "sec_log=", "sec_dbg=", "etb_buf=",
	"sec_debug.", "msm_rtb.", 0 };

static int starts(const char *s, const char *p) { while (*p) if (*s++ != *p++) return 0; return 1; }

void __attribute__((noreturn, used)) real_start(u32 zero, u32 mach, u32 *atags);
__asm__(".section .text.start,\"ax\"\n"
	".global start\n"
	"start:\n"
	" ldr sp, =" SPTOP "\n"
	" b real_start\n"
	" .ltorg\n"
	".text\n");
extern char _stub_end[];

void real_start(u32 zero, u32 mach, u32 *atags)
{
	u32 i, *s, *d, *t, n;
	char *o = CMDBUF;
	const char *old = "";
	(void)zero;

	/* 1. read registers (hex text) */
	char fbp[4 + 19 * 9 + 1], *f = fbp;
	*f++ = 'f'; *f++ = 'b'; *f++ = 'p'; *f++ = '=';
	for (i = 0; i < sizeof(offs) / 4; i++) {
		u32 v = RD(MDP + offs[i]); int k;
		for (k = 28; k >= 0; k -= 4) *f++ = "0123456789abcdef"[(v >> k) & 15];
		*f++ = ',';
	}
	f[-1] = 0;

	/* 2. rebuild tag list with a new cmdline */
	if (atags && atags[1] == TAG_CORE) {
		t = TAGS_NEW;
		for (s = atags; s[1] != 0; s += s[0]) {
			if (s[1] == TAG_CMDLINE) { old = (const char *)(s + 2); continue; }
			for (n = 0; n < s[0]; n++) t[n] = s[n];
			t += s[0];
		}
		/* filtered old cmdline */
		const char *p = old;
		while (*p) {
			const char *e = p; int sk = 0, j;
			while (*e && *e != ' ') e++;
			for (j = 0; skip[j]; j++) if (starts(p, skip[j])) sk = 1;
			if (!sk) { const char *q; if (o != CMDBUF) *o++ = ' '; for (q = p; q < e; q++) *o++ = *q; }
			p = *e ? e + 1 : e;
		}
		*o++ = ' ';
		for (f = fbp; *f; ) *o++ = *f++;
		*o = 0;
		n = (u32)(o - CMDBUF) + 1;
		t[0] = 2 + ((n + 3) >> 2); t[1] = TAG_CMDLINE;
		for (i = 0; i < (n + 3) >> 2; i++) t[2 + i] = 0;
		for (i = 0; i < n; i++) ((char *)(t + 2))[i] = CMDBUF[i];
		t += t[0];
		t[0] = 0; t[1] = 0;
		atags = TAGS_NEW;
	}

	/* 3. copy stock zImage and jump */
	s = (u32 *)_stub_end; d = (u32 *)ZDST;
	for (i = 0; i < (ZSIZE + 3) / 4; i++) d[i] = s[i];
	((void (*)(u32, u32, u32 *))ZDST)(0, mach, atags);
	for (;;) ;
}
