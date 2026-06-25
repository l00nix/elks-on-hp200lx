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

R3D16 test result:

- `R3D16A` used the stock INT13 vector `0070:0809`; the `DL=81` read returned
  `CF=1 AH=80`.
- `R3D16B` installed the Dubs INT13 handler at `9000:0000`; the first handler
  bytes were:

```text
E9 BE 02 00 02 00 00 00 00 00 00 00 00 F0 01 06
```

- `R3D16C` copied the same handler to `8000:0000`; the first handler bytes
  matched the `9000:0000` copy.
- With the PCMCIA/CF card inserted, both `R3D16B` and `R3D16C` stopped at:

```text
About to call INT13 AH=02 DL=81 C0/H0/S1
```

- After removing the PCMCIA/CF card, both tests returned and wrote output.
  They reported `CF=0 AH=01`, but the first 32 bytes of the destination buffer
  were all `53`.
- This is not a valid sector read. The useful conclusion is that the Dubs
  handler is present and entered, but it appears to wait indefinitely for ATA
  status while the card is inserted. Once the card is removed, the handler
  returns with floating/invalid bus data.

## R3D17 Diagnostic

R3D17 avoids INT13 reads and probes the Dubs/CardIO ATA port path directly with
bounded polling. This should identify which ATA status transition is missing
without hanging forever in the Dubs INT13 handler.

The bundle includes:

```text
CARDIO.EXE
PUT13.EXE
INT13.BIN
VECT13.DAT
COPY80.DAT
VECT80.DAT
ATADMPA.COM
ATADMPB.COM
ATADMPC.COM
BIOS512.EXE
```

Three 8.3-safe batch files are provided:

```text
R3D17A.BAT  CARDIO, then bounded direct ATA probe
R3D17B.BAT  CARDIO, PUT13 + INT13.BIN at 9000:0000, then bounded direct ATA probe
R3D17C.BAT  CARDIO, PUT13 + INT13.BIN copied to 8000:0000, then bounded direct ATA probe
```

Each variant writes a distinct output file:

```text
ATADMPA.TXT
ATADMPB.TXT
ATADMPC.TXT
```

The direct probe records:

- initial values read from `1F0-1F7` and `3F6`
- the status trace while selecting the drive
- a bounded `IDENTIFY` command (`EC`)
- a bounded sector read command (`20`) for `C0/H0/S1`
- the first 32 data bytes only if the card asserts DRQ

Expected useful outcomes:

- If status at `1F7` remains stuck with `BSY` set, the Dubs handler hang is
  explained by its unbounded busy-wait loop.
- If status never shows `DRQ`, the card is not reaching the ATA data-transfer
  phase at the Dubs/CardIO port mapping.
- If status shows `DRQ` and data is readable, the next step is to compare the
  direct probe command sequence with the Dubs INT13 handler sequence.

R3D17 test result:

- The user rebooted the HP 200LX between variants `A`, `B`, and `C`, which is a
  good clean-state test method for this work.
- None of the variants hung.
- All variants showed the same suspicious initial register pattern at the Dubs
  handler's hard-coded ATA window:

```text
Initial 1F0-1F7: 3B 3B 3B 3B 3B 3B 3B 3B   3F6: 3B
```

- `IDENTIFY EC` and `READ 20 C0/H0/S1` both ended with status `3B`, and the
  first 32 bytes read from the data port were also all `3B`.
- Variants with the Dubs INT13 handler installed or relocated did not change
  this pattern.
- This strongly suggests that the CF card is not actually visible at `1F0` in
  this test setup. A real ATA register window should not read as the same byte
  in every register before and after commands.

## R3D18 Diagnostic

R3D18 is a read-only I/O window scan. It does not issue ATA commands; it only
samples candidate I/O ranges to see whether `CARDIO` makes any plausible ATA
register block appear somewhere other than `1F0`.

Three 8.3-safe batch files are provided:

```text
R3D18A.BAT  scan before CARDIO
R3D18B.BAT  CARDIO, then scan
R3D18C.BAT  CARDIO + Dubs INT13 copied to 8000:0000, then scan
```

Each variant writes a distinct output file:

```text
IOSCANA.TXT
IOSCANB.TXT
IOSCANC.TXT
```

The scan records the BIOS fixed-disk count at `0040:0075`, then reads these
candidate base windows:

