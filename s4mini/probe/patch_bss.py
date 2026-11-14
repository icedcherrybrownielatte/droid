p="/home/user/uniloader/arch/arm/load-kernel.c"; s=open(p).read()
helper=r'''
/*
 * The kernel is copied flat (file offset == load offset), but Mach-O zerofill (vmsize > filesize, i.e. BSS)
 * is not in the file, so those bytes hold whatever the previous boot / the following segments left there.
 * Zero them, or statics such as processor_list start out as garbage.
 */
static void xnu_zero_bss(unsigned int load_pa)
{
	unsigned char *p = (unsigned char *)load_pa;
	unsigned int base = 0, ncmds, off, i;

	if ((p[0] | (p[1] << 8) | (p[2] << 16) | ((unsigned)p[3] << 24)) != J1_MH_MAGIC)
		return;
	ncmds = p[16] | (p[17] << 8) | (p[18] << 16) | ((unsigned)p[19] << 24);
	off = 28;
	for (i = 0; i < ncmds; i++) {
		unsigned int cmd = *(unsigned int *)(p + off), csize = *(unsigned int *)(p + off + 4);

		if (cmd == J1_LC_SEGMENT) {
			unsigned int vmaddr = *(unsigned int *)(p + off + 24);

			if (vmaddr && (base == 0 || vmaddr < base))
				base = vmaddr;
		}
		if (csize == 0)
			break;
		off += csize;
	}
	off = 28;
	for (i = 0; i < ncmds; i++) {
		unsigned int cmd = *(unsigned int *)(p + off), csize = *(unsigned int *)(p + off + 4);

		if (cmd == J1_LC_SEGMENT) {
			unsigned int vmaddr = *(unsigned int *)(p + off + 24);
			unsigned int vmsize = *(unsigned int *)(p + off + 28);
			unsigned int filesize = *(unsigned int *)(p + off + 36);

			if (vmaddr && vmsize > filesize && vmaddr >= base) {
				unsigned int dst = load_pa + (vmaddr - base) + filesize;

				printk(KERN_INFO, "xnu: zero bss %08x +%x\n", dst, vmsize - filesize);
				memset((void *)dst, 0, vmsize - filesize);
			}
		}
		if (csize == 0)
			break;
		off += csize;
	}
}
'''
s=s.replace("void arch_load_kernel_xnu(void *kernel, void *dt, void *ramdisk)\n{",helper+"\nvoid arch_load_kernel_xnu(void *kernel, void *dt, void *ramdisk)\n{",1)
# call after the kernel copy/decode, before DT placement
marker="\t/* Apple-format device tree right behind the kernel image."
assert marker in s
s=s.replace(marker,"\txnu_zero_bss(load_pa);\n\n"+marker,1)
open(p,"w").write(s); print("ok")
