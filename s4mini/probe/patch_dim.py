p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
assert "p[0]=p[1]=p[2]=on?255:0;" in s
s=s.replace("p[0]=p[1]=p[2]=on?255:0;","p[0]=p[1]=p[2]=on?90:0;",1)
open(p,"w").write(s); print("ok")
