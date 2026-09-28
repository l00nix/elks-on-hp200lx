# HP 200LX Release 3.5.1 beta 1 — remove the kernel RAMdisk driver

28 September 2026. **Hardware-test beta; Release 3.5 remains the stable release.**
This beta is built and checked, but has not yet been booted on the HP 200LX.

## Change and purpose

Release 3.5 kept `CONFIG_BLK_DEV_RAM=y` with `CONFIG_RAMDISK_SECTORS=0`.
That recovered the unused RAMdisk memory while retaining the driver. This beta
sets `CONFIG_BLK_DEV_RAM` off and removes both preload RAMdisk configuration
values. The generated configuration contains no enabled RAMdisk macros, the
fresh build has no `rd.o`, and the kernel map has no RAMdisk driver symbols.

The only kernel-source changes from 3.5 are beta identification strings. CF,
firmware interrupts, keyboard, memory allocation and networking options are
unchanged. The HP kernel load segment remains `0340h`, and firmware RAM remains
reserved at `0x90000–0x9FFFF`. Root is still the Minix partition `/dev/cfa1`.

The earlier MEMLAB6/7 attempts were recorded as hanging at the DOS loader's
copy/jump handoff. The working MEMLAB16 fix retained the driver with zero
sectors. Those results motivate a real hardware regression test; this build
does not establish that the old loader problem is solved.

## Measured space savings

| Component | Release 3.5 | 3.5.1 beta 1 | Reduction |
| --- | ---: | ---: | ---: |
| Image file | 63,320 B | 62,032 B | 1,288 B |
| Near code | 39,808 B | 38,784 B | 1,024 B |
| Far code | 12,704 B | 12,624 B | 80 B |
| Initialized data | 5,344 B | 5,184 B | 160 B |
| BSS | 4,432 B | 4,432 B | 0 B |
| Relocation records | 2,840 B | 2,816 B | 24 B |

These are build-to-build measurements, including the changed version strings.
The 1,288-byte file reduction is about 1.26 KiB. It is not another 360 KiB RAM
recovery: the zero-sector setting already reclaimed that reservation. Actual
available program memory still needs comparison with `meminfo` on hardware.

This is a first space-saving step toward the planned Version 4 NE2000/networking
work. Networking is not enabled here. Later work needs a size budget for sockets,
TCP/IP and Ethernet, plus validated PCMCIA I/O and IRQ routing and CF/NIC
coexistence. The current IBM-PC NE2K default is IRQ12, which the HP platform
does not expose; IRQ2 is already owned by the HP firmware. Card resources must
be established rather than assuming the ordinary-PC defaults fit picoPCMCIA.

## Install and test

Download `hp200lx-release3.5.1-beta1.zip`. Copy its complete `ELKS351` folder to
`C:\ELKS351`. Keep `C:\ELKS35` for the Release 3.5 fallback. Keep the existing
Release 3/3.1 ELKS CF root card and the working DOS configuration, including
`STACKS=0,0`. No CF rewrite is required.

From fresh DOS outside System Manager:

```text
C:
CD \ELKS351
RUN351B1
```

Look for `HPR351B1 ROM`, the `/dev/cfa1` Minix root mount and a shell prompt.
The kernel's `rd: 0K ramdisk ...` line should disappear completely.
The loader may still print `ROOTEND=8C00`: **keep `ROOT092` and `BTGVDX.COM`**.
This beta removes the kernel driver, not the legacy DOS loader's root-file copy.
Both loader files are byte-identical to Release 3.5. Loader cleanup is a separate
experiment once this configuration boots reliably.

At the shell, try `ls /`, `cat /etc/issue` and `meminfo`; then repeat keyboard,
zoom and panning checks. Photograph the boot and memory results. If it stops,
photograph the last screen and retain `C:\ELKS351\HP351B1.TXT`.
To fall back, reboot to DOS, `CD \ELKS35` and run `RUNR35`.

## Verification and source

- Clean Linux/IA16 GCC 6.3.0 kernel build passed.
- Generated configuration, object list and kernel map confirm driver removal.
- Image header, natural file length, segment bounds, firmware/ATA symbols and
  CF-root loader options checked. No artificial image padding was added.
- 12 platform mock cases pass with RAMdisk macros absent; seven firmware-bridge
  and DOS-snapshot emulator tests pass using the unchanged bridge fixture.
- The rebuilt beta copy helper passes full copy/readback, eight injected errors,
  and five wrong-size cases, including rejection of the Release 3.5 image.
- HP/PC/PC98 load-base checks, patch reconstruction, DOS 8.3/CRLF checks and ZIP
  content/CRC checks pass. None of these emulate a full HP 200LX boot.

Source branch: [hp200lx-release-3.5.1-beta1](https://github.com/l00nix/elks-on-hp200lx/tree/hp200lx-release-3.5.1-beta1).
The `hp200lx-release3.5.1-beta1-source.zip` kit contains the pinned upstream
archive, four patches, exact configuration, helper source and tests. It retains
the Release 3.5 platform/CF patches and adds only the beta identification patch;
the RAMdisk removal is in `hp200lx.config`.

Build on Linux from the kit directory with the ELKS IA16 toolchain in `BASE/cross`:

```sh
BASE=/path/to/elks WORK=/new/build/path bash build.sh
nasm -f bin B351COPY.ASM -o B351COPY.COM
python3 verify_kernel.py /new/build/path
python3 tests/run_platform.py
python3 test_load_base.py /new/build/path/elks/include/linuxmt/config.h
python3 test_fwcopy.py
python3 test_abi.py
```

The emulator tests require Python's `unicorn` package. Kernel:
`K351B1`, 62,032 bytes, SHA-256 `7839bc409d1a8ffbf7331b7843b82506306381f899354054a68c26cebdd1254e`.

Upstream base: `69dfd4f274139ef1f533c646711db84902b0cfe4`. Release 3.5's
[architecture and credits](https://github.com/l00nix/elks-on-hp200lx/blob/hp200lx-release-3.5/docs/hp200lx/RELEASE3.5.md)
continue to apply. This is a kernel/boot beta reusing the existing userland.
