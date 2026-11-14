p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; s=open(p).read()
old=r"    LoadConstantToReg(((\fbp) + 500*1620 + (\idx)*48), r2)"
assert old in s
s=s.replace(old, r"    LoadConstantToReg(((\fbp) + 500*1620 + 1500 - (\idx)*48), r2)",1)
open(p,"w").write(s)
p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
s=s.replace("xo=(n%40U)*13U,","xo=520U-(n%40U)*13U,",1)
open(p,"w").write(s); print("ok")