```text
1F0, 170, 1E8, 168, 180, 100, 120, 140, 160,
200, 220, 240, 300, 320, 340, 360
```

For each base it samples `base+0` through `base+7`, plus the corresponding
alternate-status/control port.

Useful outcomes:

- A base that changes after `CARDIO` is the most interesting candidate.
- A base whose registers are not all the same byte is more plausible than the
  repeated `3B` seen at `1F0`.
- If a plausible base appears, the next diagnostic should target only that base
  with bounded `IDENTIFY` and `READ` commands.

R3D18 test result:

- All three variants reported the BIOS fixed-disk count at `0040:0075` as
  `00`.
- The Dubs hard-coded ATA window stayed unmapped-looking in every variant:

```text
base 01F0 regs: 3B 3B 3B 3B 3B 3B 3B 3B  alt 03F6 = 3B
```

- The alternate candidate windows also mostly read as repeated `3B`.
- A few one-byte differences appeared in different places between runs
  (`63`, `BB`, `53`), but they were not stable across variants and did not
  form an ATA-like register block.
- This means `CARDIO` did not make a stable ATA register window visible at
  `1F0/3F6` or at any of the common alternate windows scanned by R3D18.

## R3D19 Diagnostic

R3D19 shifts from port probing to Socket Services return-code probing.

Disassembly of `CARDIO.EXE` shows that it uses `INT 1Ah` Socket Services calls
with these constants:

```text
SetSocket:    AX=8E00 BX=0180 CX=1101 DX=0000 SI=0002 DI=8005
SetWindow 9:  AX=8900 BX=0109 CX=0008 DX=0501 SI=01F0
SetWindow 10: AX=8900 BX=010A CX=0002 DX=0501 SI=03F6
```

Those calls are intended to configure the HP 200LX PCMCIA I/O windows so that
the card appears as an ATA device at `1F0-1F7` with alternate status/control at
`3F6`.

The R3D19 `SSSET` probe calls the same Socket Services functions and logs:

- the carry flag and output `AX/BX/CX/DX/SI/DI` after each call
- the BIOS fixed-disk count at `0040:0075`
- `1F0-1F7` and `3F6` before and after the calls

Three 8.3-safe batch files are provided:

```text
R3D19A.BAT  run SSSETA directly, without CARDIO first
R3D19B.BAT  run CARDIO, capture CARDIOB.TXT, then run SSSETB
R3D19C.BAT  run CARDIO, relocate Dubs INT13 to 8000:0000, then run SSSETC
```

Expected interpretation:

- If a Socket Services call reports carry set or an error code, the problem is
  likely at the PCMCIA socket/window setup layer.
- If the calls report success but `1F0/3F6` still read as repeated `3B`, then
  the socket/window setup alone is not enough. The missing piece may be ATA
  card attribute/configuration setup before the I/O window becomes active.
- If the calls report success and the register block changes to plausible ATA
  values, the next step is to retry a bounded ATA `IDENTIFY` immediately after
  the successful setup sequence.

R3D19 test result:

- The `SSSET?.TXT` files came back as zero-byte files.
- This likely means the diagnostic created/truncated the output file but did
  not successfully close it with logged data after running the Socket Services
  calls.

## R3D20 Diagnostic

R3D20 supersedes R3D19 with the same Socket Services call sequence but a more
defensive logger:

- At program start, the output file is created/truncated.
- Each emitted text fragment is then appended through a fresh
  open/seek-to-end/write/close cycle.
- This is intentionally slower, but it should preserve partial output even if
  a later Socket Services call stalls or exits oddly.

The R3D20 batch-file matrix is the same as R3D19:

```text
R3D20A.BAT  run SSSETA directly, without CARDIO first
R3D20B.BAT  run CARDIO, capture CARDIOB.TXT, then run SSSETB
R3D20C.BAT  run CARDIO, relocate Dubs INT13 to 8000:0000, then run SSSETC
```

R3D20 test result:

- The defensive logger worked; all three `SSSET?.TXT` files contained output.
- All three variants reported `CF=1 AX=0B00` for every Socket Services call.
- `CARDIOB.TXT` and `CARDIOC.TXT` contained only the normal CARDIO banner and
  no printed CARDIO error messages.
- The port samples still read as repeated `3B` at `1F0-1F7` and `3F6`, except
  for one unstable single-byte `53` in variant B.

