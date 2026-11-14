p="/home/user/uniloader/main/main.c"; s=open(p).read()
a=s.index("static void fallback_to_android(void *zimage)")
b=s.index("#endif\n",a)
new=r'''static void fallback_to_android(void *zimage)
{
	(void)zimage;
	wdt_write(WDT_EN, 0);
	printk(KERN_INFO, "fallback: previous XNU attempt did not finish -> rebooting to recovery\n");
	{
		volatile unsigned int w;

		for (w = 0; w < 0x02000000; w++)
			;
	}
	/* Same thing `reboot recovery` does in the Samsung kernel (restart.c): IMEM restart
	 * reason 0x77665502 (read by aboot), then drop PS_HOLD to power-cycle the PMIC. */
	*(volatile unsigned int *)0x2A00065Cu = 0x77665502;
	*(volatile unsigned int *)0x00800820u = 0;
	for (;;)
		;
}
'''
s=s[:a]+new+s[b:]
open(p,"w").write(s)
