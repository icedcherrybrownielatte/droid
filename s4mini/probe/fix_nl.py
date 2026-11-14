p="/home/user/uniloader/main/main.c"; s=open(p).read()
s=s.replace('flag set\n");','flag set\n");').replace('then Android\n");','then Android\n");')
open(p,"w").write(s)
