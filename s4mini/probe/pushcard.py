import subprocess,hashlib,time
A='../../tools/platform-tools-dl/platform-tools/adb.exe'
src='../../ipsw_x/card.img'
p=subprocess.Popen([A,'exec-in','dd of=/dev/block/mmcblk0p24 bs=1048576'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
h=hashlib.md5(); n=0; t=time.time()
with open(src,'rb') as f:
    while True:
        b=f.read(1<<20)
        if not b: break
        p.stdin.write(b); h.update(b); n+=len(b)
p.stdin.close(); out=p.communicate()[0]; print(out.decode(errors='ignore')[-200:]); print(n,h.hexdigest(),time.time()-t)
open('card.md5','w').write(h.hexdigest()+' %d'%n)
