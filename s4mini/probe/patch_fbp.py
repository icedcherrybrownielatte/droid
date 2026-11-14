p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
s=s.replace(r"((bp) + 500*1620", r"((\fbp) + 500*1620")
open(p,"w").write(s)
import re
print([l for l in s.split("\n") if "500*1620" in l])