The apparent contradiction between CARDIO reporting no error and `SSSET`
reporting errors led to a closer disassembly of `CARDIO.EXE`. The previous
probe had byte-swapped several fields when translating Borland `union REGS`
stores into raw register values.

Corrected values from the `CARDIO.EXE` disassembly:

```text
SetSocket:    AX=8E00 BX=8001 CX=0111 DX=0000 SI=0002 DI=8005
SetWindow 9:  AX=8900 BX=0901 CX=0008 DX=0501 SI=01F0
SetWindow 10: AX=8900 BX=0A01 CX=0002 DX=0501 SI=03F6
```

## R3D21 Diagnostic

R3D21 reruns the Socket Services return-code probe using the corrected
register values above.

Three 8.3-safe batch files are provided:

```text
R3D21A.BAT  run SSSETA directly, without CARDIO first
R3D21B.BAT  run CARDIO, capture CARDIOB.TXT, then run SSSETB
R3D21C.BAT  run CARDIO, relocate Dubs INT13 to 8000:0000, then run SSSETC
```

R3D21 test result:

- All three corrected Socket Services calls returned success:

```text
INT1A SetSocket AH=8E CF=0 AX=8E00 BX=8001 CX=0111 DX=0000 SI=0002 DI=8005
INT1A SetWindow09 base=1F0 size=8 CF=0 AX=8900 BX=0901 CX=0008 DX=0501 SI=01F0 DI=8005
INT1A SetWindow0A base=3F6 size=2 CF=0 AX=8900 BX=0A01 CX=0002 DX=0501 SI=03F6 DI=8005
```

- Despite successful host-side socket/window setup, `1F0-1F7` and `3F6` still
  read as repeated `3B`.
- This strongly suggests the host I/O windows are being configured, but the
  card itself is not responding as an ATA I/O device at those addresses.

The HP Developer Guide's PCMCIA chapter matches this result. It states that a
plug-in card returns to its default memory-card state on insertion/power-on and
that software must write configuration data to the card's attribute memory in
order to enable I/O mode. Only after that does `SetSocket`/`SetWindow` create a
useful I/O path.

## R3D22 Diagnostic

R3D22 logs the missing pre-window stage: the CardBIOS call made by `CARDIO.EXE`
before the Socket Services calls.

Disassembly of `CARDIO.EXE` shows a single CardBIOS request packet copied from
its data segment:

```text
10 09 01 00 00 00 01 00 00 01 00 00 00 00 00 00
```

`CARDIO.EXE` then calls:

```text
AX=B000
ES:BX -> 16-byte CardBIOS request packet
INT 1A
```

R3D22 replays that visible sequence and logs the packet bytes before and after
the call, the carry flag and registers returned by CardBIOS, and the `1F0/3F6`
port state after CardBIOS and after Socket Services.

Three 8.3-safe batch files are provided:

```text
R3D22A.BAT  run CBSETA directly, without CARDIO first
R3D22B.BAT  run CARDIO, capture CARDIOB.TXT, then run CBSETB
R3D22C.BAT  run CARDIO, relocate Dubs INT13 to 8000:0000, then run CBSETC
```

R3D22 test result:

- All three variants reported CardBIOS success:

```text
INT1A CardBIOS AX=B000 ES:BX=packet CF=0 AX=0000
```

- The packet bytes were unchanged by the call:

```text
10 09 01 00 00 00 01 00 00 01 00 00 00 00 00 00
```

- The corrected Socket Services calls still returned success.
- Despite that, `1F0-1F7` and `3F6` stayed at the repeated `3B` background
  value after CardBIOS and after Socket Services.

This means the visible static packet plus the corrected Socket Services calls
are still not enough to make the CF card decode as an ATA I/O device.

Reviewing the `CARDIO.EXE` disassembly again showed that `CARDIO` does not
appear to pass only the unmodified static packet. It copies the template and
then patches the packet tail before the `AX=B000` call. The most likely
interpretation is a far pointer to a one-byte configuration data buffer.

## R3D23 Diagnostic

R3D23 supersedes R3D22 by replaying the CardBIOS packet with the suspected
patched tail:

```text
bytes 00-12  copied from the CARDIO.EXE template
bytes 13-14  offset of a local one-byte data buffer
bytes 15-16  segment of that local data buffer
```

The data byte is varied across the three test programs:

