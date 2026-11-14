U="/home/user/uniloader/"
p=U+"Kconfig"; s=open(p).read()
s=s.replace("config SELFTEST_CHAIN","config FALLBACK_TEST_CHAIN\n\tbool \"Fallback test: chain to the embedded stock zImage immediately (no watchdog reset)\"\n\tdepends on SERRANO_FALLBACK\n\tdefault n\n\nconfig SELFTEST_CHAIN",1)
open(p,"w").write(s)
p=U+"main/main.c"; s=open(p).read()
s=s.replace("#ifdef CONFIG_SERRANO_FALLBACK\n\tif (*FB_FLAG == FB_MAGIC) {","#ifdef CONFIG_SERRANO_FALLBACK\n#ifdef CONFIG_FALLBACK_TEST_CHAIN\n\t*FB_FLAG = FB_MAGIC;\n#endif\n\tif (*FB_FLAG == FB_MAGIC) {",1)
open(p,"w").write(s)
