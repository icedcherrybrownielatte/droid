"""One-off: 64-bit FIFO support + debug in ja3g_sdmmc.inc (Exynos5 dw_mmc has a 64-bit data FIFO)."""
BS = chr(92)
p = 'ja3g_sdmmc.inc'
s = open(p, newline='').read()


def rep(o, n):
    global s
    assert s.count(o) == 1, (o[:60], s.count(o))
    s = s.replace(o, n)


rep("#define R_VERID\t\t0x06C\n", "#define R_VERID\t\t0x06C\n#define R_HCON\t\t0x070\n")
rep(" IOLock *mutex; bool initialized; UInt32 rca; UInt32 errs; UInt32 dataOff;",
    " IOLock *mutex; bool initialized; UInt32 rca; UInt32 errs; UInt32 dataOff; UInt32 fifo64;")
rep("  while(c--&&i<words) o[i++]=regs[dataOff/4];",
    "  if(fifo64){\t/* 64-bit FIFO (HCON data width 2): FCNT counts 64-bit entries, read them whole */\n"
    "   while(c--&&i+1<words){ UInt64 v=*(volatile UInt64 *)((volatile UInt8 *)regs+dataOff); o[i++]=(UInt32)v; o[i++]=(UInt32)(v>>32); }\n"
    "  } else\n"
    "   while(c--&&i<words) o[i++]=regs[dataOff/4];")
rep(" mmio=0; map=0; regs=0; mutex=0; initialized=false; rca=1; errs=0; dataOff=0x200;",
    " mmio=0; map=0; regs=0; mutex=0; initialized=false; rca=1; errs=0; dataOff=0x200; fifo64=0;")
rep(" dataOff=(ver<0x240aU)?0x100U:0x200U;",
    " dataOff=(ver<0x240aU)?0x100U:0x200U;\n fifo64=(((rd(R_HCON)>>7)&7U)==2U);\n"
    ' printf("J5410 eMMC: HCON=%08x fifo64=%u data@%x' + BS + 'n",(unsigned)rd(R_HCON),(unsigned)fifo64,(unsigned)dataOff);')
rep('p1type=%02x' + BS + 'n",r,(unsigned)g_lastint,sec[510],sec[511],sec[450]);',
    'p1type=%02x w0=%08x w111=%08x' + BS + 'n",r,(unsigned)g_lastint,sec[510],sec[511],sec[450],((UInt32*)sec)[0],((UInt32*)sec)[111]);')
open(p, 'w', newline='').write(s)
print('ok')