```text
R3D23A.BAT  patched CardBIOS packet, data byte 00
R3D23B.BAT  CARDIO first, then patched packet, data byte 01
R3D23C.BAT  CARDIO and Dubs INT13 relocation, then patched packet, data 02
```

Each variant writes distinct output files:

```text
R3D23A.BAT  CB23A.TXT
R3D23B.BAT  CARDIOB.TXT and CB23B.TXT
R3D23C.BAT  CARDIOC.TXT and CB23C.TXT
```

This diagnostic still does not issue ATA sector reads or writes. It only calls
CardBIOS/Socket Services and samples the candidate ATA registers. If any
variant changes `1F0-1F7` or `3F6` away from the repeated `3B` pattern, the
next step should be a bounded direct ATA `IDENTIFY`/sector-read probe using
that exact setup sequence.

R3D23 test result:

- All three variants returned CardBIOS success:

```text
INT1A CardBIOS AX=B000 ES:BX=packet CF=0 AX=0000
```

- The patched packet before and after the call remained:

```text
10 09 01 00 00 00 01 00 00 01 00 00 00 06 04 3C 07
```

- The corrected Socket Services calls still returned success.
- Despite that, `1F0-1F7` and `3F6` still read as the repeated `3B`
  background value after CardBIOS and after Socket Services.
- One run showed a single unstable `63` byte at `1F3` after CardBIOS only,
  but the port block returned to all `3B` after Socket Services. This looks
  like bus noise rather than a decoded ATA register.

This confirms that the visible CardBIOS packet, even with the suspected
patched data pointer, is still not enough to make the card decode at the ATA
I/O ports. The next step is to stop guessing the CardBIOS packet and directly
inspect PCMCIA common/attribute memory.

## R3D24 Diagnostic

R3D24 maps the plug-in card memory through the HP 200LX Hornet E-bank
registers documented in the HP 100LX/200LX Developer's Guide.

The diagnostic saves the existing Hornet bank and attribute-select registers,
maps the plug-in slot into the `E000:0000` window, copies small samples into
local RAM, restores the original Hornet registers, and only then writes the
text dump. It does not call DOS while the E-bank window is remapped.

The sampled views are:

- common memory view at `E000:0000`
- raw attribute memory view at `E000:0000`
- even-byte extraction from the attribute memory view

The test matrix is:

```text
R3D24A.BAT  NCS0 direct dump without CARDIO first
R3D24B.BAT  CARDIO first, then NCS0 direct dump
R3D24C.BAT  CARDIO first, then NCS1 direct dump test
```

Expected output files:

```text
R3D24A.BAT  CIS24A.TXT
R3D24B.BAT  CARDIOB.TXT and CIS24B.TXT
R3D24C.BAT  CARDIOC.TXT and CIS24C.TXT
```

What we want to see is a real PCMCIA CIS tuple stream, most likely in the
attribute even-byte extraction. If that appears, the next diagnostic can parse
the configuration tuple, find the Configuration Option Register address, and
write the correct I/O-enable value deliberately.

R3D24 test result:

- The `CIS24?.TXT` output files came back as zero-byte files.
- This likely means the program created/truncated the output file, then did
  not reach the final DOS close after entering the risky Hornet E-bank remap
  path.
- Since R3D24 held the output file open until the very end, even the early
  header text would not necessarily be visible if the program stalled before
  closing the file.

## R3D25 Diagnostic

R3D25 keeps the same direct Hornet E-bank CIS/attribute-memory idea, but makes
the logger more defensive:

- every output fragment opens, appends, and closes the output file
- the common-memory capture is reduced to 128 bytes
- the attribute-memory capture is reduced to 512 bytes
- each risky capture stage writes a breadcrumb before it starts

The test matrix is:

```text
R3D25A.BAT  NCS0 direct dump without CARDIO first
R3D25B.BAT  CARDIO first, then NCS0 direct dump
R3D25C.BAT  CARDIO first, then NCS1 direct dump test
```

Expected output files:

```text
R3D25A.BAT  CIS25A.TXT
R3D25B.BAT  CARDIOB.TXT and CIS25B.TXT
R3D25C.BAT  CARDIOC.TXT and CIS25C.TXT
```

If R3D25 still stalls, the partial `CIS25?.TXT` file should show whether it
stopped before the common-memory capture, during the common-memory capture, or
during the attribute-memory capture.

R3D25 test result:

- All three variants completed and closed their output files correctly.
- The saved Hornet E-bank registers for variants A/B were:

