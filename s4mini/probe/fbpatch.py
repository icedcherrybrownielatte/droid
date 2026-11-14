import sys
p = sys.argv[1]
s = open(p).read()
old = "\t(void)zimage;\n\twdt_write(WDT_EN, 0);\n"
new = r'''	(void)zimage;
	{	/* DEBUG: append the APCS WDT block state to XNU's persistent trace (ram_console at
		 * 0x8fe00000, marker at +0x60000) so TWRP's last_kmsg shows why the last boot reset. */
		volatile unsigned char *rb = (volatile unsigned char *)0x8fe00000u;
		volatile unsigned int *mk = (volatile unsigned int *)(0x8fe00000u + 0x60000u);
		static const char hx[] = "0123456789abcdef";
		const char *t = "\nUNILOADER fallback: WDT 38..5c =";
		unsigned int idx, k, o, v;
		if (mk[0] == 0x584E5542u && mk[1] > 16u && mk[1] < 0x4B000u - 0x1000u) {
			idx = mk[1];
#define FBPUT(ch) do { rb[12u + idx] = (unsigned char)(ch); idx++; } while (0)
			while (*t) FBPUT(*t++);
			for (o = 0x38u; o <= 0x5cu; o += 4u) {
				v = *(volatile unsigned int *)(0x0208A000u + o);
				FBPUT(' ');
				for (k = 0; k < 8u; k++) FBPUT(hx[(v >> (28u - 4u * k)) & 15u]);
			}
			FBPUT('\n');
#undef FBPUT
			mk[1] = idx;
			*(volatile unsigned int *)(0x8fe00000u + 4u) = idx;
			*(volatile unsigned int *)(0x8fe00000u + 8u) = idx;
		}
	}
	wdt_write(WDT_EN, 0);
'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("ok")
