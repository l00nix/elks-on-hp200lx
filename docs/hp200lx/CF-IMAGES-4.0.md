# Release 4.0 CF images and offline growth

Release 4.0 preserves the four candidate-1 image bytes. Use the separate 4.0 boot
ZIP (FINAL2b) in C:\ELKS39FB; any older embedded /linux or release banner is
historical. The DOS loader selects the kernel from C:, not /linux on the card.
CF images include the tested ELX utility updates and corrected HP Nano-X suite.

All profiles use one Minix V1 partition starting at sector 63, 1 KiB blocks,
14-character names and 2048 inodes (1561 initially free). Growth adds data space,
not inodes. The 8/16/32/64 MB profiles occupy 7/14/30/60 MiB of card space.
The main README lists exact byte counts; a physical card must be at least that large.

## One base image, offline expansion

The 8 MB edition is the base. It reserves eight zone bitmap blocks, enough for
the 64 MB profile. The larger editions are generated from it without moving
existing inodes or data blocks. This costs only four extra bitmap KiB compared
with the old 8 MB edition's layout.

**There is no first-boot or mounted-root resizer.** The frozen ELKS Minix driver
does not implement online growth. Editing its partition table while running
would also leave filesystem geometry and cached kernel state inconsistent.
The host script changes the partition extent, filesystem size and allocation
bitmap together, then verifies all file contents and metadata are preserved.

Python 3.9 or newer, with no third-party packages, is sufficient. Keep
`grow_cf.py` and `minix.py` together:

```sh
python3 grow_cf.py R4C108.IMG my64.img --card-mb 64
```

Choose `16`, `32` or `64` as appropriate. The output must not already exist.
Check its exact byte size against the destination card before writing it.
The supplied pre-expanded images avoid this step for a fresh installation.

**To grow after using the card**, preserve the files added since installation:

1. Exit applications and run `shutdown -r` on the HP. Wait for DOS, switch off,
   then move the CF card to the host reader. Do not pull a running root card.
2. Identify the reader with `diskutil list external physical` on macOS. Unmount
   that disk and read its whole contents to a regular file, for example
   `used-card.img`. Use the reader's actual disk identifier, not an assumed one.
3. Run `python3 grow_cf.py used-card.img grown-card.img --card-mb 64`.
   Use the current card dump, **not the original distribution image**, to retain
   your files. This supports a dump with unused trailing card space; data outside
   the single partition is not copied into the output.
4. Check the output filesystem, write the new whole-card image to media large
   enough for it, verify the written bytes, then boot with the same CF boot kit.
   Keep the input dump until the expanded card passes its tests.

The script accepts regular files only and refuses devices, symlinks, existing
outputs, dirty/error-marked filesystems, extra partitions, orphaned allocations,
duplicate block ownership, incorrect link counts, shrinking and older images
without the reserved bitmap layout. A failed check leaves the source untouched.
It does not repair damaged filesystems or write a physical card.

For an independent Linux check, extract the partition and run `fsck.minix` on
the extracted regular file (never the running HP root):

```sh
python3 - <<'PY'
from pathlib import Path
from grow_cf import inspect
image = Path('grown-card.img').read_bytes()
fs, records = inspect(image)
with open('root-check.minix', 'xb') as output:
    output.write(fs.data)
print('Paths:', len(records), 'Free bytes:', fs.free_bytes())
PY
fsck.minix -fsv root-check.minix
```

## Validation

All four distribution images passed independent host filesystem checks and
content/metadata comparison. The growth suite passed 13 tests; a 34 MiB fixture
allocated zones beyond 32 MiB and read back with a matching hash. Growth after
adding a simulated user file preserved that file. These are host-side results.
Hardware storage/sleep/persistence acceptance is summarized separately; it does
not imply physical high-zone testing on every capacity/card combination.

Image build sources and exact pinned inputs are included in the image-tools ZIP.
The historical candidate reports are preserved as provenance, not current
installation instructions. Images themselves are unchanged for the 4.0 promotion.
