/* Class keeps the S4 mini name IOS7M8930SDMMC: IOS7LeoHFSFile matches its provider by that name. */
/* Galaxy S4 GT-I9500 (Exynos 5410) eMMC block device: Synopsys DesignWare MMC (dw_mmc.0 @0x12200000),
 * read-only PIO, no DMA, polled. S-Boot leaves the eMMC initialised in transfer state (it just read BOOT
 * from it). The exposed "card" is the SYSTEM partition (mmcblk0p20, LBA 6348800), which holds card.img:
 * MBR + FAT32 with IOS7/ROOTFS.HFS, found by IOS7LeoHFSFile exactly as on the S4 mini.
 * Register numbers: Linux drivers/mmc/host/dw_mmc.h (Samsung 3.4 kernel). Every wait is bounded. */
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
extern int printf(const char *,...);
}
#define DW_PA		0x12200000U
#define CARD_LBA	6348800ULL	/* /sys/block/mmcblk0/mmcblk0p20/start */
#define CARD_SECTORS	3410116ULL	/* card.img = 1745979392 bytes */
#define TB_1S		24000000ULL	/* timebase: MCT 24 MHz */
#define R_CTRL		0x000
#define R_CLKDIV	0x008
#define R_CLKENA	0x010
#define R_TMOUT		0x014
#define R_CTYPE		0x018
#define R_BLKSIZ	0x01C
#define R_BYTCNT	0x020
#define R_INTMASK	0x024
#define R_CMDARG	0x028
#define R_CMD		0x02C
#define R_RESP0		0x030
#define R_RINTSTS	0x044
#define R_STATUS	0x048
#define R_FIFOTH	0x04C
#define R_VERID		0x06C
#define R_HCON		0x070
#define R_BMOD		0x080
#define CTRL_RESET	(1U<<0)
#define CTRL_FIFO_RESET	(1U<<1)
#define CTRL_DMA_RESET	(1U<<2)
#define CTRL_INT_EN	(1U<<4)
#define CTRL_USE_IDMAC	(1U<<25)
#define CMD_START	(1U<<31)
#define CMD_HOLD	(1U<<29)
#define CMD_PRV_WAIT	(1U<<13)
#define CMD_SEND_STOP	(1U<<12)
#define CMD_DAT_EXP	(1U<<9)
#define CMD_RESP_CRC	(1U<<8)
#define CMD_RESP_EXP	(1U<<6)
#define CMD_STOP	(1U<<14)
#define I_RE		(1U<<1)
#define I_CD		(1U<<2)
#define I_DTO		(1U<<3)
#define I_RCRC		(1U<<6)
#define I_DCRC		(1U<<7)
#define I_RTO		(1U<<8)
#define I_DRTO		(1U<<9)
#define I_HTO		(1U<<10)
#define I_FRUN		(1U<<11)
#define I_HLE		(1U<<12)
#define I_SBE		(1U<<13)
#define I_ACD		(1U<<14)
#define I_EBE		(1U<<15)
#define I_CMD_ERR	(I_RE|I_RCRC|I_RTO|I_HLE)
#define I_DATA_ERR	(I_DCRC|I_DRTO|I_HTO|I_FRUN|I_SBE|I_EBE)
#define ST_BUSY		(1U<<9)
#define FCNT(s)		(((s)>>17)&0x1FFFU)
static volatile unsigned long g_reads; static volatile unsigned g_errs,g_lastrc,g_lastint;
class IOS7M8930SDMMC : public IOBlockStorageDevice {
 OSDeclareDefaultStructors(IOS7M8930SDMMC)
 IOMemoryDescriptor *mmio; IOMemoryMap *map; volatile UInt32 *regs;
 IOLock *mutex; bool initialized; UInt32 rca; UInt32 errs; UInt32 dataOff; UInt32 fifo64;
 UInt32 rd(unsigned o){ UInt32 v=regs[o/4]; __asm__ __volatile__("dsb sy":::"memory"); return v; }
 void wr(unsigned o,UInt32 v){ __asm__ __volatile__("dsb sy":::"memory"); regs[o/4]=v; __asm__ __volatile__("dsb sy":::"memory"); }
 int waitIdle(void);
 int fifoReset(void);
 int cmd(UInt32 idx,UInt32 arg,UInt32 flags,UInt32 *resp);
 int readBlocks(UInt64 lba,UInt32 n,UInt8 *out);
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
/* card/controller data path idle (STATUS.data_busy clear), bounded 1 s */
int IOS7M8930SDMMC::waitIdle(void)
{
 UInt64 st=mach_absolute_time();
 while(rd(R_STATUS)&ST_BUSY){ if(mach_absolute_time()-st>TB_1S) return -1; }
 return 0;
}
int IOS7M8930SDMMC::fifoReset(void)
{
 UInt64 st=mach_absolute_time();
 wr(R_CTRL,rd(R_CTRL)|CTRL_FIFO_RESET);
 while(rd(R_CTRL)&CTRL_FIFO_RESET){ if(mach_absolute_time()-st>TB_1S) return -1; }
 return 0;
}
/* Issue a command and wait for command-done. flags: CMD_* bits (data bits included by the caller). */
int IOS7M8930SDMMC::cmd(UInt32 idx,UInt32 arg,UInt32 flags,UInt32 *resp)
{
 UInt64 st=mach_absolute_time(), lim=TB_1S/2ULL;
 UInt32 s;
 wr(R_RINTSTS,I_CMD_ERR|I_CD);
 wr(R_CMDARG,arg);
 wr(R_CMD,CMD_START|CMD_HOLD|(idx&0x3fU)|flags);
 while(rd(R_CMD)&CMD_START){ if(mach_absolute_time()-st>lim) return -1; }	/* controller took it */
 for(;;){
  s=rd(R_RINTSTS);
  if(s&I_CD) break;
  if(mach_absolute_time()-st>lim){ g_lastint=s; return -2; }
 }
 wr(R_RINTSTS,I_CD);
 if(s&(I_RTO|I_RE|I_HLE)){ g_lastint=s; wr(R_RINTSTS,I_CMD_ERR); return -3; }
 if((s&I_RCRC)&&idx!=1){ g_lastint=s; wr(R_RINTSTS,I_RCRC); return -4; }
 if(resp) resp[0]=rd(R_RESP0);
 return 0;
}
/* CMD17/CMD18 PIO read of n (<=128) sectors at window lba; CMD18 uses the controller's auto-stop (CMD12). */
int IOS7M8930SDMMC::readBlocks(UInt64 lba,UInt32 n,UInt8 *out)
{
 UInt32 resp[1],words=n*128U,i=0,s; UInt32 *o=(UInt32*)out;
 UInt64 st,lim=TB_1S;
 int r;
 if(waitIdle()) { errs++; g_errs=errs; return -10; }
 if(fifoReset()) { errs++; g_errs=errs; return -11; }
 wr(R_RINTSTS,0xFFFFFFFFU);
 wr(R_BLKSIZ,512U);
 wr(R_BYTCNT,n*512U);
 r=cmd(n>1?18U:17U,(UInt32)(lba+CARD_LBA),CMD_RESP_EXP|CMD_RESP_CRC|CMD_DAT_EXP|CMD_PRV_WAIT|(n>1?CMD_SEND_STOP:0U),resp);
 if(r){ errs++; g_errs=errs; g_lastrc=(unsigned)r; return r; }
 st=mach_absolute_time();
 while(i<words){
  s=rd(R_RINTSTS);
  if(s&I_DATA_ERR){ g_lastint=s; errs++; g_errs=errs; wr(R_RINTSTS,0xFFFFFFFFU); (void)waitIdle(); return -4; }
  UInt32 c=FCNT(rd(R_STATUS));
  if(!c){ if(mach_absolute_time()-st>lim){ g_lastint=s; errs++; g_errs=errs; return -5; } continue; }
  if(fifo64){	/* 64-bit FIFO (HCON data width 2): FCNT counts 64-bit entries, read them whole */
   while(c--&&i+1<words){ UInt64 v=*(volatile UInt64 *)((volatile UInt8 *)regs+dataOff); o[i++]=(UInt32)v; o[i++]=(UInt32)(v>>32); }
  } else
   while(c--&&i<words) o[i++]=regs[dataOff/4];
  wr(R_RINTSTS,(1U<<5));		/* RXDR */
 }
 st=mach_absolute_time();
 while(!(rd(R_RINTSTS)&I_DTO)){ if(mach_absolute_time()-st>lim) break; }
 if(n>1){ st=mach_absolute_time(); while(!(rd(R_RINTSTS)&I_ACD)){ if(mach_absolute_time()-st>lim) break; } }
 wr(R_RINTSTS,0xFFFFFFFFU);
 (void)waitIdle();
 return 0;
}
bool IOS7M8930SDMMC::init(OSDictionary *p)
{
 mmio=0; map=0; regs=0; mutex=0; initialized=false; rca=1; errs=0; dataOff=0x200; fifo64=0;
 return IOBlockStorageDevice::init(p);
}
bool IOS7M8930SDMMC::start(IOService *provider)
{
 if(!IOBlockStorageDevice::start(provider)) return false;
 mutex=IOLockAlloc(); if(!mutex) return false;
 mmio=IOMemoryDescriptor::withPhysicalAddress(DW_PA,0x1000,kIODirectionInOut);
 if(!mmio) return false;
 map=mmio->map(kIOMapInhibitCache);
 if(!map||!map->getAddress()) return false;
 regs=(volatile UInt32*)map->getAddress();
 UInt32 ver=rd(R_VERID)&0xffffU;
 dataOff=(ver<0x240aU)?0x100U:0x200U;
 fifo64=(((rd(R_HCON)>>7)&7U)==2U);
 printf("J5410 eMMC: HCON=%08x fifo64=%u data@%x\n",(unsigned)rd(R_HCON),(unsigned)fifo64,(unsigned)dataOff);
 printf("J5410 eMMC: VERID=%04x CTRL=%08x BMOD=%08x CLKDIV=%08x CLKENA=%08x CTYPE=%08x STATUS=%08x FIFOTH=%08x RINTSTS=%08x\n",
  (unsigned)ver,(unsigned)rd(R_CTRL),(unsigned)rd(R_BMOD),(unsigned)rd(R_CLKDIV),(unsigned)rd(R_CLKENA),
  (unsigned)rd(R_CTYPE),(unsigned)rd(R_STATUS),(unsigned)rd(R_FIFOTH),(unsigned)rd(R_RINTSTS));
 /* PIO: no IDMAC, no interrupts to the GIC (we poll RINTSTS), data timeout max */
 wr(R_CTRL,(rd(R_CTRL)&~(CTRL_USE_IDMAC|CTRL_INT_EN)));
 wr(R_BMOD,0);
 wr(R_INTMASK,0);
 wr(R_TMOUT,0xFFFFFF40U);
 (void)waitIdle();
 (void)fifoReset();
 wr(R_RINTSTS,0xFFFFFFFFU);
 /* find the card's RCA (Linux gives eMMC RCA 1) and make sure it is selected (transfer state 4) */
 UInt32 resp[1]={0}; int ok=0; UInt32 tryrca[3]={1,2,3};
 for(int k=0;k<3&&!ok;k++){
  if(cmd(13,tryrca[k]<<16,CMD_RESP_EXP|CMD_RESP_CRC,resp)==0){
   UInt32 state=(resp[0]>>9)&15U;
   printf("J5410 eMMC: CMD13 rca=%u status=%08x state=%u\n",(unsigned)tryrca[k],(unsigned)resp[0],(unsigned)state);
   rca=tryrca[k];
   if(state==3) cmd(7,rca<<16,CMD_RESP_EXP|CMD_RESP_CRC,resp);	/* stand-by -> transfer */
   ok=1;
  } else printf("J5410 eMMC: CMD13 rca=%u failed int=%08x\n",(unsigned)tryrca[k],(unsigned)g_lastint);
 }
 UInt8 sec[512];
 int r=readBlocks(0,1,sec);
 printf("J5410 eMMC: read window LBA0 r=%d int=%08x sig=%02x%02x p1type=%02x w0=%08x w111=%08x\n",r,(unsigned)g_lastint,sec[510],sec[511],sec[450],((UInt32*)sec)[0],((UInt32*)sec)[111]);
 if(r||sec[510]!=0x55||sec[511]!=0xaa){ printf("J5410 eMMC: no MBR in the card window\n"); return false; }
 /* multi-block sanity: 8 sectors from 0 must start with the same MBR */
 { UInt8 *b=(UInt8*)IOMalloc(4096); if(b){ r=readBlocks(0,8,b); printf("J5410 eMMC: CMD18 x8 r=%d match=%d\n",r,b&&!memcmp(b,sec,512)); IOFree(b,4096); } }
 initialized=true;
 OSObject *dec=OSUnserializeXML(ios7labStoragePersonalities);
 OSArray *drv=OSDynamicCast(OSArray,dec);
 if(!drv||!gIOCatalogue->addDrivers(drv,false)) { if(dec)dec->release(); return false; }
 dec->release();
 return true;
}
void IOS7M8930SDMMC::free(){ if(mutex)IOLockFree(mutex); if(map)map->release(); if(mmio)mmio->release(); IOBlockStorageDevice::free(); }
char *IOS7M8930SDMMC::getVendorString(){static char t[]="Samsung";return t;}
char *IOS7M8930SDMMC::getProductString(){static char t[]="Exynos5410 eMMC";return t;}
char *IOS7M8930SDMMC::getRevisionString(){static char t[]="PIO";return t;}
char *IOS7M8930SDMMC::getAdditionalDeviceInfoString(){static char t[]="dw_mmc.0 SYSTEM";return t;}
IOReturn IOS7M8930SDMMC::reportBlockSize(UInt64 *v){if(!v)return kIOReturnBadArgument;*v=512;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportMaxValidBlock(UInt64 *v){if(!v||!initialized)return kIOReturnNotReady;*v=CARD_SECTORS-1;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportEjectability(bool *v){if(!v)return kIOReturnBadArgument;*v=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportLockability(bool *v){if(!v)return kIOReturnBadArgument;*v=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportRemovability(bool *v){if(!v)return kIOReturnBadArgument;*v=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportMediaState(bool *p,bool *c){if(!p||!c)return kIOReturnBadArgument;*p=initialized;*c=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportPollRequirements(bool *r,bool *e){if(!r||!e)return kIOReturnBadArgument;*r=false;*e=false;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::reportWriteProtection(bool *v){if(!v)return kIOReturnBadArgument;*v=true;return kIOReturnSuccess;}
IOReturn IOS7M8930SDMMC::doAsyncReadWrite(IOMemoryDescriptor *buffer,UInt64 block,UInt64 count,
 IOStorageAttributes *attributes,IOStorageCompletion *completion)
{
 UInt64 bytes=0;
 if(!buffer||!completion||!completion->action||!initialized||
    block>=CARD_SECTORS||count==0||block+count>CARD_SECTORS||
    count*512U!=buffer->getLength())return kIOReturnBadArgument;
 if(buffer->getDirection()!=kIODirectionIn)return kIOReturnNotWritable;
 if(attributes&&(attributes->options||attributes->reserved0032||attributes->reserved0064))return kIOReturnUnsupported;
 bytes=count*512U;
 IOStorageCompletion saved=*completion;UInt64 completed=0;IOReturn result=kIOReturnSuccess;
 uint8_t *tmp=(uint8_t*)IOMalloc((unsigned)bytes);
 if(!tmp)return kIOReturnNoMemory;
 IOLockLock(mutex);
 for(UInt64 i=0;i<count&&result==kIOReturnSuccess;){
  UInt32 n=(count-i>128U)?128U:(UInt32)(count-i);
  int rc=readBlocks(block+i,n,tmp+i*512U); g_reads++; g_lastrc=(unsigned)rc;
  if(rc){	/* fall back to single sectors, one retry each */
   for(UInt32 k=0;k<n&&result==kIOReturnSuccess;k++){
    rc=readBlocks(block+i+k,1,tmp+(i+k)*512U);
    if(rc) rc=readBlocks(block+i+k,1,tmp+(i+k)*512U);
    if(rc) result=kIOReturnIOError;
   }
  }
  i+=n;
 }
 IOLockUnlock(mutex);
 if(result==kIOReturnSuccess){
  if(buffer->writeBytes(0,tmp,(unsigned)bytes)!=(unsigned)bytes)result=kIOReturnUnderrun;
  else completed=bytes;
 }
 IOFree(tmp,(unsigned)bytes);
 {
  static unsigned long nn;
  if(((++nn)&0x3ffUL)==1UL) printf("J5410 eMMC rd blk=%llu n=%llu res=%d errs=%u #%lu\n",(unsigned long long)block,(unsigned long long)count,result,(unsigned)g_errs,nn);
 }
 IOStorage::complete(&saved,result,completed); return kIOReturnSuccess;
}
void ios7j1_register_sd(IOService *platform)
{
 IOS7M8930SDMMC *device=new IOS7M8930SDMMC;if(!device){panic("J5410 SDMMC alloc failed");return;}
 bool attached=false,success=false;
 if(device->init())attached=device->attach(platform);
 if(attached&&device->start(platform)){
  device->registerService();success=true;
 }
 if(!success)printf("J5410 SDMMC: init/attach/start failed\n");
 if(attached&&!success)device->detach(platform);
 device->release();
}
