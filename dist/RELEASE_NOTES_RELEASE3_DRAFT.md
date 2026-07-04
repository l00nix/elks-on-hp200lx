# Release 3 - Persistent PCMCIA/CF Root Filesystem

Release 3 is the first HP 200LX ELKS release with both:

- working built-in HP 200LX keyboard input
- a persistent Minix root filesystem on a PCMCIA/CF card

The kernel now mounts the CF card as `/dev/cfa1`, so files written inside ELKS
survive a full reboot.

![HP 200LX running ELKS Release 3](https://github.com/l00nix/elks-on-hp200lx/raw/hp200lx-release-3/docs/hp200lx/images/release3-hphello.jpg)

## What Works

- Boots ELKS on a real HP 200LX with 4 MB RAM.
- Uses the internal HP 200LX keyboard; no external keyboard is required.
- Mounts the PCMCIA/CF Minix partition as `/`.
- Persists files and configuration changes across reboot.
- Includes the regular ELKS 2880K Minix filesystem contents.
- Adds `/bin/hphello` for a simple HP 200LX release screenshot.
- Includes common ELKS programs such as `tetris`, `digger`, `elkirc`, `memopad`, Nano-X tools, and `nxjpeg` (not tested yet).

Expected boot line:

```text
VFS: Mounted root device /dev/cfa1 (0501) minix filesystem.
```

## Downloads

- `hp200lx-release3.zip`
  - DOS boot bundle for `C:\ELKS`
  - normal entry point: `RUNELKS.BAT`
  - fallback entry point: `RUNCARD.BAT`

- `hp200lx-release3-rootcf.zip`
  - contains `R3ROOT.IMG`, a dd-able 30 MB PCMCIA/CF Minix root image

Checksums:

```text
77f243dd0bcdfadb8d36bfc9271ecc37d47c15904b1d13a9f30b15de3e59b562  hp200lx-release3.zip
f770d2be6d804cdfa6fa8e332533ee111b45401ec520e8ded2746530b854ca2a  hp200lx-release3-rootcf.zip
2f346ad04526a37536178e463f78b478b774e051278572361f6e72bdec704aa1  R3ROOT.IMG
```

## Install Summary

Before starting, boot the HP 200LX to the DOS `C:` drive prompt, not into the built-in HP PIM application. In `AUTOEXEC.BAT`, comment out the `200` line so the PIM shell does not start automatically and more RAM remains available for ELKS:

```dos
REM 200
```

Release 3 uses a conservative two-stage boot:

```text
HP 200LX internal C: drive  -> DOS boot bundle in C:\ELKS
PCMCIA/CF card              -> persistent ELKS Minix root filesystem
```

1. Copy the contents of `hp200lx-release3.zip` to `C:\ELKS` on the HP 200LX.
2. Write `R3ROOT.IMG` from `hp200lx-release3-rootcf.zip` to a spare CF card.
3. Boot the HP 200LX into DOS from the internal `C:` drive, landing at the DOS prompt rather than the HP PIM application.
4. Insert the prepared PCMCIA/CF card.
5. Run:

   ```dos
   C:
   CD \ELKS
   RUNELKS
   ```

If `RUNELKS` does not see the card, reboot fully and try:

```dos
C:
CD \ELKS
RUNCARD
```

## Persistence Test

Inside ELKS:

```text
echo r3test >/root/r3test.txt
sync
cat /root/r3test.txt
```

Reboot fully back to DOS, run `RUNELKS` again, then:

```text
cat /root/r3test.txt
```

The file should still be present.

## Notes

- This is still an experimental downstream/community build.
- The boot files intentionally live on the internal DOS `C:` drive.
- A fully self-contained bootable PCMCIA/CF card was tested, but it was not
  stable enough for this release.
- The single-card installer idea remains a good future Release 4 target.
