/* MSM8930 (Galaxy S4 mini) eMMC block device: msmsdcc (SDC1 @0x12400000) read-only PIO.
 * The Samsung aboot already powered/initialised the eMMC and left it in transfer state.
 * We (re)select it if needed, then read 512-byte sectors with CMD17 through the MCI FIFO.
 * The exposed "card" is the eMMC userdata partition (LBA window), which holds an MBR + FAT32
 * volume containing IOS7/ROOTFS.HFS, found by IOS7LeoHFSFile. Register layout = ARM PL180 /
 * Linux msm_sdcc factual numbers. */
#if defined(BOARD_CONFIG_MSM8930_SERRANO)
#include <IOKit/storage/IOBlockStorageDevice.h>
#include <IOKit/storage/IOStorage.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOCatalogue.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSUnserialize.h>
#include <kern/debug.h>
#include "IOS7LabStoragePersonalities.h"
extern "C" {
#include <mach/mach_time.h>
extern void ios7m8930_mark(unsigned int n);
extern void ios7m8930_hex9(unsigned int v);
extern void ios7m8930_hex10(unsigned int v);
extern void ios7m8930_hexN(unsigned int row,unsigned int v);
extern unsigned ios7leo_status_word(void);
extern int printf(const char *,...);
extern void ios7m8930_ioservice_stats(unsigned *o);
}
#define SDC1_PA		0x12400000U
#define USERDATA_LBA	4030464ULL
#define USERDATA_SECTORS 11239391ULL
#define R_POWER 0x00
#define R_CLOCK 0x04
#define R_ARG   0x08
#define R_CMD   0x0c
#define R_RESP  0x14
#define R_DTIMER 0x24
#define R_DLEN  0x28
#define R_DCTL  0x2c
#define R_STATUS 0x34
#define R_CLEAR 0x38
#define R_FIFO  0x80
#define S_CMDCRC (1U<<0)
#define S_DATACRC (1U<<1)
#define S_CMDTO (1U<<2)
#define S_DATATO (1U<<3)
#define S_RXOVR (1U<<5)
#define S_RESPEND (1U<<6)
#define S_CMDSENT (1U<<7)
#define S_DATAEND (1U<<8)
#define S_STARTERR (1U<<9)
#define S_RXAVL (1U<<21)
#define CMD_RESP (1U<<6)
#define CMD_LONG (1U<<7)
#define CMD_ENABLE (1U<<10)
#define CMD_DAT (1U<<12)
#define CLEAR_ALL 0x070007FFU
static volatile unsigned long g_reads; static volatile unsigned g_errs,g_lastrc,g_state,g_r0,g_sig,g_cmd13rc,g_rca,g_started; static volatile unsigned long long g_lastblk;
static volatile unsigned g_step; static volatile UInt32 *g_regs; static volatile unsigned g_clock0,g_mode,g_swrc; static volatile unsigned g_laststat,g_clock;
static void m8930_ticker(void *)
{
 for(unsigned n=0;;n++){
  IOSleep(1000);
  ios7m8930_hexN(8,(g_step<<28)|((unsigned)g_lastblk&0xffffff));
  ios7m8930_hexN(9,ios7leo_status_word());
  ios7m8930_hexN(14,(g_mode<<28)|g_swrc);
  if(n%5) continue;
  { unsigned st[3]={0,0,0}; ios7m8930_ioservice_stats(st);
  printf("SDST[%u] rd=%lu leo=%08x jobs=%u wait=%u cfg=%u\n",n,g_reads,ios7leo_status_word(),st[0],st[1],st[2]); }
  if(n>200) break;
 }
}
class IOS7M8930SDMMC : public IOBlockStorageDevice {
 OSDeclareDefaultStructors(IOS7M8930SDMMC)
 IOMemoryDescriptor *mmio; IOMemoryMap *map; volatile UInt32 *regs;
 IOLock *mutex; bool initialized; UInt32 rca; UInt32 errs;
 UInt32 rd(unsigned o){ UInt32 v=regs[o/4]; __asm__ __volatile__("dsb sy":::"memory"); return v; }
 void wr(unsigned o,UInt32 v){ __asm__ __volatile__("dsb sy":::"memory"); regs[o/4]=v; __asm__ __volatile__("dsb sy":::"memory"); }
 int cmd(UInt32 idx,UInt32 arg,UInt32 flags,UInt32 *resp);
 int readSector(UInt64 lba,UInt8 *out);
 int sw(UInt32 idx,UInt32 val);
 int tryMode(int k);
public:
 virtual bool init(OSDictionary *properties=0);
 virtual bool start(IOService *provider);
 virtual void free();
 virtual IOReturn doAsyncReadWrite(IOMemoryDescriptor *,UInt64,UInt64,IOStorageAttributes *,IOStorageCompletion *);
 virtual IOReturn doEjectMedia(){return kIOReturnUnsupported;}
 virtual IOReturn doFormatMedia(UInt64){return kIOReturnUnsupported;}
 virtual UInt32 doGetFormatCapacities(UInt64 *,UInt32)const{return 0;}
 virtual IOReturn doLockUnlockMedia(bool){return kIOReturnUnsupported;}
 virtual IOReturn doSynchronizeCache(){return kIOReturnUnsupported;}
 virtual char *getVendorString();virtual char *getProductString();
 virtual char *getRevisionString();virtual char *getAdditionalDeviceInfoString();
 virtual IOReturn reportBlockSize(UInt64 *);
 virtual IOReturn reportMaxValidBlock(UInt64 *);
 virtual IOReturn reportEjectability(bool *);
 virtual IOReturn reportLockability(bool *);
 virtual IOReturn reportRemovability(bool *);
 virtual IOReturn reportMediaState(bool *,bool *);
 virtual IOReturn reportPollRequirements(bool *,bool *);
 virtual IOReturn reportWriteProtection(bool *);
};
OSDefineMetaClassAndStructors(IOS7M8930SDMMC,IOBlockStorageDevice)
int IOS7M8930SDMMC::cmd(UInt32 idx,UInt32 arg,UInt32 flags,UInt32 *resp)
{
 UInt64 st=mach_absolute_time(), lim=6750000ULL/2ULL;	/* ~0.5 s at 6.75 MHz */
 wr(R_CLEAR,CLEAR_ALL);
 wr(R_ARG,arg);
 wr(R_CMD,(idx&0x3f)|flags|CMD_ENABLE);
 for(;;){
  UInt32 s=rd(R_STATUS);
  if(s&S_CMDTO){ wr(R_CLEAR,S_CMDTO); return -2; }
  if(s&S_CMDCRC){ if(idx!=1&&idx!=41){ wr(R_CLEAR,S_CMDCRC); return -3; } }
  if(s&(S_RESPEND|S_CMDSENT)){
   if(resp&&(flags&CMD_RESP)){ resp[0]=rd(R_RESP); if(flags&CMD_LONG){ resp[1]=rd(R_RESP+4); resp[2]=rd(R_RESP+8); resp[3]=rd(R_RESP+12);} }
   wr(R_CLEAR,S_RESPEND|S_CMDSENT|S_CMDCRC);
   return 0;
  }
  if(mach_absolute_time()-st>lim) return -1;
 }
}
int IOS7M8930SDMMC::readSector(UInt64 lba,UInt8 *out)
{
 UInt32 resp[4],i,w; UInt32 *o=(UInt32*)out;
 UInt64 st,lim=6750000ULL;	/* 1 s */
 wr(R_CLEAR,CLEAR_ALL);
 wr(R_DTIMER,0xFFFFFFFFU);
 wr(R_DLEN,512);
 wr(R_DCTL,1U|(1U<<1)|(512U<<4));		/* enable | read | 512-byte blocks */
 /* card is block-addressed (sector mode) */
 int r=cmd(17,(UInt32)(lba+USERDATA_LBA),CMD_RESP|CMD_DAT,resp);
 if(r){ errs++; g_errs=errs; wr(R_DCTL,0); return r; }
 st=mach_absolute_time();
 for(i=0;i<128;){
  UInt32 s=rd(R_STATUS);
  if(s&(S_DATACRC|S_DATATO|S_RXOVR|S_STARTERR)){ errs++; g_errs=errs; g_laststat=s; wr(R_CLEAR,CLEAR_ALL); wr(R_DCTL,0); return -4; }
  if(s&S_RXAVL){ w=rd(R_FIFO+((i*4U)&63U)); o[i++]=w; continue; }
  if(mach_absolute_time()-st>lim){ errs++; g_errs=errs; wr(R_DCTL,0); return -5; }
 }
 st=mach_absolute_time();
 while(!(rd(R_STATUS)&S_DATAEND)){ if(mach_absolute_time()-st>lim) break; }
 wr(R_CLEAR,CLEAR_ALL); wr(R_DCTL,0);
 return 0;
}
int IOS7M8930SDMMC::sw(UInt32 idx,UInt32 val)
{
 UInt32 resp[4]; int r=cmd(6,(3U<<24)|(idx<<16)|(val<<8)|1U,CMD_RESP,resp);
 if(r) return r;
 UInt64 st=mach_absolute_time();
 for(;;){
  if(cmd(13,rca<<16,CMD_RESP,resp)==0 && ((resp[0]>>9)&15U)==4 && (resp[0]&0x100U)) return (resp[0]&0x80U)?-9:0;
  if(mach_absolute_time()-st>6750000ULL) return -8;
 }
}
int IOS7M8930SDMMC::tryMode(int k)
{
 UInt32 clk0=g_clock0; UInt8 sec[512]; int r=0;
 g_swrc=0;
 if(k==1){ wr(R_CLOCK,clk0^(1U<<14)); }
 else if(k==2||k==3||k==4){
  UInt32 wbits=(k==2)?(1U<<10):(k==3)?0U:(2U<<10), cw=(k==2)?2U:(k==3)?0U:1U;
  r=sw(183,cw); g_swrc=(unsigned)r&0xff;
  r=sw(185,0); g_swrc=(g_swrc<<8)|((unsigned)r&0xff);
  wr(R_CLOCK,((clk0&~0x400FFU&~(3U<<10)&~(1U<<14))|wbits|0x0FU));
 }
 r=readSector(0,sec); g_r0=(unsigned)r; g_sig=((UInt32)sec[510]<<8)|sec[511];
 g_clock=rd(R_CLOCK);
 return (r==0&&sec[510]==0x55&&sec[511]==0xaa)?0:-1;
}
bool IOS7M8930SDMMC::init(OSDictionary *p)
{
 mmio=0; map=0; regs=0; mutex=0; initialized=false; rca=2; errs=0;
 return IOBlockStorageDevice::init(p);
}
bool IOS7M8930SDMMC::start(IOService *provider)
{
 if(!IOBlockStorageDevice::start(provider)) return false;
 mutex=IOLockAlloc(); if(!mutex) return false;
 mmio=IOMemoryDescriptor::withPhysicalAddress(SDC1_PA,0x1000,kIODirectionInOut);
 if(!mmio) return false;
 map=mmio->map(kIOMapInhibitCache);
 if(!map||!map->getAddress()) return false;
 regs=(volatile UInt32*)map->getAddress(); g_regs=regs; g_started=1; /* ticker disabled: IOCreateThread(m8930_ticker,0); */
 g_clock=rd(R_CLOCK); g_clock0=g_clock;
 ios7m8930_mark(800);
 IOLog("M8930 SDC1: POWER=%08x CLOCK=%08x STATUS=%08x\n",(unsigned)rd(R_POWER),(unsigned)rd(R_CLOCK),(unsigned)rd(R_STATUS));
 ios7m8930_hex10(rd(R_CLOCK));
 /* find RCA: CMD13 with RCA 2 then 1; reselect (CMD7) if not in transfer state */
 UInt32 resp[4]={0,0,0,0}; int ok=0; g_cmd13rc=(unsigned)-99; UInt32 tryrca[3]={2,1,0};
 for(int k=0;k<3&&!ok;k++){
  if(cmd(13,tryrca[k]<<16,CMD_RESP,resp)==0){
   UInt32 state=(resp[0]>>9)&15U;
   IOLog("M8930 SDC1: CMD13 rca=%u status=%08x state=%u\n",(unsigned)tryrca[k],(unsigned)resp[0],(unsigned)state);
   rca=tryrca[k]; g_rca=rca; g_state=state; g_cmd13rc=0;
   if(state!=4){ cmd(7,rca<<16,CMD_RESP,resp); }
   ok=1;
  }
 }
 ios7m8930_mark(ok?801:802);
 UInt8 sec[512];
 int r=-1;
 for(int k=0;k<5;k++){ g_mode=k; r=tryMode(k); IOLog("M8930 SDC1: mode %d -> %d sig=%04x stat=%08x clk=%08x sw=%04x\n",k,r,g_sig,(unsigned)g_laststat,(unsigned)g_clock,(unsigned)g_swrc); if(r==0) break; }
 r=readSector(0,sec); g_r0=(unsigned)r;
 IOLog("M8930 SDC1: read LBA0 r=%d sig=%02x%02x p1type=%02x\n",r,sec[510],sec[511],sec[450]);
 ios7m8930_hex9(((UInt32)sec[510]<<8|sec[511])|((UInt32)(r&0xff)<<24));
 if(r||sec[510]!=0x55||sec[511]!=0xaa){ IOLog("M8930 SDC1: no MBR\n"); return false; }
 ios7m8930_mark(803);
 initialized=true;
 OSObject *dec=OSUnserializeXML(ios7labStoragePersonalities);
 OSArray *drv=OSDynamicCast(OSArray,dec);
 if(!drv||!gIOCatalogue->addDrivers(drv,false)) { if(dec)dec->release(); return false; }
 dec->release();
 return true;
}
void IOS7M8930SDMMC::free(){ if(mutex)IOLockFree(mutex); if(map)map->release(); if(mmio)mmio->release(); IOBlockStorageDevice::free(); }
char *IOS7M8930SDMMC::getVendorString(){static char t[]="Samsung";return t;}
char *IOS7M8930SDMMC::getProductString(){static char t[]="MSM8930 eMMC";return t;}
char *IOS7M8930SDMMC::getRevisionString(){static char t[]="PIO";return t;}
char *IOS7M8930SDMMC::getAdditionalDeviceInfoString(){static char t[]="MSM8930 SDC1";return t;}
IOReturn IOS7M8930SDMMC::reportBlockSize(UInt64 *v){ios7m8930_mark(810);if(!v)return kIOReturnBadArgument;*v=512;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportMaxValidBlock(UInt64 *v){ios7m8930_mark(811);if(!v||!initialized)return kIOReturnNotReady;*v=USERDATA_SECTORS-1;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportEjectability(bool *v){ios7m8930_mark(812);if(!v)return kIOReturnBadArgument;*v=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportLockability(bool *v){ios7m8930_mark(813);if(!v)return kIOReturnBadArgument;*v=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportRemovability(bool *v){ios7m8930_mark(814);if(!v)return kIOReturnBadArgument;*v=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportMediaState(bool *p,bool *c){ios7m8930_mark(815);if(!p||!c)return kIOReturnBadArgument;*p=initialized;*c=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportPollRequirements(bool *r,bool *e){ios7m8930_mark(816);if(!r||!e)return kIOReturnBadArgument;*r=false;*e=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportWriteProtection(bool *v){ios7m8930_mark(817);if(!v)return kIOReturnBadArgument;*v=true;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::doAsyncReadWrite(IOMemoryDescriptor *buffer,UInt64 block,UInt64 count,
 IOStorageAttributes *attributes,IOStorageCompletion *completion)
{
 UInt64 bytes=0;
 if(!buffer||!completion||!completion->action||!initialized||
    block>=USERDATA_SECTORS||count==0||block+count>USERDATA_SECTORS||
    count*512U!=buffer->getLength())return kIOReturnBadArgument;
 if(buffer->getDirection()!=kIODirectionIn)return kIOReturnNotWritable;
 if(attributes&&(attributes->options||attributes->reserved0032||attributes->reserved0064))return kIOReturnUnsupported;
 bytes=count*512U; g_step=1;
 IOStorageCompletion saved=*completion;UInt64 completed=0;IOReturn result=kIOReturnSuccess;
 uint8_t *tmp=(uint8_t*)IOMalloc((unsigned)bytes);
 if(!tmp)return kIOReturnNoMemory;
 g_step=2; IOLockLock(mutex); g_step=3;
 for(UInt64 i=0;i<count&&result==kIOReturnSuccess;i++){
  int rc=readSector(block+i,tmp+i*512U); g_reads++; g_lastrc=(unsigned)rc; g_lastblk=block+i;
  if(rc){ rc=readSector(block+i,tmp+i*512U); }	/* one retry */
  if(rc) result=kIOReturnIOError;
 }
 IOLockUnlock(mutex); g_step=4;
 if(result==kIOReturnSuccess){
  if(buffer->writeBytes(0,tmp,(unsigned)bytes)!=(unsigned)bytes)result=kIOReturnUnderrun;
  else completed=bytes;
 }
 IOFree(tmp,(unsigned)bytes); g_step=5;
 {
  static unsigned long n;
  if(((++n)&0x3ffUL)==1UL){ IOLog("M8930SD rd blk=%llu n=%llu res=%d #%lu\n",(unsigned long long)block,(unsigned long long)count,result,n); ios7m8930_hex10((unsigned)block); }
 }
 g_step=6; IOStorage::complete(&saved,result,completed); g_step=7; return kIOReturnSuccess;
}
void ios7j1_register_sd(IOService *platform)
{
 IOS7M8930SDMMC *device=new IOS7M8930SDMMC;if(!device){panic("M8930 SDMMC alloc failed");return;}
 bool attached=false,success=false;
 if(device->init())attached=device->attach(platform);
 if(attached&&device->start(platform)){
  device->registerService();success=true;
 }
 if(!success)IOLog("M8930 SDMMC: init/attach/start failed\n");
 if(attached&&!success)device->detach(platform);
 device->release();
}
#endif
