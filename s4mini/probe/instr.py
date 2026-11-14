#!/usr/bin/env python3
"""instr.py <file> <func-signature-start> <base> : insert MARKI(n) after each one-tab-indented call statement of the function."""
import re,sys
p,sig,base=sys.argv[1],sys.argv[2],int(sys.argv[3])
s=open(p).read()
a=s.index(sig+"\n{") if (sig+"\n{") in s else s.index(sig)
a=s.index("{",a)
# find end of function: first "\n}\n" after a
b=s.index("\n}\n",a)
body=s[a:b].split("\n")
out=[];k=0;mp=[]
for l in body:
    out.append(l)
    if re.match(r"^\t[A-Za-z_][A-Za-z_0-9]*\(.*\);\s*$",l) and "panic" not in l:
        out.append("\tMARKI(%d);"%(base+k)); mp.append((base+k,l.strip())); k+=1
s=s[:a]+"\n".join(out)+s[b:]
hdr='''#if defined(BOARD_CONFIG_MSM8930_SERRANO)
#ifndef MARKI
extern void ios7m8930_mark(unsigned int n);
#define MARKI(n) ios7m8930_mark(n)
#endif
#else
#ifndef MARKI
#define MARKI(n) do{}while(0)
#endif
#endif
'''
if "define MARKI" not in s:
    i=s.index(sig)
    j=s.rfind("\n\n",0,i)
    s=s[:j]+"\n"+hdr+s[j:]
open(p,"w").write(s)
with open("/mnt/c/Users/User/Desktop/Droid/s4mini/probe/marks_map.txt","a") as f:
    for n,t in mp: f.write("%d (0x%X): after %s [%s]\n"%(n,n,t,sig))
print(len(mp),"marks")
