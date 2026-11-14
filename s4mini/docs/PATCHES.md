# Patch inventory (state at 2026-11-13)

## On-device disk patches (phone `mmcblk0p24` = `ipsw_x/card.img`)

card.img offset = shared-cache file offset + 0x551da800 (mapping 0 is contiguous; verified several times).
Each patch was read-verified before and after writing; original sectors backed up in `probe/`.
Note: the local `ipsw_x/card.img` is NOT patched; only the phone copy is.

| What | Cache addr | Change | Sector(s) / backup |
|---|---|---|---|
| powerd crash: IOKit fn 0x2e1a2914 (CFDictionarySetValue on immutable dict) | 0x2e1a2914 | `bx lr` | 2857960 / `probe/s_dev.bin` |
| MobileKeyBag send/wait helper (keybagd never answers, no AppleKeyStore) | 0x32bc3498 | `movs r0,#1; bx lr` (01207047) | 3009774 / `probe/s_mkb.bin` |
| QuartzCore `gles_new_context` → `b.w sw_new_context` | 0x2f9ff260 | fff7ccbf | 2907853 / `probe/s_ca.bin` |
| `TCCAccessPreflight` → granted | 0x34a27318 | 00207047 | 3072013 / `probe/s_tcc_TCCAccessPreflight.bin` |
| `TCCAccessRequest` → true | 0x34a26bd8 | 01207047 | 3072009 / `probe/s_tcc_TCCAccessRequest.bin` |
| `TCCAccessCheckAuditToken` → true | 0x34a2758c | 01207047 | 3072014 / `probe/s_tcc_TCCAccessCheckAuditToken.bin` |
| `-[BBDataProviderConnection initWithServiceName:onQueue:]` skip "is client a UIApplication" probe (BKSApplicationStateMonitor `applicationInfoForPID:` + `dispatch_semaphore_wait` FOREVER deadlocked SpringBoard's main thread in `_startBulletinBoardServer`). Gave the first lock screen (run 50). | 0x310f72be | `beq.w`→`b.w 0x310f73f2` (00f09880→00f098b8) | 2954893+190 / `probe/s_bb_BBDPC_skipUIAppProbe.bin` (`probe/tools/bbpatch.py`) |
| `/Applications/Setup.app` renamed `Setux.app` (HFS catalog key + thread records, 9 copies) | — | name char 'p'→'x' | `probe/setup_rename_backup/sec_*.bin` |
| `/etc/fstab` (decmpfs) `/dev/disk1 / hfs rw 0 0` | — | earlier session | see PROGRESS.md |

## Kernel (WSL `~/xnu-j1/xnu`, board MSM8930_SERRANO) — notable changes

Functional fixes (keep):
- `osfmk/arm/traps_lo.s`: `icache_inv_trap` → `arm_icache_sync_all`, `dcache_inv_trap` →
  `arm_dcache_wbinv_all` (was invalidate-only DCISW; GT-I9100 CACHE16 fix).
- `osfmk/arm/pmap.c`: `pte_sync` adds DSB; `pt_clean_range` cleans new L1/L2 table pages and grown L1.
- `iokit/.../IOS7LeoDisplay.cpp` `createOffscreen`: parses the IOSurface XML properties dict
  (OSUnserializeXML) instead of requiring one exact captured blob (CA asked with BytesPerRow 0x880).
  This is what made iOS render.
- `osfmk/arm/trap.c`: user-abort "LIVELOCK" detector only counts repeats when the PTE is already valid
  (it was killing configd/locationd on legitimate re-faults).
- `bsd/kern/kern_exec.c`: env injected into every exec: `CFLOG_FORCE_STDERR=1`, `CA_NO_ACCEL=1`,
  `QUARTZCORE_LOG_FILE=/dev/console`. Exec block list `j1_blocked[]`: `/ReportCrash`, `/tccd`,
  `/mDNSResponder`, `/accountsd` (Setup.app removed after rename). "blocked" message limited to 6.
- `bsd/kern/decmpfs.c` (after decmpfs fetch, matched by uncompressed size + 8-byte signature, sets
  `ios7j1_checkin_seen` bits; watcher prints them as `CK`):
  - backboardd (0x6cb10) file 0x2efe8 beq→nop (CK|4) and 0x2e6d0 beq→nop (CK|16): system-app check-in hacks.
  - SpringBoard (0x418480) file 0xc4e54+2 `bne`→`b 0xc5ebe` (CK|64, prints `J1 PATCH SpringBoard nobuddy`):
    VA 0xc5e20 decides InBuddyMode (setupApplication com.apple.purplebuddy still found in Setux.app +
    activation check). In buddy mode SpringBoard shows its own Apple logo (`PUIProgressWindow`, "Buddy Fake
    Logo") and launches Setup, which never draws: that was the "logo forever" state.
  - backboardd file 0xa088 → `bx lr` (no boot logo window): disabled (`if (0 && ...)`), the logo was SpringBoard's.
- `osfmk/arm/pmap.c` `pmap_remove_range`: wired_count underflow clamped instead of panic (per-page wiring bug).
- `pexpert/arm/pe_msm8930_serrano.c`: `J1_SECLOG_SIZE` 0x9800 (TWRP last_kmsg window); `ios7j1_touch_probe()`
  read-only GSBI3/QUP/TLMM snapshot. `bsd/kern/bsd_init.c` watcher runs 40 rounds, probes at rounds 1/39.
- `iokit/Kernel/IOUserClient.cpp` `j1_uc_log`: off (`if (1 || ...)`); alternating selectors flooded the ring.
- `bsd/kern/kern_exit.c`: `J1 X` exit line skipped for launchd exit 0x200 (respawn spam).
- `osfmk/kern/debug.c`: nested panic ≥2 sets `ios7j1_seclog_frozen` (keeps first panic in last_kmsg).
- `osfmk/arm/trap.c` fatal handler: prints FATAL + r0–r12, then freezes the log.
- `pexpert/arm/pe_msm8930_serrano.c`: ring-buffer log wraps to offset 16 so the "XNUTRACE<sig>" tag
  survives; `ios7j1_seclog_flush()` is a no-op stub.

Debug state (revert/adjust as needed):
- `pe_msm8930_serrano.c`: console flush keeps running after the first GUI frame but only the top 300
  lines (`m8930_flush_row` wraps at 300); `j1_panel_console_enabled` is never cleared (`if(0 && ...)`).
  Frame stats `J1 frame #` for the first 20 presents; ASCII frame dumps and J1SHOT dumps disabled (`if(0)`).
  Primary surface pre-filled grey 0xFF404040 (shows as the grey/white screen at GUI start).
- `bsd/kern/bsd_init.c` watcher: SpringBoard thread dumps at rounds 14/20/26 (`J1U pid36 ...`),
  backboardd dumps off, RAM stress off, clk dump on.
- `security/mac_base.c`: sandbox fake disabled (`if (0 && ...)`).
- `msm8930_timer.c`: `ios7j1_reboot_recovery()` defined but unused; heartbeat `<T irq idx secs>`.

## uniLoader (`~/uniloader`)

- `main/main.c` fallback writes `UNILOADER fallback: IMEM65C=... TMR 00..9c:` into the trace ring
  (never seen yet, long-boot resets clear RAM).
- `blob/dtb`: `/chosen display-scale=2, display-rotation=0` (fixed "No image found for apple-logo").
