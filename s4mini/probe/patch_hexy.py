p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
assert "yo=600U+row*26U;" in s
s=s.replace("yo=600U+row*26U;","yo=(row==8U)?430U:(600U+row*22U);",1)
open(p,"w").write(s); print("ok")
