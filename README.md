# ELKS Linux on the HP 200LX

A **downstream fork of [ELKS](https://github.com/ghaerr/elks)** that brings the
ELKS 16-bit Unix-like kernel up on **Hewlett-Packard 200LX palmtop** hardware.

> This is community bring-up work, not an official ELKS release. It is a fork of
> `ghaerr/elks`; the upstream project's own README should be preserved as
> `UPSTREAM-README.md`. All upstream credit and the GPLv2 license remain with
> the ELKS authors. This fork tracks the HP 200LX effort discussed in
> [ghaerr/elks#2236](https://github.com/ghaerr/elks/issues/2236).

---

## Release 2 - Internal Keyboard

**Release 2 boots ELKS to a usable interactive shell on a real, stock-clock
HP 200LX, with working input from the built-in HP 200LX keyboard.**

This is the first self-contained HP 200LX ELKS release: no external keyboard is
needed. The tested build lineage is `N59`; the release package keeps the tested
DOS entry point name `RUNN59`.

![HP 200LX running ELKS Release 2 with no external keyboard attached](docs/hp200lx/images/release2-unit.jpg)

*Release 2 on real HP 200LX hardware: ELKS running from the built-in keyboard,
with no external keyboard attached.*

What works in Release 2:

- Boots cleanly to `/bin/sh` using the BIOS console and RAM-root minix
  filesystem.
- The **built-in HP 200LX keyboard** types into the ELKS shell.
- Normal letters, numbers, punctuation, Enter, Backspace, Tab, and Space work.
- Held Shift works, for example `Shift+q` produces `Q`.
- Held Ctrl works, for example `Ctrl+c` reaches the shell/application.
- Shift plus the blue HP application/menu keys produces the expected shifted
  symbols such as `! @ # $ ^ & ( )`.
- `fork()`/`exec()` work; external commands such as `ls` and `cat` run from the
  RAM-root filesystem.

Example shell session:

```text
# ls
bin   bootopts  dev  etc  home  lib  linux  mnt  root  tmp
# cd etc
# cat /etc/issue
ELKS 0.9.2-dev
# echo hi
hi
```

![ELKS shell on the HP 200LX showing ls and cat /etc/issue typed from the internal keyboard](docs/hp200lx/images/release2-shell.jpg)

*Release 2 shell session on the HP 200LX: `ls` and `cat /etc/issue` typed on the
built-in keyboard.*

### Release 2 artifact

- Package: [`releases/hp200lx-release2.zip`](releases/hp200lx-release2.zip)
- Tested DOS entry point: `RUNN59`
- Kernel image inside the package: `KERNBOP`
- Kernel size: `61488` bytes
- Kernel SHA256:
  `c29f88aa2c3979effdaa2f13f5a2566799bfb262178af68c8fe7b699475825d1`
- Package SHA256:
  `2be5647745ae6a523262a5c21e51c3fca0295ae6abfcf59272673eaca3a4a6c1`

### Release 2 limitations

- This remains an experimental downstream/community ELKS build for the HP 200LX.
- The root filesystem is still a RAM disk loaded by the DOS boot chain. This is
  enough for a shell and small commands, but it is not yet a persistent native
  install.
- Persistent PCMCIA/CF hard-disk access from inside ELKS is a separate future
  task.
- The HP-specific keyboard work has been proven on real hardware, but it still
  needs cleanup before it is suitable as an upstreamable ELKS platform driver.
- HP-specific convenience functions such as display zoom, contrast, inverse
  video, and other firmware-level key combinations still need separate review.

---

## Release 1 - External Keyboard Bring-Up

Release 1 proved the core boot path: ELKS could boot to a shell on the HP 200LX,
run from a RAM-root filesystem, and accept input through an external serial
keyboard path. It established the memory-map fixes, idle-loop polling approach,
and DOS loader packaging that Release 2 builds on.

Release 2 supersedes Release 1 for normal use because the HP 200LX is now
self-contained.

---

## Install (run Release 2 on an HP 200LX)

You need a **stock-clock HP 200LX**, DOS on the internal drive or CF-backed DOS
volume, and a way to copy files to the palmtop's `C:` drive.

1. Download [`hp200lx-release2.zip`](releases/hp200lx-release2.zip) from this
   repository and unzip it. You get a `hp200lx-release2/` folder.
2. Copy **all** files from that folder to `C:\ELKS` on the HP 200LX. Back up or
   rename any existing `C:\ELKS` first.
3. From DOS on the 200LX:

   ```dos
   C:
   CD \ELKS
   RUNN59
   ```

4. ELKS boots. When the shell prompt appears, type on the built-in HP 200LX
   keyboard.

To uninstall, boot back to DOS and remove or rename `C:\ELKS`. This release
runs entirely through the DOS loader chain from that directory. It does not
repartition the drive or install a boot loader, so there is nothing else to
undo.

The package includes the boot helpers and images needed by the DOS boot chain:

| File | Purpose |
| --- | --- |
| `RUNN59.BAT` | Tested DOS entry point for Release 2. |
| `KERNBOP` | ELKS kernel image from the N59 internal-keyboard build. |
| `ROOT092` | RAM-root minix filesystem image. |
| `CARDIO.EXE` | HP 200LX card/RAM-disk loader helper from the MINIX-on-200LX boot chain. |
| `PUT13.EXE` | INT 13h handler loader helper. |
| `MKINTS.COM` | Captures interrupt vectors for the loader path. |
| `BTGVDX.COM` | DOS loader used to launch the ELKS image. |
| `VECT13.DAT` | DEBUG script used by the boot chain. |

---

## How it works (the key ideas)

### 1. DOS loader chain inherited from the MINIX-on-200LX work

The HP 200LX can be made to boot a non-DOS system from DOS by using the loader
chain descended from Richard Dubs' MINIX-on-HP-200LX work. The release package
uses that path to prepare the RAM-root image and launch the ELKS kernel.

This keeps Release 2 non-destructive: it runs from `C:\ELKS` and returns to DOS
on reboot.

### 2. BIOS console

Release 2 uses the BIOS console path, which is a good match for the HP 200LX
display hardware. The goal for this release is a reliable text shell on the
real palmtop, not direct framebuffer ownership.

### 3. Idle-loop polling

The HP 200LX does not behave like a normal PC/XT with a standard keyboard
controller and timer path. Earlier testing showed that relying on normal
interrupt-driven keyboard input was not sufficient.

Instead, the HP 200LX input path is polled from the kernel idle loop and
decoded keystrokes are pushed into the console tty queue:

```text
idle loop -> HP 200LX scanner -> Console_conin() -> tty input queue -> shell
```

This avoids depending on missing or incompatible PC keyboard interrupts.

### 4. Direct HP 200LX keyboard matrix scanner

Release 2 uses a direct scanner for the HP 200LX keyboard matrix. During the
N24-N59 bring-up series, the key matrix was mapped as tuple values and then
translated into ELKS console input.

The final breakthrough was in the N58/N59 scanner:

- Modifier artifacts are filtered out as non-feedable key candidates.
- The scanner selects the first tuple that can actually produce console input.
- Held Shift and held Ctrl are recognized while a normal key is pressed.
- A one-shot fallback is retained for cases where the hardware scanning cadence
  reports modifier state separately from the following key.

That combination gives normal shell typing behavior on real HP 200LX hardware.

### 5. RAM-root memory-map fix

The DOS loader preloads the RAM-root image at a fixed segment, but stock ELKS
assumed a more conventional memory layout. The HP 200LX build caps the process
pool below the RAM-root start so `fork()` does not corrupt the filesystem image.

This is why shell commands such as `ls`, `cat`, and small external programs can
run without destabilizing the root filesystem.

---

## What changed vs upstream ELKS

The exact source branch for Release 2 should be named separately from the older
external-keyboard branch, for example `hp200lx-internal-keyboard` or
`hp200lx-release2`.

At a high level, Release 2 changes are in the same small group of HP 200LX
bring-up areas:

| Area | Change |
| --- | --- |
| Kernel idle loop | Poll HP 200LX input from the idle loop and feed the console tty queue. |
| Keyboard driver | Add direct HP 200LX matrix scanner and tuple-to-character map. |
| Modifier handling | Support held Shift/Ctrl plus a one-shot fallback for hardware timing edge cases. |
| Memory map | Keep process memory from overlapping the RAM-root image. |
| Console config | Use BIOS console and a RAM-root minix filesystem. |
| Build config | Add/maintain an HP 200LX-specific kernel configuration. |

Suggested release branch/tag naming:

```text
branch: hp200lx-internal-keyboard
tag:    hp200lx-release-2
title:  Release 2 - Internal Keyboard
```

---

## Roadmap

- Clean up the HP 200LX keyboard scanner into a maintainable platform-specific
  driver.
- Document the final tuple map and include a keyboard diagram in `docs/hp200lx`.
- Investigate persistent PCMCIA/CF hard-disk support from inside ELKS.
- Review the HP 200LX BIOS/video functions for display zoom, contrast, inverse
  video, and related key combinations.
- Harden and stress-test memory behavior under heavier process pressure.
- Review double-speed HP 200LX units separately; Release 2 was tested on a
  stock-clock unit.
- Decide which parts can be proposed upstream and which should remain in this
  downstream hardware fork.

---

## Credits

- [ELKS](https://github.com/ghaerr/elks) and its authors - the kernel this
  builds on (GPLv2).
- **Greg Haerr** and the ELKS community - for the upstream project and discussion
  in [ghaerr/elks#2236](https://github.com/ghaerr/elks/issues/2236).
- **Richard L. Dubs** - the MINIX-on-HP-200LX work that this DOS boot/loader
  chain descends from; see the archived
  [`l00nix/dubs-minix-repo`](https://github.com/l00nix/dubs-minix-repo).
- The HP 100LX/200LX Developer's Guide and HP 200LX user documentation - for
  the low-level keyboard, BIOS, and display details.
- The [`l00nix/gentleos-hp200lx`](https://github.com/l00nix/gentleos-hp200lx)
  work - for prior evidence that the internal HP 200LX keyboard can be driven
  directly.
- All real-hardware testing in this repo was done on an HP 200LX with 4 MB RAM
  and a DOS/FAT storage setup.