```text
70 6F 6E 6D 6C 6B 6A 69 62: 04 04 04 04 04 04 04 04 00
```

- The common-memory view, raw attribute-memory view, and even-byte attribute
  extraction all remained the repeated `3B` background value.
- Variant C's final register readback differed (`1A` values), but the memory
  views still remained `3B`.

This means the raw Hornet E-bank register writes used by R3D24/R3D25 are not
enough to expose the CF card's CIS. The HP Developer Guide warns that window
state should normally be saved/restored using Int 63h page-map services, and
that Socket Services does not fully describe windows that are also used by
System ROM. The next diagnostic therefore uses Int 63h mapping rather than
direct E-bank register writes.

## R3D26 Diagnostic

R3D26 uses the HP documented Int 63h memory mapping functions:

```text
AX=0103  get page-map save-array size
AX=0100  save page map
AH=00    map NCS0 logical page 0 to a CPU physical page
AX=0101  restore page map
```

After mapping common memory, it temporarily flips the relevant Hornet
attribute-select bit for that same bank and snapshots attribute memory. The
page map is restored before the dump is written.

The test matrix is:

```text
R3D26A.BAT  map NCS0 logical page 0 to E000 without CARDIO first
R3D26B.BAT  CARDIO first, then map NCS0 logical page 0 to E000
R3D26C.BAT  CARDIO first, then map NCS0 logical page 0 to D000
```

Expected output files:

```text
R3D26A.BAT  CIS26A.TXT
R3D26B.BAT  CARDIOB.TXT and CIS26B.TXT
R3D26C.BAT  CARDIOC.TXT and CIS26C.TXT
```

Key things to inspect are the Int 63h `AH=00` map status and whether the data
changes away from `3B`. If the mapped attribute even-byte view contains CIS
tuples, the next step is to parse the configuration tuple and write the
correct I/O-enable value to the card configuration register.

R3D26 partial test result:

- `R3D26A.BAT` appears to hang immediately after the batch `echo` line.
- The program should have printed its own title before the first Int 63h call,
  so this needs a smaller smoke test before continuing with full page mapping.

## R3D27 Diagnostic

R3D27 is a tiny Int 63h smoke test with BIOS teletype breadcrumbs:

```text
S?0  program started
1    DOS output file was created and initial text was logged
2    just before the Int 63h call
3    just after the Int 63h call returned
```

The test matrix is:

```text
R3D27A.BAT  DOS/file logging baseline only, no Int 63h call
R3D27B.BAT  Int 63h AX=0103 memory-map save-size call
R3D27C.BAT  Int 63h AX=8303 XIP save-size call
```

Expected output files:

```text
R3D27A.BAT  I63T27A.TXT
R3D27B.BAT  I63T27B.TXT
R3D27C.BAT  I63T27C.TXT
```

If a run hangs, the last visible breadcrumb should identify whether the
failure is in DOS logging or the Int 63h call itself.

R3D27 test result:

- `R3D27A.BAT` completed the DOS/file logging baseline.
- `R3D27B.BAT` completed the Int 63h memory-map save-size call:

```text
After Int63, AX=0013
```

- `R3D27C.BAT` completed the Int 63h XIP save-size call:

```text
After Int63, AX=000A
```

This is a useful narrowing result. Int 63h itself is callable from DOS, and
the returned sizes match the HP Developer Guide expectations: 19 bytes for the
memory page-map save array and 10 bytes for the XIP page-map save array. That
means the R3D26 hang was probably not caused by the presence of Int 63h or by
basic DOS logging. The next test should split page mapping into smaller stages.

## R3D28 Diagnostic

R3D28 is a staged Int 63h page-map test that deliberately does not read from
the mapped memory window. This separates "the map call hangs" from "touching
the mapped page hangs."

The test matrix is:

```text
R3D28A.BAT  save current page map only, no map call
R3D28B.BAT  save map, map NCS0 logical page 0 to E000, restore map
R3D28C.BAT  save map, map NCS0 logical page 0 to D000, restore map
```

Expected output files:

```text
R3D28A.BAT  I63M28A.TXT
R3D28B.BAT  I63M28B.TXT
R3D28C.BAT  I63M28C.TXT
```

BIOS teletype breadcrumbs:

```text
S?0  program started
1    DOS output file was created and initial text was logged
2    AX=0103 memory-map save-size returned
3    AX=0100 save page-map returned
4    AH=00 map call returned; about to restore the saved map
```

