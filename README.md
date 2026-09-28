# ELKS on HP 200LX — Release 3.5.2c

[Release 3.5.2c](https://github.com/l00nix/elks-on-hp200lx/releases/tag/hp200lx-release-3.5.2c)
measures every valid task-stack ROM call to improve coverage after 3.5.2b's
single task sample. Shared-stack sampling remains one in 32 and guards are
checked on every valid call. `meminfo` prints four HPST lines with
`sample=all/32`; task sample and call counts should match.

Build/emulator checks pass. Photo 25824 confirms **8 measured task calls out of 8**, with task/shared peaks
82/700 and 222/1,024 bytes. Shared samples are 148 from 4,735 calls. Both guards
and `unknown` are zero; meminfo reports 376K free. The `sample=all/32` mode is
working in this run. Longer workload coverage and an explicit speed/control
report remain pending. [Hardware evidence](https://github.com/l00nix/elks-on-hp200lx/blob/codex/hp200lx-release-3.5.2c/docs/hp200lx/hardware-results/2026-09-28-3.5.2c-meminfo.md).

Use `C:\ELKS352C` and `RUN352C` with the existing CF root card.
[Instructions and measurement limitations](docs/hp200lx/RELEASE3.5.2C.md).
[3.5.2b hardware evidence](docs/hp200lx/hardware-results/2026-09-28-3.5.2b-meminfo.md).
Task/shared stack sizes remain 700/1,024 bytes, relocation 0340h. RAMdisk and
networking remain disabled; DOS-style ON/OFF suspend remains unsupported.
Stable 3.5 remains stable. Keep 3.5.2b as the recent working diagnostic fallback.

---

![logo](https://github.com/ghaerr/elks/blob/master/Documentation/img/ELKS-Logo.png)


![cross](https://github.com/jbruchon/elks/workflows/cross/badge.svg)
![main](https://github.com/jbruchon/elks/workflows/main/badge.svg)


# What is ELKS?

ELKS is a project providing an early fork of the Linux OS for systems based on the Intel
IA16 architecture (16-bit processors: 8086, 8088, 80188, 80186, 80286, NEC V20, V30
and compatibles). Such systems can be ancient computers (IBM-PC XT / AT and clones)
as well as more recent SBCs, SoCs, FPGAs, as well as modern 80386+ x86 desktops.
ELKS supports networking, graphics, ia16-elf-gcc, OpenWatcom C and its own native
C compiler, and installation to HDD using both MINIX and MSDOS FAT filesystems.

## Memory requirements

* Stock images require 512k RAM
* ELKS requires 256k RAM to run, 512k to be really useful
* No hardware MMU required
* ROM-based systems can run in 128k RAM

## Try ELKS online
You can [play with ELKS online](https://copy.sh/v86/?profile=elks) thanks to the v86 emulator. Login with "root" and no password. Go to the bin folder and try the different commands available. Try nxtetris. Start the game by pressing "n".
  
## Watch ELKS in action

- [ELKS, a 16-bit no-MMU Linux on Amstrad PC 2086](https://www.youtube.com/watch?v=eooviN1SdQ8) (thanks @pawoswm-arm)
- [Booting ELKS on an old 286 MB from 1,44MB floppy](https://www.youtube.com/watch?v=6rwlqmdebxk) (thanks @xrayer)
- [Epson PC Portable Q150A / Equity LT (Nec V30 8086 - 1989)](https://youtu.be/ZDffBj6zY-w?t=687) (thanks Alejandro)
- [ELKS on ESP32 through IBM PC emulator](https://www.youtube.com/watch?v=Tr2yMjrgP8o) (thanks @fdivitto)

## Screenshots

ELKS running on QEMU
![ss1](https://github.com/ghaerr/elks/blob/master/Screenshots/ELKS_0.7.0.png)

Nano-X running on ELKS
![ss8](https://github.com/ghaerr/elks/blob/master/Screenshots/Nano-X_on_ELKS.png)

Olivetti M24 8086 CPU
![ss2](https://github.com/ghaerr/elks/blob/master/Screenshots/Olivetti_M24_8086_CPU.png)

ELKS Networking showing netstat and process list
![ss3](https://github.com/ghaerr/elks/blob/master/Screenshots/ELKS_Networking.png)

Running ELKS Basic on PC-9801UV21 (NEC V30 CPU)
![ss4](https://github.com/ghaerr/elks/blob/master/Screenshots/PC-9801UV21_V30_CPU.png)

Running Matrix and vi on multiple consoles
![ss5](https://github.com/ghaerr/elks/blob/master/Screenshots/ELKS_Matrix.jpg)

Of course Doom
![ss6](https://github.com/ghaerr/elks/blob/master/Screenshots/ELKS_Doom.png)

Telnet to an old BBS
![ss7](https://github.com/ghaerr/elks/blob/master/Screenshots/ELKS_telnet_BBS.jpg)

## Downloads

A full set of disk images are available for download, for you to try out ELKS: [Downloads](https://github.com/ghaerr/elks/releases).

## How to build

Full build instructions are [here](https://github.com/ghaerr/elks/blob/master/BUILD.md).

## Wiki

Help on how to use ELKS, as well as technical tutorials, are available on our [Wiki](https://github.com/ghaerr/elks/wiki).

## Documentation

More information is in the Documentation folder: [Index of ELKS Documentation](https://htmlpreview.github.io/?https://github.com/ghaerr/elks/blob/master/Documentation/index.html).

## Resources

Other projects and resources interesting to ELKS and our programming community:

- [8086 toolchain](https://github.com/ghaerr/8086-toolchain) A full C toolchain capable of running on Linux, macOS and natively on ELKS, featuring C compiler
and preprocessor, as86 assembler, ld86 linker, disassembler, make, and a complete C library.
- [blink16](https://github.com/ghaerr/blink16) A visual 8086 emulator and debugger capable of booting the ELKS kernel for symbolic debugging, as well as an emulator for ELKS executables.
- [Size Optimization Tricks](https://justine.lol/sizetricks/) A great article from Justine Tunney's blog showing how big things can be done without bloat.
- [gcc-ia16](https://github.com/tkchia/gcc-ia16) TK Chia's gcc compiler targeted for 8086, maintained and used for the ELKS kernel and all its applications.

## More information

Questions? Problems? Patches? Open an issue on the ELKS GitHub project!
