# HP 200LX Release 3.5.2 beta 1 — measure the firmware stack

28 September 2026. **Diagnostic prerelease; real HP boot and measurements pending.**
Release 3.5 remains stable. This builds on the hardware-tested 3.5.1 beta without
the RAMdisk driver. Networking and DOS-style ON/OFF suspend remain unsupported
in this configuration.

This responds to [Greg Haerr's stack and relocation questions](https://github.com/ghaerr/elks/issues/2236#issuecomment-5875768512).
The earlier 1 KiB shared interrupt stack was precautionary: there is no measured
HP ROM requirement or demonstrated 512-byte overflow. User-mode interrupts use
the current task's kernel stack, so enlarging only the shared stack does not
establish safety. This beta gathers evidence before changing that arrangement.

## Changes

`CONFIG_HP200LX_STACK_DIAG=y` enables an assembly probe around the actual HP ROM
IRQ2 call. It recognizes the current task's kernel stack and the shared
interrupt stack by address, paints unused words below the live SP with `A55Ah`,
then scans for writes after ROM returns. It records separate peaks and sample
counts, checks the existing task guard, and adds a two-byte shared-stack guard.
Per-call metadata permits nested calls; scan and statistics updates run with
interrupts disabled and do not call C or print from the IRQ handler.

The existing CF installation's `meminfo` requests `MEM_GETUSAGE`, which now prints
three `HPST` diagnostic lines from normal syscall context before returning its
usual memory information. No new user program, ioctl format or CF rewrite is
needed. Any other program making that ioctl will also trigger the report.

Task stacks remain **700 bytes** and the shared interrupt stack **1,024 bytes**.
The probe adds **six bytes** of per-call metadata, on top of the bridge's existing
12-byte register save and six-byte fake interrupt frame. It does not move ROM
execution to a private stack. Diagnostics default off in configuration; with
them off, the bridge is byte-identical to 3.5.1's bridge.

`HPBOOT` prints the configured initial load, staging and final relocation
segments. Expected: `initial=100 staging=1400 reloc=340 stacks=700/1024`.
The segment values are hexadecimal (physical addresses `01000h`, `14000h`,
`03400h`). `0340h` is `REL_SYSSEG`, not the initial DOS load segment. This beta
retains that known-working setting; it does not retry `00B0h` or claim a proven
low-memory conflict.

## Install and collect results

Download `hp200lx-release3.5.2-beta1.zip` and copy its entire `ELKS352` directory
to `C:\ELKS352`. Keep `C:\ELKS35` and `C:\ELKS351` as fallbacks. Use the same
working ELKS CF root card and DOS configuration, including `STACKS=0,0`.
From fresh DOS outside System Manager:

```text
C:
CD \ELKS352
RUN352B1
```

Keep `ROOT092` and `BTGVDX.COM`: the legacy loader still uses them. A loader
`ROOTEND=8C00` message is expected even though the kernel RAMdisk driver is absent.
Look for `HPR352B1 ROM`, the `HPBOOT` line, `/dev/cfa1` mounting and the shell.
Photograph the boot screen, then run:

```sh
ls /
cat /etc/issue
meminfo
```

Photograph all three `HPST` lines and the memory figures. Repeat normal typing,
key repeat, zoom/panning and `ls`/`cat` reads; run `meminfo` again. Then exercise a
busy user process while using the keyboard and zoom/panning:

```sh
while :; do :; done
```

Use Ctrl-C to stop, then run `meminfo` again. If Ctrl-C fails, record that and
reboot; do not infer that both stack paths were measured. We need nonzero `n`
for **both** task and IRQ records. The counters provide coverage evidence;
workload names alone do not establish which path ran. Further testing can add
longer runs and representative applications once the initial results look good.

The report is printed on the kernel console; redirecting `meminfo` stdout does
not reliably capture it. Photos are the primary evidence for this beta.
If boot fails, retain `C:\ELKS352\HP352B1.TXT` and photograph the last screen.
Fallback after reboot to DOS: `CD \ELKS351` / `RUN351B1`, or stable
`CD \ELKS35` / `RUNR35`.

## Reading HPST

| Field | Meaning |
| --- | --- |
| `task` / `irq` | Current task kernel stack / shared interrupt stack |
| `n` | Measured ROM calls; saturates at 65,535 while peaks keep updating |
| `entry` | Largest use at bridge entry, before its saved registers and probe metadata |
| `used=X/Y` | Deepest written watermark from stack top, including pre-existing use and probe; Y is capacity |
| `rom` | Deepest written watermark below the probe metadata, including the six-byte fake interrupt frame and any nested work on that stack |
| `guard` | Sticky hexadecimal flags: 1 = bad before ROM, 2 = bad after ROM; 3 = both observed |
| `unknown` | Saturating count of calls with unrecognized, odd or near-exhausted bounds that used the plain bridge without painting |

Peaks are independent and may come from different calls. They reset only on
reboot. `used` is not a measurement of ROM code alone. Treat any nonzero `guard`
or `unknown` as a failed diagnostic run: photograph it and return to the working
beta before further stress testing. A zero count means no measurements for that
stack, not zero usage.

This measures **written locations**, not the lowest transient SP: untouched
allocated space, writes equal to the marker, other IRQ-only paths and firmware
using a separate SS can escape measurement. Stack guards also cannot detect every
possible overwrite. The kernel ABI requires DS=SS; a mismatch bypasses the probe
without touching its globals. No such bypass is counted in `unknown`.
The probe paints/scans on every measured call, adding interrupt latency and
changing timing; report any new lag or keyboard regression. Guard success and
small peaks do not prove an absolute worst case or justify a smaller stack by
themselves. A future stack-size experiment should follow real HP measurements.

## Build and validation

Kernel `K352B1`: **62,624 bytes**, SHA-256
`32a162b2ecbd1b307f19ceb2c970aed4c5b94402adff848f6a15255845f898b1`.
Compared with 3.5.1 beta 1, the image grows 592 bytes (near text +384, initialized
data +208); BSS grows 32 bytes. Far text and relocation sizes are unchanged.
The image remains 696 bytes smaller than stable 3.5; this diagnostic is not a
further space-saving release.

- Linux/IA16 GCC 6.3 build passes; image/header, segment limits, no-RAMdisk and
  networking-off checks pass. Shared guard position and stack size verified.
- 14 platform/mock cases cover existing handoff behavior, guard initialization,
  relocation reporting, statistics formatting and interrupt-flag restoration.
- Seven new Unicorn tests execute the freshly linked production probe: both
  stack types, exact synthetic depths, live-data preservation, nested calls,
  corrupt guards, unknown bounds, count saturation and register preservation.
- Seven existing firmware ABI/snapshot tests pass. Separately recompiling with
  diagnostics off produces the original bridge bytes; platform C also compiles.
- DOS helper copy/readback, eight injected errors and six wrong-size cases pass.
  HP/non-HP/PC98 relocation checks, patch reconstruction and ZIP checks pass.

These tests use a synthetic ROM and do not emulate a complete HP boot or measure
real ROM stack demand. Hardware results for this beta remain pending.

The source kit includes pinned upstream
`69dfd4f274139ef1f533c646711db84902b0cfe4`, five incremental patches, the exact
configuration, helper source, tests and linked fixtures. Patch 5 contains these
diagnostics and version labels; patches 1–4 retain their earlier provenance.
The [Release 3.5 architecture and credits](https://github.com/l00nix/elks-on-hp200lx/blob/hp200lx-release-3.5/docs/hp200lx/RELEASE3.5.md)
continue to apply.

On Linux with the ELKS IA16 toolchain at `BASE/cross`, from the source kit:

```sh
BASE=/path/to/elks WORK=/new/build/path bash build.sh
bash tests/build_stack_fixture.sh /new/build/path
bash tests/check_diag_off.sh /new/build/path
nasm -f bin B352COPY.ASM -o B352COPY.COM
python3 verify_kernel.py /new/build/path
python3 tests/run_platform.py
python3 tests/test_stack.py
python3 test_abi.py
python3 test_fwcopy.py
python3 test_load_base.py /new/build/path/elks/include/linuxmt/config.h
```

Emulator tests require Python's `unicorn` package. `VALIDATION.json` records
binary sizes and digest. Stable 3.5 and earlier beta downloads remain unchanged.
