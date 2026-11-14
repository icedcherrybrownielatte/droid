"""Wire the EXYNOS5410_JA3G board into ~/xnu-s4. JA3G builds also define BOARD_CONFIG_MSM8930_SERRANO so every
iOS-userspace fix of the S4 mini port applies; only hardware-specific SERRANO code is excluded for JA3G."""
import os, shutil
X = os.path.expanduser('~/xnu-s4/xnu')
S = '/mnt/c/Users/User/Desktop/Droid/s4/stage3'
CR = chr(13); LF = chr(10); CRLF = CR + LF
NOT = ' && !defined(BOARD_CONFIG_EXYNOS5410_JA3G)'


def edit(path, old, new, count=1):
    p = os.path.join(X, path)
    s = open(p, newline='').read()
    if CRLF in s:
        old = old.replace(LF, CRLF); new = new.replace(LF, CRLF)
    if new in s:
        print('already', path); return
    assert s.count(old) == count, (path, old[:70], s.count(old))
    open(p, 'w', newline='').write(s.replace(old, new))


edit('makedefs/MakeInc.def', 'EXYNOS3475_J1XLTE MSM8930_SERRANO\n', 'EXYNOS3475_J1XLTE MSM8930_SERRANO EXYNOS5410_JA3G\n')
edit('makedefs/MakeInc.def', '-DBOARD_CONFIG_$(MACHINE_CONFIG)\n',
     '-DBOARD_CONFIG_$(MACHINE_CONFIG) $(if $(filter EXYNOS5410_JA3G,$(MACHINE_CONFIG)),-DBOARD_CONFIG_MSM8930_SERRANO=1)\n')
edit('makedefs/MakeInc.def', 'ARCH_FLAGS_ARM_MSM8930_SERRANO = -arch armv7\n',
     'ARCH_FLAGS_ARM_MSM8930_SERRANO = -arch armv7\nARCH_FLAGS_ARM_EXYNOS5410_JA3G = -arch armv7\n')
edit('makedefs/MakeInc.def', 'ARCH_FLAGS_ARM_MSM8930_SERRANO = --target=armv7-apple-darwin -mthumb\n',
     'ARCH_FLAGS_ARM_MSM8930_SERRANO = --target=armv7-apple-darwin -mthumb\nARCH_FLAGS_ARM_EXYNOS5410_JA3G = --target=armv7-apple-darwin -mthumb\n')

edit('pexpert/conf/files.arm', 'pexpert/arm/msm8930_timer.c standard\n',
     'pexpert/arm/msm8930_timer.c standard\npexpert/arm/pe_exynos5410_ja3g.c standard\npexpert/arm/exynos5410_timer.c standard\n')
shutil.copy(S + '/exynos5410_timer.c', X + '/pexpert/arm/exynos5410_timer.c')

