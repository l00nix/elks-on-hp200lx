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

## Test Notes to Capture

When testing `RUNR3D12`, record or copy:

- `IODUMP.TXT`
- whether `RUNR3D12.BAT` runs successfully after `CARDIO`
- a photo of the output only if copying `IODUMP.TXT` is inconvenient

## Open Questions

- Does ELKS call BIOS INT13 for `0x80` on this configuration?
- Does the Dubs handler expect to remain at `0x9000`, or is it position-independent enough to run at `0x8000`?
- Does `CARDIO` leave the CF card mapped to ATA-compatible I/O ports after ELKS starts?
- Does ELKS need a direct PCMCIA/ATA driver instead of relying on the BIOS/INT13 path?
