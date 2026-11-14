# iOS 7.1.2 port - progress log

> **TARGET CHANGED (2026-11-10): LG G3 Beat dropped. New target: Samsung Galaxy Tab E 9.6 (SM-T562).**
> See "Session 2" at the bottom. Sections below marked "LG" are historical; the workstation
> prep (toolchain, clones, CRLF warning) still applies.

Old target: LG G3 Beat (D722), Snapdragon 400 (likely MSM8226), 1 GB RAM, 720p.
Reference port: kOtusin/xnu-j1xlte + kOtusin/uniloader (Galaxy J1 2016, Exynos 3475).

## 2026-11-10 - Session 1: workstation prep

### Done
- Cloned `xnu-j1xlte` and `uniloader` into `C:\Users\User\Desktop\Droid\`.
- Android platform-tools (adb/fastboot 37.0.1) at
  `C:\Users\User\Desktop\Droid\tools\platform-tools-dl\platform-tools\`.
- WSL2 Ubuntu: installed `gcc-arm-linux-gnueabi`, `gcc-aarch64-linux-gnu`, `dtc`,
  `lz4`, `abootimg`, `img2simg` tools, bison/flex/cmake/ninja.
- Fresh LF clone of uniloader at `~/uniloader` in WSL (Windows checkout has CRLF
  and breaks Kconfig: `soc/Kconfig:258: unknown option "It"`. ALWAYS build from WSL clones).
- Verified uniloader toolchain: `make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- j1xlte_defconfig`
  succeeds. `make` then stops at `blob/Image` missing (needs the XNU kernel blob).

### Findings about the reference port
- Boot chain: vendor bootloader (S-Boot) -> uniloader (boot.img) -> XNU (embedded,
  `CONFIG_EMBED_XNU=y`) -> iOS userland from SD card (FAT) incl. dyld shared cache.
- `j1xlte_defconfig` key values: TEXT_BASE 0x20008000, XNU phys base 0x30000000,
  virt base 0x80000000, framebuffer reused from bootloader (0x57E05000, 480x800 ARGB8888),
  cmdline `keepsyms=1 kprintf=1 debug=0x14e`.
- uniloader board code per device lives in `board/<vendor>/board-<dev>.c`, SoC support
  in `soc/`, drivers in `drivers/`. No LG boards exist; only Qualcomm SoC file is `msm8916.c`.
- XNU tree is based on HTC HD2 (QSD8250, Qualcomm) port. Board file for J1 is
  `xnu/pexpert/arm/pe_exynos3475_j1.c`; HD2 one is `pe_qsd8250_leo.c`.
  IOKit drivers in `xnu/iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/`
  (`j1_sdmmc.c`, `IOS7LeoDisplay.cpp`, `IOS7LeoHIDTouch.cpp`).
- Repo is source only. Per its own audit it is NOT a standalone build: needs a
  Darwin/Mach-O ARM toolchain, generated MIG/syscall headers, target config.
  No iOS rootfs, shared cache, SDK, or toolchain included.

### Blockers / unknowns
1. Darwin ARM cross toolchain for XNU (cctools/ld64 + clang targeting armv7 Mach-O) not set up.
2. iOS 7.1.2 rootfs + dyld shared cache source (user must supply legally obtained IPSW;
   iPhone 4S/5-class armv7/armv7s firmware).
3. Bootloader on D722: unlock status and a way to run uniloader (boot.img via fastboot
   or LAF/download mode). Unlocking or flashing may wipe data and can brick.
4. Need MSM8226 facts: memory map, UART, GIC/timer, SDCC (eMMC/SD) base, MDP/DSI,
   touch controller, framebuffer address left by LG bootloader.
5. uniloader has no MSM8226 SoC support.

### Next, when phone is connected (read-only recon first)
```
adb devices -l
adb shell getprop ro.product.device ro.board.platform ro.bootloader ro.boot.hardware
adb shell cat /proc/cpuinfo /proc/iomem /proc/meminfo /proc/cmdline
adb shell cat /proc/device-tree/model; adb pull /sys/firmware/devicetree/base (DT dump)
adb shell ls -l /dev/block/platform/*/by-name   (partition layout)
adb shell cat /sys/class/graphics/fb0/{virtual_size,stride,bits_per_pixel}
adb shell su -c 'dd if=/dev/block/... '  (only if rooted; backups of boot/aboot)
fastboot getvar all   (only if bootloader reachable)
```
Safety rules for this project: back up boot, recovery and aboot partitions before any
flash. No flashing or unlock without explicit confirmation from the user.

## 2026-11-10 - Session 2: retarget to Galaxy Tab E 9.6 (SM-T562)

### Device facts (third-party sources, NOT verified on hardware)
- Family SM-T560 (Wi-Fi) / SM-T561 (3G); SM-T562 spec page not found online, treat as a 3G variant.
- SoC reported as Spreadtrum SC7730 / SC7730SE: quad Cortex-A7 @ ~1.3 GHz (ARMv7), Mali-400 MP2,
  1.5 GB RAM, 8 GB storage, 1280x800 display. One source says SC9830. CONFIRM via adb recon.
- Same CPU core as the J1 reference (Exynos 3475, Cortex-A7), so the ARMv7 userland side carries over.

### Support status in reference repos
- uniloader: no Spreadtrum/SC7730 SoC support, no T56x board, no `samsung` T562 config
  (grep for t562/t560/sc7730/spreadtrum/marvell: no hits). Only Samsung Exynos, Qualcomm msm8916+, Apple, MediaTek SoCs.
- xnu-j1xlte: no SC7730 platform expert. Needs a new `pe_sc7730_t562.c` plus drivers.
- Not reusable from J1: Exynos DECON/SDMMC/UART/timer code. Spreadtrum needs its own: UART, GIC
  (Cortex-A7 GIC-400 likely), generic timer, SDIO/eMMC (SDHCI-like), display (DISPC), touch.
- Samsung bootloader on this tablet is Spreadtrum-based (not S-Boot Exynos); boot/flash path is
  different (SPD download mode / Odin-compatible, FDL loaders). Needs research.

### Next
1. Plug tablet in with USB debugging, run read-only recon (cpuinfo, iomem, DT, partitions, fb).
2. Confirm SoC, memory map, UART base, fb address left by bootloader.
3. Decide boot method (uniloader as boot.img payload vs chainload).

## 2026-11-10 - Session 3: TARGET = Samsung Galaxy S4 mini (GT-I9190, serrano3gxx). Recon done.

Tablet and LG dropped. S4 mini chosen: Qualcomm (HD2/APQ8060 lineage already in xnu tree), Odin, kernel sources.
Recon pulled via adb into `recon/`; verified partition backups in `backup/` (SHA256SUMS.txt; efs/modemst hold IMEI/radio data, keep private).

### Device (verified on hardware)
- GT-I9190, SoC MSM8930AB (board string msm8960), dual Krait (CPU implementer 0x51, part 0x04d, ARMv7).
  CPU features: `vfpv4 idiva idivt neon` => armv7s (iPhone 5) code should run. ~1.39 GB usable RAM.
- Running LineageOS 17.1 (Android 10) unofficial userdebug, kernel 3.4.113, bootloader I9190XXUCPK1,
  warranty bit 1 (custom already). `adb root` works (userdebug). Kernel has NO device tree (board-file kernel).
- Display: MIPI DSI video panel (Samsung), 540x960, fb0 32bpp, line_length 2176, virtual 540x2880 (triple buffer),
  channel order R at bit 24, G 16, B 8, A 0 (RGBA, alpha in low byte). fb smem_start 0x822bd000 len 0x5fa000
  (this is the Linux kernel's allocation, NOT the bootloader's splash fb - need to find the bootloader one).
- Touch: Atmel MXT336S on I2C bus 3, address 0x4a. Block device: eMMC on `msm_sdcc.1`.

### Memory map (from /proc/iomem)
- RAM: 80200000-87ffffff, 8e800000-8effffff, 8f800000-8fafffff, 8fe00000-8fefffff, 90000000-9fdfffff,
  a0000000-a5ffffff, a6100000-de9fffff. rmtfs reserved 8fb00000-8fdfffff. Linux kernel at 80208000.
- Peripherals: MDP 05100000-051effff, MIPI DSI 04700000-047effff, Adreno kgsl regs 04300000,
  GSBI/UARTDM: 16440000, 16540000 (uartdm_resource), msm_serial_hs on gsbi 16500000, QUP I2C at 12480000/16200000/16300000/
  1a000000/1a100000/1a200000, USB HS 12500000, DMOV 18320000. SDCC registers are not listed in /proc/iomem
  (get from Samsung kernel source: arch/arm/mach-msm/devices-msm8960.c / board-serrano*).

### Boot image facts
- boot.img: page 2048, kernel load 0x80208000, ramdisk 0x82200000, tags 0x80200100, kernel 4.3 MB.
  Stock-style Android boot.img is accepted by this bootloader (custom ROM runs). Plan: uniloader packed as boot.img
  kernel with XNU embedded, flash with Odin/heimdall/fastboot-equivalent AFTER backups (done).
- Partitions (by-name on msm_sdcc.1): modem p1, sbl1-3 p2-4, aboot p5, rpm p6, tz p7, boot p13, recovery p14,
  system p21 (1.5 GB), cache p22, userdata p24 (5.4 GB).
- Backups verified md5: sbl1 sbl2 sbl3 rpm tz aboot boot recovery param efs modemst1 modemst2 fsg.

### Pitfalls
- Git Bash mangles `/data/...` args to adb: use `export MSYS_NO_PATHCONV=1`.
- `adb exec-out dd` of rpm/modemst1 produced short files; use dd to /data/local/tmp + adb pull, verify with md5sum.

### Next
1. Get Samsung serrano / msm8930 kernel source (LineageOS android_kernel_samsung_msm8930-common) for SDCC, UART, GIC, timer, MDP.
2. Find bootloader splash framebuffer address (dump /dev/mem or check aboot) and test UART availability.
3. Add MSM8930 SoC + serrano board to uniloader; add pe_msm8930_serrano.c + drivers to XNU (start from pe_apq8060.c).
4. Darwin armv7 toolchain, iOS 7.1.2 rootfs (user supplies IPSW).

## 2026-11-10 - Session 4: kernel source + register map

Source: `LineageOS/android_kernel_samsung_msm8930-common` branch lineage-17.1, HEAD `90c8fa00`
(= exact commit of the kernel running on the phone). Cloned to WSL `~/k8930`; device tree repo
`android_device_samsung_serrano-common` at `~/dev-serrano-common`. Board files: `arch/arm/mach-msm/board-8930*.c`,
defconfig `msm8930_serrano_eur_3g_defconfig`. IO maps: `include/mach/msm_iomap-8930.h`.

### Register map for MSM8930 (from kernel source, cross-checked with /proc/iomem)
| Block | Phys base |
|---|---|
| qGIC distributor | 0x02000000 |
| qGIC CPU interface | 0x02002000 |
| Timer (GPT at +0x4, DGT at +0x24) | 0x0200A000 (MSM8930_TMR_PHYS) |
| SDC1 (eMMC, msm_sdcc.1) | 0x12400000 (DML +0x800, BAM +0x2000) |
| SDC3 (SD card slot) | 0x12180000 |
| GSBI5 UARTDM | 0x16440000 (GSBI 0x16400000 + 0x40000) |
| GSBI6 UARTDM (msm_serial_hs) | 0x16540000 |
| MDP | 0x05100000, MIPI DSI 0x04700000, Adreno 3D regs 0x04300000 |
| USB HS | 0x12500000 |

### Reuse in xnu tree
- `pe_apq8060.c`/`.h` (HP TouchPad, MSM8660 family) uses the same qGIC/GPT/DGT register layouts but with
  different bases: GIC dist 0x02080000 / cpu 0x02081000, timer 0x02000000. MSM8930 needs bases above.
  => new `pe_msm8930_serrano.c/.h` can be a near copy of pe_apq8060 with changed bases, IRQ numbers, memory map.
- `pe_qsd8250_leo.c` + IOS7Leo* display/HID code: HD2 uses MDP3 and a different panel. S4 mini uses MDP4 video-mode
  DSI. Simplest first display = reuse the bootloader-configured scanout (like the J1 port did), no MDP programming.
- SDCC: Qualcomm msmsdcc (not Exynos DW-MMC). Need MSMSDCC driver using DMOV/BAM or PIO mode on 0x12400000.
- Platform config switch lives in `osfmk/arm/PlatformConfigs.h` (BOARD_CONFIG_*), add BOARD_CONFIG_MSM8930_SERRANO.

### Still unknown
- Bootloader splash fb address (Linux kernel fb at 0x822bd000 is kernel-allocated). Find via aboot disassembly / RAM dump.
- Whether any usable UART is exposed (S4 mini: possibly via USB cable UART/JIG mode, not verified).
- Exact reserved ranges (kernel mem_map: ion carveouts, rtb) for XNU memory policy.

## 2026-11-10 - Session 5: first code (uniloader serrano3gxx + XNU timer scaffold)

Working tree for uniloader is WSL `~/uniloader` (LF). Deliverable: `patches/uniloader-serrano3gxx.patch`
(apply with `git apply` on a fresh LF clone of kOtusin/uniloader).

### uniloader (builds)
`make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- serrano3gxx_defconfig && make` => `uniLoader` (655 KB with 4 KB dummy blobs).
Changes:
- `soc/Kconfig`, `soc/Makefile`, `include/soc/msm8930.h`, `soc/qualcomm/msm8930.c`: new QC32_8930 SoC (empty init;
  Samsung bootloader leaves clocks/GIC/display on).
- `board/samsung/board-serrano3gxx.c` + Kconfig/Makefile + `configs/serrano3gxx_defconfig`:
  TEXT_BASE 0x80208000 (= boot.img kernel load addr), XNU phys base 0xA6100000, memsize 0x38800000
  (RAM block a6100000-de9fffff), ramdisk 0x82200000. uart_puts is a NO-OP on purpose: touching a clock-gated
  Qualcomm UARTDM stalls the bus. simplefb only registered when CONFIG_XNU_FB_BASE != 0 (it is 0: bootloader fb unknown).
- `arch/arm/start.S`, `arch/arm/load-kernel.c`: J1 debug paint (hardcoded 0x57Exxxxx, unmapped on Qualcomm) is now gated by
  new `CONFIG_DEBUG_PAINT` (default y only for J1). Without this the loader would write to unmapped addresses at entry.
- Not done: Hyp/non-secure entry assumptions, SD/eMMC loading (sd-boot.c is Exynos-only), cacheslice/rootfs loading
  (needs a Qualcomm msmsdcc reader), real blobs (kernel Image, dtb, ramdisk).

### XNU (scaffold, NOT built)
- `xnu/pexpert/arm/msm8930_timer.{h,c}`: qGIC (0x02000000/0x02002000) + DGT timer (0x0200A000+0x24, 6.75 MHz, IRQ 17),
  guarded by `BOARD_CONFIG_MSM8930_SERRANO`, same API shape as j1_timer.c. Syntax-checked with stub headers only.
- Still required for XNU: add `BOARD_CONFIG_MSM8930_SERRANO` to PlatformConfigs.h and the ~111 J1-specific
  `#if` sites in 33 files (bsd_init.c, kern_exec.c, pmap.c, trap.c, locore.s ...; each needs review, they carry J1 hacks),
  a new `pe_msm8930_serrano.c` (copy of pe_exynos3475_j1.c; its `j1_video_ok()` hardcodes 480x800, phys 0x30000000, fb 0x57E05000),
  MSM SDCC (msmsdcc) IOKit storage driver, display scanout/panel handling, Atmel MXT336S touch, files.arm entries.

### Blockers now
1. Bootloader fb address (needed for any on-screen output). No UART, so display is the only debug channel.
2. Darwin armv7 toolchain + generated MIG headers to even compile XNU.
3. iOS 7.1.2 IPSW rootfs/dyld cache (user-supplied).

## 2026-11-10 - Session 6: bootloader framebuffer search (NOT FOUND yet)

Result: fb address of the bootloader splash is still unknown. Nothing was written to the phone.

### What was checked
- `aboot.img` is Qualcomm LK-derived (strings: display_init, mipi_config, "Config MIPI_VIDEO_PANEL",
  mipi_video_samsung_oled_qhd_pt_init), Thumb-2, header words `5, 3, 0, 0x88e00000` => loaded/run at 0x88e00000.
  Its DRAM bank table (file offset 0x51720) lists banks, not the fb. Static literal scans found no fb pointer
  (strings/data are referenced position-independently; only 13 MDP/DSI constants, all DSI/MDP-config code near 0x88e0d28x-0x88e0d804).
- Reserved/known RAM in bootloader range: sec_log 0x88400008, sec_dbg 0x88490004, rmtfs 0x8fb00000 (from kernel cmdline/iomem).
- Live Linux fb is 0x822bd000 (kernel allocated): NOT the bootloader's. Reading live MDP regs only shows Linux's state.
- Not available on the device: /dev/mem, /proc/kcore, mdp debugfs. CONFIG_MODULES=y but MODVERSIONS=y (module would need
  CRCs from /proc/kallsyms and a gcc<=11 build); and it would only reveal Linux's fb anyway.
- Early dmesg is truncated (starts at ~8.8 s), so no early msm_fb prints.

### Remaining ways to find it (all need a probe boot image, i.e. a boot partition write = user approval)
1. Probe payload that reads MDP4 pipe SRC-address registers at handoff and reprograms scanout to a buffer we own
   (RGB1 pipe regs MDP+0x40000.., overlay0 MDP+0x10000, DMA_P MDP+0x90000), user reports what the screen shows.
2. Payload chain-loads the stock Linux kernel with the MDP register dump appended to the kernel cmdline, readable
   afterwards via `adb shell cat /proc/cmdline` (no need to look at the screen).
3. Fuller disassembly of aboot's LK display path (mdp/mipi_dsi init, `fbcon_config`) in Ghidra.
Recovery path if a probe fails: boot partition backup is `backup/boot.img` (verified); restore via recovery + adb or Odin.

## 2026-11-10 - Session 7: probe boot image built (NOT flashed)

`probe/` : `probe.c` (ARM stub linked at 0x80208000) + stock Lineage zImage appended => `probe/boot_probe.img`
(10 MB, header copied from stock, kernel = stub 1200 B + zImage, original ramdisk, SEANDROIDENFORCE trailer).
Rebuild: `wsl bash probe/build.sh` (+ re-pack step in Session 7 python, see boot_probe.img.sha256).
Behaviour: sets sp, reads 19 MDP4 registers (MDP+0x0, overlay 0x10000/4, VG1/VG2/RGB1/RGB2 pipes size/srcp0_addr/ystride,
DMA_P cfg/size/addr/ystride), rebuilds the ATAG list with the cmdline minus cordon/connie/sec_log/sec_dbg/etb_buf/
sec_debug./msm_rtb. tokens plus `fbp=<19 hex words>`, copies zImage to 0x81800000 and jumps with r0=0,r1=machtype,r2=new atags.
Tested only under QEMU virt (fake MDP in RAM): filtering, fbp append and chain-load OK. Not tested on hardware.
Risks: reading MDP regs with clocks gated would hang the boot; removed cmdline tokens drop Samsung debug-log reservations.
Scripts: `probe/flash_probe.sh` (dd boot partition via adb root, checksum-verified push), `probe/restore_boot.sh` (from backup/boot.img).
Read result after Android boots: `adb shell cat /proc/cmdline`, look for `fbp=`.
Recovery if it hangs: recovery partition untouched (Vol Up+Home+Power), then restore; or Odin in download mode (Vol Down+Home+Power).
Register order in fbp: 0x0,0x10000,0x10004, VG1 0x20000/10/40, VG2 0x30000/10/40, RGB1 0x40000/10/40, RGB2 0x50000/10/40, DMA_P 0x90000/04/08/0c.

## 2026-11-10 - Session 8: probe flashed, FRAMEBUFFER FOUND

Probe boot image booted Android normally; `fbp=` read from /proc/cmdline:
`04030705,000000ff,0000000b, VG1 00200020,0,00000060, VG2 same, RGB1 same, RGB2 same, DMA_P 0100213f,03c0021c,88100000,00000654`
- Overlay pipes idle (src addr 0). Live scanout is MDP DMA_P: **buffer 0x88100000**, size 0x03c0021c = 540x960,
  **ystride 0x654 = 1620 B = 540*3 => RGB888 (24 bpp)**, cfg 0x0100213f. MDP hw rev 0x04030705.
- This is Android's state after Linux boot; the bootloader splash fb is expected to be the same DMA_P buffer
  (aboot hands over a running DSI video scanout). Needs on-screen confirmation in a later probe/uniloader draw test.
- Fix in uniloader serrano config: XNU_FB_BASE=0x88100000, width 540, RGB888 stride 3 (applied).
- boot partition restored to stock backup afterwards (md5 matches backup/boot.img).

## 2026-11-10 - Session 9: framebuffer CONFIRMED on screen

`probe/paint.c` (boot_paint.img) painted white strip + R/G/B bands to 0x88100000 (540x960, stride 1620, bytes R,G,B) before
chain-loading stock zImage. User saw correct R/G/B bands => **bootloader scanout = 0x88100000, RGB888 (memory order R,G,B), stride 1620.**
Also proves: custom code at 0x80208000 runs (MMU off, caches off), MDP/DGT register access is safe, boot.img chain-load works.
Boot partition restored to stock afterwards (md5 matches backup/boot.img). Scripts: probe/flash_paint.sh.
Serial: none; screen is the debug channel. Next: uniloader-on-device test with real console text (simplefb), then storage.

## 2026-11-10 - Session 10: uniloader selftest on hardware (autonomous mode)

User approved autonomous work. Built `serrano3gxx_selftest_defconfig` (CONFIG_SELFTEST_CHAIN: print console via simplefb,
wait ~8 s, chain-load stock zImage from blob/Image with bootloader r1/r2 saved at 0x80203ff8). Also gated J1-only memtest
(`CONFIG_SAMSUNG_J1XLTE`) and J1 debug paint. Image `probe/boot_selftest.img` (uniLoader 5.1 MB incl. zImage blob).
Result: flashed, phone rebooted and came back to Android => uniloader entry, relocation check, console init and chain-load survived.
On-screen text NOT yet confirmed (awaiting user report). Boot restored to stock afterwards.

## 2026-11-10 - Session 11: console text CONFIRMED
User saw uniLoader logo + selftest text on the S4 mini screen. Display path (simplefb at 0x88100000, RGB888 540x960), uniloader
entry/relocation, printk console and chain-load are all working on hardware. Next: XNU build toolchain.

### Toolchain plan (blocked on permission, Session 11)
XNU (imbushuo/xnu lineage, built with plain `make TARGET_CONFIGS="debug arm <CONFIG>"`) needs a Mach-O armv7 toolchain.
Plan: tpoechtrager/cctools-port (ld64 + as, target arm-apple-darwin11) cloned at WSL `~/cctools-port`, with clang 21 (supports armv7).
Host deps installed in WSL: llvm, libtool, autoconf, automake, pkg-config, libxar-dev.
Still missing after cctools: MIG, ctfconvert/ctfmerge (dtrace tools), iOS 7 SDK headers, xnu-deps-linux.
The auto-mode classifier denied running `./configure` of the cloned cctools-port (code from an external repo); needs user OK / permission rule.

## 2026-11-10 - Session 12: Mach-O armv7 toolchain WORKS
Settings rule (.claude/settings.json, created by user) allowed `cctools-port` WSL commands.
Built in WSL: libdispatch (swift-corelibs, ~/cctools-port/deps-install) -> cctools-port (ld64/as/ar/lipo/otool, prefix ~/cctools,
target arm-apple-darwin11). Verified: `clang --target=armv7-apple-ios7 -nostdlib -c` => Mach-O armv7 object; `arm-apple-darwin11-ld -arch armv7 -r` links it.
Use: `export PATH=$HOME/cctools/bin:$PATH`.
Next: MIG, ctfconvert/ctfmerge stubs, SDK headers, build XNU (j1 tree) to see how far `make TARGET_CONFIGS="debug arm EXYNOS3475_J1"` goes
(as a baseline before porting to MSM8930).

### MIG attempt (Session 12, unfinished)
bootstrap_cmds cloned (~/cctools-port/deps-bootstrap_cmds). migcom needs a lexer/parser (flex/bison OK) but compiling it on Linux against
xnu's mach headers hits host/glibc type conflicts (bsd/i386/_types.h vs glibc, missing libkern/OSByteOrder.h, `rtMaxReplySize` member mismatch
=> bootstrap_cmds version newer than this XNU's expectations). Options: (a) use an older bootstrap_cmds matching xnu-1699-era mig,
(b) compile migcom with a small private shim header set instead of the real xnu headers, (c) use Darling's Linux mig port.
Remaining before any XNU compile: MIG, ctfconvert/ctfmerge (can stub), iOS 7 SDK headers, then fix the J1 tree's build, then the MSM8930 port.

## 2026-11-10 - Session 13: MIG WORKS
bootstrap_cmds-91 migcom built on Linux with a tiny private shim (~/cctools-port/mig-shim: real osfmk message.h/port.h/ndr.h + stubs),
excluding handler.c. Installed `~/cctools/bin/mig` (mig.sh, bash) + `~/cctools/libexec/migcom` + `~/cctools/bin/cc` wrapper (clang --target=armv7-apple-ios7).
Usage: `export PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc; mig -arch armv7 -user x.c -server y.c -header z.h -I<dir> file.defs` (note: -I joined to its path).
Verified on osfmk/mach/clock_reply.defs. LF clone of the J1 xnu tree at WSL ~/xnu-j1 (Windows checkout has CRLF).

## 2026-11-10 - Session 13b: XNU (J1 tree) COMPILES AND LINKS on Linux
Build recipe (WSL `~/xnu-j1`, LF clone of kOtusin/xnu-j1xlte):
```
export PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc HOST_CC=$HOME/cctools/bin/hostcc
cd ~/xnu-j1/xnu && . SETUP/setup.sh
make TARGET_CONFIGS="release arm EXYNOS3475_J1XLTE" MAKEJOBS=-j8 SDKROOT=$HOME/sdk/ios7
```
Result: `BUILD/obj/RELEASE_ARM_EXYNOS3475_J1XLTE/mach_kernel` Mach-O armv7, 9 MB, __TEXT vmaddr 0x80001000 (the kext .symbolset step still
fails on `--target` flag in kextsymboltool: irrelevant for booting).
Shims created in ~/cctools/bin: xcrun (fake, maps -find to my tools), cc (clang --target=armv7-apple-ios7), hostcc (K&R-tolerant host clang),
mig + libexec/migcom, setsegname, kextsymboltool (host tools built from xnu SETUP + libstuff), ld64-wrapper (-> arm-apple-darwin11-ld).
Edits to the build copy only: makedefs/MakeInc.cmd (xcrun path), makedefs/MakeInc.def (ld64-wrapper path), libkern/c++/OSKext.cpp
(struct copy -> bcopy to dodge a `_memcpy.412` undefined symbol with clang 21).
Next: add BOARD_CONFIG_MSM8930_SERRANO / MSM8930_SERRANO target config and build it.

## 2026-11-10 - Session 14: XNU for MSM8930_SERRANO COMPILES AND LINKS
Target config `MSM8930_SERRANO` added to the build copy (WSL ~/xnu-j1). Patch: `patches/xnu-msm8930-serrano.patch` (apply to a fresh LF clone of kOtusin/xnu-j1xlte;
also needs the host-tool edits listed in Session 13b: MakeInc.cmd xcrun path, MakeInc.def ld64-wrapper path, OSKext.cpp bcopy).
Changes: (1) all J1 compat `#if` sites now also accept BOARD_CONFIG_MSM8930_SERRANO (mechanical, 23 files, incl. IOKit display/HID/HFS sites);
(2) new `pexpert/arm/pe_msm8930_serrano.c` (platform expert derived from the J1 one: phys base 0xA6100000, mem 0x38800000, fb 0x88100000 540x960,
UART no-op) and `msm8930_timer.{c,h}` (qGIC + DGT, from kernel sources); (3) `IOS7M8930SDMMC.cpp` placeholder `ios7j1_register_sd`;
(4) files.arm entries; MakeInc.def machine config + ARCH_FLAGS; nokextd header guard.
Output: `probe/mach_kernel_serrano` (Mach-O armv7, 8.96 MB). NOT booted yet.
Known gaps before it can boot: (a) fb is 24 bpp RGB888 but XNU console/display code assumes 32 bpp (need DMA_P reprogram to ARGB8888 or conversion blit);
(b) storage: no msmsdcc driver, so ROOTFS.HFS cannot be read (placeholder only); (c) no Apple device tree / boot_args built for this board in uniloader
(check CONFIG_XNU_* path in load-kernel.c, j1xlte-specific); (d) iOS 7.1.2 rootfs + dyld shared cache from user IPSW; (e) touch driver (Atmel MXT336S) not written.

## 2026-11-10 - Session 15: FIRST XNU BOOT ATTEMPT on the S4 mini
Built: shadow-framebuffer (32bpp BGRA in kernel memory -> 24bpp RGB888 scanout, 60 rows per 10 ms tick) in pe_msm8930_serrano.c;
`probe/mkdt.py` minimal Apple DT (root compatible "S4MINI,1","AppleARM"; /chosen/memory-map, /cpus/cpu0, /arm-io, /defaults);
uniloader `serrano3gxx_xnu_defconfig` embedding mach_kernel_serrano + DT + 2 KB dummy ramdisk => `probe/boot_xnu.img` (9.7 MB).
No rootfs/DSC/storage driver yet, so best case: kernel boots, prints to the screen, then panics/hangs when it can't find the root.
Recovery if the phone sticks: hold Vol Up + Home + Power -> recovery -> `adb` -> `bash probe/restore_boot.sh` (or Odin in download mode).

## 2026-11-10 - Session 16: XNU PRINTS ON SCREEN
User reports kernel text on the S4 mini screen after flashing boot_xnu.img: uniloader -> XNU entry -> framebuffer text path (shadow->scanout flush) works.
Awaiting the text (last lines / panic) to see how far XNU got. Boot partition still holds boot_xnu.img (restore via recovery + probe/restore_boot.sh).

## 2026-11-10 - Session 17: camera works; first XNU boot attempt did NOT get past uniloader
Webcam: ffmpeg dshow from "OBS Virtual Camera" (needs OBS Start Virtual Camera with the webcam source); frame is rotated 90deg:
`ffmpeg -f dshow -i video="OBS Virtual Camera" -frames:v 3 -update 1 raw.jpg; ffmpeg -i raw.jpg -vf "crop=1000:1080:0:0,transpose=1,scale=iw*1.6:ih*1.6:flags=lanczos,unsharp=5:5:1.5" rot.png` (recon/cam/).
Reading the first photo: the screen shows the uniLoader banner/log ending at "xnu: entry offset ea8e0 (parsed)"; no XNU output => XNU hangs/dies right after entry
(the earlier "kernel text" was uniloader's log). Fixes in this build (not yet run):
- 2x console zoom (XNU console 270x480, flush upscales to 540x960) for webcam legibility.
- locore.s: S4-mini identity sections (0x88100000, 0x88200000 scanout; 0x02000000 GIC/timer) in the entry tables; the J1 UART/FB sections (0x13800000, 0x57E00000...) are now J1-only.
- arm_vm_init.c: seeds 0x881/0x882/0x020 identity sections in the new tables (MSM only).
- `ios7m8930_mark(n)`: draws small coloured progress boxes at the bottom of the scanout (bar n at x=n*26, y=900+14*(n/40)); arm_init marks 1..20 around each init step,
  stage checkpoints 6..10 -> bars 66..70, bsd stages 0x1.. -> 41+.
Iteration plan without recovery key combos: stock boot stays in `boot`, XNU test image lives in the `recovery` partition
(`probe/rec_xnu.img`); `adb reboot recovery` boots XNU, power-hold returns to Android. One-time setup via TWRP: `bash probe/stage_recovery_xnu.sh`.
Phone currently stuck in the old XNU boot image (boot partition) until the user boots TWRP (Vol Up+Home+Power).

## 2026-11-10 - Session 18: new capture rig + boot-loop to XNU recovery image
Capture: `iphonecontrol/snap.py` (second iPhone photographs the S4 mini screen; needs iphoneview.py --usb running; reads photos/IMG_xxxx.JPG). Far better quality than the webcam.
Photo of the running image: build date 14:51:15 (first marker build), log ends at `xnu: entry offset cc8e0 (parsed)`, no markers => XNU dies before arm_init.
Problem: every boot (normal, battery pull, recovery combo) now lands in uniloader although `boot` holds stock. Likely cause: `adb reboot recovery` set a recovery
flag (BCB in a Samsung partition) that only a real recovery clears, so all boots load the `recovery` partition (= our XNU image).
Fix path: download mode (Vol Down + Home + Power) -> Odin -> `odin/recovery.tar.md5` (TWRP recovery.img from backup/) -> boots TWRP (adb) -> I restore boot/clear the flag.

## 2026-11-10 - Session 19: watchdog fallback mechanism
Odin restored TWRP; flags cleared; Android back. Rule from user: never write the `recovery` partition again (boot partition only; `probe/flash_boot.sh <img>`).
Built `serrano3gxx_fb_test_defconfig`: uniloader arms the MSM WDT0 (0x0208A038: RST+0, EN+8, BARK+0x14, BITE+0x24; 23 s), sets RAM flag 0x584E5550 @0x80203fd0,
XNU is LZ4-compressed (probe/mklz4.py: 9.0 MB -> 4.7 MB) and the stock zImage rides in the ramdisk blob so boot.img still fits 10 MB. XNU pets the WDT in its timer tick.
Hang test on hardware: WDT bite fired, RAM flag survived the reset, second boot printed "fallback: previous XNU attempt did not finish -> Android (4527400 bytes)"
=> mechanism works (watchdog reset + RAM persistence confirmed). BUT the chained stock kernel then did not come up (no adb after 3+ min, screen frozen on that line).
Selftest chain (no WDT reset) worked earlier with the same zImage/address, so the difference is state after a WDT-bite reset. Investigating.

### Session 19b - why the chain failed: the boot.img ramdisk
Chain-only test (no WDT) also failed => not a watchdog-state problem. Root cause: the image I packed used a dummy 2 KB ramdisk; Android's /init lives in the
boot.img ramdisk (770 KB), so the stock kernel booted with no root. Earlier selftest worked because it kept the original ramdisk.
Fix: pack with the original `probe/ramdisk.img` and shrink the payload: stripped kernel (`arm-apple-darwin11-strip -S -x`, 9.0 -> 6.35 MB) + LZ4 (3.54 MB) + zImage 4.5 MB + ramdisk 0.77 MB = ~9.5 MB < 10 MB.
NOTE: uniloader's make does not track blob/* changes: `touch arch/arm/start.S` before `make` after replacing blobs.
Image: probe/boot_fallback.img (real XNU run + WDT fallback to Android).

## 2026-11-10 - Session 20: fallback = reboot to TWRP (clean PMIC reset)
Photo (iPhone, after unlocking it - snap.py needs the iPhone unlocked; `open` says "device locked" otherwise) shows the chain-to-Android fallback hangs at
"fallback: previous XNU attempt did not finish -> Android" even with the real ramdisk, i.e. chaining the stock kernel after a WDT-bite reset is unreliable.
New approach (what the user asked for): on fallback, mimic `reboot recovery` from the Samsung kernel source (restart.c):
IMEM restart reason `*(0x2A00065C)=0x77665502` (aboot reads it) then `*(0x00800820)=0` (PSHOLD_CTL_SU = TLMM 0x00800000+0x820) => PMIC power cycle -> TWRP with adb.
Image: probe/boot_recfb.img (XNU + 23 s WDT + RAM flag; second boot reboots to recovery). Iteration loop becomes: in TWRP `adb push` + dd to `boot`, `adb reboot`, photograph,
XNU hang -> WDT -> recovery (TWRP) automatically. Restart-reason codes in the kernel: 0x77665500 normal, 0x77665501 bootloader/download, 0x77665502 recovery.
Session 20b: first recovery-fallback run did NOT reach TWRP: I used the wrong IMEM address. MSM8930 IMEM is 0x2A03F000 (not 0x2A000000), so restart_reason is at 0x2A03F65C.
Fixed in uniloader main.c; image rebuilt (probe/boot_recfb.img). Also seen: PS_HOLD reset (0x00800820) does reset the SoC and clears the RAM flag.

## Session 21 — XNU boots to BSD / root-device wait (2026-11-10)

Result: kernel console text now renders on the S4 mini. XNU reaches `bsd_init`, IOKit matching, AppleARMCPU/AppleARMIO,
mbinit, kminit, pseudo_inits, and then blocks: `Waiting on <dict IOProviderClass=IOMedia Content=Apple_HFS>` (no root disk).

Debug technique: progress marks drawn straight into bootloader scanout via VA alias 0x30000000 (strongly-ordered sections
l1[0x300]/[0x301]) + hex readout rows (row8 = last mark, rows 9/10 free-form values at y=452/474). uniLoader clears y>=540 before entry
so stale marks cannot mislead. Camera rig: iphonecontrol/snap.py. adb pinned with ANDROID_SERIAL=077af85a (T561 also on this PC).

Bugs found, in order:
1. Executing section's identity map overwritten by SDRAM linear map -> restore identity of the executing section.
2. Scanout PA collides with kernel linear-map VA; alias at 0xC0000000 clobbered -> alias moved to 0x30000000.
3. BSS not zeroed by uniLoader flat copy -> xnu_zero_bss() in load-kernel.c.
4. __KLD segment __constructor (kld bootstrap, 2 thumb ctors at 0x807a500d/5041) hung OSRuntimeInitializeCPP -> skip __KLD in ctor scan.
5. DGT timer PPI (IRQ 17) was configured level-triggered; the MSM timer pulses -> never delivered, IOKitInitializeTime/waitForService
   timed waits hung forever. Fix: GIC_DIST_CONFIG edge bit. Timer ticks now fire, scheduler preempts, boot proceeds.

Debug marks still in tree (kernel_bootstrap 300-317, kernel_bootstrap_thread 499-532, bsd_init 620+, IOKit 600-606, OSRuntime 700-722).

Next: msmsdcc (SDC1 0x12400000 eMMC / SDC3 0x12180000 SD) block driver publishing IOMedia, HFS rootfs (needs user IPSW: iPhone 5 armv7s
or 4S), fuller Apple DT, touch, remove marks. Phone WDT-resets to TWRP after 58 s automatically.

## Session 22 — rootfs + storage driver (2026-11-10)

- IPSW: iPhone5,2 7.1.2 (11D257) in repo root. Rootfs DMG 058-4447-009.dmg decrypted (vfdecrypt algo in probe/vfdec.py, key from
  theapplewiki Keys:Sochi_11D257_(iPhone5,2)), UDIF->raw (probe/udif2raw.py), HFSX partition at +0x8000 (ipsw_x/rootfs_hfsx.img).
  7-Zip extracted tree in ipsw_x/rootfs (launchd, dyld_shared_cache_armv7s present). NOTE: armv7s-only cache -> kernel must report cpusubtype v7s.
- Root-file design reused from HD2/J1: raw block device -> IOBlockStorageDriver -> IOMedia -> IOS7LeoHFSFile (fat_locator) finds
  IOS7/ROOTFS.HFS in the single MBR FAT32 partition and exposes it as Apple_HFS with RAM copy-on-write. HFSX header patched (journal bit +
  journalInfoBlock cleared, truncated to exact volume size) by probe/mkfatimg.py; card image = MBR + FAT32(spc 8) = ipsw_x/card.img (1.74 GB).
- Storage target: eMMC userdata (mmcblk0p24, start LBA 4030464, 11239391 sectors) - Android data wiped (user OK'd).
- New driver iokit/.../IOS7M8930SDMMC.cpp: msmsdcc SDC1 (0x12400000) PIO read-only, CMD17 via MCI FIFO, relies on aboot's eMMC state
  (CMD13 rca 2/1, CMD7 if not transfer). IOS7LeoHFSFile accepts IOS7M8930SDMMC. Untested on HW at time of writing.
- adb exec-in streaming dropped 2 bytes mid-stream (corrupt after ~650 MB). Use probe/pushcard2.py: 64 MiB chunks via adb push to /cache,
  dd seek, md5 verify per chunk.
- Added: WDT no longer petted after 3000 ticks (30 s) so fallback to TWRP works while XNU keeps running.

### Session 22b — storage works, scheduler bug found (2026-11-11)
- msmsdcc driver FIXED and verified on HW: DATA_CTL block size field takes byte count (512<<4, not log2) and FIFO is a 16-word window read at
  sequential addresses (FIFO + (i*4 & 63)). Reference: Qualcomm LK mmc.c (android.googlesource.com/kernel/lk, qcom-dima-8x74-fixes). eMMC
  left in transfer state by aboot works as-is (CMD13 rca=2 state=4, LBA0 sig 55aa, ptype 0c).
- IOS7LeoHFSFile (fat_locator) located+validated IOS7/ROOTFS.HFS (file size constant in IOS7LeoHFSFile.cpp changed to 1741471744; probe accepts
  IOS7M8930SDMMC). Earlier builds printed "Leo file: validated ... registerService returned".
- IOKitInitializeTime: skipped IORTC wait on this port (deadlocked vs IOMediaBSDClient waiting for IOBSD resource).
- Kernel threads run with CPSR.I set; timer IRQs are only taken in the idle WFI window (cooperative). In-kernel IRQ preemption path
  (traps_lo.s preempt_kernel -> ast_taken) disabled for MSM8930.
- Kernel-thread self-termination (thread_terminate -> ast_taken(AST_APC) -> thread_terminate_self) never completes; IOKit config threads now
  PARK in IOSleep(500) loop instead of exiting (workaround in IOService.cpp _IOConfigThread::main).
- CURRENT BLOCKER: newly created kernel threads never run. Counters: only 1 config thread ever started while gNumConfigThreads reached 10
  (jobs=9 outstanding), run queue count = 14 threads, processor->state=RUNNING. thread_select/thread_invoke (Switch_context to a thread that has
  never run) is suspect. Root disk therefore never appears (HFSFile start / HFSDriver never run) and bsd_init waits for Apple_HFS.
- Debug infra: marks (row 12), hexN rows 8..18 below console (y=612+22*(row-8)), full-console flush from park loop, SC>/SC< and DSM printf.
  adb must be pinned: ANDROID_SERIAL=077af85a. Rootfs now on eMMC userdata as FAT32 card image (probe/pushcard2.py verified chunk writes).

### Session 22c — hang with IRQs masked (2026-11-11)
- Timer IRQ counter (row 10) freezes at ~0x12 across two photos 10 s apart: CPU hard-hung with CPSR.I set shortly after storage/IOKit matching
  starts. Earlier "run queue starved" theory (rq=22, hq=95) was a symptom, not the cause. Re-enabled preempt_kernel->ast_taken in traps_lo.s (no change).
- HFS driver (IOS7LeoHFSDriver) never starts because matching jobs never complete (counters ios7m8930_dbg[0..3] stay 0).
- Next: identify the spinner. Ideas: use WDT bark/FIQ to sample PC while IRQs masked, or bisect with marks inside doServiceMatch/probeCandidates
  for the HFSFile job and IOMediaBSDClient publication (IOBSD wait), or log lock acquisition (simple_lock spin with IRQs off).
- Camera: iphone must be awake/unlocked; crop right/bottom; keep console 300 rows so hex rows at y>=612 stay in frame.

## Session 23 — ROOT FILESYSTEM MOUNTS (iOS 7.1.2 HFSX from eMMC)
- Hang root cause chain: (1) DGT timer race fixed earlier; (2) my own debug thread `m8930_ticker` (IOS7M8930SDMMC.cpp) did `IOSleep(1000)` and busy-waited in `clock_delay_until`->`machine_delay_until` because new kernel threads ran with IRQs masked (`ml_get_interrupts_enabled()==FALSE`), starving the whole scheduler. Found via frame-walk of return addresses in `M8930_get_timebase` and flags dump in `_clock_delay_until_deadline`.
- Fixes: ticker thread disabled; `thread_continue` always `spllo()` on MSM8930; `Call_continuation` does `cpsie i`; `dgt_get_count()` no longer requires two identical MMIO reads (bounded retry).
- Result: IOKit matching completes (22 jobs), IOS7LeoHFSDriver publishes Apple_HFS, bsd_init mountroot OK:
  `HFS: Vol: Sochi11D257.N420S`, `vfs_mountroot returned errno=0`, `root mount readonly=1`.
- Next: bsd_init continues -> launchd (/sbin/launchd, armv7s cpusubtype), dyld shared cache armv7s.

## Session 23b — iOS USERLAND RUNS (launchd as PID 1)
- Init-thread starvation: ~22 parked IOKit config threads looped on IOSleep(20)+full fb flush at pri 80. Park now blocks forever (assert_wait/thread_block).
- WFI idle loses wakeups on this port: machine_idle is a busy idle with `cpsie i` for MSM8930 (a first attempt returned with IRQs masked -> watchdog -> phone stuck in a garbage-screen/download state needing Power+VolUp).
- Low identity mappings (VA 0x30000000 fb alias, 0x0208A038 WDT) are TTBR0 space and vanish once a user pmap is active: hexrow now draws via the kernel ml_io_map of the scanout; WDT petted via ml_io_map (ios7m8930_pet_wdt()).
- decmpfs: built-in zlib decompressors for compression types 3 (xattr) and 4 (resource fork) in bsd/kern/decmpfs.c (iOS rootfs binaries are HFS-compressed; without them exec of /sbin/launchd failed with errno 45 ENOTSUP).
- Storage speed: CMD18 multi-block reads (<=64 blocks) in IOS7M8930SDMMC + batched clean-run reads in IOS7LeoHFSFile (readRun, up to 256 sectors).
- Result: `init execve returned err=0`; launchd runs in user mode, spawns further processes, prints "Kext loading now disabled", then `PMRD: PagingOff all drivers took ...` and the device reboots (userland called reboot()). Next: find who/why.

## Session 23c — launchd brings up the iOS daemon set
- /etc/fstab patched on-disk (decmpfs xattr at card.img 0x43cdf038, sector 2221816 of mmcblk0p24): `/dev/disk1 / hfs rw 0 0` (no fsck pass, no separate /var). Before: fsck_hfs "QUICKCHECK ONLY; NO HFS SIGNATURE FOUND" -> launchctl called reboot().
- Root volume was built with 0 free blocks ("No space left on device"): IOS7LeoHFSFile now presents the HFSX volume 1 GiB larger (LEO_GROW_BLOCKS 262144): volume headers patched on base reads, reads past the file are zeros, writes go to the RAM COW overlay; fileBytes() reports the virtual size so IOS7LeoHFSDriver publishes Apple_HFS.
- maxproc raised (NPROC 532 for MSM8930; was 52 from MAXUSERS 2 -> "proc: table is full").
- Debug: reboot() prints the requester and holds; every exec/exit printed (`J1 exec pid N (name)`, `J1 exit pid N (name) xstat`).
- Result: ~70 daemons start (UserEventAgent, powerd, identityservicesd, MobileStorageMounter, fairplayd.H2, installd, mstreamd, wirelessproxd, DumpPanic, ...). Seen: launchd[20] usermode data abort EXC_BAD_ACCESS; many CODE SIGNING cs_invalid_page notices (harmless while CS not enforced).

## Session 24 — boot speed fixed; daemons up; backboardd hits the graphics wall (2026-11-12)
- CPU hog found by sampling the interrupted PC/LR (+thread) at every timer tick into a ring and symbolizing user PCs against the
  dyld shared cache (probe/dsc_lookup.py, cache slide printed by the kernel). The hog was my own debug drawing: every syscall return
  (thread_return_join -> ios7m8930_tbr) and every ml_set_interrupts_enabled drew hex rows into the framebuffer, plus a 100..600-row
  uncached scanout copy on every tick. Removed; console refresh now every 4th tick. Boot to ~50 daemons in ~20 s (was minutes).
- Missing iOS 7 syscalls (table ends at 439): 441 guarded_open_np, 442 guarded_close_np, 444 change_fdguard_np, 446 proc_rlimit_control
  shimmed in bsd/dev/arm/unix_syscalls.c (guards accepted, not enforced); other 440..479 return ENOTSUP instead of SIGSYS.
  (accountsd/aggregated/passd/mediaserverd were being killed by SIGSYS.)
- Debug aids: `J1 EXC pid name e far kr pc lr` + user r7 backtrace on every user exception; `J1 ABRT` + backtrace + stack string scan on
  __pthread_kill(SIGABRT); `J1 NOSYS`; `J1 sp <name> err`; `J1 X pid name xstat`. probe/dsc_dis.py disassembles cache code (capstone).
- powerd: CF trap (udf) in IOKit power-settings defaults (CFDictionarySetValue on the Battery/AC/UPS profile dict). Not blocking.
- **backboardd: uncaught NSInternalInconsistencyException "No window server display found"** (BKDisplayStartWindowServer,
  megatrond/BKDisplay.m). QuartzCore's CAWindowServer finds no display = no IOMobileFramebuffer service in the IORegistry.
  This is the graphics wall: next step is a kernel IOMobileFramebuffer-compatible driver over the MSM8930 MDP framebuffer
  (user-client selectors used by IOMobileFramebuffer.framework), then the CoreAnimation renderer (needs IOSurface + a GL path; the
  iPhone5 SGX543 userland driver cannot run on Adreno 305).

## Session 25 — display published, first GUI frame, SpringBoard blocked in check-in
- Link fix: clang emits `_memcpy.N` aliases; OSRuntime.cpp stub list extended to 62..139.
- AppleCLCD/IOSurfaceRoot (IOS7LeoDisplay.cpp) now publishes at 540x960 (sticky `ios7j1_disp_stage`: 0x900 = published, +1 per fb open).
  backboardd opens fb (D903), "No window server display found" gone. First real swap presented (P1); later swaps are
  surface-0 (layer clear) -> now accepted as no-op success (S a01xxxx). Console no longer disabled after first present.
- Status in `J1 sp` / `J1W round` lines: D=disp stage, P=presents, S=last swap diag, CK=check-in bits, T=EVFILT_TIMER pops.
- backboardd (pid 31) + SpringBoard (pid 36) alive. SpringBoard main thread blocked: `_BKSSystemAppCheckIn`
  (BackBoardServices) waits on semaphore for backboardd's `_BKCheckInXXSystemAppCanStart` (msgh_id 0x5b9939).
  Kernel logs IsWaiting (0x5b9938) from SB (CK bit1) but CanStart never sent (bit2 never set).
- backboardd flow: main -> startSystemAppCheckInServer -> ... migration queue -> resumeServer -> dispatch_after 0.1s ->
  -[BKSystemAppSentinel bootstrapSystemApp] -> lock_bootstrap (enumerates launchd jobs, finds SB, sends CanStart).
  IsWaiting handler at backboardd vmaddr 0x2ffd0 (checks bootstrapped ivar, else stores port).
- Experiment: decmpfs output patch (file off 0x2efe8 beq->nop) makes handler always "can start immediately";
  patch applies (CK bit4, bit8 = backboardd is decmpfs-compressed, size 0x6cb10) but CanStart STILL not sent ->
  IsWaiting handler never runs; check-in MIG server likely blocked (sentinel lock held / queue stuck).
- EVFILT_TIMER OK (fflags 0x1c ABS|NSEC|LEEWAY, calendar ~ uptime, pops counted). Unix stderr echo (`E<pid>:`) +
  CFLOG_FORCE_STDERR env injection added but BackBoard logs via ASL -> nothing seen.
- backboardd threads: main idle in CFRunLoop; thread1 libdispatch manager (kevent); thread2 QuartzCore render thread
  (fn_2f9fcd35) in mach_msg; others mach_msg. Next: get bt of remaining threads (watcher cap 6, photos miss them),
  find the thread holding the sentinel lock / the check-in server queue.
- Tools: probe/macho_dis.py (thumb disasm w/ selref/class/cfstring notes), probe/macho_xref.py, probe/dsc_str.py.

## Session 26 — SpringBoard past check-in; profiled/powerd chain; SB init logging
- backboardd thread dump: dispatch worker parked in MediaToolbox sync RPC (not the blocker).
- Kernel: SpringBoard's IsWaiting (msgh 0x5b9938) is delivered to backboardd (receiver pid 31, dequeued, seqno 1).
  backboardd `_BKCheckInXXSystemAppIsWaiting` (0x2f6a0) first calls `BKSecurityManager hasEntitlement:forAuditToken:`;
  that failed because csops(CS_OPS_ENTITLEMENTS_BLOB) returned EINVAL: p_csflags has no CS_VALID (no AMFI, pages
  fail validation). Fix in bsd/kern/kern_proc.c (MSM8930): serve the signed entitlements blob regardless of CS_VALID
  (SpringBoard blob 0x1a7f bytes). Backstop: decmpfs patch nops the entitlement-check beq in backboardd (file 0x2e6d4).
  Result: CanStart sent (CK1f), SpringBoard proceeds.
- SpringBoard next blocked: ManagedConfiguration -> AppSupport sync msg -> profiled; profiled blocked in IOPMLib MIG
  (msgh 0x11d30) -> powerd. SpringBoard itself also calls powerd (pm MIG 70003).
- powerd crash: IOKit fn 0x2e1a2914 (power-profile defaults) does CFDictionarySetValue on an immutable nested dict
  (CF ARM-mode helper 0x2d3e4b58 traps on flag 0x40). Fix: shared cache patched ON DISK (card.img on mmcblk0p24):
  cache file off 0x21a2914 = card.img 0x5737d114 (sector 2857960 +276): f0b5 -> 7047 (bx lr). Backup sector in
  probe/s_dev.bin. powerd now stays alive (pid ~50).
- SpringBoard now runs init: stderr shows "SpringBoard[36] Loaded logger: SBAppInstallationLog / SBIconLog /
  SBWorkspaceLog ..."; D904 = second framebuffer open. Clock is 1969 (no RTC).
- Debug infra: watcher dumps at round 18 then freezes console (2 s sleep first: periodic flush otherwise drops lines);
  dump walks user stacks after dropping task_lock (copyinmap under task_lock hung); bt only for thread 0.
  Console handed to GUI permanently after 2nd present (pe_msm8930_serrano.c).
- trap.c: user data-abort LIVELOCK (vm_fault success, CPU re-faults; seen far 0x2ef000 fsr 0x807) now logs proc+lr
  and after 64 repeats fails the fault (EXC_BAD_ACCESS) instead of spinning.
- Open: system hard-hangs ~round 13 (~150 s) then watchdog reboot; last line "J1 sp DuetLST". Find what hangs.
- Hang analysis: uniLoader WDT (0x0208A038, bite 58 s) is petted from the timer IRQ, so the fixed reset at ~210 s
  = timer IRQs stopped at ~150 s (CPU stuck with IRQs off). Not the watcher dump (reset persists with dump disabled),
  not a kernel panic (panic hook holds text 70 s), not reboot() (syscall is held with a J1 REBOOT line).
  Around then: SpringBoard presenting (P1..P4), ReportCrash fault storm (UDA total 131072, far 3dac6d80 pc 2be695a2).
  Next: find the IRQs-off spin (candidates: display swap path locks, pmap/fault path under storm). Idea: persistent
  RAM trace readable after reset, or sample pc ring via WDT bark.
- Watchdog pet window extended to 420 s (msm8930_timer.c); GUI handoff of console disabled again (pe_msm8930_serrano.c).

## Session 27 — persistent trace; KDP hang fixed; Setup app starts; warm reset at ~170 s unresolved
- Persistent kernel trace: console mirrored into TWRP's persistent_ram (ram_console) at phys 0x8fe00000
  (header sig "DBGC", start, size; data at +12, 300 KiB ring). Marker at +0x60000 ('XNUB', idx, boots, sig) lets
  consecutive XNU boots append. Timer IRQ writes "<T n x dgt_seconds>" heartbeats. Read after reset in TWRP:
  `adb shell cat /proc/last_kmsg`. (Reading /dev/mem 0x88400000 crashes TWRP: don't.)
- Hang #1 fixed: ReportCrash -> stack_snapshot syscall -> stackshot trap -> kernel prefetch abort -> straight into
  KDP "Waiting for remote debugger" forever. stack_snapshot2 now returns ENOTSUP (bsd/kern/kdebug.c).
  Kernel prefetch-abort path now prints J1 KPABT pc/lr/bt; Debugger()/panic_context print their reason.
- pmap_destroy_page returned with pmap_object locked when lookup failed: fixed.
- After fixes: SpringBoard presents (P7..P16), lockdown "no ActivationState" -> launches Setup.app (Setup Assistant).
- Unresolved: silent warm reset at 164-182 s kernel uptime in every full boot (sometimes 17 s in early launchd).
  Ruled out: WDT0 (switched off at timebase init, EN=0 verified by readback; status 4), kernel panic/KDP,
  reboot()/host_reboot/PE halt (no hook fires), CPU sleep (IOCPUSleepKernel refused+logged, never called),
  thermal (TSENS 40-49 C after reset), framebuffer present copy (skipped -> still resets), RAM top 4 MB
  (XNU memSize cut to 0x38400000, end 0xDE500000 = Linux System RAM end), eMMC DMA (driver is PIO).
  PMIC restart reason unchanged (KPD) => warm reset (PS_HOLD / secure watchdog / XPU-TZ).
  dgt_get_count made IRQ-safe and glitch-proof (delta accumulate, reject >40 s forward jumps).
  Timed reboot to recovery at 420 s (IMEM 0x2A03F65C=0x77665502, PS_HOLD 0x00800820=0) never reached in full boots.
  Next ideas: TZ/secure watchdog or XPU violation from some MMIO touched by userland-triggered kernel code
  (IOKit user clients); bisect by disabling kernel drivers (touch, display vsync, SDMMC write path) one at a time.
- uniLoader: fallback path appends WDT regs into the trace (not seen yet: writes may be lost or bootloader goes
  straight to recovery). CONFIG_XNU_MEMSIZE=0x38400000.

## Session 28 — silent warm reset hunt (panic recursion, SMPL red herring)
- Clock/voltage OK: CPU0 HFPLL L=0x22 (918 MHz), SAW PMIC data 0xa6 (~1.225 V, above Android's 1.075 V). L2 HFPLL off.
- Panel console OFF (j1_panel_console_enabled=0) => no silent reset, instead a visible kernel panic loop that FROZE the
  phone (no self-reboot; user had to power-cycle). last_kmsg showed: panic -> Debugger("double panic") -> backtrace
  print -> ___doprnt data abort (far 0xe8e6bac5, pc 0x8002cbb6, from _panic_prologue) -> new panic -> ... recursion
  until stack death; ring wrapped, first panic lost. Reverted to console ON (self-resets to TWRP again).
- Attempts to halt/reboot from panic paths (ios7j1_reboot_recovery) froze the phone: reverted. Kept only:
  debug.c nested panic >=2 sets ios7j1_seclog_frozen (stops last_kmsg writes so the first panic survives).
  ios7j1_reboot_recovery() helper still defined in msm8930_timer.c, unused.
- TWRP dmesg after resets: "PMIC Restart Reason: Triggered from SMPL". Probably uniLoader's fallback PS_HOLD power
  cycle, NOT the XNU reset (Session 27 saw KPD). Battery 100 %, 4.36 V, charging. Not proven either way.
- RAM stress (4x ios7j1_ram_scan per watcher round) off: still resets (~68 s vs 99 s), same progress. Left off.
- Per-IRQ "<P pc lr cpsr>" trailer in last_kmsg never appeared; one run reset at ~12 s. Reverted.
- Rule from user: if a change regresses progress, revert it instead of building on it.
- Current config: launchd-only exec, panel console on, pmap_destroy normal, RAM stress off, clk dump on.

## Session 28b — FIRST iOS-RENDERED FRAME (Apple logo) on the S4 mini panel
Fixes this session (all verified by last_kmsg):
- Fake "UDA: LIVELOCK" detector killed configd/locationd: same far/pc is a legit re-allocated page (each retry had a
  new object + new phys page). trap.c now counts a repeat only if the software PTE is already valid.
- Page-table pages (new L1s, new L2s, grown L1) are now cleaned to PoC + DSB (pmap.c pt_clean_range, pte_sync dsb).
- Exec block list trimmed to Setup.app + ReportCrash (SpringBoard main thread was waiting on mediaserverd).
- Shared cache on-disk patches (card.img on mmcblk0p24, backups in probe/):
  * MobileKeyBag send/wait helper 0x32bc3498 -> movs r0,#1; bx lr (keybagd never answers, no AppleKeyStore).
    sector 3009774 +152, backup probe/s_mkb.bin.
  * QuartzCore gles_new_context 0x2f9ff260 -> b.w sw_new_context (no effect found yet; EAGLServer builds GL inline
    and already falls back to Server::sw_renderer). sector 2907853 +96, backup probe/s_ca.bin.
- Device tree (uniloader blob/dtb): /chosen display-scale=2, display-rotation=0 (UIKit/MobileGestalt read it):
  fixes backboardd "No image found for apple-logo". Original probe/dtb_orig.bin.
- Env injected into every exec: CA_NO_ACCEL=1 (only affects CG IOSurfaceQueue), QUARTZCORE_LOG_FILE=/dev/console.
- ROOT CAUSE of black frames: IOS7LeoDisplay createOffscreen (IOSurface create, selector 0) only accepted a byte-exact
  captured XML dict; CoreAnimation asks with IOSurfaceBytesPerRow 0x880 (captured 0x870) -> kIOReturnUnsupported ->
  render server had no render target. Now the dict is parsed (OSUnserializeXML) and the surface created.
  Result: frames 2..4 = Apple logo (ASCII dump of the presented surface in probe/first_ios_frame_ascii.txt).
- Debug aids: frame stats + ASCII dump of presented frames (pe_msm8930_serrano.c), primary surface pre-filled grey
  (0xFF404040) at creation, SB/backboardd thread dumps at watcher rounds 10-12 (bsd_init.c).
- Still open: silent warm reset ~155-165 s (no panic text); mediaserverd/accountsd "Data/Stack execution not
  permitted" at page-aligned heap addresses (RW pages executed: likely remapped trampolines); SpringBoard UI frames.
