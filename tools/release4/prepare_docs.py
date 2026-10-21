from pathlib import Path
import shutil
P=Path(__file__).resolve().parents[2]
D=P/'output/hp200lx-release4.0/docs'; D.mkdir(parents=True,exist_ok=True)
old=(P/'docs/release4-staging/README.md').read_text()
end = old.index('![meminfo at the standard') if '![meminfo at the standard' in old else old.index('### Sleep modes')
keys=old[old.index('## HP BIOS functions'):end]
readme='''# ELKS on the HP 200LX

**HP 200LX package 4.0 · based on ELKS 0.9.2**

Run [ELKS](https://github.com/ghaerr/elks), a small Linux system for 16-bit x86
computers, on the HP 200LX with its built-in keyboard, native display controls,
persistent storage and graphical HTTP browsing. One DOS launcher selects between
**two kernels**: CF root storage, or an internal filesystem file on C: that leaves
the PCMCIA slot available for an Accton Ethernet card.

[Download 4.0](https://github.com/l00nix/elks-on-hp200lx/releases/tag/hp200lx-release-4.0)
· [Changes since 3.5](docs/hp200lx/RELEASE-4.0.md)
· [Hardware acceptance](docs/hp200lx/ACCEPTANCE-4.0.md)
· [Build/source guide](docs/hp200lx/BUILD-4.0.md)
· [Historical releases](https://github.com/l00nix/elks-on-hp200lx/releases)
· [Pre-4.0 README archive](docs/hp200lx/history/README-before-4.0.md)

**4.0 is the HP integration package version, not an upstream ELKS version.**
It promotes the accepted **3.9 FINAL2b** binaries unchanged. The DOS boot folder
remains **C:\\ELKS39FB**, and the boot banner / `uname -a` retain
`hp200lx-3.9-final2b-local` or `hp200lx-3.9-final2b-cf`, dated 2026-10-20.
Keep all boot-kit files together; do not mix helpers and kernels from other builds.

![ELKSWeb displaying FrogFind on a single-speed HP 200LX](docs/hp200lx/media/release4-frogfind-single.jpg)

*Actual palmtop during Release 4 acceptance: the single-speed unit loaded
FrogFind over the Internet through the Accton card, including the frog GIF.*

## What works

- Factory-speed and double-speed HP 200LX operation; `/DS` selects the display correction.
- BIOS keyboard, zoom, panning, cursor focus and screen inversion.
- A 636 KiB conventional-memory boundary, reserving the top 4 KiB for firmware.
  This is a boundary, not free application RAM; kernel and programs use part of it.
- Writable Minix root on CF (`/dev/cfa1`) or in a DOS C: image (`/dev/ssd`),
  with mapping/storage validation and guarded recovery.
- Guarded CF sleep, including the tested `edit` text-editor case.
- Opt-in writable local sleep at the idle shell, with an empty slot or the
  tested Accton EN2216 R02. See the exact scope below.
- DHCP, DNS and live HTTP browsing using the local kernel, Accton and `ktcp`.
  FrogFind and 68k.news rendered on real hardware; large pages are slow.
- ELKSWeb plus ELXbat, ELXstat, ELX Commander, ELXdash, ELXctl and ELXcap.
- Corrected HP Nano-X applications and `nx` launcher in the CF images.
- Serial shell helper and stock ELKS v0.9.2 raw Minix image compatibility.

'''+keys+'''
### Sleep modes

| Boot mode | Sleep support in 4.0 |
| --- | --- |
| `/CF` | Guarded local text-console sleep; idle shell and `edit` tested. No extra sleep flag. |
| `/LOCAL C:\\NAME.MNX /NONET` | Sleep disabled unless `/SLEEPTEST` is added. |
| `/LOCAL C:\\NAME.MNX /NONET /SLEEPTEST` | Writable local root; **empty slot**; idle initial shell only. |
| `/LOCAL C:\\NAME.MNX /SLEEPNIC` | Opt-in Accton EN2216 R02 recovery; idle initial shell and idle `ktcp`. Do not add `/NONET`. |

Before sleep, exit graphics/apps and close the serial shell. In local mode,
`edit` deliberately blocks sleep; CF's guarded text-reader policy permits the
tested editor case. Unsupported activity or a card in the empty-slot mode
produces a refusal beep/message. A refusal is expected behaviour, not a request
to bypass a guard. Storage is synced and checked before sleep and after wake.
A recovery-integrity failure stops operation rather than continuing writes.

With `/SLEEPNIC`, leave the Accton inserted and cable connected. The same `ktcp`
process survived repeated sleep/wake cycles, and fresh DNS/HTTP/GIF requests
worked after waking on both speed variants. This does not promise preservation
of active TCP sessions or DHCP leases through arbitrarily long sleeps.
Graphics, serial sessions and general application suspend are outside scope.

## Choose your filesystem

Download the **boot ZIP** plus either a CF ZIP or the local-images ZIP.
The boot kit contains 11 files totalling **185,173 bytes** and generates a kernel
copy of up to **82,384 bytes**. Allow **320 KiB free on C:** for the boot kit,
working copy and allocation slack, in addition to any MNX image.

| Option | Filesystem | PCMCIA slot | DOS command from C:\\ELKS39FB |
| --- | --- | --- | --- |
| CF root | Whole-card Minix partition | Occupied by CF | `RUNELKS /CF` |
| Local root | Raw Minix file in C:\\ | Empty or supported NIC | `RUNELKS /LOCAL C:\\ELKS2M.MNX /NONET` |

Add `/DS` for a double-speed machine. Boot from a plain DOS prompt after exiting
System Manager. Retain the tested DSPEED initialization for an accelerated unit,
and unload its resident hook with `DSPEED /R` before starting ELKS.

### CompactFlash installation

The four downloads have identical userland contents. Exact sizes deliberately
leave headroom below nominal card capacities:

| Nominal card | Image inside ZIP | Exact bytes | Filesystem KiB |
| --- | --- | ---: | ---: |
| 8 MB | `R4C108.IMG` | 7,340,032 | 7,136 |
| 16 MB | `R4C116.IMG` | 14,680,064 | 14,304 |
| 32 MB | `R4C132.IMG` | 31,457,280 | 30,688 |
| 64 MB | `R4C164.IMG` | 62,914,560 | 61,408 |

1. Verify the release SHA-256 checksums. Use media at least as large as the exact image.
2. Write the IMG to the **whole CF card**, replacing its contents and partition table.
   Back up any files you need first, and verify the written image afterward.
3. Copy the boot ZIP's `ELKS39FB` folder to `C:\\ELKS39FB` on the HP.
4. Insert the prepared CF, exit System Manager, then run:

   ```dos
   C:
   CD \\ELKS39FB
   RUNELKS /CF
   ```

   On double-speed hardware, use `RUNELKS /DS /CF`.
5. Confirm `/dev/cfa1` is the mounted root. Keep the root card inserted while ELKS runs.

The CF images include corrected HP Nano-X, the tested ELX utility updates,
ELKSWeb, `nx`, `/root/ser`, and ANSI defaults. The kernel is loaded from C:;
the older `/linux` copy and development banners inside these byte-preserved
images are not used to select the running kernel.

The images use Minix V1, 1 KiB blocks and 14-character names. Larger cards keep
unused capacity beyond the image. The included **host-side** `grow_cf.py` can
expand an image or a compatible saved card dump to the 16/32/64 MB profiles.
There is no automatic first-boot or mounted-root expansion. See
[CF image and growth guide](docs/hp200lx/CF-IMAGES-4.0.md).

### Internal C: installation

The names describe the intended model class, not the image size:

| File | Exact bytes | Initial free space inside | Recommended free C: before installation |
| --- | ---: | ---: | ---: |
| `ELKS2M.MNX` | 737,280 (720 KiB) | 94 KiB | 1.1 MiB |
| `ELKS4M.MNX` | 3,145,728 (3 MiB) | 224 KiB | 3.4 MiB |

Check actual free C: capacity. Case labels and DOS conventional-memory totals
alone do not establish installed RAM; storage allocation and existing files
also affect what fits. Free space inside MNX is already part of its file size.

1. Back up an existing MNX before replacing it. Copy the chosen file directly
   to `C:\\` and the complete boot directory to `C:\\ELKS39FB`.
2. Start with an empty slot and networking disabled:

   ```dos
   C:
   CD \\ELKS39FB
   RUNELKS /LOCAL C:\\ELKS2M.MNX /NONET
   ```

   Substitute `ELKS4M.MNX` for the full image and add `/DS` on accelerated hardware.
   To enable empty-slot local sleep, also add `/SLEEPTEST`.
3. Confirm root is `/dev/ssd`. These files are accessed in place in the internal
   battery-backed RAM disk; they are not copied into conventional application RAM.
4. For Ethernet, return to DOS, insert the Accton and boot without `/NONET`:

   ```dos
   RUNELKS /DS /LOCAL C:\\ELKS4M.MNX /SLEEPNIC
   ```

   Omit `/DS` on factory-speed hardware. `/SLEEPNIC` is optional; it enables the
   tested idle-network sleep path.

Both images derive from upstream ELKS v0.9.2, retain its DHCP-capable network
userland, and add ELKSWeb and the ELX tools. The compact edition omits Nano-X,
games and manuals. The full edition retains stock programs; **the corrected HP
Nano-X suite is supplied in the CF images**, not promised for the stock-derived
local image. Both local images are preserved unchanged from the tests and contain
ELXbat 0.1.3 and ELXdash 0.2.0-test3. Install the separate utility update pack for
ELXbat 0.1.4's partial redraw and ELXdash test4's clearer charging lock/labels.
See [ELX tools](docs/hp200lx/ELX-TOOLS-4.0.md).

The loader also accepts the tested upstream **v0.9.2 fd2880-minix.img** as a raw
filesystem: copy it to a DOS 8.3 name such as `C:\\FD2880.IMG`, then use
`RUNELKS /LOCAL C:\\FD2880.IMG`. The loader uses the HP kernel, not the floppy
boot sector or `/linux`. Stock images do not include ELKSWeb or `/root/ser`.
Other image versions and filesystem formats require separate validation.

### Networking

The qualified card is the **Accton EN2216 R02**, using the NE2000 path.
Buffalo, Netgear and other cards are not covered by Release 4 hardware acceptance.
CF-root mode does not provide Ethernet; picoPCMCIA/DualSlot support is future work.
Do not hot-plug a NIC or root CF while ELKS is running.

On the supplied local images, start client networking once:

```sh
ktcp -b -p ne0
netstat
web http://frogfind.8088retro.com/
```

With no static addresses, this `ktcp` requests DHCP. Alternatively, `net start ne0`
uses `/etc/net.cfg`, including its default server-daemon list. For sleep testing,
use only `ktcp` and the idle shell; extra daemons can block the sleep guard.
Do not start a second `ktcp` if one is already running. Static configuration
belongs in `/etc/net.cfg` and DNS configuration in `/etc/resolv.conf`.

The stock server daemons can report `SO_NOBUFFER: Invalid argument` with the HP
kernel. These server features are not qualified; that message does not invalidate
a successful DHCP/client HTTP test. The direct `ktcp` command avoids starting them.

ELKSWeb supports **HTTP**, not native HTTPS. `68k.news` rendered successfully,
but its roughly 92 KB page can take a long time to parse/layout and leaves very
little cache headroom on a nearly full compact filesystem. Start with FrogFind.
Navigation and forms have narrower test coverage than page loading/rendering.

## Everyday use

Run `meminfo`, `df` and `ps` to inspect the system. Use `export TERM=ansi` if an
image has not already set it. The firmware warning and cached voltage readings
are not estimates of remaining battery runtime.

| Tool | Start / basic controls |
| --- | --- |
| ELKSWeb | `web` for welcome page; `web http://frogfind.8088retro.com/`; Tab selects links, Enter opens, F6 or Ctrl+L focuses address. |
| ELXbat | `elxbat`; R rereads cached voltage, Q/Esc exits. Updated build redraws changed regions. |
| ELXstat | `elxstat` or `elxstat -v` for firmware/system information. |
| ELX Commander | `elxcmd /root /tmp`; Tab panels, arrows selection, V view, C copy, M move, D delete, N new directory, Q back/exit. |
| ELXdash | `elxdash`; Tab controls, Left/Right adjust, B battery menu, arrows select, Enter chooses, Esc closes. |
| ELXctl | `elxctl status`, `elxctl --help`; command-line display/sound/firmware settings. |
| ELXcap | `elxcap /root/SCREEN.BMP`; manual or delayed BMP/PBM capture. Alt+period hotkey hook is **not included**. |

See [tool instructions and update procedure](docs/hp200lx/ELX-TOOLS-4.0.md).
Charging controls remain experimental and locked unless `elxdash --charge-test`
is explicitly used. Release 4 acceptance does not certify NiCd charging.

On CF, use `nx`, `nx nxclock`, or `nx nxjpeg /root/earth.jpg`. JPEG rendering can
be slow. ELKSWeb and the ELX tools use their own graphics paths and do not need Nano-X.

![Nano-X clock on the HP 200LX](docs/hp200lx/media/nxclock.jpg)

*Development photograph; exact build and speed of this capture were not recorded.*

### Serial shell

On the palmtop, run `sh /root/ser`. For an unmodified stock image:

```sh
stty sane 9600 < /dev/ttyS0
/bin/sh < /dev/ttyS0 > /dev/ttyS0 2>&1
```

Connect the peer at **9600 baud, 8N1**. Type `exit` from the peer to release the
serial shell before sleep. Local Ctrl+C did not reliably release the redirected
shell on every tested image; do not depend on it as the serial-exit method.

### Shutdown and reset

Exit applications and use `shutdown -r` to sync/unmount and reboot into DOS.
Do not move or replace an MNX file while ELKS is using it. A hard reset is a last
resort: unsaved data and pending writes can be lost. If the HP asks whether to
initialize after a reset, press **N** to preserve the internal C: drive.

## Validation and limits

The maintainer accepted the hardware tests and sleep guards on 21 October 2026.
The test record distinguishes user observations from serial-verified checks:
[acceptance summary](docs/hp200lx/ACCEPTANCE-4.0.md).
The binaries passed 39 discovered software checks with no skips, and release
packaging verifies every boot file and filesystem against the frozen hashes.

CF growth beyond 32 MiB has host-side allocation/readback/fsck coverage; this is
not a claim that every CF capacity/card combination or every high-zone workload
was tested physically. Both post-test MNX copies passed forced read-only offline
filesystem checks; their clean flags were unset, with no structural errors found.
No repair or clean-flag rewrite was performed.

Source and licenses are supplied with the release. The matching build source is
in **hp200lx-4.0-source.tar.gz**; follow its release build guide rather than the
historical repository-root build instructions. Older embedded documentation and
banners in preserved images identify their original construction builds.

## Credits and related projects

Thanks to the [ELKS authors](https://github.com/ghaerr/elks), Greg Haerr,
Richard L. Dubs for HP PCMCIA/BIOS work, Mack Baggette for the HP MINIX firmware
approach, and Stefan Peichl for DSPEED and SLEEPON. Thanks to YYZKevin for
[COMrade](https://github.com/yyzkevin/COMrade), used for hardware development.
See also [ELKSWeb](https://github.com/l00nix/ELKSWeb) and
[MINIX 2 on HP 200LX](https://github.com/l00nix/minix-2-hp200lx).

GEMCAP/CAPLX, CXCTL, ABC/LX and Norton Commander informed utility workflows and
interface ideas. The ELX tools are independent implementations; their original
component/font notices remain in the source and image license files. No HP ROM
or proprietary DOS runtime is distributed. DOS LXdash is a separate project.
'''
(D/'README.md').write_text(readme)
notes='''# HP 200LX package 4.0 — ELKS 0.9.2

Release 4.0 promotes the hardware-accepted **3.9 FINAL2b** kernels and DOS helpers
without changing their bytes. The installation directory remains **C:\\ELKS39FB**;
the internal version strings remain `3.9-final2b`. Package 4.0 is separate from
upstream ELKS 0.9.2.

## Changes since published 3.5

| Area | Changes |
| --- | --- |
| HP firmware integration | Expanded/refined BIOS keyboard, display and power handling. Version 3.5 already had ROM keyboard, zoom and panning; subsequent work integrates focus, recovery and controls more completely. |
| Memory recovery | Reserved firmware area reduced to 4 KiB, reaching the 636 KiB conventional-memory boundary. Development reclaim probes and `/ARM` flags removed from normal startup. This is not free application RAM. |
| Single/double speed | `/DS` display correction; factory-speed and accelerated hardware exercised. |
| Dual-kernel boot | One `RUNELKS` launcher chooses a CF-only kernel or local/NIC kernel, with matched DOS helpers. CF is the default or explicit `/CF`; `/LOCAL C:\\NAME.MNX` selects internal storage. |
| CF storage | Improved initialization/recovery, validated writable root with fallback, sleep/wake and reboot persistence. Refreshed 8/16/32/64 MB image profiles. |
| Internal filesystem | Writable banked C: filesystem access leaves PCMCIA available for Ethernet. Image-length/mapping checks replace the old fixed-size restriction; 720 KiB, 3 MiB and stock upstream v0.9.2 2.88 MB filesystems tested. |
| Sleep/wake | Guarded CF sleep including the tested `edit` case. Opt-in writable local empty-slot `/NONET /SLEEPTEST`; Accton `/SLEEPNIC` preserves idle ktcp and recovers network hardware. Local sleep requires the idle initial shell. Unsupported activity gets refusal message/beep. |
| Networking | Accton EN2216 R02 initialization and IRQ recovery, DHCP with stock-derived local userland, DNS and live HTTP. Repeated connected-cable sleep/wake followed by fresh requests on both speed variants. |
| Console/serial | ANSI startup support and `/root/ser`; stock diagnostics ABI compatibility. Serial shell exit uses peer `exit`; local Ctrl+C behaviour varies by image. |
| Nano-X | Corrected startup, divide fault, JPEG rendering and text restoration; CF images include `nx`, terminal, clock and viewer. |
| ELKSWeb | Native graphical HTTP browser with offline welcome page, GIF rendering, digit-leading hostnames and argument-forwarding `web`; 68k.news and FrogFind rendered on real HP hardware. |
| ELX tools | ELXbat/ELXstat, Commander, ELXctl, ELXdash and ELXcap. Updated battery redraw and power status; dashboard controls and experimental charging lock; Commander file operations checked. Cached volts are not charge percentages. |
| Images and growth | Preserved 720 KiB/3 MiB local test images plus four refreshed CF capacities. Host-side CF growth script; no online/first-boot resizer. |
| Documentation | Two installation paths, SVG key shortcuts, hardware photographs, usage guides, source/asset manifests and practical reboot/sleep limits. |

## Downloads

- `hp200lx-4.0-boot.zip`: required, 11 unchanged boot files under ELKS39FB.
- `hp200lx-4.0-local-images.zip`: ELKS2M.MNX (737,280 bytes), ELKS4M.MNX (3,145,728 bytes).
- `hp200lx-4.0-cf-{8,16,32,64}mb.zip`: whole-card images, respectively
  7,340,032 / 14,680,064 / 31,457,280 / 62,914,560 bytes after extraction.
- `hp200lx-4.0-elx-tools.zip`: tested utility binaries, ELX40.TAR and instructions.
  Use this update pack with the unchanged local images; CF already includes these builds.
- `hp200lx-4.0-source.tar.gz`: matching kernel/loader/application sources and build guide.
- `hp200lx-4.0-image-tools.zip`: injector, offline CF growth/build tools and preserved build inputs.
- `SHA256SUMS.txt`, `MANIFEST.json`: hashes, exact sizes and provenance.

Allow 320 KiB free C: space for boot files and generated kernel, plus the selected
MNX file. Keep loader/kernel versions matched. Whole-card CF images replace card
contents; MNX files are ordinary DOS files and must not be written as whole disks.

## Acceptance and limitations

Hardware acceptance closed by the maintainer on 2026-10-21, including sleep guards.
Factory-/double-speed, local/CF storage, Accton networking and repeated recovery
were exercised. Both post-test local images passed forced read-only offline
filesystem checks, with no structural errors; clean flags were unset and not
rewritten. 39 kernel/loader checks passed, none skipped. Packaging verifies frozen
binary/image identity. See the repository acceptance summary for evidence scope.

Local sleep remains opt-in and idle-shell-only. Graphics, serial sessions, general
application suspend, NIC hot-plug, arbitrary NICs and active-TCP survival are not
qualified. CF `edit` sleep does not imply local `edit` sleep. Charging is experimental,
locked by default, and not certified. ELXcap's Alt+period hook is not in these kernels.

The 720 KiB/3 MiB images retain older ELX builds and their original banners; use
the separate update pack for current utilities. The corrected HP Nano-X programs
are in CF images. Stock-derived local userland may print SO_NOBUFFER errors when
starting server daemons; DHCP/client browsing was verified using ktcp. High-zone
CF growth validation is host-side, not a blanket physical-card qualification.
Large webpages can be slow and exhaust the compact image's spare space.

PicoPCMCIA/DualSlot, broader NIC support and a minimal no-sleep kernel profile
remain future work. No new features were introduced while promoting FINAL2b.
'''
(D/'RELEASE-4.0.md').write_text(notes)
(D/'ACCEPTANCE-4.0.md').write_text('''# Release 4.0 hardware acceptance

The maintainer declared all planned tests complete on **2026-10-21**, including
sleep-guard behaviour, and authorized release. This records acceptance of the
FINAL2b promotion; it does not fabricate individual measurements absent from logs.

| Coverage | Evidence and result |
| --- | --- |
| Local boot | 720 KiB and 3 MiB images exercised on hardware; stock v0.9.2 FD2880 boot/browser also demonstrated. Exact FINAL2b local identities confirmed by serial on both speed variants. |
| Accton sleep, both speeds | User reported six connected-cable sleep/wake cycles, including a roughly 30-second sleep. Serial checks retained ktcp PID 4 across repeated checks and verified marker hashes, new writes, DNS, fresh HTTP and GIF download after wake. |
| Internet after wake | FrogFind HTML fetched (1,273 bytes) and GIF (1,888 bytes); GIF MD5 7ca81e8805d80095e8de8baf2c1b87b3. No ktcp restart for those checks. |
| Local double persistence | /root/sleep2, MD5 e5ba02f8716d16acefcc92e600fab736, matched before/after and in the DOS backing image. |
| Local single persistence | /root/sleep2b, MD5 4b4322e154f0e0d98d4d7fabe525b56a, matched after repeated wake and reboot. |
| Offline local checks | Entire single image downloaded; double image reconstructed from 4 KiB CRC map/delta and independently matched against whole-file DOS CRC/length. Forced read-only mfsck -fsv exited 0 for both; copied images unchanged. |
| Offline caveat | Both post-test copies had state 0: clean flag unset, error flag unset. No structural errors found, no repair/flag rewrite performed. Cause of the flag state not established. |
| CF | Both speed variants exercised during acceptance. Exact FINAL2b double CF identity confirmed; user reported edit sleep. Old markers remained unchanged; new cf2bprobe MD5 6d41fc2811f5e4145930745e2b18eaa5 survived reboot. Single exact-FINAL2b CF detail is not separately captured in the final serial record; maintainer closed overall acceptance. |
| Empty-slot local double | FINAL2b local root confirmed; user reported shell sleep and edit refusal. Existing marker matched; new write/sync/read succeeded. Source explicitly restricts local sleep to PID 1 idle shell. |
| Guards | Maintainer confirmed sleep guards work. Local edit refusal is expected. Graphics/serial/general-app suspend are excluded. |
| Applications | User confirmed ELXbat partial updates/power status, ELXdash menu/locked charging, and Commander view/copy/no-overwrite/move/delete/cancel/mkdir/nonempty-directory refusal. Serial checked file hashes. These utility binaries did not change during FINAL2b promotion. |

## Frozen build identity

- KERNLOC SHA256: 800272df3f11dda6e4e98864c691f15025fff934c8ced128856f980704ab81b1
- KERNCF SHA256: e48701173b95857289547ecc958ae62580bc4a7f150395ee23d1827abdeeffa5
- Build identity: hp200lx-3.9-final2b-local / hp200lx-3.9-final2b-cf, 2026-10-20.
- Software suite: 39 discovered, 39 passed, zero skipped. Preserved-image handoffs
  and unchanged utility hashes/audits also passed.
- Image construction: independent Minix checks, payload/metadata comparison and
  reproducible images. CF growth has 13 regression tests plus host-side data beyond
  32 MiB readback/fsck; it is not evidence of physical high-zone access on every card.

Offline copy SHA256s (used images, not distribution downloads):

- Single: 155a11c7b6688d7b25024e2983988b4135e8df56675784985bd823d26ce811e7
- Double: a535653d246b609b029667191aa7cdd7e52422e3a7eae4f3e5930f4eda3e969a

Raw chronological hardware notes remain in the project acceptance archive.
The release source includes frozen software-validation reports. Earlier reports
marked “hardware pending” retain their original dates; this acceptance summary
supersedes that status, without changing historical evidence.
''')
(D/'BUILD-4.0.md').write_text('''# Release 4.0 source and build guide

Download `hp200lx-4.0-source.tar.gz` from the release and verify SHA256SUMS.
The authoritative matching source is the archive's `hp200lx-4.0-source/` tree.
Repository-root ELKS source/build instructions are historical; use this snapshot
for the released HP kernels. `src/` contains ELKS, `ports/local1/` the DOS helpers
and kernel profiles, `applications/` the frozen ELX sources, and `vendor/` the
browser/graphics sources and notices. `SOURCE-HISTORY.md` preserves provenance.

The package promotes FINAL2b without recompiling or changing binary IDs.
Build on a Linux host with the ELKS IA16 cross toolchain, NASM, make, Python 3
and a C compiler. The toolchain is an external dependency, not included.
From the extracted root:

```sh
export CROSS=/absolute/path/to/elks/cross
bash ports/local1/build.sh
bash assemble-final2.sh
```

The build creates CF and local kernels and their matching sizes/maps/helpers.
`ports/local1/RUNELKS.BAT` uses the fixed C:\\ELKS39FB directory. Do not change
kernel size constants or combine helpers from another build. The source archive
also includes frozen linked artifacts for the emulator checks and comparison.
No claim of cross-toolchain byte reproducibility is made for an arbitrary compiler.

For software checks, install Python `unicorn` and supply the original files:

```sh
export HPLOCAL_TEST_IMAGE=/absolute/path/to/fd2880-minix.img
export HPLOCAL_720_IMAGE=/absolute/path/to/ELKS2M.MNX
export HPLOCAL_3M_IMAGE=/absolute/path/to/ELKS4M.MNX
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 verify-preserved.py
```

Run checks from the extracted root. `verify-preserved.py` uses the historical
FINAL2 validation manifest to check unchanged filesystem/application inputs.
Individual utility build instructions remain in applications/*; ELKSWeb source
and its external-build integration are maintained at https://github.com/l00nix/ELKSWeb.
The source archive includes the browser snapshot matching the shipped binary.

The image-tools ZIP includes the stock-image injector and exact historical CF
build inputs. Their historical READMEs describe original candidate construction;
use the 4.0 README for installation and support scope. Existing image/kernel
banners are deliberately retained. No proprietary HP ROM or DOS runtime is bundled.
''')
(D/'ELX-TOOLS-4.0.md').write_text('''# ELX tools in Release 4.0

CF images already contain the tested updates. The unchanged local MNX images
contain earlier builds; use `hp200lx-4.0-elx-tools.zip` to update those or an older
filesystem. These executables run under ELKS, not DOS.

Transfer individual files from `bin/` to a writable ELKS filesystem. For a roomy
filesystem, transfer `ELX40.TAR`, then from /root run `tar xf ELX40.TAR` and
`cd /root/elx40`. Run `./elxbat` etc. to select the update rather than /bin's older
copy. Check `df` before transfer: the 720 KiB image may not have room for both
archive and extracted files. Transfer one executable at a time when space is tight.
To install permanently, keep a host backup, then copy the chosen executable to
/bin and `chmod 755 /bin/NAME`. No automatic installer is run.

| Program | Usage |
| --- | --- |
| ELXbat 0.1.4 | `elxbat`; partial redraw of changed regions, light theme, two voltage gauges, power icon and nominal warning markers. R rereads, Q/Esc exits. |
| ELXstat | `elxstat`, `elxstat -v`; firmware/system summary including cached battery volts and power source. |
| ELX Commander | `elxcmd LEFT RIGHT`; Tab switches panel; arrows select; Enter opens; V views; C copies; M moves; D deletes; N creates directory; R refreshes; Q returns from viewer or exits panels. Read each confirmation prompt. Existing destinations are not overwritten. |
| ELXdash 0.2.0-test4 | `elxdash`; Tab selects, Left/Right adjusts; B opens Battery menu; Up/Down selects, Enter chooses, Esc cancels. Q exits. Charging stays locked without explicit `--charge-test`; charging is experimental and not certified by this release. |
| ELXctl | `elxctl status`, `elxctl contrast 16`, `elxctl volume 2`, `elxctl zoom 80x25`, `elxctl annunciators right`, `elxctl firmware-timeout 180`. `--help` lists options. Firmware timeout is not ELKS's sleep policy. |
| ELXcap | `elxcap /root/SCREEN.BMP` captures the HP display. `-f pbm` selects PBM; default BMP and PBM preserve the same monochrome pixels. Existing files are not overwritten. |

Delayed capture from the palmtop:

```sh
elxcap -q -d 15 /root/BATTERY.BMP >/tmp/elxcap.log 2>&1 &
elxbat
```

Leave ELXbat visible for at least 15 seconds. Alternatively, run a manual capture
from an existing serial shell while the desired display remains on the HP.
The optional `--hotkey` / Alt+period kernel integration is not included in 4.0;
“kernel patch needed” for that mode is expected.

Battery values are firmware-cached voltages of unknown age, not percentages or
remaining runtime. Gauge triangles are nominal BIOS reference thresholds;
firmware alert flags are shown separately. Release acceptance does not establish
ADC freshness or certify charging. Sleep is blocked while graphics tools run.

Original GPL/font notices accompany the source. GEMCAP/CAPLX inspired capture,
CXCTL and ABC/LX informed control workflows, and Commander uses the familiar
Norton Commander two-panel model; these are independent implementations.
''')
cf=(P/'output/hp200lx-release4-cf-c1/README.md').read_text()
# Keep the detailed growth procedure while replacing stale candidate/publication sections.
growth=cf[cf.index('## One base image'):cf.index('## Validation and remaining hardware tests')]
(D/'CF-IMAGES-4.0.md').write_text('''# Release 4.0 CF images and offline growth

Release 4.0 preserves the four candidate-1 image bytes. Use the separate 4.0 boot
ZIP (FINAL2b) in C:\\ELKS39FB; any older embedded /linux or release banner is
historical. The DOS loader selects the kernel from C:, not /linux on the card.
CF images include the tested ELX utility updates and corrected HP Nano-X suite.

All profiles use one Minix V1 partition starting at sector 63, 1 KiB blocks,
14-character names and 2048 inodes (1561 initially free). Growth adds data space,
not inodes. The 8/16/32/64 MB profiles occupy 7/14/30/60 MiB of card space.
The main README lists exact byte counts; a physical card must be at least that large.

'''+growth+'''## Validation

All four distribution images passed independent host filesystem checks and
content/metadata comparison. The growth suite passed 13 tests; a 34 MiB fixture
allocated zones beyond 32 MiB and read back with a matching hash. Growth after
adding a simulated user file preserved that file. These are host-side results.
Hardware storage/sleep/persistence acceptance is summarized separately; it does
not imply physical high-zone testing on every capacity/card combination.

Image build sources and exact pinned inputs are included in the image-tools ZIP.
The historical candidate reports are preserved as provenance, not current
installation instructions. Images themselves are unchanged for the 4.0 promotion.
''')
print('Prepared', len(list(D.glob('*.md'))), 'release documents')
