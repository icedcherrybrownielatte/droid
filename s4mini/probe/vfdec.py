import sys,struct,hmac,hashlib
from Crypto.Cipher import AES
src,dst,key=sys.argv[1],sys.argv[2],bytes.fromhex(sys.argv[3])
aes,hk=key[:16],key[16:36]
f=open(src,'rb'); h=f.read(0x60)
bs=struct.unpack('>I',h[0x34:0x38])[0]; dsz=struct.unpack('>Q',h[0x38:0x40])[0]; off=struct.unpack('>Q',h[0x40:0x48])[0]
print('blocksize',bs,'datasize',dsz,'dataoffset',off)
f.seek(off); o=open(dst,'wb'); n=0; left=dsz
while left>0:
    d=f.read(min(bs,left))
    if not d: break
    iv=hmac.new(hk,struct.pack('>I',n),hashlib.sha1).digest()[:16]
    d=d[:len(d)//16*16]; o.write(AES.new(aes,AES.MODE_CBC,iv).decrypt(d)); n+=1; left-=len(d)
o.close()
