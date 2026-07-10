# Release 3.1 - RAMdisk Memory Fix

Release 3.1 is a boot-package update for Release 3. It keeps the same HP 200LX
PCMCIA/CF persistent Minix root filesystem design, but fixes the unused RAMdisk
reservation that was consuming most of the conventional memory available to
ELKS programs.

## What Changed From Release 3

- Updated `KERNBOP` with the MEMLAB16-tested R3D46 kernel patch.
- Changed the kernel RAMdisk reservation from `360K` to `0K`.
- Kept the persistent root filesystem on `/dev/cfa1`.
- Kept `BTGVDX.COM` and `ROOT092` in the DOS boot package for compatibility
  with the current custom loader path.
- Confirmed `vi` works once `TERM=ansi` is exported.

## Expected Boot Clues

`BTGVDX` may still show the legacy loader line:

```text
ROOTEND=8C00
```

The ELKS kernel should then show:

```text
rd: 0K ramdisk at 3200:0000
VFS: Mounted root device /dev/cfa1 (0501) minix filesystem.
```

## Real-Hardware Result

On an HP 200LX with 4 MB RAM, the MEMLAB16/Release 3.1 candidate reached the
ELKS shell and `meminfo` showed approximately:

```text
Main 79/512K used, 431K free
```

This recovers the conventional memory previously lost to the unused RAMdisk
reservation.

## Downloads

- `hp200lx-release3.1.zip`
  - DOS boot package for `C:\ELKS`.
  - Contains the updated `KERNBOP`.
- `hp200lx-release3-rootcf.zip`
  - Unchanged Release 3 PCMCIA/CF root image package.
  - Contains `R3ROOT.IMG`.

Checksums:

```text
4ce7788969635c625d4c21524e89cd9e4c07fb77266d67e36d9681cfce753461  hp200lx-release3.1.zip
bf6ac72d5f090cc3062876f910f477da61216cd171c0664fcfb2942ac4aa54d0  KERNBOP
f770d2be6d804cdfa6fa8e332533ee111b45401ec520e8ded2746530b854ca2a  hp200lx-release3-rootcf.zip
2f346ad04526a37536178e463f78b478b774e051278572361f6e72bdec704aa1  R3ROOT.IMG
```

## Install Notes

Use Release 3.1 exactly like Release 3:

1. Copy the contents of `hp200lx-release3.1.zip` to `C:\ELKS`.
2. Write `R3ROOT.IMG` from `hp200lx-release3-rootcf.zip` to the PCMCIA/CF card.
3. Boot DOS to the `C:` prompt.
4. On double-speed modified machines, run `DSPEED/R` before starting ELKS.
5. Run `RUNELKS` from `C:\ELKS`.

After boot, set the terminal type before starting `vi`:

```text
TERM=ansi
export TERM
vi
```

## Remaining Cleanup

Release 3.1 deliberately keeps the proven Release 3 loader path. The legacy
`ROOT092` file is still copied by `BTGVDX`, but the kernel no longer reserves
ELKS process memory for it after boot. A later cleanup can remove the custom
loader RAMdisk path entirely.
