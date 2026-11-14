# Handoff — where the port stands (2026-11-13)

## PAUSED 2026-11-14 — resume here

- Phone unplugged; it holds **run 82** in `boot` (half resolution: iOS at 270x480 scale 1, 2x2 pixel doubling
  to the 540x960 panel; DTB `display-scale=1`; `J1CPU` loop-speed probe at watcher round 2). Run 82 was flashed
  and booted but never evaluated: on reconnect, pull `/proc/last_kmsg` first (if it survived) and check
  `J1CPU ... per us`, whether the UI is faster, and whether scale-1 artwork looks acceptable.
  Revert half-res: `leoWidth/leoHeight/leoRow` back to 540/960/2160 in IOS7LeoDisplay.cpp, present loop in
  pe_msm8930_serrano.c back to the 1:1 copy, DTB `s4mini/probe/dtb_scale2.bin` into `~/uniloader/blob/dtb`.
- State at pause: lock screen -> slide to unlock -> home screen works (run 80/81). Touch works but is sluggish,
  Home/Power wake works, colours correct (run 81). UI far too slow to open apps.
- Next steps, in order:
  1. Read run 82 results. If the CPU clock is low (Krait left slow by aboot), raise it (acpuclock-8930
     HFPLL/L2 sequence) — likely the biggest win.
  2. Touch latency: move the mXT poll off the busy-wait (CHG GPIO11 interrupt or a lower-priority thread).
  3. Remove debug load: SpringBoard sampler thread (`J1S`), J1Q prints, frame stats.
  4. Second CPU (SMP) only if 1–3 are not enough.
  5. AssistiveTouch forced on but not visible yet; assetsd SIGBUS loop; CommCenter absent (more CT XPC waits).
- Workspace moved: S4 mini files are under `s4mini/` (scripts fixed, `iter.sh` runs from `s4mini/probe`).

## What works