Useful interpretations:

- If A hangs, the save-map call (`AX=0100`) or output-file path is the problem.
- If A completes but B or C hangs before breadcrumb `4`, the Int 63h `AH=00`
  page-map call itself is unsafe with that physical page/device selection.
- If B or C prints `4` but hangs afterward, restoring the saved page map
  (`AX=0101`) is the unsafe operation.
- If B or C completes, the next diagnostic can carefully read a few bytes from
  the mapped window after adding before/after restore breadcrumbs.

R3D28 test result:

- All three runs completed.
- `AX=0103` returned `0013`.
- `AX=0100` returned `0000` and saved 19 zero bytes for the current page-map
  state.
- Mapping NCS0 logical page 0 to E000 returned:

```text
Int63 AH=00 map NCS0 logical0 AX=0008 BX=0000 DX=0005
```

- Mapping NCS0 logical page 0 to D000 returned:

```text
Int63 AH=00 map NCS0 logical0 AX=0004 BX=0000 DX=0005
```

- Restoring the saved page map returned `AX=0001`.

The `AH=00` byte in these return values looks like success, with `AL` left as
the requested physical page or restore subfunction value. This strongly
suggests the R3D26 failure was not the Int 63h map call itself. The next step
is to touch a very small mapped memory window, then restore the page map before
doing any DOS file I/O.

## R3D29 Diagnostic

R3D29 is the first cautious mapped-memory read test. Each variant maps NCS0
logical page 0, copies only 32 bytes from the mapped physical segment into a
local buffer, restores the saved page map, and only then logs the buffer to
disk.

The test matrix is:

```text
R3D29A.BAT  map/read E000 without CARDIO
R3D29B.BAT  CARDIO, then map/read E000
R3D29C.BAT  CARDIO, then map/read D000
```

Expected output files:

```text
R3D29A.BAT  I63R29A.TXT
R3D29B.BAT  CARD29B.TXT and I63R29B.TXT
R3D29C.BAT  CARD29C.TXT and I63R29C.TXT
```

BIOS teletype breadcrumbs:

```text
S?0  program started
1    output file was created and initial text logged
2    save-size and save-map calls returned
3    map call returned
R    about to copy 32 bytes from the mapped segment
4    mapped 32-byte copy returned
5    saved page map was restored; file logging resumes
```

Useful interpretations:

- If a run reaches `3` but not `R`, the branch around map success or screen
  output is suspect.
- If a run reaches `R` but not `4`, reading the mapped segment is hanging.
- If a run reaches `4` but not `5`, the restore call after a real memory read
  is hanging.
- If a run completes but the 32 bytes are still all `3B` or all `FF`, the page
  may be mapped but not to the CF card's CIS/common memory.

R3D29 test result:

- All three runs completed, including the small mapped read and map restore.
- The mapped reads were stable and non-`3B`, but did not resemble a PCMCIA CIS
  tuple stream.
- E000 without `CARDIO` and E000 after `CARDIO` were identical:

```text
0C 00 00 E5 00 00 E0 50 0C 00 00 00 00 00 50 7E
0C 00 00 E5 00 00 E0 50 0C 00 00 00 00 00 50 7E
```

- D000 after `CARDIO` was nearly the same, with one repeated byte changed:

```text
0C 00 00 E5 00 00 E0 50 0C 80 00 00 00 00 50 7E
0C 00 00 E5 00 00 E0 50 0C 80 00 00 00 00 50 7E
```

Because the E000 result did not change after `CARDIO`, this looks more like a
fixed memory mapping or alias than the configured card tuple space. The HP
Developer Guide says that non-RAM cards expose attribute memory, and the CIS
should be in that attribute-memory view. R3D30 therefore repeats the small read
while explicitly selecting the attribute-memory view for the mapped bank.

## R3D30 Diagnostic

R3D30 maps the same page as R3D29 but reads both common and attribute views:

```text
R3D30A.BAT  map/read E000 common+attribute without CARDIO
R3D30B.BAT  CARDIO, then map/read E000 common+attribute
R3D30C.BAT  CARDIO, then map/read D000 common+attribute
```

The attribute-memory select masks follow the HP Developer Guide's Hornet
register description:

```text
E0 attribute select bit: 0x10
D0 attribute select bit: 0x01
```

Expected output files:

```text
R3D30A.BAT  I63A30A.TXT
R3D30B.BAT  CARD30B.TXT and I63A30B.TXT
R3D30C.BAT  CARD30C.TXT and I63A30C.TXT
```

BIOS teletype breadcrumbs:

```text
S?0  program started
1    output file was created and initial text logged
2    save-size and save-map calls returned
3    map call returned
C    about to copy 32 common-memory bytes
4    common copy returned
A    about to select attribute memory and copy 64 bytes
5    attribute copy returned
6    saved page map was restored; file logging resumes
```

Useful interpretations:

- If common matches R3D29 but attribute starts with recognizable CIS bytes
  such as `01`, `1A`, or other PCMCIA tuple IDs, we can move on to tuple
  parsing and configuration-register discovery.
- If common and attribute are identical, the attribute-select bit is not
  affecting this mapped window, so we need a different CardBIOS/Socket
  Services path to CIS.
- If attribute hangs, the bank select is valid but the attribute-memory access
  path is still unsafe or incomplete.

R3D30 test result:

- All three variants completed.
- The attribute selector register changed and restored as expected:

```text
R3D30A/R3D30B E000: 00 -> 10 -> 00
R3D30C        D000: 00 -> 01 -> 00
```

- However, common and attribute reads were identical in all variants.
- The even bytes from the attribute view did not resemble a PCMCIA CIS tuple
  stream.
- The E000 result was still identical with and without `CARDIO`.

This means we can manipulate the Hornet attribute-select bit, but the mapped
window still does not appear to be the CF card's attribute memory. The next
question is whether Int63 `AH=00` is actually programming the Hornet bank
registers for NCS0, or whether it is returning success while leaving us mapped
to some existing ROM/RAM alias.

## R3D31 Diagnostic

R3D31 avoids mapped-memory reads and instead snapshots the Hornet bank
registers around the Int63 mapping call:

```text
R3D31A.BAT  map NCS0 logical0 to E000 without CARDIO
R3D31B.BAT  CARDIO, then map NCS0 logical0 to E000
R3D31C.BAT  CARDIO, then map NCS0 logical0 to D000
```

Expected output files:

```text
R3D31A.BAT  I63G31A.TXT
R3D31B.BAT  CARD31B.TXT and I63G31B.TXT
R3D31C.BAT  CARD31C.TXT and I63G31C.TXT
```

The register order in each `I63G31?.TXT` file is:

```text
D0R0 D0R1 D1R0 D1R1 D2R0 D2R1 D3R0 D3R1
E0R0 E0R1 E1R0 E1R1 E2R0 E2R1 E3R0 E3R1 ATTR
```

It records:

- Int63 `AX=0103` save-array size
- Int63 `AX=0100` save-map status
- Int63 `AH=02` mapping state before the map
- Hornet bank registers before the map
- Int63 `AH=00` map status
- Hornet bank registers after the map
- Int63 `AH=02` mapping state after the map
- Hornet bank registers after setting the attribute-select bit
- Int63 `AX=0101` restore status
- Hornet bank registers after restore

Useful interpretations:

- For E000 variants, `E0R1` is the most important byte. If Int63 maps NCS0
  into E000, `E0R1` should show an enabled NCS0 bank, expected in the shape of
  `0D` for `FS1=0`, enabled, chip-select `101`.
- For the D000 variant, `D0R1` is the equivalent byte.
- If Int63 function `AH=02` claims the page is mapped to device select `0005`
  but the Hornet register does not show NCS0, the BIOS abstraction is not
  touching the expected physical bank.
- If the bank registers do show NCS0 but the memory bytes remain non-CIS, the
  next lead is card power/configuration or the exact common-vs-attribute memory
  selection mechanism.

R3D31 test result:

- All three variants completed.
- Int63 function `AH=02` reported the expected state transitions:

```text
before:  BX=FFFF DX=0000
mapped:  BX=0000 DX=0005
restore: BX=FFFF DX=0000
```

- This means the HP BIOS/Int63 abstraction believes physical page 08/E000 or
  04/D000 is being mapped to NCS0 logical page 0.
- The raw Hornet index/data register dump was not useful as a per-register
  decode. Every probed bank register returned the same byte for a given state:

```text
E000 mapped: 04 04 04 ... ATTR=00
D000 mapped: 1A 1A 1A ... ATTR=00
attribute selected: all 10 for E000, all 01 for D000
```

