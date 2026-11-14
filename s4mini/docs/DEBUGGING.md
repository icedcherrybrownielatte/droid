# Debugging techniques that work on this device

## Kernel log after reset

- XNU mirrors console output into TWRP's persistent_ram (ram_console) at phys 0x8fe00000.
  In TWRP: `adb -s 077af85a shell cat /proc/last_kmsg > lastkNN.txt`. Do NOT read /dev/mem 0x88400000
  (crashes TWRP).
- Lost when: the user holds Power+Volume Up (cold reset), or a long boot resets with RAM loss and a
  second XNU boot starts. A ~12 KB log ending at `IOS7LAB vm_map` ~12 s means you are looking at a
  short second boot, not the interesting one.
- Heartbeat lines `<T irqcount logidx dgt_seconds>` give uptime of the last boot.
- Watcher lines `J1W round N nprocs bb sb P<presents> S<swapdiag> CK<checkin> T<timers>` every ~30 s.
- Large print bursts (ASCII art, hex dumps of frames) overwrite the 300 KiB ring and seemed to
  correlate with resets: keep diagnostic output small.

## Reading the panel with the camera

- When RAM logs are lost, keep the kernel console on the panel and read it from photos
  (`iphonecontrol/photos/IMG_*.JPG`, 3264x2448, panel text is rotated: `rotate(-90, expand=True)`,
  crop the top ~62%). Contact sheets of the last 40–60 photos show the boot timeline at a glance:
  kernel text → grey (first GUI frame, pre-fill) → Apple logo → Samsung splash → TWRP.
- If the iPhone camera stops producing photos: it is locked or out of storage; ask the user.

## Symbolizing user addresses

- Thread dumps `J1U pid36 sl<slide>` print UNSLID shared-cache addresses already.
- `probe/dsc_lookup.py <cache> addr...` → image + nearest function start.
- Helper tools saved in `probe/tools/`: `locsyms.py <img> <addr>|=<substring>` parses the cache's local-symbols section
  (offset at header 0x48) and gives real names, e.g. `-[UIApplication _handleDelegateCallbacks...]`.
- `probe/dsc_dis.py <cache> start end` thumb disassembly; `probe/macho_dis.py` / `macho_xref.py`
  for standalone binaries (SpringBoard, backboardd).
- Also in `probe/tools/`: `dscxref.py <image> <hexaddr...>` (movw/movt+add-pc xrefs in a cache image),
  `whichimg.py "<string>"` (which cache image holds a string), `adt.py` (dump/patch the uniLoader
  Apple device tree), `tccpatch.py` / `renamesetup.py` (the verified on-device sector patchers; templates
  for future patches). They hardcode Windows paths under `C:\Users\User\Desktop\Droid`.
- Kernel symbols: `/home/user/cctools/bin/arm-apple-darwin11-nm -n probe/mk_cur`.

## Finding shared-cache patch locations on the phone

card.img offset = cache file offset + 0x551da800. Confirm by searching a unique 64-byte pattern from the
cache in `ipsw_x/card.img` before patching.

## Known dead ends (do not repeat)

- Halting/rebooting from panic paths (froze the phone, needed manual reset).
- Panel console fully off after first GUI frame (resets earlier in recent runs).
- Batching ram_console writes (no effect on resets).
- Trusting only the ram_console marker word (lost the log completely).
- Faking all Sandbox `__mac_syscall` calls (call 2 hangs launchd).
- IRQ-off theory (survived 16 s masked), 100% CPU theory, power/USB theory.
