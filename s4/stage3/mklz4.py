#!/usr/bin/env python3
"""Raw LZ4 block compressor (greedy) -> single block, no frame. usage: mklz4.py in out"""
import sys,struct
def compress(d):
    n=len(d); out=bytearray(); ht={}; i=0; anchor=0
    limit=n-12  # last match must start before n-12; last 5 bytes literals
    def emit(lit_start,lit_end,off,mlen):
        ll=lit_end-lit_start; tok=min(ll,15)<<4
        ml=mlen-4 if mlen else 0
        if mlen: tok|=min(ml,15)
        out.append(tok)
        if ll>=15:
            r=ll-15
            while r>=255: out.append(255); r-=255
            out.append(r)
        out.extend(d[lit_start:lit_end])
        if mlen:
            out.extend(struct.pack('<H',off))
            if ml>=15:
                r=ml-15
                while r>=255: out.append(255); r-=255
                out.append(r)
    while i<limit:
        key=d[i:i+4]; cand=ht.get(key); ht[key]=i
        if cand is not None and i-cand<=65535 and d[cand:cand+4]==key:
            m=4; maxm=n-5-i
            while m<maxm and d[cand+m]==d[i+m]: m+=1
            emit(anchor,i,i-cand,m)
            for j in range(i+1,min(i+m,limit)): ht[d[j:j+4]]=j
            i+=m; anchor=i
        else: i+=1
    emit(anchor,n,0,0)
    return bytes(out)
def decompress(c,size):
    o=bytearray(); i=0
    while i<len(c):
        t=c[i]; i+=1; ll=t>>4
        if ll==15:
            while True:
                b=c[i]; i+=1; ll+=b
                if b!=255: break
        o+=c[i:i+ll]; i+=ll
        if i>=len(c): break
        off=c[i]|(c[i+1]<<8); i+=2; ml=t&15
        if ml==15:
            while True:
                b=c[i]; i+=1; ml+=b
                if b!=255: break
        ml+=4
        for _ in range(ml): o.append(o[-off])
    return bytes(o)
if __name__=="__main__":
    d=open(sys.argv[1],'rb').read(); c=compress(d)
    assert decompress(c,len(d))==d, "roundtrip failed"
    open(sys.argv[2],'wb').write(c); print(len(d),'->',len(c))
