import os
p = os.path.expanduser("~/xnu-j1/xnu/osfmk/kern/debug.c")
s = open(p).read()
a = """	va_list	listp;
	spl_t	s;

	if(enable_timing)
		enable_timing = 0;
"""
assert a in s
b = """	va_list	listp;
	spl_t	s;

#if defined(BOARD_CONFIG_MSM8930_SERRANO)
	{	/* DEBUG: panics are otherwise invisible (console is flushed from the timer IRQ only) */
		extern void ios7m8930_hexN(unsigned int row, unsigned int v);
		extern void ios7m8930_fb_flush_all(void);
		extern int printf(const char *, ...);
		static int once;
		ios7m8930_hexN(15, 0xDEAD0000U | (unsigned)(once & 0xffff));
		ios7m8930_hexN(16, ((unsigned int)__builtin_return_address(0)) & ~1U);
		if (!once++) {
			va_list l2;
			printf("\\nPANIC caller=%08x: ", ((unsigned int)__builtin_return_address(0)) & ~1U);
			va_start(l2, str);
			_doprnt(str, &l2, conslog_putc, 0);
			va_end(l2);
			printf("\\n");
			ios7m8930_fb_flush_all();
		}
	}
#endif
	if(enable_timing)
		enable_timing = 0;
"""
s = s.replace(a, b, 1)
open(p, "w").write(s)
print("panic patched")