# S4 mini hardware files: not on JA3G
edit('pexpert/arm/msm8930_timer.c', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' + NOT + '\n')
p = X + '/pexpert/arm/pe_msm8930_serrano.c'
s = open(p, newline='').read().replace(CRLF, LF)
if NOT not in s:
    s = s.replace('#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' + NOT + '\n', 1)
    # the trailing hex helpers sit after the file's #endif: move that #endif to the end
    lines = s.split('\n')
    last = max(i for i, l in enumerate(lines) if l == '#endif')
    del lines[last]
    s = '\n'.join(lines).rstrip('\n') + '\n#endif\n'
    open(p, 'w', newline='').write(s)

# early boot: S4 mini scanout/qGIC identity maps and white bars point into plain RAM on the S4
edit('osfmk/arm/locore.s', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n/* White bar idx',
     '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' + NOT + '\n/* White bar idx')
edit('osfmk/arm/locore.s', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* S4 mini: identity-map',
     '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' + NOT + '\n    /* S4 mini: identity-map')
edit('osfmk/arm/locore.s', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    /* identity sections for the scanout',
     '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' + NOT + '\n    /* identity sections for the scanout')
edit('osfmk/arm/arm_vm_init.c', '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n    {\n        volatile unsigned int *l1 = (volatile unsigned int *)phys_to_virt(cpu_ttb);\n        l1[0x300]',
     '#if defined(BOARD_CONFIG_MSM8930_SERRANO)' + NOT + '\n    {\n        volatile unsigned int *l1 = (volatile unsigned int *)phys_to_virt(cpu_ttb);\n        l1[0x300]')

# eMMC: the MSM SDCC driver must not run on Exynos (first a stub, replaced below by the dw_mmc driver)
if 'IOS7J5410SDMMC.inc' not in open(X + '/iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/IOS7M8930SDMMC.cpp').read(): edit('iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/IOS7M8930SDMMC.cpp',
     '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n#include <IOKit/storage/IOBlockStorageDevice.h>',
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n#include <IOKit/IOLib.h>\n#include <IOKit/IOService.h>\n'
     'void ios7j1_register_sd(IOService *platform)\n{\n (void)platform;\n IOLog("JA3G: eMMC (dw_mmc) driver not ported yet, no root device' + chr(92) + 'n");\n}\n'
     '#elif defined(BOARD_CONFIG_MSM8930_SERRANO)\n#include <IOKit/storage/IOBlockStorageDevice.h>')
print('integrate ok')

# panic: show it for 20 s, then reboot to TWRP (the S4 has no button-free way out of a halted kernel)
edit('osfmk/arm/model_dep.c', '    { extern void ios7m8930_fb_flush_all(void); ios7m8930_fb_flush_all(); }\n    hw_atomic_add(&debug_mode, 1);\n',
     '    { extern void ios7m8930_fb_flush_all(void); ios7m8930_fb_flush_all(); }\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n    { extern void ios7j1_reboot_recovery(unsigned int secs); ios7j1_reboot_recovery(20); }\n#endif\n'
     '    hw_atomic_add(&debug_mode, 1);\n')
print('integrate panic-reboot ok')

# eMMC driver for the S4 (dw_mmc PIO): included into IOS7M8930SDMMC.cpp in place of the stub
P = 'iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/'
shutil.copy(S + '/ja3g_sdmmc.inc', X + '/' + P + 'IOS7J5410SDMMC.inc')
edit(P + 'IOS7M8930SDMMC.cpp',
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n#include <IOKit/IOLib.h>\n#include <IOKit/IOService.h>\n'
     'void ios7j1_register_sd(IOService *platform)\n{\n (void)platform;\n IOLog("JA3G: eMMC (dw_mmc) driver not ported yet, no root device' + chr(92) + 'n");\n}\n',
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n#include "IOS7J5410SDMMC.inc"\n')
print('integrate sdmmc ok')

# GUI surface on the S4: 540x960 at display-scale 2 (DT blob stage3/dtb_ja3g.bin) = 270x480 points like the
# S4 mini; ios7j1_display_present doubles it 2x2 into the 1080x1920 panel.
edit('iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/IOS7LeoDisplay.cpp',
     '#if defined(BOARD_CONFIG_MSM8930_SERRANO)\n/* Galaxy S4 mini panel: 540x960.',
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\nstatic const uint32_t leoWidth=540,leoHeight=960,leoRow=2176;\n#elif defined(BOARD_CONFIG_MSM8930_SERRANO)\n/* Galaxy S4 mini panel: 540x960.')
print('integrate display ok')

# debug: IOKit config-thread/job counters, printed by the timed reboot (exynos5410_timer.c)
p = X + '/iokit/Kernel/IOService.cpp'
s = open(p, newline='').read()
if 'ios7j5410_iokit_stats' not in s:
    s += ('\n#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
          'extern "C" void ios7j5410_iokit_stats(void);\n'
          'extern "C" void ios7j5410_iokit_stats(void)\n{\n'
          ' printf("IOKIT jobs out=%d cfgthreads=%d waiting=%d cfgstarts=%u cfgwaits=%u run=%u queued=%u' + chr(92) + 'n",\n'
          '  gOutstandingJobs, gNumConfigThreads, gNumWaitingThreads, gCfgStarts, gCfgWaits, gJobsRun,\n'
          '  gJobs ? (unsigned)gJobs->getCount() : 0U);\n}\n#endif\n')
    open(p, 'w', newline='').write(s)
print('integrate iokit-stats ok')

# debug: trace IOService::startMatching decisions (JA3G only)
edit('iokit/Kernel/IOService.cpp',
     '    if( sync)\n\t__state[1] |= kIOServiceSynchronousState;\n    else\n\t__state[1] &= ~kIOServiceSynchronousState;\n',
     '    if( sync)\n\t__state[1] |= kIOServiceSynchronousState;\n    else\n\t__state[1] &= ~kIOServiceSynchronousState;\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '    printf("SM %s sync=%d need=%d wake=%d st0=%x st1=%x' + chr(92) + 'n", getName(), (int)sync, (int)needConfig, (int)needWake, (unsigned)__state[0], (unsigned)__state[1]);\n'
     '#endif\n')
print('integrate sm-trace ok')

# Cortex-A15 treats Write-Through memory as NON-cacheable (A15 TRM): the S4 mini's WT/no-write-allocate
# defaults left the S4 kernel and userland running uncached (~550 ns per loop iteration). Use WB/WA on JA3G.
edit('osfmk/arm/arm_vm_init.c',
     '        /* Writethrough, no write allocate. */\n        *ptv |= (MMU_TEXCB_CA_WT_NWA << 2);\n',
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '        /* Write-back, write-allocate (TEX=001 C=1 B=1): A15 does not cache write-through memory. */\n'
     '        *ptv |= (1U << 6) | 0x8U | 0x4U;\n'
     '#else\n'
     '        /* Writethrough, no write allocate. */\n        *ptv |= (MMU_TEXCB_CA_WT_NWA << 2);\n'
     '#endif\n')
WT = '(ARM_CACHEBIT_WT_NWA_BUFFERED << 2) | (ARM_L2_4KB_TEX(ARM_L2_TEX_100 | ARM_CACHEBIT_WT_NWA_BUFFERED))'
p = X + '/osfmk/arm/pmap.c'
s = open(p, newline='').read()
if 'J5410_NORMAL_MEM' not in s:
    s = s.replace('unsigned int pmap_get_cache_attributes(ppnum_t pn) {',
        '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
        '/* A15: write-through is non-cacheable, so normal memory is write-back write-allocate (inner+outer). */\n'
        '#define J5410_NORMAL_MEM ((ARM_CACHEBIT_WB_WA_BUFFERED << 2) | (ARM_L2_4KB_TEX(ARM_L2_TEX_100 | ARM_CACHEBIT_WB_WA_BUFFERED)))\n'
        '#else\n#define J5410_NORMAL_MEM (' + WT + ')\n#endif\n'
        'unsigned int pmap_get_cache_attributes(ppnum_t pn) {', 1)
    old1 = '        return ' + WT + ';\n'
    old2 = '        template |= ' + WT + ';\n\n    return template;'
    assert s.count(old1) == 1 and s.count(old2) == 1, (s.count(old1), s.count(old2))
    s = s.replace(old1, '        return J5410_NORMAL_MEM;\n').replace(old2, '        template |= J5410_NORMAL_MEM;\n\n    return template;')
    open(p, 'w', newline='').write(s)
print('integrate wbwa ok')

# Page-table walks: TTBR attributes 0x18 = inner non-cacheable walks. With write-back memory the walker then
# misses PTEs still in the D-cache (user fault loop at the first page-in). On JA3G walk inner+outer WB-WA
# (IRGN=01: bit6, RGN=01: bit3) so the walker is coherent with the D-cache.
for f, n in (('osfmk/arm/machine_routines_asm.s', 2), ('osfmk/arm/locore.s', 2)):
    p = X + '/' + f
    s = open(p, newline='').read()
    if 'J5410_TTB_ATTR' not in s:
        s = s.replace('#0x18\n', '#J5410_TTB_ATTR\n')
        s = s.replace('#J5410_TTB_ATTR\n', '#0x18\n')  # restore all, then switch only TTBR lines below
        lines = s.split('\n')
        hits = 0
        for i, l in enumerate(lines):
            if l.strip() in ('orr     r0, r0, #0x18', 'orr     r5, r4, #0x18', 'orr     r6, r4, #0x18'):
                lines[i] = l.replace('#0x18', '#J5410_TTB_ATTR'); hits += 1
        assert hits == n, (f, hits)
        hdr = ('#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n#define J5410_TTB_ATTR 0x48\n#else\n#define J5410_TTB_ATTR 0x18\n#endif\n')
        s = hdr + '\n'.join(lines)
        open(p, 'w', newline='').write(s)
print('integrate ttbr ok')

# debug: dump every thread (proc, state, wait event, continuation, pri) - called at the timed reboot
p = X + '/osfmk/kern/sched_prim.c'
s = open(p, newline='').read()
if 'ios7j5410_dump_threads' not in s:
    NL = chr(92) + 'n'
    s += ('\n#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
          'extern char *proc_name_address(void *p);\n'
          'extern queue_head_t threads;\n'
          'void ios7j5410_dump_threads(void);\n'
          'void ios7j5410_dump_threads(void)\n{\n'
          '\tthread_t th; unsigned int n = 0;\n'
          '\tqueue_iterate(&threads, th, thread_t, threads) {\n'
          '\t\tvoid *bp = th->task ? get_bsdtask_info(th->task) : NULL;\n'
          '\t\tprintf("J5410 TH %p %-16s st=%x pri=%d ev=%p cont=%p wres=%d' + NL + '", th, bp ? proc_name_address(bp) : "kernel",\n'
          '\t\t    th->state, th->sched_pri, (void *)th->wait_event, (void *)th->continuation, th->wait_result);\n'
          '\t\tif (++n >= 400U) break;\n\t}\n}\n#endif\n')
    open(p, 'w', newline='').write(s)
print('integrate threaddump ok')

# User TTBR0 walks (arm_context_switch) used 0x13 = write-through walks, i.e. non-cacheable on A15: with
# write-back memory the walker then used stale user PTEs (heap corruption after fork). Same WB-WA as the kernel.
p = X + '/osfmk/arm/armv/cpufunc-v7.s'
s = open(p, newline='').read()
if 'J5410_UTTB_ATTR' not in s:
    o = '\torrlt\tr0, r0, #0x13\t\t@ ckpt9-A: TTBR0 IRGN=WT,RGN=WT,S=1 (match WT linear map)\n\torrge\tr0, r0, #0x13\t\t@ ckpt9-A: TTBR0 IRGN=WT,RGN=WT,S=1 (match WT linear map)\n'
    assert s.count(o) == 1, s.count(o)
    s = s.replace(o, '\torrlt\tr0, r0, #J5410_UTTB_ATTR\t@ ckpt9-A: TTBR0 walk attributes (WT on Krait, WB-WA on A15)\n\torrge\tr0, r0, #J5410_UTTB_ATTR\n')
    s = '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n#define J5410_UTTB_ATTR 0x48\n#else\n#define J5410_UTTB_ATTR 0x13\n#endif\n' + s
    open(p, 'w', newline='').write(s)
print('integrate uttb ok')

# debug: who in launchd asks for reboot - user backtrace + strings reachable from the user stack
edit('bsd/kern/kern_xxx.c',
     '\t\tprintf("J1 REBOOT requested by pid %d (%s) opt=0x%x' + chr(92) + 'n", p->p_pid, p->p_comm, uap->opt);\n',
     '\t\tprintf("J1 REBOOT requested by pid %d (%s) opt=0x%x' + chr(92) + 'n", p->p_pid, p->p_comm, uap->opt);\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '\t\t{ extern void ios7m8930_user_bt(void); extern void ios7m8930_user_strings(void); ios7m8930_user_bt(); ios7m8930_user_strings(); }\n'
     '#endif\n')
print('integrate reboot-bt ok')

# panic(): the S4 mini's "hold the text ~70 s while petting the WDT" spin runs for many minutes on the S4 (and
# keeps the watchdog quiet); skip it - Debugger() shows the panic 20 s and reboots to TWRP.
edit('osfmk/kern/debug.c',
     '\t\t\t{\t/* DEBUG: hold the panic text on screen ~70 s (pet WDT), then let it bite -> TWRP */\n',
     '#if !defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n\t\t\t{\t/* DEBUG: hold the panic text on screen ~70 s (pet WDT), then let it bite -> TWRP */\n')
edit('osfmk/kern/debug.c',
     '\t\t\t\tfor (spin = 0; spin < 3000000000ULL; spin++) { { extern void ios7m8930_pet_wdt(void); ios7m8930_pet_wdt(); } }\n\t\t\t}\n',
     '\t\t\t\tfor (spin = 0; spin < 3000000000ULL; spin++) { { extern void ios7m8930_pet_wdt(void); ios7m8930_pet_wdt(); } }\n\t\t\t}\n#endif\n')
print('integrate panic-hold ok')

# A15 (out of order): a TLB invalidate must not overtake the PTE store, or the walker refills the stale entry
# (stale writable mappings after COW write-protect = heap corruption after fork). DSB before every TLBI.
p = X + '/osfmk/arm/armv/cpufunc-v7.s'
s = open(p, newline='').read()
if 'J5410: dsb before TLBI' not in s:
    for ent in ('ENTRY(arm_tlb_flushID_ASID)\n', 'ENTRY(arm_tlb_flushID)\n', 'ENTRY(arm_tlb_flushID_SE)\n'):
        assert s.count(ent) == 1, ent
        s = s.replace(ent, ent + '\tdsb\t\t\t\t@ J5410: dsb before TLBI (PTE store visible to the walker)\n')
    open(p, 'w', newline='').write(s)
print('integrate tlbi-dsb ok')

# A15 + write-back: RAM pages must never get a second, non-cacheable mapping (mismatched aliases lose data;
# NOCACHE also stuck to reused pages; VM_WIMG_DEFAULT fell through to template 0 = strongly ordered).
# No DMA masters on this port, so managed RAM stays write-back for every mapping.
edit('osfmk/arm/pmap.c',
     'void pmap_set_cache_attributes(ppnum_t pn, unsigned int cacheattr)\n{\n    unsigned int current, template = 0;\n    int pai;\n',
     'void pmap_set_cache_attributes(ppnum_t pn, unsigned int cacheattr)\n{\n    unsigned int current, template = 0;\n    int pai;\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '    if (pmap_valid_page(pn)) {\n'
     '        LOCK_PVH(pai);\n'
     '        pmap_update_cache_attributes_locked(pn, J5410_NORMAL_MEM);\n'
     '        phys_attribute_clear(pn, PMAP_OSPTE_TYPE_NOCACHE);\n'
     '        UNLOCK_PVH(pai);\n'
     '        return;\n'
     '    }\n'
     '#endif\n')
print('integrate cacheattr ok')

# pmap_destroy freed the pmap + tables while cpu->user_pmap still pointed at it: the next pmap allocated at
# the same address made pmap_switch skip the TTBR0 switch, so the new process ran on the dead process's
# freed (reused) page tables -> memory corruption. Forget it and load the kernel tables before freeing.
edit('osfmk/arm/pmap.c',
     '    /*\n     * If the pmap still has a reference count, we don\'t kill it.\n     */\n    if (refcnt != 0) {\n        return;\n    }\n',
     '    /*\n     * If the pmap still has a reference count, we don\'t kill it.\n     */\n    if (refcnt != 0) {\n        return;\n    }\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '    {\n'
     '        spl_t s2;\n'
     '        SPLVM(s2);\n'
     '        if (current_cpu_datap()->user_pmap == pmap) {\n'
     '            current_cpu_datap()->user_pmap = NULL;\n'
     '            arm_set_context_id(0);\n'
     '            arm_context_switch(kernel_pmap->pm_l1_phys);\n'
     '        }\n'
     '        SPLX(s2);\n'
     '    }\n'
     '#endif\n')
print('integrate pmap-destroy ok')

# A15 local monitor is address-insensitive: clear it on every exception return (kernel context too).
edit('osfmk/arm/traps_lo.s',
     'restore_kernel_context:\n    ldmfd   sp, {r0-r12}\n',
     'restore_kernel_context:\n#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n    clrex\n#endif\n    ldmfd   sp, {r0-r12}\n')
print('integrate clrex ok')

# debug: no ASLR for PID 1 (launchd) so its crash/assumes return addresses map 1:1 onto the binary
edit('bsd/kern/mach_loader.c',
     '\tif (!(imgp->ip_flags & IMGPF_DISABLE_ASLR)) {\n\t\taslr_offset = random();\n',
     '\tif (!(imgp->ip_flags & IMGPF_DISABLE_ASLR)\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '\t    && proc_pid(vfs_context_proc(imgp->ip_vfs_context)) != 1\n'
     '#endif\n'
     '\t    ) {\n\t\taslr_offset = random();\n')
print('integrate launchd-noaslr ok')

# debug: why does launchd's mach_port_deallocate(mach_task_self(), mach_host_self()) fail on the S4?
edit('osfmk/ipc/mach_kernelrpc.c',
     '\trv = mach_port_deallocate(task->itk_space, args->name);\n\t\ndone:\n',
     '\trv = mach_port_deallocate(task->itk_space, args->name);\n'
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '\tif (rv) { extern int proc_selfpid(void); static unsigned n; if (n++ < 40) printf("J5410 port_dealloc pid %d name %x target %x rv %x' + chr(92) + 'n", proc_selfpid(), args->name, args->target, rv); }\n'
     '#endif\n'
     '\t\ndone:\n')
print('integrate dealloc-trace ok')

# test: no pmap nesting of the shared region on JA3G (shared cache mapped per process, plain mappings)
edit('osfmk/vm/vm_shared_region.c',
     '\tshared_region->sr_pmap_nesting_start = pmap_nesting_start;\n',
     '#if defined(BOARD_CONFIG_EXYNOS5410_JA3G)\n'
     '\tpmap_nesting_start = base_address + size;\t/* whole region via the non-nested prefix path */\n'
     '\tpmap_nesting_size = 0;\n'
     '#endif\n'
     '\tshared_region->sr_pmap_nesting_start = pmap_nesting_start;\n')
print('integrate nonest ok')
