# HP 200LX FW2A — firmware port preview

28 September 2026. **Prerelease; hardware testing is in progress.** FW2A has
hardware evidence for boot, CF root mounting and basic built-in keyboard input.
This does not yet replace Release 3.1 as the stable release.

## How close is this to vanilla ELKS?

This is our closest HP 200LX implementation to vanilla ELKS so far, based on
recorded upstream commit `69dfd4f274139ef1f533c646711db84902b0cfe4`. That is a
pinned baseline, not a claim to track today's upstream HEAD. The `hp200lx-fw2a`
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

FW2A preserves the firmware NMI vector and dispatches IRQ2 to the original HP
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
upstream jiffy-based timeouts and LBA capability validation. FW2A also restores
the DOS handoff kernel segment `0340h`; the first FW2 extraction used `00B0h`
and failed early in boot. Restoring the address passed that failure on hardware;
the precise low-memory conflict remains unproven.

The new platform code is GPL-2.0-or-later and follows the HP Developer's Guide.
No Mack MINIX source was copied into this port. This is architectural inspiration,
not a MINIX kernel transplant or a claim that the GentleOS implementation is
identical. The reused DOS boot/loader chain descends from Richard L. Dubs's
MINIX-on-HP-200LX work; existing component authorship and licenses still apply.

## Evidence and remaining checks

The FW2A photograph (25797) shows `HPFW2A ROM`, ROM IRQ2 service `F000:CF5B`,
kernel base `0340h`, `/dev/cfa1` mounted as a Minix root filesystem, and a shell
prompt. The user reported that the keyboard appears to work. Zoom had not yet
been tested. The unchecked filesystem mount is not evidence of write reliability.

Pending for this exact binary: modifiers, repeat, Ctrl-C, externally timed
`sleep`, Fn+Space zoom and Menu+arrow panning. Sustained CF writes, RTC setup,
shutdown, suspend and battery behavior are also unvalidated. The previous
FW1D3 results must not be attributed to FW2A. Busy idle remains enabled and the
test boot uses `init=/bin/sh`.

Recorded build verification: FW2A clean kernel build passed, and its header,
segments and firmware symbols were checked. FW2 had a byte-identical clean
rebuild and an ordinary PC build identical to upstream after matching version
metadata. That ordinary-PC comparison predates patch 0003; the load-base
regression check additionally verifies HP, ordinary PC and PC98 defaults.

Publication checks rerun the 12 platform mock cases, seven firmware-bridge/DOS
snapshot emulator tests, DOS copy/readback success and fault tests, and load-base
checks. Packaging verifies source reconstruction, unchanged executable bytes,
ZIP CRCs and SHA-256 checksums. These checks do not emulate an HP 200LX.

## Install

Download `hp200lx-fw2a-standalone.zip` from the
[FW2A prerelease](https://github.com/l00nix/elks-on-hp200lx/releases/tag/hp200lx-fw2a).
Copy its `ELKSFW2` folder to `C:\ELKSFW2`; avoid a nested `ELKSFW2` directory.
It includes the DOS helpers and legacy `ROOT092` loader input, but **not the
persistent CF root image**. Use the existing Release 3/3.1 ELKS CF card. New
installations also need the [Release 3 root image and card installation steps](https://github.com/l00nix/elks-on-hp200lx/tree/hp200lx#release-3---persistent-pcmciacf-root-filesystem).

For an existing `C:\ELKSFW2` installation, `hp200lx-fw2a-update.zip` supplies
only the new kernel, selector, launcher and instructions.

Keep the working DOS `CONFIG.SYS`, including `STACKS=0,0`. From fresh DOS outside
System Manager, with the ELKS CF card inserted:

```text
C:
CD \ELKSFW2
RUNFW2A
```

Use `RUNFW2A`, not the known-failing `RUNFW2`. Retain `HPFW2A.TXT` and photograph
the screen if boot stops. No CF rewrite is required for an existing installation.
If FW1D3 is already installed, reboot to DOS and run `C:\ELKSFW1\RUNFWD3.BAT`
from that directory to return to the tested fallback.

## Source and reproduction

- [Actual patched source](https://github.com/l00nix/elks-on-hp200lx/tree/hp200lx-fw2a)
- [Platform, CF and load-base commits](https://github.com/l00nix/elks-on-hp200lx/compare/69dfd4f274139ef1f533c646711db84902b0cfe4...hp200lx-fw2a)
- `ports/hp200lx/fw2a/`: three patches, exact configuration, build script,
  firmware diagnostic, helper source and regression fixtures.
- `hp200lx-fw2a-source.zip`: complete build kit with the hash-checked upstream
  archive. It includes all three patches; no separate FW2 source download is needed.

On Linux, supply the ELKS IA16 toolchain in `BASE/cross`, unpack the source kit,
and run `BASE=/path/to/elks WORK=/new/build/path bash build.sh` from its directory.
The recorded compiler is IA16 GCC 6.3.0. Normal ELKS host build dependencies are
required. Existing build directories are refused. Host tests need a C compiler
and Python; emulator tests additionally need the `unicorn` Python package.

Kernel: `KERNFW2A`, 63,320 bytes, SHA-256:

```text
9b19a88dca9e7e8ae88b72567646bbf7fe5d80342a217c76c3f107dfeea11e57
```

The tested kernel, COM files and batch launcher are unchanged by publication.
ZIP instructions are updated to reflect the boot and keyboard evidence.
`hp200lx-fw2a-checksums.zip` contains the release asset and kernel checksums.
