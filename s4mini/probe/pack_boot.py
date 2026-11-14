import struct,hashlib,sys
src,dst=sys.argv[1],sys.argv[2]
d=open('../backup/boot.img','rb').read(); hdr=bytearray(d[:2048]); page=2048
pad=lambda b: b+b'\0'*((-len(b))%page)
k=open(src,'rb').read(); r=b'\0'*2048
struct.pack_into('<I',hdr,8,len(k)); struct.pack_into('<I',hdr,16,len(r))
sha=hashlib.sha1()
for b in (k,r,b''): sha.update(b); sha.update(struct.pack('<I',len(b)))
hdr[576:608]=sha.digest().ljust(32,b'\0')
img=bytes(hdr)+pad(k)+pad(r)+b'SEANDROIDENFORCE'
assert len(img)<=10*1024*1024,len(img)
open(dst,'wb').write(img.ljust(10*1024*1024,b'\0')); print(len(img))
