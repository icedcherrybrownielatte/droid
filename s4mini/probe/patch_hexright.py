p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
assert "xo=20U+d*16U;" in s
s=s.replace("xo=20U+d*16U;","xo=392U+d*16U;",1)
open(p,"w").write(s); print("ok")
