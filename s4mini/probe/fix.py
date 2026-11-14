p="/home/user/uniloader/main/main.c"; s=open(p).read()
a=s.index("#ifdef CONFIG_SELFTEST_CHAIN"); b=s.index("\tboot_kernel(dt, kernel, ramdisk);")
new=r'''#ifdef CONFIG_SELFTEST_CHAIN
	{
		unsigned int *sv = (unsigned int *)0x80203ff8;
		unsigned int *s = (unsigned int *)kernel, *d = (unsigned int *)0x81800000, i;
		unsigned int ksz = (unsigned int)kernel_size;
		volatile unsigned int w;
		printk(KERN_INFO, "selftest: fb console OK, mach=%x atags=%x\n", sv[0], sv[1]);
		printk(KERN_INFO, "selftest: chain-loading stock zImage in ~8s\n");
		for (w = 0; w < 0x08000000; w++) ;
		for (i = 0; i < (ksz + 3) / 4; i++) d[i] = s[i];
		((void (*)(unsigned, unsigned, unsigned))0x81800000)(0, sv[0], sv[1]);
	}
#endif
'''
open(p,"w").write(s[:a]+new+s[b:])
