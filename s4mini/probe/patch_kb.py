import re
p="/home/user/xnu-j1/xnu/osfmk/kern/startup.c"; s=open(p).read()
a=s.index("kernel_bootstrap(void)\n{")
b=s.index("\n}\n",a)
body=s[a:b].split("\n")
out=[]; mapping=[]; k=0
for l in body:
    out.append(l)
    if re.match(r"^\t[A-Za-z_][A-Za-z_0-9]*\(.*\);\s*$",l) and "kernel_bootstrap_kprintf" not in l and "panic" not in l:
        out.append("\tMARKKB(%d);"%(300+k)); mapping.append((300+k,l.strip())); k+=1
s=s[:a]+"\n".join(out)+s[b:]
hdr='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
extern void ios7m8930_mark(unsigned int n);
#define MARKKB(n) ios7m8930_mark(n)
#else
#define MARKKB(n) do{}while(0)
#endif
'''
i=s.rfind("\n\n",0,a)
s=s[:i]+"\n"+hdr+s[i:]
open(p,"w").write(s)
open("/mnt/c/Users/User/Desktop/Droid/s4mini/probe/kb_marks.txt","w").write("\n".join("%d (0x%X): after %s"%(n,n,t) for n,t in mapping))
print(len(mapping))
# machine_startup marks
p="/home/user/xnu-j1/xnu/osfmk/arm/model_dep.c"; s=open(p).read()
if "MARKMS" not in s:
    s=s.replace("void machine_startup(void)\n{\n    machine_conf();","#if defined(BOARD_CONFIG_MSM8930_SERRANO)\nextern void ios7m8930_mark(unsigned int n);\n#define MARKMS(n) ios7m8930_mark(n)\n#else\n#define MARKMS(n) do{}while(0)\n#endif\nvoid machine_startup(void)\n{\n    MARKMS(210);\n    machine_conf();\n    MARKMS(211);",1)
    s=s.replace("    kernel_bootstrap();\n    return;","    MARKMS(212);\n    kernel_bootstrap();\n    return;",1)
    open(p,"w").write(s)
print("ok")
