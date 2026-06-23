# HP 200LX PCMCIA/CF Disk Notes

Release 3 work starts from the confirmed Release 2 internal-keyboard build and focuses on making the CF card visible from inside ELKS.

## Starting Point

- Hardware: HP 200LX, stock clock, 4 MB RAM.
- Storage: 48 MB CF card through a CF-to-PCMCIA adapter.
- DOS setup: DOS 5 / FAT.
- Known-good ELKS base: `hp200lx-release-2`.
- Release 2 boots to an ELKS shell and the internal HP 200LX keyboard works.

## Current Problem

The DOS loader chain can use the CF card before ELKS starts, but ELKS does not currently see it as a persistent hard disk after boot. This blocks a native/persistent setup and keeps Release 2 dependent on a RAM-root filesystem.

## First Hypothesis: INT13 Handler Overwritten at 0x9000

The Richard Dubs / MINIX-on-HP-200LX boot chain installs a custom INT13 handler for the card/RAM-disk path. In the current Release 2 boot sequence:

```text
CARDIO
DEBUG < VECT13.DAT
PUT13
MKINTS
BTGVDX
```

`VECT13.DAT` points INT13 at `9000:0000`, and `PUT13` loads the handler there.

ELKS setup code later relocates itself to the highest 64 KB-aligned segment below conventional memory top. On a 640 KB-class machine, that target is `0x9000`. If the setup relocation copies over `9000:0000`, the INT13 vector still points to `9000:0000`, but the handler bytes have been replaced by ELKS setup code.

That would explain why the card is usable before ELKS starts but disappears once ELKS is running.

## R3D1 Diagnostic

The first diagnostic keeps the Release 2 kernel unchanged and only changes the DOS-side boot sequence:

```text
CARDIO
DEBUG < VECT13.DAT
PUT13
DEBUG < COPY80.DAT
DEBUG < VECT80.DAT
DEBUG < CHK80.DBG
MKINTS
BTGVDX
```

New files:

```text
COPY80.DAT  copy 0x500 bytes from 9000:0000 to 8000:0000
VECT80.DAT  repoint INT13 vector 0000:004c to 8000:0000
CHK80.DBG   dump INT13 vector and first handler bytes at 8000:0000
RUNR3D1.BAT run the diagnostic boot sequence
```

Expected `CHK80.DBG` output:

```text
0000:004C  00 00 00 80
8000:0000  <non-zero handler bytes>
```

R3D1 test result:

- `CHK80.DBG` showed the INT13 vector repointed to `8000:0000`.
- ELKS still booted to the shell, so the DOS-side relocation did not break the boot path.
- `fdisk -l` still failed with `Error opening /dev/hda`.

This did not disprove the 0x9000 overwrite theory, but it showed that the Release 2 kernel could not test the BIOS hard-disk path because it was built without the BIOS hard disk block driver.

## R3D2 Diagnostic

R3D2 keeps the R3D1 DOS-side INT13 relocation and changes the kernel:

- `CONFIG_BLK_DEV_BHD=y`
- `CONFIG_IDE_PROBE` remains disabled
- `arch/i86/drivers/block/bios.c` prints small `R3D2 bioshd:` diagnostics around the INT13 AH=08 hard-disk parameter probe

The R3D2 kernel grew enough to land on an unproven BootELKS file phase. The linked kernel was therefore built at phase 40 and padded with 8 trailing zero bytes in the DOS package so the file presented to BootELKS lands at phase 48, the same proven phase used by Release 2. No kernel bytes were truncated.

R3D2 expected observations:

- ELKS should still boot to the shell.
- Boot output should include `R3D2 bioshd:` lines.
- `fdisk -l` should be tested again.

Useful outcomes:

- If `R3D2 bioshd:` reports a plausible drive count and `/dev/hda` appears, the BIOS INT13 path is viable.
- If the probe reports an INT13 error or zero drives, the relocated handler may not be sufficient or may not support the ELKS call pattern.
- If the system hangs during the probe, the next diagnostic should avoid automatic BIOSHD registration and use a smaller manual INT13 test path.

R3D2 test result:

- The vector check still showed `0000:004c` pointing to `8000:0000`.
- The boot did not reach ELKS. It stopped at the DOS `PAUSE` line in `RUNR3D2.BAT` after `CHK80.DBG`.

## R3D3 Diagnostic

R3D3 keeps the R3D2 kernel and DOS INT13 relocation sequence unchanged, but removes the DOS `PAUSE` after `CHK80.DBG`. This tests whether the stop was only the launcher pause rather than the BIOSHD probe kernel.

