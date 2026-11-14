p="/home/user/xnu-j1/xnu/osfmk/arm/locore.s"; L=open(p).read().split("\n")
for i,l in enumerate(L):
    if "500*1620" in l and "LoadConstantToReg" in l:
        L[i]=r"    LoadConstantToReg(((\fbp) + 500*1620 + (\idx)*48), r2)"
    if "mov     r1, #16" in l: pass
open(p,"w").write("\n".join(L))
print([l for l in L if "500*1620" in l])