This suggests the diagnostic's direct Hornet index/data read method is not a
trustworthy register decoder in this context, even though the attribute-select
bit itself can be changed. We should use CardBIOS/Socket Services rather than
raw Hornet bank-register reads for the next step.

## LxCic /T Finding

Running `LXCIC /T` successfully produced a valid CIS dump for the CF card.

Product tuple:

```text
SunDisk SDP 5/3 0.6
```

Important tuples:

```text
Tuple 21 = 04 01
Tuple 1A = 01 07 00 02 0F
Tuple 1B = C2 ... F0 01 07 F6 03 01 ...
Tuple 1B = C3 ... 70 01 07 76 03 01 ...
```

Interpretation:

- Function ID `04`: fixed disk / flash drive.
- Config register tuple says the raw attribute-memory config-register base is
  `0x0200`; the LxCic/CardBIOS write path uses `0x0100`.
- Config table entry `C2` advertises primary IDE I/O windows:

```text
1F0-1F7 and 3F6
```

- Config table entry `C3` advertises secondary IDE I/O windows:

```text
170-177 and 376
```

This is the first clean confirmation from the card itself that standard IDE
I/O windows are valid configurations. The direct ATA probes likely failed
because the card was not fully configured into the matching COR/FCSR state, or
because the Socket Services I/O window setup and COR/FCSR write sequence needs
to be reproduced more exactly.

## R3D32 Diagnostic

R3D32 uses the CIS values directly instead of guessing.

The diagnostic sequence is:

1. Read the CIS through CardBIOS `INT 1Ah AX=B000h`.
2. Call Socket Services `SetSocket` (`AX=8E00h`) for socket 1.
3. Call Socket Services `SetWindow` (`AX=8900h`) for the advertised IDE I/O
   windows.
4. Write the COR at CardBIOS address `0x0100`.
5. Read/write/read FCSR at CardBIOS address `0x0101`, ORing in `0x28`
   for 8-bit I/O and audio/FCSR bit behavior as done by LxCic.
6. Probe the resulting ATA status/data ports with bounded waits.

The test matrix is:

```text
R3D32A.BAT  primary IDE 1F0/3F6, COR=42, no CARDIO
R3D32B.BAT  CARDIO first, then primary IDE 1F0/3F6, COR=42
R3D32C.BAT  secondary IDE 170/376, COR=43, no CARDIO
```

Expected output files:

```text
R3D32A.BAT  CF32A.TXT
R3D32B.BAT  CARD32B.TXT and CF32B.TXT
R3D32C.BAT  CF32C.TXT
```

R3D32 test result:

- All three variants appeared to run, but `CF32A.TXT`, `CF32B.TXT`, and
  `CF32C.TXT` remained 0 bytes.
- `CARD32B.TXT` was written correctly because it was created by the separate
  `CARDIO > CARD32B.TXT` command before the CF configuration probe started.

This is likely a diagnostic design problem rather than a useful card result.
The probe opened a log file on the CF card, then reconfigured that same
PCMCIA/CF card into IDE I/O mode. If the CF card is the DOS filesystem, the
socket/COR work can make DOS lose the disk underneath the open file handle.

## R3D33 Diagnostic

R3D33 repeats the R3D32 CIS-driven configuration sequence but removes all file
logging from the COM program. It prints to the screen only.

The test matrix is:

```text
R3D33A.BAT  primary IDE 1F0/3F6, COR=42, no CARDIO
R3D33B.BAT  CARDIO first, then primary IDE 1F0/3F6, COR=42
R3D33C.BAT  secondary IDE 170/376, COR=43, no CARDIO
```

Expected artifacts:

```text
R3D33B.BAT  CARD33B.TXT if the pre-probe CARDIO redirection succeeds
all runs     screen photos of the probe output
```

Expect DOS disk access to be unreliable after a run because the diagnostic may
successfully move the CF card away from the DOS filesystem mode and into IDE
I/O mode.

## Open Questions

- Does ELKS call BIOS INT13 for `0x80` on this configuration?
- Does the Dubs handler expect to remain at `0x9000`, or is it position-independent enough to run at `0x8000`?
- Does `CARDIO` leave the CF card mapped to ATA-compatible I/O ports after ELKS starts?
- Does ELKS need a direct PCMCIA/ATA driver instead of relying on the BIOS/INT13 path?
