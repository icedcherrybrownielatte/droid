# move.md — full handoff for a new Claude Code session (new machine)

Written 2026-11-14 at the end of a long session. Everything needed to continue: what the project is, how the
machine was set up, what every file/script does, the exact state of each device, what was being done at the
moment of the move, and what was planned next. Read this whole file first, then `CLAUDE.md`,
`s4/STATUS.md`, and `s4mini/docs/HANDOFF.md`.

---------------------------------------------------------------------------------------------------------------

## 0. TL;DR

- Project: run **iOS 7.1.2** (iPhone5,2 / build 11D257, armv7s userspace) on **Samsung Android phones** using a
  fork of **xnu-j1 (XNU 2422, ARMv7)** loaded by **uniLoader** from the Android `boot` partition.
- Two target phones:
  1. **Galaxy S4 mini GT-I9190 (MSM8930, Krait)** — PAUSED by the user. Reached lock screen + home screen
     (touch, Home/Power, unlock work; very slow). Everything in `s4mini/`. Resume notes: `s4mini/docs/HANDOFF.md`.
  2. **Galaxy S4 GT-I9500 (Exynos 5410, boots on Cortex-A15)** — ACTIVE. Everything in `s4/`. XNU boots from
     eMMC, iOS userland starts (launchd, ~55–58 processes, backboardd + SpringBoard), first GUI frame (Apple logo)
     shown on the panel. **Current blocker: userland memory corruption since caches were enabled**
     (details §7, plan §8).
- At the moment of the move: the last test (run 37, "no shared-region pmap nesting") completed and did NOT fix
  the corruption. The S4 sits in TWRP with the safe bounce image in BOOT, screen blanked (§9).

---------------------------------------------------------------------------------------------------------------

## 1. Hard safety rules (user-given, never break)

- **Never write the `recovery` partition** (TWRP lives there; it is the only way back). Only write `boot`
  (and, for the S4, SYSTEM p20 which the user explicitly gave to the iOS disk image).
- **Only touch the right device by serial.** S4 mini = `077af85a`. S4 = `4d0023254b106097`. Other devices
  on the PC (a T561 tablet, an iPad, the iPhone used as camera) must never be touched by adb/flash.
- **The phone must always come back to TWRP by itself.** No code that halts/spins forever.
  On the S4: uniLoader arms the watchdog; XNU pets it from the timer IRQ; XNU timed reboot at 420 s;
  panic → reboot after 20 s. (See §6.4 for what still can go wrong.)
- **OLED burn-in (S4):** the user asked to avoid frozen/static screens. Blank TWRP's screen after each run
  (`echo 0 > /sys/class/backlight/panel/brightness; echo 1 > /sys/class/graphics/fb0/blank`). If the phone is
  stuck on a static image and not on USB, tell the user immediately (PushNotification + plain text) to hold
  **Vol Up + Home + Power** to get to TWRP.
- **Disk image writes** are sector by sector: read sector, back it up, verify original bytes, patch, write,
  re-read and compare md5. Never blind.
- **If a change makes boot progress worse, revert it** rather than stacking fixes (user rule, also in memory).
- **Double-check before flashing that the code is actually new** (user got burned by flashing an unchanged
  build). S4 mini `iter.sh` has a NO_CHANGE guard; for S4 grep that edits landed before `mk.sh`.
- Ask before outward-facing actions. The user's email is private (never put it anywhere external).
- User is often away: prefer self-recovering experiments; "no prompting me" when they say they are away.
- User preferences: terse status updates; dense photo coverage (storage not a concern); show screenshots/photos
  when something new is displayed; explain plainly when asking for physical actions.
- The session used "caveman"/ultracave terse style for chat (a user skill); files/docs are written normally.

---------------------------------------------------------------------------------------------------------------

## 2. Machine / environment setup (old machine; recreate on the new one)

Windows 11 IoT Enterprise LTSC 2024, user `User`, workspace `C:\Users\User\Desktop\Droid`.
Shells: PowerShell (primary in Claude Code), Git-bash (Bash tool), WSL Ubuntu (26.04.1 LTS, user `user`).

### 2.1 Windows side
- adb: `C:\Users\User\Desktop\Droid\tools\platform-tools-dl\platform-tools\adb.exe` (NOT on PATH).
  In Git-bash always `export MSYS_NO_PATHCONV=1` or remote paths get mangled (`/cache/x` → `C:/Program Files/Git/cache/x`).
- Python 3.14 (Windows) with `paramiko`, `pygame-ce` (iphoneview), usbmux support inside `iphoneview.py`.
- Odin (user has it) for flashing TWRP tars. TWRP for S4: `s4/twrp_dl/twrp-3.1.1-0-i9500.img.tar`
  (md5 0a53ae431e7628d01db349cc10481dea). The user later flashed **their own TWRP build with MTP disabled** so adb
  works automatically in TWRP on the S4 (stock 3.1.1 exposed MTP only).
