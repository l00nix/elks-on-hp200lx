# HP 200LX Release 3.5 — firmware release

28 September 2026. Release 3.5 has
hardware evidence for boot, CF root mounting, basic built-in keyboard input,
zoom and panning.
This supersedes Release 3.1 as the current numbered release. Remaining validation
limits are listed below.

## How close is this to vanilla ELKS?

This is our closest HP 200LX implementation to vanilla ELKS so far, based on
recorded upstream commit `69dfd4f274139ef1f533c646711db84902b0cfe4`. That is a
pinned baseline, not a claim to track today's upstream HEAD. The `hp200lx-release-3.5`
branch starts directly at that commit; it does not inherit the Release 3.1
experimental source tree. The kernel and diagnostic utility changes touch 20
files (423 added lines, 5 removed), before release documentation and packaging.

ELKS retains its scheduler, filesystem implementation, standard memory allocator
and scan-code-to-TTY path. HP adaptations are guarded by `CONFIG_HP200LX_FW`;
the release also pins build version text. The existing Release 3/3.1 CF root
filesystem and DOS loader helpers are reused, so this is a new upstream-based
kernel and boot package, not a completely rebuilt userland distribution.

## GentleOS, MINIX and the BIOS approach

The working [GentleOS HP 200LX port](https://github.com/l00nix/gentleos-hp200lx)
and the historical MINIX-on-HP-200LX work encouraged a firmware reuse approach:
keep the HP BIOS services and their working memory alive, and let them handle
the machine-specific keyboard scanning and debounce.

Release 3.5 preserves the firmware NMI vector and dispatches IRQ2 to the original HP
ROM service. That service produces PC-style scan codes consumed by ELKS's IRQ1
keyboard driver. ELKS then handles key translation and TTY input. This is not
the old direct matrix scanner or BIOS INT 16h polling implementation. The ROM
owns IRQ2 acknowledgement; ELKS avoids a second EOI. AT LED commands and XT
port-61 acknowledgement strobes are disabled for the HP configuration.

Firmware RAM at physical `0x90000–0x9FFFF` is reserved, overlapping `umb=` regions
are rejected, and firmware interrupt service gets a 1 KiB interrupt stack.
ELKS TIMER0 uses the tested HP mode-3 setting, while the HP firmware retains
its own services. A one-time, guarded IRQ0 handoff clears an inherited PIC
in-service state only when ISR is exactly 01 and no ELKS IRQ0/1/2 handler has
run. The original cause of that inherited state is still under investigation.

The CF patch retains HP socket transfer and initialization quirks, but restores
upstream jiffy-based timeouts and LBA capability validation. Release 3.5 also restores
the DOS handoff kernel segment `0340h`; the first FW2 extraction used `00B0h`
and failed early in boot. Restoring the address passed that failure on hardware;
the precise low-memory conflict remains unproven.

The new platform code is GPL-2.0-or-later and follows the HP Developer's Guide.
No Mack MINIX source was copied into this port. This is architectural inspiration,
not a MINIX kernel transplant or a claim that the GentleOS implementation is
identical. The reused DOS boot/loader chain descends from Richard L. Dubs's
MINIX-on-HP-200LX work; existing component authorship and licenses still apply.

## Evidence and remaining checks

The development-candidate photograph (25797) shows the firmware identifier, ROM IRQ2 service `F000:CF5B`,
kernel base `0340h`, `/dev/cfa1` mounted as a Minix root filesystem, and a shell
prompt. The user reported that the keyboard appears to work, then confirmed:
"Zoom and zoom paning works". Zoom and panning are therefore confirmed on Release 3.5.
The unchecked filesystem mount is not evidence of write reliability.

Remaining checks for this implementation: modifiers, repeat, Ctrl-C, externally timed
`sleep`. Sustained CF writes, RTC setup,
shutdown, suspend and battery behavior are also unvalidated. The previous
FW1D3 results must not be attributed to Release 3.5. Busy idle remains enabled and the
test boot uses `init=/bin/sh`.

Recorded build verification: Release 3.5 clean kernel build passed, and its header,
segments and firmware symbols were checked. FW2 had a byte-identical clean
rebuild and an ordinary PC build identical to upstream after matching version
metadata. That ordinary-PC comparison predates patch 0003; the load-base
regression check additionally verifies HP, ordinary PC and PC98 defaults.

Publication checks rerun the 12 platform mock cases, seven firmware-bridge/DOS
snapshot emulator tests, DOS copy/readback success and fault tests, and load-base
checks. Packaging verifies source reconstruction, kernel differences limited to
the two version strings,
ZIP CRCs and SHA-256 checksums. These checks do not emulate an HP 200LX.

## Install

Download `hp200lx-release3.5.zip` from the
[Release 3.5](https://github.com/l00nix/elks-on-hp200lx/releases/tag/hp200lx-release-3.5).
Copy its `ELKS35` folder to `C:\ELKS35`; avoid a nested `ELKS35` directory.
It includes the DOS helpers and legacy `ROOT092` loader input, but **not the
persistent CF root image**. Use the existing Release 3/3.1 ELKS CF card. New
installations also need the [Release 3 root image and card installation steps](https://github.com/l00nix/elks-on-hp200lx/tree/hp200lx#release-3---persistent-pcmciacf-root-filesystem).

When upgrading from an earlier release, install the complete `ELKS35` folder
from the main ZIP. Keep your existing CF card.

When upgrading from an earlier release, install the complete `ELKS35` folder
from the main ZIP. Keep your existing CF card.

For an existing `C:\ELKS35` installation, `hp200lx-release3.5-update.zip` supplies
only the new kernel, selector, launcher and instructions.

Keep the working DOS `CONFIG.SYS`, including `STACKS=0,0`. From fresh DOS outside
System Manager, with the ELKS CF card inserted:

```text
C:
CD \ELKS35
RUNR35
```

Use `RUNR35`. Retain `HPR35.TXT` and photograph
the screen if boot stops. No CF rewrite is required for an existing installation.
If FW1D3 is already installed, reboot to DOS and run `C:\ELKSFW1\RUNFWD3.BAT`
from that directory to return to the tested fallback.

## Source and reproduction

- [Actual patched source](https://github.com/l00nix/elks-on-hp200lx/tree/hp200lx-release-3.5)
- [Platform, CF and load-base commits](https://github.com/l00nix/elks-on-hp200lx/compare/69dfd4f274139ef1f533c646711db84902b0cfe4...hp200lx-release-3.5)
- `ports/hp200lx/release3.5/`: three patches, exact configuration, build script,
  firmware diagnostic, helper source and regression fixtures.
- `hp200lx-release3.5-source.zip`: complete build kit with the hash-checked upstream
  archive. It includes all three patches; no separate FW2 source download is needed.

On Linux, supply the ELKS IA16 toolchain in `BASE/cross`, unpack the source kit,
and run `BASE=/path/to/elks WORK=/new/build/path bash build.sh` from its directory.
Rebuild the DOS copy helper with `nasm -f bin R35COPY.ASM -o R35COPY.COM`.
The recorded compiler is IA16 GCC 6.3.0. Normal ELKS host build dependencies are
required. Existing build directories are refused. Host tests need a C compiler
and Python; emulator tests additionally need the `unicorn` Python package.

Kernel: `KERNR35`, 63,320 bytes, SHA-256:

```text
f7c2154df67da26b265e3b770ce30cdf7281687e8229bfde799132629ccd1fa4
```

Release 3.5 renames the DOS folder, kernel, checked-copy helper, launcher and log.
The rebuilt kernel differs from the tested development candidate only in two
same-length identification strings; executable code and layout are unchanged.
The renamed DOS copy helper is rebuilt and its success/failure tests rerun.
`hp200lx-release3.5-checksums.zip` contains the release asset and kernel checksums.

Run `python3 tests/run_platform.py` for platform tests. Run the load-base test
with the built `elks/include/linuxmt/config.h` path as its argument.
The ABI fixture is the previously linked, unchanged FW2 firmware bridge.
