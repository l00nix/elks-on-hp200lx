# HP 200LX Release 3.5.2c — full task-stack ROM coverage

**Diagnostic prerelease. Initial HP stack measurements received. Stable 3.5 remains stable.**

Follow-up photo 25825 records **over 1,000 task measurements** and task/shared
written peaks **202/700 and 224/1,024 bytes**; both ROM-region peaks are 168 bytes.
Shared measurements are 481 from 15,392 calls. Both guards and `unknown` remain
zero, with 376K free. The user confirms zoom, panning and speed seem fine.
The exact busy-loop/Ctrl-C procedure is not yet confirmed; these are observed
peaks, not worst-case guarantees. [Hardware evidence](https://github.com/l00nix/elks-on-hp200lx/blob/codex/hp200lx-release-3.5.2c/docs/hp200lx/hardware-results/2026-09-28-3.5.2c-meminfo.md).


3.5.2b restored faster screen output with one-in-32 sampling. Photo 25823 recorded
16 task-stack calls but only one measured sample; the shared path had 4,082 calls
and 128 samples. This beta targets the small task stack raised by Greg Haerr.

## Change from 3.5.2b

Every recognized task-stack ROM IRQ2 call now gets a written-depth measurement.
The shared stack still measures its first valid call, then calls 33, 65, etc.
Guard checks before and after ROM remain active on every valid call. Stack
sizes stay **700 bytes task / 1,024 bytes shared**. The final relocation segment
remains **0340h**; HPBOOT retains initial 0100h and staging 1400h. RAMdisk and
networking remain disabled. DOS-style ON/OFF suspend remains unsupported.

The third HPST line now says **`sample=all/32 guard=each`**: all task calls,
one in 32 shared calls. Task `n` should equal task `calls` until both saturate
at 65,535. Shared `n` grows once per 32 valid calls, starting with the first.
Counters saturate but measurements, guards and peak updates keep working.
Other HPST fields retain their earlier meanings: `used` is the deepest written
location from stack top, `rom` is the written depth below probe metadata,
`entry` is the peak bridge-entry use across valid calls, and `unknown` counts
rejected bounds. Peaks may come from different calls.

Measured calls add six bytes of probe metadata; skipped shared calls add four
for guard checking. The existing register saves and fake interrupt frame remain.
Every task call is measured, but this is still a written-watermark measurement,
not proof of all stack-pointer movement or an absolute worst case. Untouched
allocations, marker-value writes and a different firmware SS can escape it.
Shared sampling can miss rare peaks. Guards cannot catch every possible overwrite.
The `guard=each` label refers to recognized valid bounds; DS/SS mismatch bypasses
statistics, and unknown/odd/too-low bounds increment `unknown` and use the plain
bridge. No stack-size reduction is made in this test.

## Install and test

Download **hp200lx-release3.5.2c.zip**. Copy the complete **ELKS352C** folder to
**`C:\ELKS352C`**, including the final C. Keep ELKS352B and earlier working
folders. Use the existing ELKS CF root card and DOS configuration including
`STACKS=0,0`; no CF rewrite or userland update is required.

From fresh DOS outside System Manager:

```text
C:
CD \ELKS352C
RUN352C
```

Kernel/banner: `K352C` / `HPR352C ROM`. Keep ROOT092 and BTGVDX.COM: the legacy
loader still needs them. ROOTEND=8C00 is expected. If boot fails, photograph
the last screen and retain `HP352C.TXT`.

1. Check output speed with `ls /` and `cat /etc/issue`, then keyboard, zoom and
   panning. Run `meminfo` and photograph all four HPST lines and memory figures.
2. Confirm `sample=all/32`; task `n` and task `calls` should match. Repeat normal
   typing and file reads, then another `meminfo` to collect more task samples.
3. If normal use works, run `while :; do :; done`, use typing/zoom/panning while
   it runs, stop with Ctrl-C, then run `meminfo` again. Note if Ctrl-C fails.

The busy user loop is intended to exercise IRQ2 arriving during user execution,
which uses the task kernel stack. Actual growing task counters establish
coverage. Full task probing can slow CPU-bound workloads; report new lag or
screen-output regressions instead of assuming 3.5.2b's speed is guaranteed.
The many shared calls remain sampled to limit ordinary diagnostic overhead.

If `guard` or `unknown` is nonzero, photograph and return to the working fallback
before further stress. To use 3.5.2b again, reboot to DOS and run `RUN352B` from
`C:\ELKS352B`; stable fallback is `C:\ELKS35` / `RUNR35`. The HPST output uses
the kernel console, so redirected meminfo stdout may not capture it.

## Build and validation

`K352C`: **62,768 bytes**, SHA-256 `c07b3aa614afd5693a3f23a5a3aeccd503e55733e0b3f1e26a4cd61db6b69d76`.

- Clean Linux/IA16 GCC 6.3 kernel build; natural image/header, segment bounds,
  guard placement, RAMdisk-absent and networking-disabled checks pass.
- 12 production-assembly emulator tests pass, including every-task/one-in-32
  shared cadence through 65 calls, task phase bypass, counter saturation,
  exact synthetic depths, nested measured calls, ABI preservation, unknown
  bounds and guards on measured/skipped paths.
- 14 platform/mock cases and seven existing ABI/snapshot cases pass.
- Diagnostic-off assembly matches the earlier uninstrumented bridge bytes;
  diagnostic-off platform C compiles.
- DOS copy/readback, injected file errors and wrong-size rejection, relocation
  checks, patch reconstruction, DOS names/CRLF and ZIP validation pass.

Synthetic ROM tests validate the probe, not the real HP ROM's worst-case demand
or hardware performance. Those remain hardware-test questions.

The source ZIP includes upstream `69dfd4f274139ef1f533c646711db84902b0cfe4`, seven
incremental patches, exact configuration, DOS helper source, tests and fixtures.
Patch 7 changes task sampling and release labels. Earlier release assets stay
unchanged. The [Release 3.5 architecture and credits](https://github.com/l00nix/elks-on-hp200lx/blob/hp200lx-release-3.5/docs/hp200lx/RELEASE3.5.md)
continue to apply.

From the source kit on Linux with the ELKS IA16 toolchain under `BASE/cross`:

```sh
BASE=/path/to/elks WORK=/new/build/path bash build.sh
bash tests/build_stack_fixture.sh /new/build/path
bash tests/check_diag_off.sh /new/build/path
nasm -f bin B352CCPY.ASM -o B352CCPY.COM
python3 verify_kernel.py /new/build/path
python3 tests/run_platform.py
python3 tests/test_stack.py
python3 test_abi.py
python3 test_fwcopy.py
python3 test_load_base.py /new/build/path/elks/include/linuxmt/config.h
```

Emulator tests require Python Unicorn. VALIDATION.json contains build metrics.
Only the boot ZIP is uploaded to captainfuture; source/checksums remain on GitHub.