- Samsung/Google USB drivers installed (S4 in TWRP enumerates as `USB\VID_18D1&PID_D001\4D0023254B106097`).
- adb server sometimes misses the device after a reboot: `adb kill-server; adb start-server` fixes it
  (`s4/flash_boot.sh` and `s4/run.sh` already do this every 60 s while waiting).

### 2.2 WSL side (`\\wsl.localhost\Ubuntu\home\user` = `~`)
- Toolchains: `clang` 21 (Ubuntu), `arm-linux-gnueabi-*` (gcc/binutils for uniLoader and raw asm),
  `~/cctools/bin/arm-apple-darwin11-*` (built from https://github.com/tpoechtrager/cctools-port: ld, as, strip,
  nm, otool, lipo...). `otool -tV` can't disassemble (no llvm disassembler) → use
  `arm-linux-gnueabi-objdump -D -b binary -marm -Mforce-thumb --adjust-vma=...` on raw bytes.
- iOS 7 SDK headers: `~/sdk/ios7` (SDKROOT for the XNU build).
- XNU trees:
  - `~/xnu-j1/` = clone of https://github.com/kOtusin/xnu-j1xlte (has `xnu/`, `nokextd/`, `network-port/`,
    `tools/`). `~/xnu-j1/xnu` = **S4 mini** tree (board `MSM8930_SERRANO`), many uncommitted changes (do not
    commit/reset; iter.sh fingerprints `git diff`).
  - `~/xnu-s4/` = **S4** tree: rsync copy of `~/xnu-j1/xnu` (without BUILD) + copies of `nokextd`,
    `network-port`, `tools` (the build includes `../../nokextd/...` relative paths). Not a git repo.
- uniLoader trees:
  - `~/uniloader` = clone of https://github.com/kOtusin/uniloader (S4 mini fork, HEAD 2daf020 + uncommitted).
  - `~/uniloader-s4` = `cp -a` copy for the S4 (board `samsung-ja3g`).
- Reference sources: `~/ref/k5410` (Samsung/LineageOS exynos5410 kernel 3.4, cm-14.1 branch: mct.c, pmu,
  sec_log, dw_mmc, persistent_ram...), `~/ref/xnu-i9100` (GT-I9100 XNU port by kernel86-64, touch/SpringBoard ideas).
- Build logs: S4 mini `~/xnu-build-last.log`; S4 `~/xnu-s4-build.log`.
- XNU build command (S4) is in `s4/stage3/build.sh`:
  `cd ~/xnu-s4/xnu && export PATH=$HOME/cctools/bin:$PATH MIGCC=$HOME/cctools/bin/cc HOST_CC=$HOME/cctools/bin/hostcc && . SETUP/setup.sh && make TARGET_CONFIGS="release arm EXYNOS5410_JA3G" MAKEJOBS=-j8 SDKROOT=$HOME/sdk/ios7`
  "unknown option: --target=..." errors in the `*.symbolset` step are normal (also on S4 mini); the kernel is
  `BUILD/obj/RELEASE_ARM_EXYNOS5410_JA3G/mach_kernel`. Failure = `": error"` or `Undefined symbols` in the log.
- WSL quirks: every `wsl` call prints "wsl: Failed to detect nested virtualization support..." (harmless; pipe
  through `tr -d '\0' | grep -v nested`). Running `wsl bash -c '... $VAR ...'` from Git-bash sometimes loses
  `$VAR`; reliable pattern = write a script file and run `MSYS_NO_PATHCONV=1 wsl bash /mnt/c/.../script.sh`
  or `wsl python3 /mnt/c/.../script.py`.
- Editing gotchas: XNU sources may be CRLF; use Python scripts with `open(p, newline='')` and exact
  `assert s.count(old) == 1` replacements. Heredoc + `'\\n'` inside Python inside bash repeatedly produced real
  newlines inside C strings and broke builds — use `chr(92) + 'n'` in Python or the Edit tool.

### 2.3 Camera rig (`iphonecontrol/`)
- A jailbroken iPhone photographs the phone screen. The user starts `python iphoneview.py --usb` (VNC viewer +
  local HTTP API, config in `C:\Users\User\.iphoneview.json`, API doc `iphonecontrol/IPHONE_API.md`).
- `snap.py --out photos`: SSH (root/alpine over usbmux) → `open com.apple.camera` → taps shutter via API →
  pulls the new JPG into `iphonecontrol/photos/`. On the current iPhone `open` returns exit code 3 even when it
  works → use `iphonecontrol/snaploop.py <count> <interval_s>` (writes `_snap_noopen.py` without that check).
- `cleandcim.py`: deletes `/var/mobile/Media/DCIM/*` on the camera iPhone (run before photo phases).
- The user also takes manual camera photos; they can be pulled with paramiko SFTP from `/var/mobile/Media/DCIM`
  (see how it was done ad hoc: list dirs, sort by mtime, `sftp.get`).
