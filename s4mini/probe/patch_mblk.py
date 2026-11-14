import os
d = os.path.expanduser("~/xnu-j1/xnu/iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/")

# ---- eMMC driver: CMD18 multi-block reads ----
p = d + "IOS7M8930SDMMC.cpp"
s = open(p).read()
assert "readBlocks" not in s
a = "int IOS7M8930SDMMC::sw(UInt32 idx,UInt32 val)\n"
assert a in s
mb = r'''/* Multi-block PIO read: CMD18 for n (<=64) sectors, then CMD12. Falls back to CMD17 on any error. */
int IOS7M8930SDMMC::readBlocks(UInt64 lba,UInt32 n,UInt8 *out)
{
 UInt32 resp[4],i,w,words=n*128U; UInt32 *o=(UInt32*)out;
 UInt64 st,lim=6750000ULL;	/* 1 s */
 if(n==1) return readSector(lba,out);
 wr(R_CLEAR,CLEAR_ALL);
 wr(R_DTIMER,0xFFFFFFFFU);
 wr(R_DLEN,n*512U);
 wr(R_DCTL,1U|(1U<<1)|(512U<<4));
 int r=cmd(18,(UInt32)(lba+USERDATA_LBA),CMD_RESP|CMD_DAT,resp);
 if(r){ errs++; g_errs=errs; wr(R_DCTL,0); cmd(12,0,CMD_RESP,resp); return r; }
 st=mach_absolute_time();
 for(i=0;i<words;){
  UInt32 s=rd(R_STATUS);
  if(s&(S_DATACRC|S_DATATO|S_RXOVR|S_STARTERR)){ errs++; g_errs=errs; g_laststat=s; wr(R_CLEAR,CLEAR_ALL); wr(R_DCTL,0); cmd(12,0,CMD_RESP,resp); return -4; }
  if(s&S_RXAVL){ w=rd(R_FIFO+((i*4U)&63U)); o[i++]=w; continue; }
  if(mach_absolute_time()-st>lim){ errs++; g_errs=errs; wr(R_DCTL,0); cmd(12,0,CMD_RESP,resp); return -5; }
 }
 st=mach_absolute_time();
 while(!(rd(R_STATUS)&S_DATAEND)){ if(mach_absolute_time()-st>lim) break; }
 wr(R_CLEAR,CLEAR_ALL); wr(R_DCTL,0);
 r=cmd(12,0,CMD_RESP,resp);
 /* wait for the card to leave the programming/data state before the next command */
 st=mach_absolute_time();
 while(cmd(13,rca<<16,CMD_RESP,resp)==0 && ((resp[0]>>9)&15U)!=4U){ if(mach_absolute_time()-st>lim) break; }
 return 0;
}
'''
s = s.replace(a, mb + a, 1)
a = "int IOS7M8930SDMMC::cmd(UInt32 idx,UInt32 arg,UInt32 flags,UInt32 *resp)\n"
# declaration: add next to readSector declaration
decl_old = "int readSector(UInt64 lba,UInt8 *out);"
if decl_old not in s:
    import re
    m = re.search(r"int\s+readSector\([^)]*\);", s)
    assert m, "readSector decl"
    decl_old = m.group(0)
s = s.replace(decl_old, decl_old + " int readBlocks(UInt64,UInt32,UInt8 *);", 1)
old_loop = """ for(UInt64 i=0;i<count&&result==kIOReturnSuccess;i++){
  int rc=readSector(block+i,tmp+i*512U); g_reads++; g_lastrc=(unsigned)rc; g_lastblk=block+i;
  if(rc){ rc=readSector(block+i,tmp+i*512U); }	/* one retry */
  if(rc) result=kIOReturnIOError;
 }
"""
assert old_loop in s
new_loop = """ for(UInt64 i=0;i<count&&result==kIOReturnSuccess;){
  UInt32 n=(count-i>64U)?64U:(UInt32)(count-i);
  int rc=readBlocks(block+i,n,tmp+i*512U); g_reads++; g_lastrc=(unsigned)rc; g_lastblk=block+i;
  if(rc){	/* fall back to single sectors, one retry each */
   for(UInt32 k=0;k<n&&result==kIOReturnSuccess;k++){
    rc=readSector(block+i+k,tmp+(i+k)*512U);
    if(rc) rc=readSector(block+i+k,tmp+(i+k)*512U);
    if(rc) result=kIOReturnIOError;
   }
  }
  i+=n;
 }
"""
s = s.replace(old_loop, new_loop, 1)
open(p, "w").write(s)

# ---- COW: expose page lookup ----
p = d + "leo_cow.h"
s = open(p).read()
if "leo_cow_page_present" not in s:
    s = s.replace("int leo_cow_read_sector(leo_cow *,uint64_t,uint8_t[512]);",
                  "int leo_cow_read_sector(leo_cow *,uint64_t,uint8_t[512]);\nint leo_cow_page_present(leo_cow *,uint64_t);", 1)
    open(p, "w").write(s)
