import re, os
root = os.path.expanduser("~/xnu-j1/xnu")

# 1. dbg array in pe file
p = root + "/pexpert/arm/pe_msm8930_serrano.c"
s = open(p).read()
if "ios7m8930_dbg[16]" not in s:
    s += "\nunsigned int ios7m8930_dbg[16];\n"
open(p, "w").write(s)

# 2. IOService.cpp: DSM hook + park rows
p = root + "/iokit/Kernel/IOService.cpp"
s = open(p).read()
nl = chr(92) + "n"
pat = '            printf("DSM %s cnt=%d' + nl + '",getName(),(int)matches->getCount());\n'
assert pat in s, "DSM printf not found"
if "ios7m8930_dbg[0]" not in s:
    s = s.replace(pat, pat + '            { const char *nm=getName(); if(nm&&!strncmp(nm,"IOS7LeoHFSF",11)) ios7m8930_dbg[0]=(unsigned)matches->getCount()+1; if(nm&&!strncmp(nm,"IOS7LeoHFSF",11)) ios7m8930_dbg[3]++; }\n', 1)
    s = s.replace('extern "C" void ios7m8930_fb_flush_all(void);\n', 'extern "C" void ios7m8930_fb_flush_all(void);\nextern "C" unsigned int ios7m8930_dbg[16];\n', 1)
    i = s.index("        { unsigned ss[20];")
    end = "ios7m8930_hexN(24, ss[15]); }"
    j = s.index(end, i) + len(end)
    s = s[:i] + "        ios7m8930_hexN(17, ios7m8930_dbg[0]); ios7m8930_hexN(18, ios7m8930_dbg[1]); ios7m8930_hexN(19, ios7m8930_dbg[2]); ios7m8930_hexN(20, ios7m8930_dbg[3]);" + s[j:]
open(p, "w").write(s)

# 3. HFS file driver counters
p = root + "/iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/IOS7LeoHFSFile.cpp"
s = open(p).read()
if "ios7m8930_dbg" not in s:
    s = s.replace("bool IOS7LeoHFSDriver::start(IOService *provider)\n{\n", "bool IOS7LeoHFSDriver::start(IOService *provider)\n{\n ios7m8930_dbg[1]++;\n", 1)
    s = s.replace("IOMedia *IOS7LeoHFSDriver::instantiateMediaObject(UInt64 base,UInt64 bytes,UInt32 block,char *name)\n{\n", "IOMedia *IOS7LeoHFSDriver::instantiateMediaObject(UInt64 base,UInt64 bytes,UInt32 block,char *name)\n{\n ios7m8930_dbg[2]++;\n", 1)
    s = s.replace('extern "C" void ios7m8930_mark(unsigned int n);\n', 'extern "C" void ios7m8930_mark(unsigned int n);\nextern "C" unsigned int ios7m8930_dbg[16];\n', 1)
open(p, "w").write(s)
print("patched")