- The user explicitly said: **use iphoneview to check the screen** instead of asking them.

---------------------------------------------------------------------------------------------------------------

## 3. Workspace layout (`C:\Users\User\Desktop\Droid`)

- `CLAUDE.md` — project guide (S4 mini oriented; safety rules; iteration loop). Keep it updated.
- `move.md` — this file.
- `iPhone5,2_7.1.2_11D257_Restore.ipsw` + `ipsw_x/` — extracted IPSW. Rootfs tree
  `ipsw_x/rootfs/Sochi11D257.N42OS/`, shared cache
  `.../System/Library/Caches/com.apple.dyld/dyld_shared_cache_armv7s`, disk image `ipsw_x/card.img`
  (1745979392 bytes, md5 cc4bf9b706eb6199563fd739b65880fc: MBR + FAT32 holding `IOS7/ROOTFS.HFS`).
  NOTE: the local card.img does NOT contain the on-disk patches (they are applied on the phones only).
  card.img offset = shared-cache file offset + 0x551da800.
- `tools/` — adb/platform-tools.
- `iphonecontrol/` — camera rig (§2.3).
- `xnu-j1xlte/` — base XNU reference copy (Windows side).
- `s4mini/` — everything S4 mini (probe scripts, docs, PROGRESS.md, backups, patches, recon, uniloader copy).
- `s4/` — everything S4 (§5).

