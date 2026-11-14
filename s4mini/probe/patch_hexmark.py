p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"; s=open(p).read()
# move font+hexrow before ios7m8930_mark
a=s.index("/* 3x5 hex font drawn at 4x scale")
b=s.index("void ios7j1_stage(unsigned int n)")
block=s[a:b]
s=s[:a]+s[b:]
m=s.index("/* Progress bars painted straight")
s=s[:m]+block+s[m:]
s=s.replace(" p[0]=col[n%6][0]; p[1]=col[n%6][1]; p[2]=col[n%6][2];\n }\n}"," p[0]=col[n%6][0]; p[1]=col[n%6][1]; p[2]=col[n%6][2];\n }\n m8930_hexrow(8,n);\n}",1)
open(p,"w").write(s); print("ok")
