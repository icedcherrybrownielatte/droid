# iOS 7.1.2 on Samsung Galaxy S4 mini (GT-I9190, MSM8930) — Claude Code guide

Port of iOS 7.1.2 (iPhone5,2, build 11D257, armv7s userspace) to the S4 mini using a fork of
xnu-j1 (XNU 2422, ARMv7) booted by uniLoader from the Android `boot` partition.
Current state, findings and next steps: `s4mini/docs/HANDOFF.md`. Full history: `s4mini/PROGRESS.md`.
Patch inventory and debugging techniques: `s4mini/docs/PATCHES.md`, `s4mini/docs/DEBUGGING.md`.

Workspace layout (2026-11-14): everything specific to the S4 mini lives in `s4mini/` (probe, docs, PROGRESS.md,
backup, odin, patches, recon, uniloader copy). Shared at the top level: `tools/` (adb), `iphonecontrol/` (camera),
`ipsw_x/` + the IPSW (same iOS 7.1.2 rootfs for every phone), `xnu-j1xlte/` (base XNU reference).
A second port target, Galaxy S4 GT-I9500 (Exynos 5410), lives in `s4/` (TWRP: `s4/twrp_dl/`).

## Hard safety rules (never break)

- NEVER write the `recovery` partition (TWRP lives there; it is the only way back). Flash `boot` only.
- Only touch the device with serial `077af85a` (`ANDROID_SERIAL=077af85a`, `adb -s 077af85a`).
  Other devices on the PC (a T561 tablet, an iPad, the iPhone camera) must not be touched.
- The phone must always come back to TWRP by itself (uniLoader fallback / kernel timed reboot at 420 s).
  Do not add code that halts or spins forever: that froze the phone and needed a manual key reset.
- Writes to the iOS disk image on the phone (`/dev/block/mmcblk0p24` = `card.img`) are done sector by
  sector: read the sector, back it up into `s4mini/probe/`, verify the original bytes, patch, write, re-read and
  compare md5. Never write blind.
- If a change makes boot progress worse, revert it rather than stacking fixes on top (user rule).
- Ask the user before anything outward-facing; the user is often away, so prefer self-recovering
  experiments and put risky untested work in an `untested/` folder for the user to try.

## Layout

- PC working dir: `C:\Users\User\Desktop\Droid` (Windows, Git-bash + WSL Ubuntu).
- XNU source: WSL `~/xnu-j1/xnu` (= `\\wsl.localhost\Ubuntu\home\user\xnu-j1\xnu`). Board: `MSM8930_SERRANO`.
- uniLoader: WSL `~/uniloader` (`.config`: `CONFIG_XNU_PHYS_BASE=0xA6100000`, `CONFIG_XNU_MEMSIZE=0x38400000`,
  `CONFIG_SERRANO_FALLBACK`). Device tree blob: `~/uniloader/blob/dtb` (Apple ADT; original saved as
  `s4mini/probe/dtb_orig.bin`, `/chosen display-scale=1, display-rotation=0` since run 82 (half resolution 270x480; the
  scale-2 blob is `s4mini/probe/dtb_scale2.bin`).
- `s4mini/probe/`: build/flash scripts, kernel logs (`lastk*.txt`), sector backups, helper tools.
- `ipsw_x/`: extracted IPSW. Rootfs tree `ipsw_x/rootfs/Sochi11D257.N42OS/`, shared cache
  `.../System/Library/Caches/com.apple.dyld/dyld_shared_cache_armv7s`, disk image `ipsw_x/card.img`
  (MBR + FAT32 holding the HFS+ rootfs; same bytes as phone partition `mmcblk0p24`).
- `iphonecontrol/`: camera rig. An iPhone photographs the S4 screen; photos land in `iphonecontrol/photos`.
  Needs the iPhone awake/unlocked and `python iphoneview.py --usb` running (the user starts it).
- adb: `tools/platform-tools-dl/platform-tools/adb.exe` (not on PATH). Use `MSYS_NO_PATHCONV=1`
  in Git-bash or remote paths get mangled (`/cache/x` becomes `C:/Program Files/Git/cache/x`).

## Iteration loop (phone must be in TWRP)

```bash
cd /c/Users/User/Desktop/Droid/s4mini/probe
MSYS_NO_PATHCONV=1 ANDROID_SERIAL=077af85a timeout 1700 bash iter.sh 40 60 4
```

`iter.sh <wait_s> <photos> <interval_s>`: builds XNU in WSL, strips + LZ4, builds uniLoader, packs
`boot_recfb.img`, flashes `boot`, verifies md5, `adb reboot`, takes photos, waits for TWRP.
`NOSNAP=1` skips photos (use when the iPhone is unavailable or out of storage).
Before each photo phase iter.sh runs `iphonecontrol/cleandcim.py` (SSH over USB, root/alpine): deletes
everything under the camera iPhone's `/var/mobile/Media/DCIM` (photos are already on the PC) so it never fills up.
`flashonly.sh` = build + flash without reboot/photos. Run long jobs in the background.

After it returns to TWRP:

```bash
A=../../tools/platform-tools-dl/platform-tools/adb.exe
$A -s 077af85a shell cat /proc/last_kmsg > lastkNN.txt
```

Build errors: `~/xnu-build-last.log` in WSL (iter.sh prints `BUILD_FAILED` and flashes nothing).

## Editing gotchas

- Editing XNU files from Windows: use small Python scripts in the scratchpad with
  `open(p, newline='')` and exact `assert s.count(old) == 1` replacements. Bash heredocs and sed through
  WSL repeatedly turned `\n` inside C strings into real newlines or CRLF and broke the build.
- After any edit, if a build fails, grep the inserted printf for a literal line break first.
- User likes dense photo coverage; storage is not a concern (unless the iPhone says it is full).

## User preferences

- Wants to see iOS UI (lock screen / SpringBoard) on the panel; send screenshots/photos with
  SendUserFile when anything new is displayed.
- Terse status updates; explain plainly when asking for physical actions (Power + Volume Up = TWRP).