p = d + "leo_cow.c"
s = open(p).read()
if "leo_cow_page_present" not in s:
    a = "int leo_cow_read_sector(leo_cow *c,uint64_t sector,uint8_t out[512])\n"
    assert a in s
    s = s.replace(a, "/* 1 if the 4 KiB page holding this sector has a private (copied) version */\nint leo_cow_page_present(leo_cow *c,uint64_t sector)\n{\n if(!c||sector>=c->sectors)return 0;\n return lookup(c,(uint32_t)(sector>>3),0)?1:0;\n}\n" + a, 1)
    open(p, "w").write(s)

# ---- HFS file layer: batched reads of clean runs ----
p = d + "IOS7LeoHFSFile.cpp"
s = open(p).read()
assert "readRun" not in s
a = "IOReturn IOS7LeoHFSFile::readPhysical(UInt64 lba,UInt8 bytes[512])\n"
assert a in s
rr = r'''/* Read n contiguous physical sectors into dst (n <= LEO_RUN_MAX) with one request. */
IOReturn IOS7LeoHFSFile::readRun(UInt64 lba,UInt32 n,IOMemoryDescriptor *dst,IOByteCount dstOff)
{
 if(!rawOpened||!raw||!runBounce||!n||n>LEO_RUN_MAX||lba>=rawSectors||n>rawSectors-lba)return kIOReturnBadArgument;
 UInt64 actual=0;
 runBounce->setLength((IOByteCount)n*512U);
 IOReturn result=raw->read(this,lba<<9,runBounce,&actual);
 if(result==kIOReturnSuccess&&actual!=(UInt64)n*512U)result=kIOReturnUnderrun;
 if(result==kIOReturnSuccess&&dst->writeBytes(dstOff,runBounce->getBytesNoCopy(),(IOByteCount)n*512U)!=(IOByteCount)n*512U)result=kIOReturnUnderrun;
 return result;
}
'''
s = s.replace(a, rr + a, 1)
a = " IOReturn readPhysical(UInt64,UInt8 [512]);\n"
assert a in s
s = s.replace(a, a + " IOReturn readRun(UInt64,UInt32,IOMemoryDescriptor *,IOByteCount);\n", 1)
# member + constant: put after the class's first member area via readPhysical decl
s = s.replace(" IOReturn readRun(UInt64,UInt32,IOMemoryDescriptor *,IOByteCount);\n",
              " IOReturn readRun(UInt64,UInt32,IOMemoryDescriptor *,IOByteCount);\n IOBufferMemoryDescriptor *runBounce;\n", 1)
if "#define LEO_RUN_MAX" not in s:
    s = s.replace("class IOS7LeoHFSFile", "#define LEO_RUN_MAX 256U\nclass IOS7LeoHFSFile", 1)

old = """  if(direction==kIODirectionIn){
   int cr=leo_cow_read_sector(&cow,block+index,bytes);backendFailed=cr==LEO_COW_IO;result=cowResult(&cow,cr);
   if(result==kIOReturnSuccess&&buffer->writeBytes((IOByteCount)completed,bytes,512)!=512)result=kIOReturnUnderrun;
  }else{"""
assert old in s
new = """  if(direction==kIODirectionIn){
   /* fast path: a run of sectors with no private COW copy is read straight from the image extents */
   if(runBounce&&!leo_cow_page_present(&cow,block+index)){
    uint64_t physical=0;uint32_t run=0;
    if(fl32_translate(&image,extents,LEO_EXTENT_CAP,block+index,&physical,&run)==FL32_OK&&run>1U){
     UInt64 n=count-index;if(n>run)n=run;if(n>LEO_RUN_MAX)n=LEO_RUN_MAX;
     UInt64 k;for(k=1;k<n;k++)if(((block+index+k)&7U)==0&&leo_cow_page_present(&cow,block+index+k))break;
     n=k;
     if(n>1U){
      result=readRun(physical,(UInt32)n,buffer,(IOByteCount)completed);
      if(result!=kIOReturnSuccess)backendFailed=true;
      else{completed+=n*512U;index+=n-1U;}
      continue;
     }
    }
   }
   int cr=leo_cow_read_sector(&cow,block+index,bytes);backendFailed=cr==LEO_COW_IO;result=cowResult(&cow,cr);
   if(result==kIOReturnSuccess&&buffer->writeBytes((IOByteCount)completed,bytes,512)!=512)result=kIOReturnUnderrun;
  }else{"""
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("ok")

p = d + "IOS7LeoHFSFile.cpp"
s = open(p).read()
a = "raw=0;bounce=0;"
assert a in s
s = s.replace(a, "raw=0;bounce=0;runBounce=0;", 1)
a = "mutex=IOLockAlloc();bounce=IOBufferMemoryDescriptor::withOptions(kIODirectionIn,512,4);"
assert a in s
s = s.replace(a, a + "runBounce=IOBufferMemoryDescriptor::withOptions(kIODirectionIn,LEO_RUN_MAX*512U,4096);", 1)
a = "if(bounce)bounce->release();"
assert a in s
s = s.replace(a, a + "if(runBounce)runBounce->release();", 1)
open(p, "w").write(s)
print("ok2")
