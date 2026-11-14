/* FB test: paint colour bands into the suspected scanout buffer, hold ~8 s, then chain-load stock zImage. */
typedef unsigned int u32;
#define FB 0x88100000u
#define W 540
#define H 960
#define STRIDE 1620
#define ZDST 0x81800000u
#define DGT_CNT (*(volatile u32 *)(0x0200A000u + 0x24 + 4))

__asm__(".section .text.start,\"ax\"\n.global start\nstart:\n ldr sp, =0x80203ff0\n b real_start\n .ltorg\n.text\n");
extern char _stub_end[];

void __attribute__((noreturn, used)) real_start(u32 zero, u32 mach, u32 *atags)
{
	volatile unsigned char *fb = (volatile unsigned char *)FB;
	u32 x, y, i, *s, *d;
	for (y = 0; y < H; y++) {
		unsigned char r = 0, g = 0, b = 0;
		if (y < 24) r = g = b = 255;
		else if (y < 320) r = 255;
		else if (y < 640) g = 255;
		else b = 255;
		for (x = 0; x < W; x++) {
			volatile unsigned char *p = fb + y * STRIDE + x * 3;
			p[0] = r; p[1] = g; p[2] = b;
		}
	}
	/* hold ~8 s using the DGT (6.75 MHz) if it runs, else a crude loop */
	{
		u32 a = DGT_CNT, c = a;
		for (i = 0; i < 2000 && c == a; i++) c = DGT_CNT;
		if (c != a) { u32 t0 = DGT_CNT; while ((DGT_CNT - t0) < 54000000u) ; }
		else for (i = 0; i < 0x06000000u; i++) __asm__ volatile("");
	}
	s = (u32 *)_stub_end; d = (u32 *)ZDST;
	for (i = 0; i < (ZSIZE + 3) / 4; i++) d[i] = s[i];
	((void (*)(u32, u32, u32 *))ZDST)(0, mach, atags);
	for (;;) ;
}
