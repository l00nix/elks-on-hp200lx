# HP 200LX Release 3.5.2d — synchronous CF and smaller task stacks

**Diagnostic prerelease. Real HP results for 3.5.2d are pending. Stable 3.5 remains stable.**

Greg Haerr confirmed that the ATA-CF driver uses synchronous programmed I/O and
does not require `CONFIG_ASYNCIO`. This release disables that option. Upstream
ELKS consequently selects **640-byte task stacks** instead of 700 and **one
block-request entry** instead of 15. No manual task-stack-size patch is added.
The shared interrupt stack remains **1,024 bytes**.

The kernel source changes from 3.5.2c are release identification only: the
`HPR352D ROM` banner and version/date string.
The behavior change comes from the configuration. The ROM diagnostic still
measures every valid task-stack call and the first shared-stack call, then one
in 32, checking guards on every valid call. Broader tracing stays disabled:
the current upstream trace and custom probe use incompatible fill patterns.

The known working final relocation remains **0340h**, initial segment 0100h
and staging 1400h. RAMdisk and networking remain disabled. DOS-style ON/OFF
suspend remains unsupported. The existing CF root and userland are reused.

## Install and test

Download **hp200lx-release3.5.2d.zip** and copy the entire **ELKS352D** folder to
**`C:\ELKS352D`**, including the final D. Keep the working ELKS352C folder.
From fresh DOS outside System Manager, with the existing `STACKS=0,0` setting:

```text
C:
CD \ELKS352D
RUN352D
```

Keep ROOT092 and BTGVDX.COM; the legacy loader needs them. The kernel is K352D.
Expect `HPR352D ROM`, `HPBOOT ... stacks=640/1024`, CF root and a shell.
ROOTEND=8C00 is expected. A boot failure should be photographed along with the
saved `HP352D.TXT` snapshot. No CF rewrite is needed.

1. Run `ls /`, `cat /etc/issue`, and `meminfo -s`. Photograph all four HPST lines
   and the memory figures. Task usage should now be reported out of **640**,
   shared usage out of **1024**, with `sample=all/32 guard=each`.
2. Check keyboard, screen-output speed, manual zoom and panning. Repeat file
   reads and `meminfo -s` to exercise CF access and gather more task samples.
3. Exercise a small CF write using a new scratch file: `echo hp352d > /hp352d.tmp`,
   `sync`, `cat /hp352d.tmp`, then `rm /hp352d.tmp` and `sync`. Use another unused
   filename if that file already exists. This exercises the write path; a cached
   readback alone is not proof of persistence across a reboot.
4. Run `while :; do :; done`, use zoom/panning while it runs, stop with Ctrl-C,
   then run `meminfo -s` again. Report any hang, CF error or output slowdown.

Task sample `n` and task `calls` should match until counters saturate at 65,535.
Shared samples grow once per 32 valid calls. If either `guard` or `unknown` is
nonzero, photograph the result and return to the working fallback before more
stress. For fallback, reboot to DOS and use `C:\ELKS352C` / `RUN352C`.
Stable fallback remains `C:\ELKS35` / `RUNR35`.

## Existing CF diagnostic-tool compatibility

Use **`meminfo -s`**, not bare `meminfo`, `meminfo -a`, `meminfo -m` or `ps`
from the older CF userland. Those process-listing modes read kernel task
structures using a compiled-in size, which changes with the smaller stack.
`meminfo -s` selects only system heap allocations and then invokes the unchanged
memory-usage ioctl, which also prints all four HPST lines. Its `Heap/free` and
`Total mem` subtotals cover the selected rows; use the final `Main` line for
overall memory totals. A matching rebuild of `meminfo`/`ps` will be needed for
full process listings in a later userland update. Ordinary shell/file operations
use the normal syscall interface and do not require a CF rewrite for this test.

## Measurements and limitations

The preceding 3.5.2c hardware test observed task/shared written peaks of
202/700 and 224/1024 bytes, with zero guards/unknown and working busy-loop
Ctrl-C. Those are observations under that workload, not worst-case guarantees.
The smaller task stack must still be tested on the HP.

`used` records the deepest written location below stack top; `rom` records
written depth below probe metadata; `entry` is peak bridge-entry usage. Their
maxima can come from different calls. Measured calls add six metadata bytes,
skipped shared calls four. Existing register saves and the fake interrupt frame
are also present. Unwritten stack allocations, marker-value writes, a different
firmware SS and rare unsampled shared calls can escape the measurement. Guards
cannot detect every overwrite. Invalid bounds use the plain bridge; DS/SS
mismatch bypasses statistics. HPST is kernel-console output and may not appear
in redirected meminfo stdout.

The guide confirms that manual zoom and panning belong to the firmware keyboard
preprocessing path. Automatic cursor tracking also relies on BIOS INT 08h and
is a separate question. See [BIOS keyboard/display findings](https://github.com/l00nix/elks-on-hp200lx/blob/hp200lx-release-3.5.2d/docs/hp200lx/BIOS-KEYBOARD-DISPLAY.md)
in `docs/hp200lx` for the guide sections and the limits of that conclusion.

## Build and validation

`K352D`: **62,472 bytes**, SHA-256 `1f3e0021103d191c6447f79c38106a77f022b49dc252fda2cb99fa3b9d752a42`.

Compared with 3.5.2c, the image is 296 bytes smaller (62,768 to 62,472).
Static kernel data+BSS falls by 208 bytes (9,920 to 9,712). The request array
shrinks from 300 to 20 bytes; other data changes make the net static saving
208 bytes. Task allocation is separately 60 bytes smaller per slot: 960 bytes
at the default 16 slots. Runtime free-memory totals await the hardware test.

- Clean Linux/IA16 GCC 6.3 build; image/header/segment checks, RAMdisk absence,
  networking/ASYNCIO/TRACE disabled, 640-byte task stack, one request entry and
  1024-byte shared-stack/guard placement verified from build outputs.
- 12 production-assembly emulator cases pass with the new 640-byte bounds:
  stack classification, exact synthetic depths, ABI preservation, nested calls,
  guards, invalid bounds, task/shared sampling and counter saturation.
- 14 platform/mock cases and seven existing ABI/snapshot cases pass.
- Diagnostics-disabled bridge bytes match the earlier uninstrumented bridge;
  diagnostics-disabled platform C compiles.
- DOS copy/readback and fault injection, wrong-image-size rejection, relocation,
  patch reconstruction, configuration/source parity, DOS 8.3 names, CRLF and
  ZIP integrity checks pass.

These are build and synthetic checks, not an HP ROM emulator or a hardware pass.

The source kit includes upstream `69dfd4f274139ef1f533c646711db84902b0cfe4`,
eight incremental patches, the exact configuration, helpers, tests and fixtures.
Patch 8 changes identification; disabling ASYNCIO is in `hp200lx.config`.
Existing release artifacts are unchanged. Build with the ELKS IA16 toolchain:

```sh
BASE=/path/to/elks WORK=/new/build/path bash build.sh
bash tests/build_stack_fixture.sh /new/build/path
bash tests/check_diag_off.sh /new/build/path
nasm -f bin B352DCPY.ASM -o B352DCPY.COM
python3 verify_kernel.py /new/build/path
python3 tests/run_platform.py
python3 tests/test_stack.py
python3 test_abi.py
python3 test_fwcopy.py
python3 test_load_base.py /new/build/path/elks/include/linuxmt/config.h
```

Emulator tests need Python Unicorn. `VALIDATION.json` records build metrics.
Only the boot ZIP goes to captainfuture. Source/checksum ZIPs remain on GitHub.
