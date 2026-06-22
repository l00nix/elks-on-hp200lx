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

If ELKS then boots normally and the BIOS disk path sees the CF card, the 0x9000 overwrite theory is likely correct.

If ELKS still does not see the disk, the next step is to instrument ELKS disk probing to determine whether INT13 returns an error, hangs, or is not being called for the expected drive number.

## Test Notes to Capture

When testing `RUNR3D1`, record:

- Whether `CHK80.DBG` shows vector `00 00 00 80`.
- The first 16 bytes dumped from `8000:0000`.
- Whether ELKS still boots to the shell.
- Whether any disk/probe output changes during boot.
- Whether any ELKS command can see hard-disk devices, for example `fdisk -l` if available.

## Open Questions

- Does ELKS call BIOS INT13 for `0x80` on this configuration?
- Does the Dubs handler expect to remain at `0x9000`, or is it position-independent enough to run at `0x8000`?
- Does `CARDIO` leave the CF card mapped to ATA-compatible I/O ports after ELKS starts?
- Does ELKS need a direct PCMCIA/ATA driver instead of relying on the BIOS/INT13 path?

