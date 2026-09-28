# HP 200LX Release 3.5.2b — sampled ROM stack diagnostics

**Diagnostic prerelease. Initial HP results show faster output and zero reported guard errors. Stable 3.5 remains the fallback.**

Initial hardware result (photo 25823): screen output is reported faster again.
Task/shared sampled peaks are 82/700 and 222/1,024 bytes, with sample counts
1/128 from 16/4,082 valid calls. Both guards and `unknown` are zero; meminfo
reports 79/455K used and 376K free. This supports the overhead explanation but
is not a timed benchmark or a worst-case stack result. [Recorded evidence](https://github.com/l00nix/elks-on-hp200lx/blob/codex/hp200lx-release-3.5.2b/docs/hp200lx/hardware-results/2026-09-28-3.5.2b-meminfo.md).


The previous 3.5.2 beta booted and supported keyboard, zoom/panning and meminfo,
but screen output became much slower. Photo 25821 recorded task/shared written
peaks of 80/700 and 282/1,024 bytes, with zero guard flags and `unknown=0`.
Painting/scanning every ROM call was the leading explanation for that slowdown;
no controlled timing measurement has established the cause.

## What changes

This build measures the **first valid ROM call on each stack, then every 32nd
call** (calls 1, 33, 65, ...). Task and shared stacks have independent sampling
phases. Every recognized call still checks its guard before and after ROM and
updates the entry-depth peak. Calls that skip sampling do no watermark painting
or scanning. Sampling continues even after counters saturate at 65,535.

`meminfo` now prints **four HPST lines**. The first two retain `n` as the number
of measured samples, `used` and `rom` as sampled written peaks, `entry` as the
entry peak across valid calls, and `guard` as sticky corruption flags. The new
line shows total valid calls for each stack and `sample=1/32 guard=each`.
The final line retains the rejected-bounds `unknown` count. All counters saturate;
peaks and sampling continue. These are since-boot figures.

Measured calls add six bytes of probe metadata; skipped calls use four bytes
for post-ROM guard checking. The bridge's existing saved registers and fake
interrupt frame remain. A skipped call can update `entry` or `guard` without
changing `n`, `used` or `rom`. `n=0` means no measured samples, not zero usage.

Task stacks remain **700 bytes**, the shared interrupt stack **1,024 bytes**,
and final relocation `REL_SYSSEG` **0340h**. HPBOOT still reports initial `0100h`,
staging `1400h`, final `0340h` (hexadecimal segments). RAMdisk and networking
remain disabled. DOS-style ON/OFF suspend remains unsupported.

## Install and test

Download **hp200lx-release3.5.2b.zip**. Copy its complete **ELKS352B** folder to
`C:\ELKS352B`; keep ELKS351 and ELKS352 for comparisons and ELKS35 as stable
fallback. Use the existing CF root card and working DOS configuration, including
`STACKS=0,0`. No CF rewrite or new userland program is needed.

From fresh DOS outside System Manager:

```text
C:
CD \ELKS352B
RUN352B
```

Keep ROOT092 and BTGVDX.COM. The legacy loader still needs both, and its
ROOTEND=8C00 message remains expected. The kernel/banner is `K352B` / `HPR352B ROM`.
If boot fails, photograph the last screen and retain `HP352B.TXT`.

1. Compare boot and `ls /` / `cat /etc/issue` output speed with the prior beta.
2. Check keyboard, zoom and panning, then run `meminfo` and photograph all four
   HPST lines and the memory summary.
3. Repeat normal typing, key repeat, display controls and file reads, then
   `meminfo` again. Both task and shared `n` must be nonzero for sampled coverage.
4. If normal use is working, run `while :; do :; done`, exercise typing/zoom,
   stop with Ctrl-C and run `meminfo` again. If Ctrl-C fails, note it and reboot.

Report whether screen output is back to the earlier speed, improved but still
slow, or unchanged. This is a hardware comparison; emulator instruction counts
are not a prediction of HP elapsed time. If `guard` or `unknown` is nonzero,
photograph the report and return to the working beta before further stress.
Fallback from fresh DOS: `CD \ELKS351` then `RUN351B1`, or `CD \ELKS35` then
`RUNR35`. HPST prints on the kernel console; stdout redirection may not capture it.

## Limits of the measurements

Sampling may miss rare peaks or align with periodic firmware activity. A lower
peak than the previous beta does **not** establish reduced ROM stack demand.
Written watermarks also miss unwritten allocations, marker-value writes and
firmware using a different SS. Guards cannot detect every possible overwrite.
The probe still changes interrupt latency and adds stack usage. This is not a
worst-case proof or a justification for reducing either stack.

The kernel ABI requires DS=SS. Mismatches use the plain bridge without accessing
the statistics; they are not included in `unknown`. Unknown, odd or too-low
bounds increment `unknown` and bypass painting and the bounded guard path.
The `guard=each` label refers to calls with recognized valid bounds.

No probe-off switch is added in this test. Comparison against 3.5.2 beta 1 tests
whether reducing scan frequency improves output; it does not isolate all probe
costs. A controlled probe-off comparison remains a possible follow-up.

## Build and validation

Kernel size: **62,736 bytes**. SHA-256: `d34a16e5fd3ffb3d059e303f1ce5df2444571a52eaea6972b28bb34b75644837`.
The binary remains below the DOS helper's 64 KiB limit, without padding.

- Clean Linux/IA16 GCC 6.3 build; kernel header, symbol/segment, shared-guard
  placement, RAMdisk-absent and networking-disabled checks pass.
- 14 platform/mock cases, including the new call-count report, pass.
- 11 production-assembly emulator tests cover ABI, both stack types, depth,
  bounds, nested measured calls, guard corruption on measured/skipped calls,
  cadence through two sample intervals, counter saturation and unused memory.
- A synthetic shared-stack call executes 3,020 instruction-hook events when
  measured and 75 when skipped. This verifies a shorter path, not hardware
  timing or a measured screen-speed improvement.
- The diagnostic-off bridge still matches the previous uninstrumented bytes;
  diagnostic-off platform C compiles. Seven existing ABI/snapshot cases pass.
- DOS copy/readback and injected file-error/wrong-size cases, relocation checks,
  patch reconstruction and ZIP checks pass. Initial HP results are recorded above;
  longer stress testing remains pending.

The source ZIP contains pinned upstream `69dfd4f274139ef1f533c646711db84902b0cfe4`,
six incremental patches, exact configuration, DOS helper source and tests.
Patch 6 adds sampling and new labels to the 3.5.2 diagnostic implementation.
The original release assets remain unchanged. The
[Release 3.5 architecture and credits](https://github.com/l00nix/elks-on-hp200lx/blob/hp200lx-release-3.5/docs/hp200lx/RELEASE3.5.md)
continue to apply.

On Linux with the ELKS IA16 toolchain in `BASE/cross`, from the extracted source kit:

```sh
BASE=/path/to/elks WORK=/new/build/path bash build.sh
bash tests/build_stack_fixture.sh /new/build/path
bash tests/check_diag_off.sh /new/build/path
nasm -f bin B352BCPY.ASM -o B352BCPY.COM
python3 verify_kernel.py /new/build/path
python3 tests/run_platform.py
python3 tests/test_stack.py
python3 test_abi.py
python3 test_fwcopy.py
python3 test_load_base.py /new/build/path/elks/include/linuxmt/config.h
```

Python emulator tests require Unicorn. `VALIDATION.json` records build metrics.
