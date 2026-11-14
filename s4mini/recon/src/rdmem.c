#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
int main(int c,char**v){
 int fd=open("/dev/mem",O_RDONLY|O_SYNC); if(fd<0){perror("open /dev/mem");return 1;}
 for(int i=1;i<c;i++){ unsigned long a=strtoul(v[i],0,0); unsigned long pg=a&~0xfffUL;
  volatile unsigned*m=mmap(0,0x1000,PROT_READ,MAP_SHARED,fd,pg);
  if(m==MAP_FAILED){perror("mmap");continue;}
  printf("0x%08lx = 0x%08x\n",a,m[(a-pg)/4]); munmap((void*)m,0x1000);} return 0;}
