import sys,struct,zlib,plistlib
src,dst=sys.argv[1],sys.argv[2]
f=open(src,'rb'); f.seek(-512,2); k=f.read(512)
assert k[:4]==b'koly'
xo,xl=struct.unpack('>QQ',k[0xD8:0xE8])
f.seek(xo); pl=plistlib.loads(f.read(xl))
o=open(dst,'wb'); tot=0
for b in pl['resource-fork']['blkx']:
    d=b['Data']; assert d[:4]==b'mish'
    first,cnt,dataoff=struct.unpack('>QQQ',d[8:32]); n=struct.unpack('>I',d[200:204])[0]
    for i in range(n):
        e=d[204+40*i:244+40*i]
        t,_,so,sc,co,cl=struct.unpack('>IIQQQQ',e)
        if t in(0x7ffffffe,0xffffffff): break
        if t==0x7ffffffe: continue
        pos=so*512; o.seek(first*512+pos) if False else None
        want=(first+so)*512
        o.seek(want)
        if t==0x80000005: f.seek(dataoff+co); o.write(zlib.decompress(f.read(cl)))
        elif t==1: f.seek(dataoff+co); o.write(f.read(cl))
        elif t in(0,2): o.write(b'\0'*(sc*512))
        else: raise SystemExit('type %x'%t)
        tot=max(tot,want+sc*512)
o.truncate(tot); o.close(); print('raw size',tot)