- uniLoader boots XNU from `boot`; kernel console on the panel (shadow buffer copied to the
  bootloader's RGB888 scanout, 540x960, stride 1620).
- launchd, backboardd (pid 31), SpringBoard (pid 36) and ~50 processes run.
- iOS renders through CoreAnimation's software path into IOSurfaces from our IOMobileFramebuffer /
  IOSurfaceRoot clone (`iokit/Drivers/KernelBuiltIn/ARM/AppleARMPlatform/IOS7LeoDisplay.cpp`).
  The Apple logo drawn by iOS appears on the panel (photo `probe/ios_applelogo_photo.jpg`,
  text dump `probe/first_ios_frame_ascii.txt`).
- After the TCC patch SpringBoard presents frames continuously (one run: 195 presents).

- LOCK SCREEN SHOWN (run 50, 2026-11-13): "slide to unlock", date 31, grabber; photo
  `probe/ios_lockscreen_photo.jpg`. Needed two fixes: SpringBoard nobuddy (decmpfs hook) and the
  BBDataProviderConnection deadlock patch (shared cache). See PATCHES.md.

- UNLOCK TO HOME SCREEN (run 80, 2026-11-14): touch (mXT336S), Home/Power wake and slide-to-unlock work.
  Key fixes, all needed:
  - Touch: PM8917 L31 (SSBI) + LVS6 (RPM) power, bit-banged I2C on GPIO16/17, T5/T9 decode like Samsung
    mxts_msm8930.c (12-bit >>2, 540x960), drain all T5 messages per poll (one per poll lost drags).
  - Keys: separate IOHIDEventService "S4HomeButton" (Consumer 0c/01; Home 0c/40 GPIO35, Power 0c/30 PM8917
    PWRKEY rt block 6 bit 3), 52-byte keyboard events; queue accepts sizes 28..204.
  - SpringBoard main thread was blocked, so input was read but never handled. Found with a 1 Hz main-thread
    sampler (`J1S` lines, sched_prim.c ios7j1_sb_sample): DISPATCH_TIME_FOREVER wait in
    -[MPAVRoutingController volumeControlIsAvailable] (shared cache patch -> NO), CommCenter XPC in
    -[SBTelephonyManager isEmergencyCallActive] (decmpfs SpringBoard patch -> NO), data-exec crashes of
    mediaserverd/accountsd (override_nx allows data exec for user maps only; kernel maps hung boot).
  - Setup: PSSetupAssistantNeedsToRun -> NO (shared cache), SpringBoard nobuddy patch.
  - ram_console: XNU writes a valid Reed-Solomon header parity, so TWRP keeps the whole 300 KiB log.
  - Panel console is off once iOS presents (log persists in RAM).

## What does not work yet

- Very slow / laggy UI; red/blue were swapped (fixed in run 81, panel wants B,G,R). Touch poll was costly
  (busy-wait bit-bang in a high-priority work loop): run 81 gates reads on CHG and uses 1 us bit timing.
- AssistiveTouch forced on (_AXSAssistiveTouchEnabled/UIEnabled -> YES); assistivetouchd starts, UI not seen yet.
- assetsd crash loop (SIGBUS).

- FIXED (run 52): panic `"pmap_remove_range: wired_count"@osfmk/arm/pmap.c:3828` ~15-20 s after the lock
  screen, right after SpringBoard logged "screen turning off" and a new global 540x960 IOSurface was made.
  The old ARM pmap tracks wiring per physical page (PMAP_OSPTE_TYPE_WIRED) not per mapping, so a shared
  page wired in one pmap gets "unwired" by another pmap whose wired_count is 0. Now clamped + logged
  (`J1 pmap_remove_range wired clamp`). Run 52 then stayed on the lock screen until the 420 s timed reboot.
- After a panic the 420 s timed reboot does not fire (timer IRQ stops); user must hold Power+Volume Up.
  The RAM log survives that reset. (Rebooting from the panic path itself is a known dead end.)
- last_kmsg window: TWRP's ECC-protected ram_console header forces start/size back to 38936, so only data
  bytes 0..38935 are shown. The XNU ring now wraps at 0x9800 to stay inside that window (newest ~38 KB,
  rotated: find the newest `<T ... secs>` heartbeat).
- No touch input yet (slide does nothing): needs mXT336S driver + IOHIDEventService for backboardd.
  Hardware (Samsung k8930 board-8930-input-mxt.c): GSBI3 QUP I2C (0x16200000 / QUP 0x16280000, SDA GPIO16,
  SCL GPIO17, QUP IRQ SPI 151), touch IRQ GPIO11, power PM8917 L31 3.3 V (direct PM8XXX LDO via SSBI) +
  LVS6 1.8 V (RPM-controlled). Existing IOS7LeoHIDTouch.cpp / leo_touch_transport.c are HD2 (QSD8250)
  specific; the HID service side may be reusable. Read-only register probe `ios7j1_touch_probe()`
  (`J1T ...` lines, watcher rounds 1 and 39) added to see what state aboot leaves.
- Silent warm reset 120–400 s into boot (no panic text). Best recent runs: ~350–397 s.
  Observations:
  - Three runs with the kernel text console drawing full-screen over iOS stayed up to the 420 s timed
    reboot; subsequent runs (console limited/disabled, TCC patch active) reset around 120–140 s,
    until the cache-trap fix (see below), after which two runs reached ~350 s and ~397 s.
  - With launchd starting no daemons the system stays up for 420 s.
  - Crash/respawn storms of tccd / mDNSResponder / accountsd made it worse (now blocked).
  - Not the cause (tested): WDT0 (disabled), heat, memory exhaustion, IRQs masked up to 16 s,
    battery/power (user confirmed), armv7s instructions (CPU has vfpv4/idiva/idivt).
  - PMIC restart reason after these resets reads SMPL, but that may be uniLoader's own PS_HOLD fallback.
  - Long boots' RAM log is lost (reset clears RAM, then a second boot overwrites the log). Reading the
    panel through the camera is the reliable way to see late state.
- Daemons crashing: accountsd / mediaserverd execute code from RW (non-executable) pages
  (CoreData `+[NSManagedObject classForEntity:]` dynamic accessors / trampolines) →
  "Data/Stack execution not permitted". tccd and mDNSResponder abort: sandbox "Policy not found"
  (no Sandbox.kext). Faking `__mac_syscall("Sandbox")` success hung launchd (call 2) or did not help
  (call 0); reverted (`if (0 && ...)` in `security/mac_base.c`).

## Suggested next steps (in order)

1. Repeat the current build 2–3 times to confirm the cache-trap fix lengthens uptime.
2. Find what SpringBoard draws: log swap surface IDs vs created surfaces; check whether
   SpringBoard's window/surface ever reaches `ios7lab_present_owned_scanout`.
3. Port remaining GT-I9100 cache fixes (see below): RAM Normal WBWA instead of write-through,
   cleaned/DSB'd PTE writes (partly done), D-clean before I-invalidate.
4. Fix RW→exec trampoline mappings (vm_map_remap protections) so accountsd/mediaserverd survive.
5. Touch input (Atmel mXT336S, I2C) and an IOHIDEventService for backboardd once UI shows.

## Reference port: Galaxy S2 (GT-I9100)

https://github.com/kernel86-64/xnu-i9100 (branch `i9100-source`), loader
https://github.com/kernel86-64/uniloader (branch `i9100`). Same xnu-j1xlte base; boots iOS 7 to
SpringBoard with touch and software display. Useful reports in `docs/progress/`:
`CACHE_I9100_20261027.md` (RAM was write-through/Device → WBWA), `CACHE16_RUNTIME_CACHE_TRAPS_20261030.md`
(user cache traps used DCISW = data loss; we applied this fix), `HOME_POWER_STABILITY_I9100_20261027.md`
(set/way loop level iterator and flag bugs in `cpufunc-v7.s` — our `arm_dcache_wbinv_all` likely does
nothing on Krait because it starts at LoC), `APP19`, `DISP18` (screen scale), `TOUCH_I9100`.
Their userspace is armv7 because Cortex-A9 lacks idiv/vfpv4; Krait has both, so armv7s is fine here.

## Device state at handoff

Phone in TWRP, `boot` holds the run-50 build (nobuddy decmpfs patch, J1UC off; on-disk BB deadlock patch).
Old photos moved to `iphonecontrol/photos_archive_20261113/` (run48/, run49/ subfolders).
Nothing running on the PC.