Claude memory dir (old machine): `C:\Users\User\.claude\projects\C--Users-User-Desktop-Droid\memory\` with
`MEMORY.md` index + `feedback-more-photos.md`, `feedback-revert-regressions.md`, `feedback-verify-new-code.md`,
`project-ports-status.md`. Recreate equivalent memories on the new machine (contents summarized in §1/§4/§5).

---------------------------------------------------------------------------------------------------------------

## 4. S4 mini (GT-I9190) — paused

- Device serial `077af85a`; adb in TWRP; BOOT flashed by `s4mini/probe/iter.sh` (build XNU → strip → LZ4 →
  uniLoader → `boot_recfb.img` → flash boot → verify → reboot → photos → wait for TWRP).
  `cd s4mini/probe; MSYS_NO_PATHCONV=1 ANDROID_SERIAL=077af85a timeout 1700 bash iter.sh 40 60 4`
  (`NOSNAP=1` = no photos, `FORCE=1` = flash even if sources unchanged). Log: `adb shell cat /proc/last_kmsg`.
- iOS disk image on `mmcblk0p24`. RAM log: TWRP ram_console at 0x8fe00000 (RS-ECC header).
- State: lock screen + home screen reached; touch (mXT336S, bit-banged I2C), Home/Power, unlock, colors OK;
  UI very slow. Run 82 (half resolution 270x480 scale 1 + CPU probe) is on the phone, results never read.
- Resume point and next steps: top of `s4mini/docs/HANDOFF.md`; history `s4mini/PROGRESS.md`;
  patches `s4mini/docs/PATCHES.md`; debugging `s4mini/docs/DEBUGGING.md`.
- IMPORTANT lesson from the S4 work that probably also applies to the S4 mini: see §7 (the S4 mini runs with
  write-through memory, which Krait caches; several pmap bugs found on the S4 also exist in the S4 mini tree:
  stale `user_pmap` after `pmap_destroy`, no DSB before TLBI, NOCACHE aliases. Consider porting those fixes
  back once the S4 is stable).

---------------------------------------------------------------------------------------------------------------

## 5. Galaxy S4 GT-I9500 (Exynos 5410) — active port

### 5.1 Device facts
- adb serial `4d0023254b106097` (ro.product `ja3gxx`), bootloader `I9500XXUHPJ3`, warranty bit 1.
- Android installed: LineageOS 16 (Android 9) — its SYSTEM partition is now overwritten by card.img (user chose
  SYSTEM p20). Backup: `s4/backup/SYSTEM.img.gz` (558 MB gz). TWRP still works; Android won't boot until SYSTEM
  is restored (`gunzip -c SYSTEM.img.gz | adb exec-in dd of=/dev/block/mmcblk0p20`, or flash ROM).
- Partitions (`/dev/block/platform/dw_mmc.0/by-name/`): BOOT=mmcblk0p9 (8 MiB), RECOVERY=mmcblk0p10 (NEVER
  write), SYSTEM=p20 (start LBA 6348800, 5660672 sectors), CACHE=p19, USERDATA=p21, EFS=p3, PARAM=p8, ...
  Full list `s4/recon/byname.txt`, `partitions.txt`. Backups of BOOT, RECOVERY (TWRP), EFS, PARAM, m9kefs1-3,
  BOTA0/1, CARRIER in `s4/backup/` (+ MD5SUMS.txt). `s4/backup/BOOT.img` = original LineageOS boot.
- Hardware (from `s4/recon/*.txt` + Samsung kernel `~/ref/k5410`):
  - Boot CPU: **Cortex-A15 r2p3** (MIDR 412fc0f3, MPIDR 80000000), SVC mode, MMU/caches off at entry.
    (Linux recon showed A7 because Linux uses the big.LITTLE switcher; S-Boot hands over on the A15.)
  - RAM 0x40000000–0xBFCFFFFF. TrustZone present (secure firmware; SMC calls in Linux for L2/power).
  - PMU 0x10040000: SWRESET +0x400, RST_STAT +0x404 (bit20 = SYS_WDTRESET), AUTOMATIC_WDT_RESET_DISABLE +0x408,
    MASK_WDT_RESET_REQUEST +0x40C, INFORM2 +0x808, INFORM3 +0x80C.
  - Reboot to TWRP (Samsung sec-reboot.c): INFORM2=0x12345678, INFORM3=0x12345674 (prefix|recovery), SWRESET=1.
  - Watchdog 0x101D0000: WTCON +0, WTDAT +4, WTCNT +8. WTCON 0xFF39 = prescale 255, enable, /128, reset enable.
    0xFFFF count ≈ 20–30 s. **After a watchdog reset S-Boot IGNORES INFORM3 and boots BOOT again** (test B →
    endless logo loop) → every stage must check RST_STAT bit20 / a DRAM marker first and SWRESET to recovery.
  - MCT (timer) 0x101C0000: global counter G_CNT_L/U 0x100/0x104 (24 MHz; S-Boot leaves it stopped →
    start with G_TCON bit8), local timer L0 base +0x300 (TCNTB +0, ICNTB +8 (bit31 update), TCON +0x20
    (bit0 start, bit1 int start, bit2 interval), INT_CSTAT +0x30, INT_ENB +0x34, WSTAT +0x40). L0 IRQ = SPI 120
    = INTID 152. L0 measured 12 MHz with TCNTB=1.
  - GIC: dist 0x10481000, cpu 0x10482000.
  - Display: S-Boot leaves **FIMD1 (0x14400000) window 2** scanning out **0x67000000**, 1080x1920,
    line 4320 bytes, ARGB8888 (bytes B,G,R,A), WINCON2=0x8035. MIPI-DSIM 0x14500000. Panel SMD AMS499QP01 (OLED).
  - eMMC: Synopsys DesignWare MMC `dw_mmc.0` at 0x12200000, VERID 0x241a (data FIFO at +0x200), HCON
    0x00e42541 → **64-bit FIFO**, card RCA 1, left in transfer state by S-Boot.
  - UART2 0x12C20000 (console ttySAC2, not used). Touch: Synaptics RMI4 on i2c-0 (0x12C60000) addr 0x20
    (not ported). Keys: gpio-keys; touchkeys sec_touchkey i2c-gpio8; PMIC sec-pmic i2c-5 0x66; MAX77803.
  - TWRP's `/proc/last_kmsg` comes from Android **persistent_ram (ram_console), 2 MB zone at 0x60000000**:
    header {u32 "DBGC" 0x43474244, u32 start, u32 size} + data; header protected by Reed-Solomon parity in the
    zone's last 16 bytes (symsize 8, poly 0x11d, fcr 0, prim 1, 16 roots). Without valid parity TWRP "corrects"
    start/size to garbage. (sec_log at 0x46000000 is NOT what TWRP shows.)
  - Boot image: header kernel 0x10008000, ramdisk 0x11000000, page 2048, zImage head required (nop sled +
    magic 0x016f2818 at 0x24). S-Boot loads our image somewhere else and we relocate (see uniLoader).
- Free RAM rules for our stages: keep clear 0x46000000 (sec_log), 0x5FF00000 (watchdog marker),
  0x60000000–0x601FFFFF (ram_console), 0x67000000–0x677E9000 (framebuffer). uniLoader TEXT_BASE 0x50008000.
  XNU RAM = 0x68000000 + 0x38000000 (to 0xA0000000).

### 5.2 Files in `s4/`
- `STATUS.md` — running status notes (detailed, chronological).
- `flash_boot.sh <img> [wait]` — pins serial, refuses unless BOOT → mmcblk0p9, pushes, zero+dd, md5-verifies,
  `adb reboot`, waits for return, blanks screen. `NOREBOOT=1` = flash only.
- `run.sh <N>` — flash `stage3/boot_xnu.img` (NOREBOOT), reboot, wait (retry once if back in < 100 s =
  uniLoader marker bounce), blank screen, save `stage3/lastk<N>.txt` (= /proc/last_kmsg).
- `write_card.sh` — backs up SYSTEM p20 and writes `ipsw_x/card.img` to it with md5 verify (done once).
- `tools/diskpatch.py [--dry]` — applies the S4 mini's 20 on-disk iOS patches to p20 sector by sector with
  backups in `s4/disk_backup/` (done, all verified): powerd IOKit fn bx lr, MobileKeyBag send/wait → ok,
  QuartzCore gles→sw context, 3×TCC, BBDataProviderConnection skip UIApp probe, PSSetupAssistantNeedsToRun NO,
  MPAVRoutingController volumeControlIsAvailable NO, AXS AssistiveTouch(UI)Enabled YES, Setup.app→Setux.app
  (9 HFS catalog sectors). fstab was already OK in card.img.
- `recon/` — `dump.sh` + Android recon dumps (cpuinfo, iomem, interrupts, dmesg, config, partitions...).
- `backup/` — partition backups (§5.1). `disk_backup/` — original sectors of disk patches.
- `stage1/` — raw-asm tests: `bounce.S` (reboot straight to TWRP; `boot_bounce.img` = SAFE image to leave in
  BOOT), `wdtest.S` (test B: WDT → logo loop, never run again), `wdtest2.S` (test C: RST_STAT/marker check →
  works), `pack_boot.py kernel out.img` (reuses `../backup/BOOT.img` header + ramdisk, ≤ 8 MiB).
- `stage2/` — uniLoader self-test image (prints board state, reboots). Proved fb + log.
- `stage3/` — XNU stage (sources of truth for the S4 kernel changes):
  - `build.sh` — XNU build in WSL (prints BUILD_OK / BUILD_FAILED).
  - `mk.sh` — build XNU, strip, LZ4 (`mklz4.py`), copy to `~/uniloader-s4/blob/Image`, copy `dtb_ja3g.bin` to
    `blob/dtb`, `make ja3g_xnu_defconfig`, build uniLoader, pack `boot_xnu.img`.
  - `ja3g_xnu_defconfig` — uniLoader config (EMBED_XNU, LZ4, PHYS_BASE 0x68000000, MEMSIZE 0x38000000,
    PAYLOAD_ENTRY 0x68001000, FB 0x67000000 1080x1920, TEXT_BASE 0x50008000, FDT_BUF_SIZE 8192).
  - `dtb_ja3g.bin` — Apple device tree (copy of S4 mini `dtb_scale2.bin`, display-scale=2).
  - `integrate.py` — **idempotent** script that applies ALL tree edits to `~/xnu-s4/xnu` (board wiring, guards,
    S4 hardware hooks, pmap/cache fixes, debug prints). Run: `wsl python3 /mnt/c/.../s4/stage3/integrate.py`.
    Each step prints "integrate ... ok" or "already ...". Source of truth for what differs from the S4 mini tree.
  - `mkpe.py` — generates `pexpert/arm/pe_exynos5410_ja3g.c` from the S4 mini PE (`pe_msm8930_serrano.c`,
    which integrate.py later guards out; run mkpe BEFORE integrate on a fresh tree).
  - `exynos5410_timer.c` — GIC + MCT timer + WDT pet + timed reboot + panic reboot + stats + cache self-test +
    thread dump hook (copied into the tree by integrate.py).
  - `ja3g_sdmmc.inc` — S4 eMMC block driver (class kept as `IOS7M8930SDMMC` because IOS7LeoHFSFile matches by
    that name), included by integrate.py into `IOS7M8930SDMMC.cpp`.
  - `abtest.py wt|wb` — switches pmap-managed pages between write-through and write-back (A/B test).
  - `patch_fifo64.py`, `patch_late.py` — one-off patch scripts (already applied).
  - `sym.sh <hex>...` — nearest kernel symbol (WSL).
  - `lastk01..36.txt` — logs of every S4 XNU run; `run3x.log` — run.sh outputs.
- `twrp_dl/` — TWRP tar for Odin.

### 5.3 uniLoader for the S4 (`~/uniloader-s4`)
- `board/samsung/board-ja3g.c`: simplefb from FIMD1 registers (finds the enabled window, start/stride/size);
  console mirrored into the TWRP ram_console (RS header ECC); `ja3g_reboot_recovery()`; WDT helpers;
  `ja3g_report()`.
- `arch/arm/start.S` (CONFIG_SAMSUNG_JA3G): very first code = safety net: INFORM2/3=recovery; if RST_STAT
  bit20 or DRAM marker 0x57D7E5A1 at 0x5FF00000 → clear marker + SWRESET (to TWRP); else set marker and arm WDT
  (0xFF39, 0xFFFF). Fix made: the relocation engine published `delta_value` before copying `.data` (overwritten
  to 0) → now stored after the copy (S-Boot loads us away from TEXT_BASE on the S4).
- `arch/arm/load-kernel.c`: S4 mini fb clear at 0x88100000 guarded out for JA3G.
- Kconfig: `EXYNOS_5410`, `SAMSUNG_JA3G`, `JA3G_SELFTEST`; `configs/ja3g_selftest_defconfig`, `ja3g_xnu_defconfig`.
- Known: S-Boot loads at most the kernel payload as given; image < 4 MiB is safest (FDT buffer shrunk).
- Marker side effect: after a forced key reset or a WDT reset, the NEXT boot bounces straight to TWRP once
  (~60 s round trip). `run.sh` retries automatically. XNU clears the marker (with DCCIMVAC) before its own
  reboot.

### 5.4 XNU for the S4 (`~/xnu-s4/xnu`, board `EXYNOS5410_JA3G`)
Design: JA3G builds also define `BOARD_CONFIG_MSM8930_SERRANO=1` (MakeInc.def) so every iOS-userspace hack of
the S4 mini applies; S4 mini hardware code is excluded with `&& !defined(BOARD_CONFIG_EXYNOS5410_JA3G)`.
Everything below is applied by `integrate.py` (+ `mkpe.py`):
- `makedefs/MakeInc.def`: machine config + ARCH_FLAGS + extra define.
- `pexpert/conf/files.arm`: `pe_exynos5410_ja3g.c`, `exynos5410_timer.c`.
- PE (`pe_exynos5410_ja3g.c`): 540x960 BGRA shadow console flushed 2x2 to the panel (only dirty text lines,
  ≤2 per tick — full flushes in the IRQ starved threads); `ios7j1_display_present` doubles 540x960 GUI frames
  to 1080x1920; ram_console log at 0x60000000 (ring 1 MB, continues after uniLoader's text);
  `ios7m8930_mark(n)` logs "[n]" markers (<1000 only); hex debug rows only during panic (they made each IRQ
  17 ms late); touch/buttons stubs (not ported); `j1_video_ok` expects physBase 0x68000000/memSize 0x38000000.
- Timer: see §5.1 MCT; 10 ms max tick; one IRQ per handler entry; WDT pet unless `panicstr`; timed reboot at
  420 s (`J5410_RUN_SECONDS`), prints stats + IOKit job counters + 16 PC/LR samples + full thread dump.
- `locore.s`/`arm_vm_init.c`: S4 mini identity maps/white bars excluded.
- eMMC driver (`ja3g_sdmmc.inc`): PIO, CTRL IDMAC/INT off, CMD13 RCA probe, CMD17/CMD18 (auto-stop), 64-bit
  FIFO reads, window = SYSTEM p20 (CARD_LBA 6348800, CARD_SECTORS 3410116), read-only.
- Display: `IOS7LeoDisplay.cpp` leoWidth 540, leoHeight 960, leoRow 2176 (scale 2 DT).
- Panic: Debugger() → `ios7j1_reboot_recovery(20)`; the S4 mini's 3e9-iteration "hold panic text + pet WDT"
  loop in `debug.c` is disabled on JA3G (it ran for many minutes on the S4 → stuck static screen).
- Memory/caching fixes (A15-specific, §7): linear map + pmap normal memory WB-WA (`J5410_NORMAL_MEM`),
  TTBR walk attributes 0x48 for kernel (locore, set_mmu_ttb) and user (`arm_context_switch` in cpufunc-v7.s),
  DSB before every TLBI, `pmap_set_cache_attributes` keeps managed RAM WB, `pmap_destroy` clears stale
  `cpu->user_pmap` and loads the kernel TTB before freeing, CLREX in `restore_kernel_context`.
- Debug additions: startMatching trace ("SM ..."), IOKit job stats, thread dump, user backtrace + stack strings
  on reboot() requests ("J1 REBOOT ..."), `mach_port_deallocate` failure trace ("J5410 port_dealloc"),
  no ASLR for PID 1 (launchd), cache self-test at boot ("J5410 cachetest"), CPU loop timing.
- LAST EDIT (applied, NOT tested): no shared-region pmap nesting (`vm_shared_region.c`, JA3G).

### 5.5 How to iterate on the S4
1. Phone in TWRP with adb (`adb devices` shows `4d0023254b106097 recovery`).
2. Edit `s4/stage3/*` (or add a step to `integrate.py`), then
   `MSYS_NO_PATHCONV=1 wsl python3 /mnt/c/Users/User/Desktop/Droid/s4/stage3/integrate.py`
   (and `mkpe.py` first if the PE generator changed — mkpe regenerates the PE file from the S4 mini PE).
3. `cd s4/stage3 && timeout 900 bash mk.sh` → `boot_xnu.img` (check BUILD_OK; on failure
   `grep ": error" ~/xnu-s4-build.log`).
4. `cd s4 && timeout 1300 bash run.sh <N>` (~8 min: 420 s run + TWRP boot).
   Meanwhile `cd iphonecontrol && python snaploop.py 14 25` for photos (user wants photos; needs iphoneview).
5. Read `s4/stage3/lastk<N>.txt` (strip markers with `sed 's/\[[0-9]*\]//g'`). Useful greps:
   `J1 exec|J1 X |J1 EXC|J1 ABRT|J1 REBOOT|J1 present|J1W round|PANIC|J5410 TH|cachetest`.
   - `J1W round N nprocs=.. bb=31 sb=36 P<presents> S.. CK<checkin bits> T..` — watcher every ~10 s
     (40 rounds). CK156/223 = backboardd/SpringBoard check-in patches applied (S4 mini lock screen ≈ CK223 + P>1).
   - `J1Q ... opened=1` = backboardd opened the HID queue; `J1 fb open` = IOMobileFramebuffer opened.
   - `J1 EXC pid name e1 far.. kr..` + `pc/lr/bt ... sl<shared cache slide>`; shared cache symbols:
     `python s4mini/probe/dsc_lookup.py <cache> <unslid hex>` and `python s4mini/probe/tools/locsyms.py x <hex>`
     (unslid = addr − slide).
   - Kernel symbols: `wsl bash /mnt/c/.../s4/stage3/sym.sh <hex>`.
6. If not back in ~8 min: photo the screen; if static/stuck, ask the user for Vol Up+Home+Power (burn-in).
7. Leave the phone safe when stopping: `NOREBOOT=1 bash s4/flash_boot.sh s4/stage1/boot_bounce.img`
   (normal boot → TWRP) and blank the screen.

---------------------------------------------------------------------------------------------------------------

## 6. Chronology of the S4 work (what was learned, in order)

1. Recon from LineageOS 16 (root adb) → `s4/recon`. Backups.
2. Test A (`bounce.S`): S-Boot runs raw code; INFORM3+SWRESET → TWRP works.
3. Test B (WDT then spin): WDT resets, but S-Boot ignores INFORM3 after WDT reset → logo loop; user had to
   key-reset. Test C (RST_STAT/marker check): works (64 s round trip).
4. TWRP MTP-only → user flashed own TWRP with MTP disabled.
5. uniLoader self-test: garbled screen (wrong stride) → read FIMD1 window regs → correct; log via ram_console.
6. XNU: boots to IOKit; panicked "J5410 IRQ drain budget exceeded" and the panic re-entered IRQs petting the
   WDT → static screen (user rescued). Fixed handler; panic → reboot 20 s.
7. "decompression FAILED": uniLoader delta bug (fixed) + image size.
8. eMMC: zeros read → 64-bit FIFO; then MBR/CMD18 OK.
9. IOKit matching never ran → livelock: IRQ-exit hex-row drawing (17 ms per IRQ) + full console flushes in
   IRQ → fixed (dirty-line flush, hex rows only on panic).
10. Root mounted, launchd + userspace up (with SYSTEM p20 card.img + disk patches).
11. Everything very slow → **A15 treats Write-Through as Non-cacheable**: kernel/user ran uncached (20M-iter
    loop 11 s vs 0.15 s). Switched to WB-WA + cacheable table walks → 75x faster, 100 Hz ticks.
12. With WB: memory corruption appeared (malloc checksum aborts, launchd bus error, kernel kalloc zone element
    zeroed panic once). Fixes tried (all kept): DSB before TLBI, WB user TTBR walks, managed RAM always WB,
    stale user_pmap fix, CLREX on kernel return, panic-hold removal. Result: fewer random crashes, GUI frames
    appear (Apple logo seen by the user), CK156/223 reached, but still: deterministic-looking crashes in
    malloc via objc autorelease (function pointer containing ASCII "appl" → 0x6c707060), xpcd/vendor_device_
    arbitrator die; launchd sometimes hits `assumes` failure (mach_port_deallocate(mach_host_self()) at
    launchd 0xd9ae) whose logging then calls NULL in libsystem_platform → SIGBUS → launchd reboot() (held by
    the kernel debug hook, everything blocks on launchd's full queue → no lock screen).
    Cache self-test (4 MB) passes → not a raw cache hardware fault.

### 6.4 Known safety gaps
- If XNU hangs with interrupts enabled but the timer still firing, the WDT keeps being petted; only the 420 s
  timed reboot saves it (it runs in the IRQ, so it works unless IRQs stop — then the WDT bites).
- A panic with interrupts off → Debugger → 20 s → SWRESET. A panic that loops before Debugger (like the old
  S4 mini hold) is the dangerous case; watch photos.
- After key resets the next boot bounces once (marker) — expected.

---------------------------------------------------------------------------------------------------------------

## 7. Current blocker analysis (S4): memory corruption with write-back caching

Facts:
- With all memory effectively uncached (old WT attributes) userland ran without corruption for 420 s
  (runs 21/22: ~57 procs; one launchd reboot in run 22 without a visible crash).
- With WB caching: corruption in user heaps and once in kernel kalloc (freed element zeroed).
- Bad pointers contain ASCII from other data ("appl"), i.e. a page holds another owner's data → suspect a
  physical page reused while still mapped somewhere, or wrong data from a page-in, or stale translations.
- Exclusive monitor, VFP lazy switch, IT bits on return, TPIDRURO, copypv/bcopy_phys/linear map, idle loop,
  DCISW routines: checked and believed OK.
- Remaining suspects (in order):
  1. ~~Shared-region pmap nesting~~ — tested in run 37: no improvement (see §9). Ruled out.
  2. pv-list/pmap_disconnect gaps (the S4 mini "wired_count underflow clamped instead of panic" hack in
     `pmap_remove_range` hides a real accounting bug — pages may be freed while still mapped). Try making it
     panic/log on JA3G to see if it triggers.
  3. eMMC data integrity under fast CPU: verify page-in data (e.g., checksum a known file region through the
     driver vs card.img) — 64-bit FIFO read uses `*(volatile UInt64*)` (check it compiles to a single ldrd that
     the bus treats as one 64-bit access).
  4. Speculative table walks on freed L2 tables (walk-cache) — after freeing L2 tables, TLBIALL.
  5. A15 L2/ACTLR config left by S-Boot/TrustZone (can't change from NS; cachetest passed though).
  6. Worst case fallback: run user pages WT (uncached, correct but slow) — `abtest.py wt` — to keep moving
     on touch/display while the bug is hunted.
- Separately: launchd's `assumes()` logging crash (NULL call in libsystem_platform `_simple_*` /
  `_os_assumes_log_ctx` path) and the failing `mach_port_deallocate(mach_task_self(), mach_host_self())`
  (trace "J5410 port_dealloc" added, not yet captured). Possible hack if needed: make that failure impossible
  or disable the reboot-hold so launchd's reboot() just returns.

## 8. Plan after the blocker
1. Stable userland → lock screen on the S4 (verify with iphoneview photos).
2. Touch: Synaptics RMI4 on i2c-0 (HS? 0x12C60000 is s3c2440-i2c.0 "standard" controller; Linux uses
   `synaptics_rmi4_i2c 0-0020`), power via regulators (check `recon/regulators.txt`); IRQ GPIO from
   `recon/gpio.txt`. Feed packets through the existing IOS7LeoHIDTouch path (same as S4 mini, see
   `ios7j1_mxt_poll` contract: return x,y in 480x800 space + down).
3. Buttons: gpio-keys (Home/Power/Vol) → `ios7j1_buttons_read`.
4. Performance: second core / SMP later; half resolution already (540x960 GUI).
5. Remove debug load (markers, SM trace, dumps, no-ASLR) when stable.
6. Back-port pmap fixes to the S4 mini tree; resume S4 mini per its HANDOFF.

---------------------------------------------------------------------------------------------------------------

## 9. Exact state at the moment of the move

- Run 37 (no shared-region nesting, md5 33ce2be587c237c25071707a43a1059b) DID complete before the stop:
  log `s4/stage3/lastk37.txt`. Result: corruption NOT fixed by disabling nesting — EXCs in
  vendor_device_arbitrator (far 0xf4008), ptp_device_arbitrator, MobileStorageMounter, launchd far0 →
  launchd REBOOT; 56 procs, P0, CK156. "J5410 port_dealloc" not printed. So suspect #1 in §7 is ruled out
  (the nonest edit is still in the tree — consider reverting it via integrate.py removal + manual undo).
- The S4 is in TWRP (adb OK), screen blanked, and BOOT holds the SAFE `s4/stage1/boot_bounce.img`
  (md5 cbed25792ca6f2ec0d19be076b83c23c). Next XNU run: `bash s4/run.sh 38` flashes `stage3/boot_xnu.img`.
- `~/xnu-s4/xnu` contains the nonest edit (vm_shared_region.c, JA3G) and the port_dealloc trace.
- S4 mini: unplugged, BOOT holds run 82 image, TWRP intact.
- Camera iPhone: iphoneview running when the user is present; DCIM cleaned periodically.

## 10. Moving to a new machine — checklist
1. Copy the whole `C:\Users\User\Desktop\Droid` folder (incl. IPSW, ipsw_x, s4, s4mini, tools, iphonecontrol).
2. Copy WSL home items: `~/xnu-j1`, `~/xnu-s4`, `~/uniloader`, `~/uniloader-s4`, `~/cctools` (or rebuild
   cctools-port), `~/sdk/ios7`, `~/ref` (or re-clone k5410 / xnu-i9100). Easiest: `wsl --export Ubuntu x.tar`
   on the old machine and `wsl --import` on the new one.
3. Install: Git for Windows (bash), Python 3 + paramiko + pygame-ce, adb (platform-tools in `tools/`),
   Samsung + Google USB drivers, WSL Ubuntu with clang, arm-linux-gnueabi toolchain, python3, make, rsync.
4. Recreate Claude memory files (§1/§3) and keep `CLAUDE.md`.
5. If paths change (user name/drive), fix hardcoded paths: `s4/stage3/mk.sh` (W=/mnt/c/Users/User/Desktop/Droid/...),
   `integrate.py` (S path), `s4/tools/diskpatch.py` (relative), `iphonecontrol/*`, `s4mini/probe/*.sh`,
   `s4mini/probe/tools/*.py` (absolute Windows paths), `CLAUDE.md`.
