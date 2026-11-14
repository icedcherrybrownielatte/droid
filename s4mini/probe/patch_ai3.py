p="/home/user/xnu-j1/xnu/osfmk/arm/arm_init.c"; s=open(p).read()
o="    machine_startup();\n"
assert o in s
s=s.replace(o,"    MARK(207);\n    machine_startup();\n",1)
open(p,"w").write(s)
# marks inside machine_startup path: osfmk/arm/model_dep.c machine_startup -> kernel_bootstrap
p="/home/user/xnu-j1/xnu/osfmk/kern/startup.c"; s=open(p).read()
import re
print([l for l in s.split("\n") if "kernel_bootstrap" in l][:3])