R3D3 test result:

- The loader got past the DOS batch file and entered `BTGVDX`.
- It read the image and root filesystem, then stopped at `Press key for quiet copy/jump`.
- That prompt is inside the loader's copy/jump path; the keyboard wait has already been patched out in this loader, so this is likely another image layout/copy cliff rather than a true key wait.
- R3D3 used an 8-byte trailing file pad to force file phase 48. That may have reintroduced a file/header consistency problem similar to earlier post-build padding failures.

## R3D4 Diagnostic

R3D4 keeps the same BIOSHD kernel content and no-pause launcher, but uses the natural linked kernel image with no trailing file padding:

- `KERNBOP` size: 67112 bytes
- loader phase: 40

This tests whether the R3D3 copy/jump stop was caused by the post-build file pad rather than the BIOSHD probe itself.

R3D4 test result:

- The boot stopped at the same `Press key for quiet copy/jump` line.
- Since the file padding was removed, the stop is not explained by trailing post-build bytes.
- The leading hypothesis is now that enabling BIOSHD pushed the kernel image over a 64 KiB boundary that the current BootELKS/BTGVDX copy/jump path does not survive.

## R3D5 Diagnostic

R3D5 keeps the same DOS-side INT13 relocation sequence but trims the BIOSHD kernel below 64 KiB:

- `KERNBOP` size: 65024 bytes
- loader phase: 0
- `CONFIG_BLK_DEV_BHD=y`
- `CONFIG_IDE_PROBE` disabled
- Release 2 HP 200LX internal keyboard scanner retained
- nonessential pseudo-tty, TCP, parallel, and PS/2 mouse pieces removed for size

This tests whether the R3D2/R3D3/R3D4 stop was a loader/copy cliff caused by the image crossing 64 KiB.

R3D5 test result:

- The trimmed BIOSHD kernel booted into the ELKS shell.
- This strongly supports the theory that the R3D2/R3D3/R3D4 hang was caused by the BIOSHD-enabled kernel crossing a loader/copy boundary near 64 KiB.
- `fdisk -l` still failed with `Error opening /dev/hda`.
- That means BIOSHD still did not expose a usable `/dev/hda`; either the INT13 hard-disk parameter probe found zero hard disks, or `/dev/hda` remained invalid at open time.

## PCMCIA / ATA-CF Finding

This ELKS tree does not appear to include a native PCMCIA/Card Services stack. Storage paths relevant to the HP 200LX are:

- BIOS INT13 hard disk support: `CONFIG_BLK_DEV_BHD`
- direct ATA-CF support: `CONFIG_BLK_DEV_ATA_CF`

For the HP 200LX, the likely model is still that DOS-side `CARDIO` initializes the PCMCIA socket and maps the CF card into ATA-compatible I/O space before ELKS starts. ELKS can then either call a BIOS/INT13 handler or try talking to the ATA ports directly.

## R3D6 Diagnostic

R3D6 tests the direct ATA-CF path:

- `CONFIG_BLK_DEV_BHD` disabled
- `CONFIG_BLK_DEV_ATA_CF` enabled
- ATA mode forced to standard ATA mode at ports `0x1f0/0x3f6`
- Dubs INT13 handler not loaded or relocated
- `CARDIO` still runs before ELKS
- `KERNBOP` size: 65464 bytes

Because BIOSHD is disabled in this diagnostic, `/dev/hda` is not the target device. Test `/dev/cfa` instead.

R3D6/R3D7 loader follow-up:

- R3D6 appeared to hang during boot. Its package intentionally had fewer files
  than earlier diagnostics because it removed the Dubs INT13 helper chain, but
  its image phase was suspect.
- R3D7 kept the same direct ATA-CF idea, restored the alternate loader in the
  package, and changed image layout while staying below 64 KiB.
- R3D7 got past the loader and printed:

```text
rd: 360K ramdisk at 3200:0000
```

then hung.

That stop point is past the DOS loader and into ELKS block-device init. The
leading hypothesis is that the upstream ATA-CF driver's `delay_10ms()` and
`ata_wait()` use `jiffies()` for timeouts. On the HP 200LX, kernel timer ticks
do not advance in this boot path, so an ATA reset delay or busy wait can spin
forever.

## R3D8 Diagnostic

R3D8 keeps the R3D6/R3D7 direct ATA-CF configuration but removes the jiffies
dependency from the ATA-CF probe path:

- `CONFIG_BLK_DEV_BHD` disabled
- `CONFIG_BLK_DEV_ATA_CF` enabled
- ATA mode forced to standard ATA mode at ports `0x1f0/0x3f6`
- `ata.c` `delay_10ms()` replaced with a bounded CPU loop
- `ata.c` `ata_wait()` replaced with a bounded port-poll loop
- Timeout should print:

```text
cf: wait timeout st=XX
```

R3D8 test result:

- ELKS booted to the shell.
- This confirms the R3D7 hang was very likely caused by the jiffies-based ATA
  wait path rather than by the loader.
- The standard ATA probe still did not find the CF card:

```text
cf: wait timeout st=ec
cfa: ATA at 1f0/3f6 xtide=0,0 not found (-6)
cf: wait timeout st=ec
cfb: ATA at 1f0/3f6 xtide=0,0 not found (-6)
```

The `st=ec` byte is suspicious because `0xec` is also the ATA IDENTIFY command
byte. This suggests the standard ATA port pair may not match how `CARDIO`
leaves the HP 200LX PCMCIA CF card mapped.

## R3D9 Diagnostic

R3D9 keeps the successful R3D8 no-jiffies ATA wait path but stops forcing
standard ATA mode:

- `CONFIG_BLK_DEV_BHD` disabled
- `CONFIG_BLK_DEV_ATA_CF` enabled
- ATA mode left as AUTO
- `ata.c` bounded CPU-loop delay retained
- `ata.c` bounded port-poll wait retained

On an 8086/8088-class system, the ELKS ATA-CF AUTO path should choose the
XTCF-style port mapping instead of standard `0x1f0/0x3f6`. This tests whether
the 200LX/CardIO combination exposes the CF card on the alternate port path
that ELKS already knows how to probe.

R3D9 test result:

- ELKS booted to the shell.
- `fdisk -l /dev/cfa` failed with `Error opening /dev/cfa`.
- The ATA-CF probe still used standard ATA:

```text
cfa: ATA at 1f0/3f6 xtide=0,0 not found (-6)
cfb: ATA at 1f0/3f6 xtide=0,0 not found (-6)
```

That means AUTO did not select XTCF on this build. The likely reason is that
the kernel reports the HP 200LX as PC/AT class CPU 5, while upstream ATA-CF
AUTO only chooses XTCF when `arch_cpu < CPU_80286`.

## R3D10 Diagnostic

R3D10 is the same direct ATA-CF path as R3D9, but with ATA-CF mode forced to
XTCF:

- `CONFIG_BLK_DEV_BHD` disabled
- `CONFIG_BLK_DEV_ATA_CF` enabled
- ATA mode forced to `3`
- R3D8/R3D9 no-jiffies ATA delay/wait fix retained

Expected boot line:

```text
cfa: ATA at 300/31c xtide=3,1 ...
```

If this still does not find the card, the next step should be a raw I/O port
dump/scanner after `CARDIO` rather than guessing more ATA-CF modes.

R3D10 test result:

- ELKS booted to the shell.
- `fdisk -l /dev/cfa` failed with `Error opening /dev/cfa`.
- The ATA-CF probe did move to the forced XTCF path:

```text
cfa: ATA at 300/31c xtide=3,0 not found
cfb: ATA at 300/31c xtide=3,0 not found
```

This means both known ELKS ATA-CF paths have missed the card:

- standard ATA: `1f0/3f6`, `xtide=0,0`
- forced XTCF: `300/31c`, `xtide=3,0`

The next diagnostic should therefore happen before ELKS starts probing the ATA
device.

## R3D11 Diagnostic

R3D11 is a DOS-side raw I/O dump:

- run `CARDIO`
- run `IODUMP.COM`
- write the result to `IODUMP.TXT`

This avoids ELKS and dumps likely ATA/PCMCIA I/O windows immediately after
`CARDIO` configures the card.

Ranges dumped:

- `1f0-1ff`, `3f0-3ff`
- `170-17f`, `370-37f`
- `300-31f`, `320-33f`
- `180-19f`, `200-21f`, `220-23f`, `240-25f`

The desired test artifact is the text file `IODUMP.TXT` copied back from DOS.

R3D11 test result:

- `IODUMP.TXT` was successfully created.
- The output showed a suspicious repeated `3B` pattern across nearly all dumped
  ports, with occasional `63`/`53` bytes.
- Reviewing `IODUMP.ASM` found a bug: the hex-print helper clobbered `DX`,
  which is also the I/O port register used by `in al, dx`.
- Therefore only the first byte of each dumped range should be considered
  trustworthy.

## R3D12 Diagnostic

R3D12 is the corrected version of R3D11:

- same DOS-side `CARDIO` then `IODUMP.COM` sequence
- `IODUMP.COM` now preserves `DX` while printing hex bytes
- expected output file remains `IODUMP.TXT`

The desired test artifact is the corrected `IODUMP.TXT`.

R3D12 test result:

- `IODUMP.TXT` was successfully created and copied back.
- The corrected dump looked internally valid: bytes at `3f8-3ff` resembled a
  real serial UART register block, which confirms the dumper was reading real
  port values.
- The likely ATA/CF candidate ranges were still mostly the repeated `3B`
  background/open-bus value:

```text
1f0-1ff  mostly 3B
170-17f  mostly 3B, with one 53
300-31f  mostly 3B, with one 63 at 300
320-33f  mostly 3B, with one 63
180-19f  mostly 3B, with two 63 bytes
200-25f  all 3B in the sampled windows
```

This strongly suggests that after `CARDIO`, the CF card is not exposed as a
simple ATA I/O window at any of the tested standard, secondary, XTCF, or common
PCMCIA-style candidate ranges. The direct ELKS ATA-CF path is therefore less
promising than the Dubs INT13 path.

## R3D13 Diagnostic

R3D13 is a DOS-side INT13 capability probe. It does not boot ELKS.

It writes `I13DUMP.TXT` and tests:

- the current INT13 vector
- BIOS fixed disk count at `0040:0075`
- INT13 `AH=00` reset
- INT13 `AH=08` drive parameters
- INT13 `AH=15` disk type
- INT13 `AH=41` extensions check
- INT13 `AH=02` read of CHS `0/0/1`

The bundle includes three variants:

```text
R3D13A.BAT  CARDIO, then probe current/default INT13
R3D13B.BAT  CARDIO, PUT13 at 9000:0000, then probe INT13
R3D13C.BAT  CARDIO, PUT13 copied to 8000:0000, then probe INT13
```

Useful outcomes:

- If `AH=02` can read sector 0 but `AH=08` fails, then the Dubs handler may be
  usable for raw reads but not for ELKS BIOSHD autodetection. A manual geometry
  fallback in ELKS BIOSHD may be needed.
- If `AH=08` and `AH=02` both work through the 8000 handler, then the next ELKS
  diagnostic should instrument why `CONFIG_BLK_DEV_BHD` did not register
  `/dev/hda`.
- If the 9000 handler works but the 8000 copy does not, then the handler is not
  position-independent and cannot simply be moved below ELKS setup relocation.
- If none of the variants can read drive `80h`, the Dubs path may require a
  different precondition than `CARDIO` + `PUT13`, or the card may only be
  available through DOS-level services rather than BIOS INT13.

R3D13 test result:

- `R3D13A.BAT` produced `I13DUMP.TXT`.
- The default BIOS/DOS INT13 path returned `CF=1 AH=80` for reset, parameters,
  disk type, extensions check, and sector read on drives `80h`, `81h`, and
  `00h`. That means the stock path does not expose the PCMCIA/CF card as an
  INT13 fixed disk after `CARDIO`.
- `R3D13B.BAT` and `R3D13C.BAT` both appeared to stop immediately after
  printing `Drive DL=80`.
- Reviewing `I13DUMP.ASM` found that the INT13 vector and BDA disk count
  printouts were wrong: the code switched `DS` to low memory and then stored
  the results through that low-memory segment instead of restoring `DS` first.
  The actual INT13 call results from `R3D13A` remain useful, but the printed
  vector/BDA lines do not.
- The stop point in `R3D13B/C` is likely the first INT13 call made by the
  probe, `AH=00` reset. The Dubs handler may not implement reset/parameter
  services, or may not tolerate the call sequence used by the probe.

## R3D14 Diagnostic

R3D14 is a narrower DOS-side INT13 direct-read probe:

- fixes the R3D13 INT13 vector/BDA print bug
- prints the true INT13 vector
- prints the first 16 bytes at the active INT13 vector
- skips `AH=00`, `AH=08`, `AH=15`, and `AH=41`
- tries only one read-only sector read: `INT13 AH=02`, `DL=80`, CHS `0/0/1`

The bundle includes three 8.3-safe batch files:

```text
R3D14A.BAT  CARDIO, then probe current/default INT13 direct read
R3D14B.BAT  CARDIO, PUT13 at 9000:0000, then direct read
R3D14C.BAT  CARDIO, PUT13 copied to 8000:0000, then direct read
```

Useful outcomes:

- If `R3D14B` or `R3D14C` reads sector 0 successfully, the Dubs handler likely
  supports raw reads but not the reset/geometry calls used by normal BIOSHD
  probing.
- If the screen shows a valid `9000:0000` or `8000:0000` vector and handler
  bytes, then hangs at `About to call INT13 AH=02`, the Dubs handler is entered
  but does not complete even for a direct read in this setup.
- If the vector/handler bytes are wrong before the read, the DOS-side
  installation sequence must be fixed before returning to ELKS.

R3D14 test result:

- `R3D14A` returned from the default BIOS INT13 handler with `CF=1 AH=80`, again
  confirming the stock BIOS/DOS INT13 path does not expose the CF card.
- `R3D14B` and `R3D14C` showed the INT13 vector correctly set to `9000:0000`
  and `8000:0000`, respectively.
- However, the first bytes at those vector targets were zeros rather than real
  handler code.
- Reviewing the Dubs archive showed why: `PUT13.EXE` requires a separate
  payload file named `INT13.BIN`, and the ELKS diagnostic/release bundles had
  included `PUT13.EXE` but not `INT13.BIN`.
- Therefore previous `PUT13`-based diagnostics did not actually install the
  Dubs INT13 handler, even when the INT13 vector itself was changed.

## R3D15 Diagnostic

R3D15 repeats the R3D14 direct-read probe but includes the missing
`INT13.BIN` from the Dubs archive.

The bundle includes:

```text
CARDIO.EXE
PUT13.EXE
INT13.BIN
VECT13.DAT
COPY80.DAT
VECT80.DAT
I13RD.COM
```

Three 8.3-safe batch files are provided:

```text
R3D15A.BAT  CARDIO, then probe current/default INT13 direct read
R3D15B.BAT  CARDIO, PUT13 + INT13.BIN at 9000:0000, then direct read
R3D15C.BAT  CARDIO, PUT13 + INT13.BIN copied to 8000:0000, then direct read
```

Useful outcomes:

- `R3D15B` should show non-zero handler bytes at `9000:0000`.
- `R3D15C` should show the same handler bytes copied to `8000:0000`.
- If either variant returns from `AH=02` with `CF=0`, then the Dubs INT13
  read path is viable and ELKS can be adjusted around it.
- If `9000:0000` works but `8000:0000` fails, the handler is likely not
  position-independent and will need to be loaded directly at a safe address
  rather than copied after the fact.

R3D15 test result:

- The `R3D15C` screenshot showed the INT13 vector correctly set to
  `8000:0000`.
- The first bytes at `8000:0000` were real handler code:

```text
B9 8E 02 00 02 00 00 00 00 00 00 00 F0 01 ...
```

- This confirms that adding `INT13.BIN` allowed `PUT13` to install the real
  Dubs INT13 payload and that the `COPY80.DAT`/`VECT80.DAT` relocation path
  copied it to `8000:0000`.
- The probe then stopped at:

```text
About to call INT13 AH=02 DL=80 C0/H0/S1
```

- Therefore the real handler is entered for `DL=80`, but that direct read call
  did not return in this test.

## R3D16 Diagnostic

R3D16 repeats the R3D15 direct-read probe but uses `DL=81` instead of `DL=80`.

Reason: Dubs' `BIOS512.C` test tool uses:

```c
biosdisk(2, 0x81, head, cylinder, sector, 1, buffer);
```

while `WINI200.C` defaults to `0x80`. Since the existing `DL=80` direct read
hangs after entering the real handler, `DL=81` is the next least-invasive test.

Three 8.3-safe batch files are provided:

```text
R3D16A.BAT  CARDIO, then probe current/default INT13 with DL=81
R3D16B.BAT  CARDIO, PUT13 + INT13.BIN at 9000:0000, then DL=81 read
R3D16C.BAT  CARDIO, PUT13 + INT13.BIN copied to 8000:0000, then DL=81 read
```

## Test Notes to Capture

When testing `R3D16`, record or copy:

- `I13R81.TXT` after each variant
- which variant was run (`A`, `B`, or `C`)
- whether any variant hangs
- the last visible line if a variant hangs
- a photo of the output only if copying `I13R81.TXT` is inconvenient

## Open Questions

- Does ELKS call BIOS INT13 for `0x80` on this configuration?
- Does the Dubs handler expect to remain at `0x9000`, or is it position-independent enough to run at `0x8000`?
- Does `CARDIO` leave the CF card mapped to ATA-compatible I/O ports after ELKS starts?
- Does ELKS need a direct PCMCIA/ATA driver instead of relying on the BIOS/INT13 path?
