p="/home/user/xnu-j1/xnu/pexpert/arm/pe_msm8930_serrano.c"
L=open(p).read().split("\n")
def sub(lo,hi,pairs):
    for i in range(lo-1,hi):
        for a,b in pairs: L[i]=L[i].replace(a,b)
sub(336,337,[("v_rowBytes=2160","v_rowBytes=1080"),("v_width=540","v_width=270"),("v_height=960","v_height=480")])
sub(350,351,[("960U*2160U","480U*1080U"),("v_width=540","v_width=270"),("v_height=960","v_height=480"),("v_rowBytes=2160","v_rowBytes=1080")])
sub(369,425,[("540U","270U"),("960U","480U"),("< 540","< 270"),("> 960","> 480"),("> 540","> 270")])
s="\n".join(L)
# flush: 2x nearest-neighbour upscale of a 270x480 console
a=s.index("  src=(const unsigned char *)j1_pixels+y*(M8930_W*4U);")
b=s.index(" }\n}",a)
new='''  src=(const unsigned char *)j1_pixels+(y>>1)*(270U*4U);
  dst=(volatile unsigned int *)(m8930_scan_map+y*1620U);
  for(x=0;x<270;x+=2){
   /* 2 BGRA console pixels -> 4 RGB scanout pixels (2x zoom) = 12 bytes */
   unsigned int r0=src[2],g0=src[1],b0=src[0],r1=src[6],g1=src[5],b1=src[4];
   dst[0]=r0|(g0<<8)|(b0<<16)|(r0<<24);
   dst[1]=g0|(b0<<8)|(r1<<16)|(g1<<24);
   dst[2]=b1|(r1<<8)|(g1<<16)|(b1<<24);
   dst+=3; src+=8;
  }
'''
s=s[:a]+new+s[b:]
open(p,"w").write(s)
