import struct,sys,os
src,dst=sys.argv[1],sys.argv[2]
# --- patch the HFSX volume: truncate to exact volume size, clear journaled bit + journalInfoBlock in both headers
f=open(src,'r+b'); f.seek(1024); h=bytearray(f.read(512))
bs,tb=struct.unpack('>II',h[40:48]); vol=bs*tb
f.truncate(vol)
def patch(off):
    f.seek(off); b=bytearray(f.read(512))
    a=struct.unpack('>I',b[4:8])[0]; a&=~0x2000; b[4:8]=struct.pack('>I',a); b[12:16]=b'\0\0\0\0'
    f.seek(off); f.write(b)
patch(1024); patch(vol-1024); f.close()
size=vol; assert size%512==0
SPC=8; RES=32; NF=2; PSTART=2048
fsz=size; fclusters=(fsz+SPC*512-1)//(SPC*512)
nclu=fclusters+2+8   # root(2), IOS(3), file from 4
# need clusters>=65525; ok
spf=((nclu+2)*4+511)//512
meta=RES+NF*spf
total=meta+(nclu)*SPC
print('file',size,'clusters',nclu,'spf',spf,'part sectors',total)
o=open(dst,'wb')
# MBR
mbr=bytearray(512)
mbr[446:462]=struct.pack('<B3sB3sII',0x80,b'\x00\x01\x01',0x0C,b'\xfe\xff\xff',PSTART,total)
mbr[510:512]=b'\x55\xaa'
o.write(mbr); o.write(b'\0'*(PSTART*512-512))
# boot sector
bsec=bytearray(512)
bsec[0:3]=b'\xeb\x58\x90'; bsec[3:11]=b'MSDOS5.0'
struct.pack_into('<HBHBHHBHHHII',bsec,11,512,SPC,RES,NF,0,0,0xF8,0,63,255,PSTART,total)
struct.pack_into('<IHHIHH',bsec,36,spf,0,0,2,1,6)
bsec[64]=0x80; bsec[66]=0x29; struct.pack_into('<I',bsec,67,0x12345678); bsec[71:82]=b'IOS7ROOT   '; bsec[82:90]=b'FAT32   '
bsec[510:512]=b'\x55\xaa'
fsi=bytearray(512); struct.pack_into('<I',fsi,0,0x41615252); struct.pack_into('<I',fsi,484,0x61417272); struct.pack_into('<II',fsi,488,0xFFFFFFFF,0xFFFFFFFF); fsi[510:512]=b'\x55\xaa'
res=bytearray(RES*512); res[0:512]=bsec; res[512:1024]=fsi; res[6*512:7*512]=bsec; res[7*512:8*512]=fsi
o.write(res)
# FAT
fat=bytearray(spf*512)
def setf(c,v): struct.pack_into('<I',fat,c*4,v)
setf(0,0x0FFFFFF8); setf(1,0x0FFFFFFF); setf(2,0x0FFFFFFF); setf(3,0x0FFFFFFF)
first=4
for i in range(fclusters):
    c=first+i; setf(c, 0x0FFFFFFF if i==fclusters-1 else c+1)
for _ in range(NF): o.write(fat)
# data area: cluster 2 = root dir, 3 = IOS dir, 4.. = file
def dent(name,attr,clu,sz):
    return name+struct.pack('<BBBHHHHHHHI',attr,0,0,0,0x21,0x21,clu>>16,0,0x21,clu&0xffff,sz)
cs=SPC*512
root=bytearray(cs); root[0:32]=dent(b'IOS7       ',0x10,3,0)
ios=bytearray(cs); ios[0:32]=dent(b'.          ',0x10,3,0); ios[32:64]=dent(b'..         ',0x10,0,0); ios[64:96]=dent(b'ROOTFS  HFS',0x20,4,size)
o.write(root); o.write(ios)
with open(src,'rb') as s:
    while True:
        b=s.read(1<<22)
        if not b: break
        o.write(b)
pad=fclusters*cs-size; o.write(b'\0'*pad)
o.write(b'\0'*(8*cs))   # trailing spare clusters
o.close(); print('image bytes',os.path.getsize(dst), 'sectors',os.path.getsize(dst)//512)
