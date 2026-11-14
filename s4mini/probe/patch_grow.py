import os
d = os.path.expanduser("~/xnu-j1/xnu/iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/")
p = d + "IOS7LeoHFSFile.cpp"
s = open(p).read()
assert "vsectors" not in s

# constants + member
s = s.replace("#define LEO_RUN_MAX 256U\n",
              "#define LEO_RUN_MAX 256U\n"
              "/* The restore-built HFSX volume has 0 free blocks. Present it 1 GiB larger: header blocks are\n"
              " * patched on the fly, reads past the backing file return zeros, writes go to the COW overlay. */\n"
              "#define LEO_GROW_BLOCKS 262144U\n", 1)
a = " IOBufferMemoryDescriptor *runBounce;\n"
assert a in s
s = s.replace(a, a + " UInt64 vsectors;\n", 1)

# every size/bounds use of image.image_sectors in this file becomes the virtual size
s = s.replace("image.image_sectors", "vsectors")
# ...except where the backing extents are translated (fl32 keeps its own image.image_sectors internally)

# set vsectors once the file is validated
a = " initialized=true;\n if(!initializeCow())"
assert a in s
s = s.replace(a, " vsectors=image.image_sectors+(UInt64)LEO_GROW_BLOCKS*(image.hfs_block_bytes/512U);\n" + a, 1)
# that line now reads vsectors=vsectors+...; fix it to use the real size
s = s.replace(" vsectors=vsectors+(UInt64)LEO_GROW_BLOCKS*(image.hfs_block_bytes/512U);",
              " vsectors=(UInt64)image.file_bytes/512U+(UInt64)LEO_GROW_BLOCKS*(image.hfs_block_bytes/512U);", 1)

# base reads: zero past the file, patch the volume headers
old = """int IOS7LeoHFSFile::readImageBase(void *cookie,uint64_t logical,uint8_t out[512])
{
 IOS7LeoHFSFile *file=(IOS7LeoHFSFile *)cookie;uint64_t physical=0;uint32_t run=0;
 if(fl32_translate(&file->image,file->extents,LEO_EXTENT_CAP,logical,&physical,&run)!=FL32_OK)return (int)kIOReturnBadArgument;
 return (int)file->readPhysical(physical,out);
}"""
assert old in s
new = """int IOS7LeoHFSFile::readImageBase(void *cookie,uint64_t logical,uint8_t out[512])
{
 IOS7LeoHFSFile *file=(IOS7LeoHFSFile *)cookie;uint64_t physical=0;uint32_t run=0;
 uint64_t real=(uint64_t)file->image.file_bytes/512U;
 bool header=(logical==2U)||(logical==file->vsectors-2U);
 uint64_t src=header?2U:logical;
 if(src>=real){bzero(out,512);return 0;}
 if(fl32_translate(&file->image,file->extents,LEO_EXTENT_CAP,src,&physical,&run)!=FL32_OK)return (int)kIOReturnBadArgument;
 int r=(int)file->readPhysical(physical,out);
 if(r==0&&header&&((out[0]=='H'&&out[1]=='+')||(out[0]=='H'&&out[1]=='X'))){
  uint32_t total=((uint32_t)out[44]<<24)|((uint32_t)out[45]<<16)|((uint32_t)out[46]<<8)|out[47];
  uint32_t freeb=((uint32_t)out[48]<<24)|((uint32_t)out[49]<<16)|((uint32_t)out[50]<<8)|out[51];
  total+=LEO_GROW_BLOCKS;freeb+=LEO_GROW_BLOCKS;
  out[44]=(uint8_t)(total>>24);out[45]=(uint8_t)(total>>16);out[46]=(uint8_t)(total>>8);out[47]=(uint8_t)total;
  out[48]=(uint8_t)(freeb>>24);out[49]=(uint8_t)(freeb>>16);out[50]=(uint8_t)(freeb>>8);out[51]=(uint8_t)freeb;
 }
 return r;
}"""
s = s.replace(old, new, 1)

# fast path must not cover the patched header sector or anything beyond the backing file
old = "   if(runBounce&&!leo_cow_page_present(&cow,block+index)){"
assert old in s
s = s.replace(old, "   if(runBounce&&block+index>=8U&&block+index+LEO_RUN_MAX<=(UInt64)image.file_bytes/512U&&!leo_cow_page_present(&cow,block+index)){", 1)
open(p, "w").write(s)
print("ok")
