import os,re
root=os.path.expanduser("~/xnu-j1/xnu")
p=root+"/iokit/Kernel/IOService.cpp"
s=open(p).read()
s=re.sub(r"        \+\+pn; ios7m8930_hexN\(13, ios7m8930_dbg\[0\]\);[^\n]*\n","        ++pn;\n",s)
open(p,"w").write(s)
p=root+"/pexpert/arm/msm8930_timer.c"
s=open(p).read()
a="\t\t(void)dgt_get_count();"
assert a in s
if "ios7m8930_hexN(13" not in s:
    s=s.replace(a,"\t\t{ extern void ios7m8930_hexN(unsigned int,unsigned int); uint32_t *cx=(uint32_t *)context; if (!(m_irqs & 15U)) { ios7m8930_hexN(13, cx[15]); ios7m8930_hexN(14, cx[14]); ios7m8930_hexN(15, cx[16]); } }\n"+a,1)
open(p,"w").write(s)
print("ok")
