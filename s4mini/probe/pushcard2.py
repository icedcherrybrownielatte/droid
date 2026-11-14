import subprocess,hashlib,os,sys
A='../../tools/platform-tools-dl/platform-tools/adb.exe'
SRC='../../ipsw_x/card.img'; DEV='/dev/block/mmcblk0p24'; CH=64<<20
def sh(c): return subprocess.run([A,'shell',c],capture_output=True,text=True).stdout
size=os.path.getsize(SRC); n=(size+CH-1)//CH
f=open(SRC,'rb'); bad=0
for i in range(n):
    f.seek(i*CH); data=f.read(CH); l=hashlib.md5(data).hexdigest(); cnt=(len(data)+(1<<20)-1)>>20
    # compare only len(data) bytes on device
    def devmd5():
        return sh('dd if=%s bs=1048576 skip=%d count=%d 2>/dev/null | head -c %d | md5sum'%(DEV,i*64,cnt,len(data))).split()[0]
    if devmd5()==l: print(i,'ok',flush=True); continue
    for attempt in range(4):
        open('chunk.bin','wb').write(data)
        subprocess.run([A,'push','chunk.bin','/cache/chunk.bin'],capture_output=True)
        r=sh('md5sum /cache/chunk.bin').split()[0]
        if r!=l: print(i,'push mismatch, retry',flush=True); continue
        sh('dd if=/cache/chunk.bin of=%s bs=1048576 seek=%d 2>/dev/null; sync'%(DEV,i*64))
        if devmd5()==l: print(i,'written+verified',flush=True); break
        print(i,'dev mismatch, retry',flush=True)
    else:
        print(i,'FAILED'); bad+=1
print('DONE bad=',bad)
