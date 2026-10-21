# HP 200LX package 4.0 — ELKS 0.9.2

Release 4.0 provides the accepted dual-kernel implementation with consistent
4.0 naming. Install the boot folder at **C:\ELKS4**. Kernel IDs are
`hp200lx-4.0-local` and `hp200lx-4.0-cf`, dated 2026-10-21.

**Naming refresh, 21 October 2026:** boot folder/helper names, kernel version
text, image banners and instructions now use 4.0. Application payloads and
filesystem sizes are unchanged. Replace the complete boot folder when updating;
existing personal MNX/CF filesystems can continue to be used without reimaging.
Historical release tags and acceptance records are retained.

## Changes since published 3.5

| Area | Changes |
| --- | --- |
| HP firmware integration | Expanded/refined BIOS keyboard, display and power handling. Version 3.5 already had ROM keyboard, zoom and panning; subsequent work integrates focus, recovery and controls more completely. |
| Memory recovery | Reserved firmware area reduced to 4 KiB, reaching the 636 KiB conventional-memory boundary. Development reclaim probes and `/ARM` flags removed from normal startup. This is not free application RAM. |
| Single/double speed | `/DS` display correction; factory-speed and accelerated hardware exercised. |
| Dual-kernel boot | One `RUNELKS` launcher chooses a CF-only kernel or local/NIC kernel, with matched DOS helpers. CF is the default or explicit `/CF`; `/LOCAL C:\NAME.MNX` selects internal storage. |
| CF storage | Improved initialization/recovery, validated writable root with fallback, sleep/wake and reboot persistence. Refreshed 8/16/32/64 MB image profiles. |
| Internal filesystem | Writable banked C: filesystem access leaves PCMCIA available for Ethernet. Image-length/mapping checks replace the old fixed-size restriction; 720 KiB, 3 MiB and stock upstream v0.9.2 2.88 MB filesystems tested. |
| Sleep/wake | Guarded CF sleep including the tested `edit` case. Opt-in writable local empty-slot `/NONET /SLEEPTEST`; Accton `/SLEEPNIC` preserves idle ktcp and recovers network hardware. Local sleep requires the idle initial shell. Unsupported activity gets refusal message/beep. |
| Networking | Accton EN2216 R02 initialization and IRQ recovery, DHCP with stock-derived local userland, DNS and live HTTP. Repeated connected-cable sleep/wake followed by fresh requests on both speed variants. |
| Console/serial | ANSI startup support and `/root/ser`; stock diagnostics ABI compatibility. Serial shell exit uses peer `exit`; local Ctrl+C behaviour varies by image. |
| Nano-X | Corrected startup, divide fault, JPEG rendering and text restoration; CF images include `nx`, terminal, clock and viewer. |
| ELKSWeb | Native graphical HTTP browser with offline welcome page, GIF rendering, digit-leading hostnames and argument-forwarding `web`; 68k.news and FrogFind rendered on real HP hardware. |
| ELX tools | ELXbat/ELXstat, Commander, ELXctl, ELXdash and ELXcap. Updated battery redraw and power status; dashboard controls and experimental charging lock; Commander file operations checked. Cached volts are not charge percentages. |
| Images and growth | 720 KiB/3 MiB local test images with refreshed banners plus four CF capacities. Host-side CF growth script; no online/first-boot resizer. |
| Documentation | Two installation paths, SVG key shortcuts, hardware photographs, usage guides, source/asset manifests and practical reboot/sleep limits. |

## Downloads

- `hp200lx-4.0-boot.zip`: required, 11 matched boot files under ELKS4.
- `hp200lx-4.0-local-images.zip`: ELKS2M.MNX (737,280 bytes), ELKS4M.MNX (3,145,728 bytes).
- `hp200lx-4.0-cf-{8,16,32,64}mb.zip`: whole-card images, respectively
  7,340,032 / 14,680,064 / 31,457,280 / 62,914,560 bytes after extraction.
- `hp200lx-4.0-elx-tools.zip`: tested utility binaries, ELX40.TAR and instructions.
  Use this update pack with the local images; CF already includes these builds.
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
rewritten. 39 kernel/loader checks passed, none skipped. Packaging verifies release hashes, naming-only kernel changes and unchanged application payloads. See the repository acceptance summary for evidence scope.

Local sleep remains opt-in and idle-shell-only. Graphics, serial sessions, general
application suspend, NIC hot-plug, arbitrary NICs and active-TCP survival are not
qualified. CF `edit` sleep does not imply local `edit` sleep. Charging is experimental,
locked by default, and not certified. ELXcap's Alt+period hook is not in these kernels.

The 720 KiB/3 MiB images retain older ELX builds with updated 4.0 banners; use
the separate update pack for current utilities. The corrected HP Nano-X programs
are in CF images. Stock-derived local userland may print SO_NOBUFFER errors when
starting server daemons; DHCP/client browsing was verified using ktcp. High-zone
CF growth validation is host-side, not a blanket physical-card qualification.
Large webpages can be slow and exhaust the compact image's spare space.

PicoPCMCIA/DualSlot, broader NIC support and a minimal no-sleep kernel profile
remain future work. No new features were introduced while promoting the accepted candidate.
