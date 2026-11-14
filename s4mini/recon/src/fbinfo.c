#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
int main(void){
 int fd=open("/dev/graphics/fb0",O_RDWR); if(fd<0) fd=open("/dev/fb0",O_RDWR);
 struct fb_fix_screeninfo f; struct fb_var_screeninfo v;
 if(fd<0){perror("open");return 1;}
 ioctl(fd,FBIOGET_FSCREENINFO,&f); ioctl(fd,FBIOGET_VSCREENINFO,&v);
 printf("smem_start=0x%lx smem_len=0x%x line_length=%u\n",f.smem_start,f.smem_len,f.line_length);
 printf("xres=%u yres=%u vx=%u vy=%u bpp=%u r=%u/%u g=%u/%u b=%u/%u a=%u/%u\n",v.xres,v.yres,v.xres_virtual,v.yres_virtual,v.bits_per_pixel,v.red.offset,v.red.length,v.green.offset,v.green.length,v.blue.offset,v.blue.length,v.transp.offset,v.transp.length);
 return 0;}
