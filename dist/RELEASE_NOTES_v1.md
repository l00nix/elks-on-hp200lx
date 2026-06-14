# Release 1 — "Newton" (Partial Success)

*This is an unofficial downstream/community release from
`l00nix/elks-on-hp200lx`, not an upstream ELKS release.*

First bring-up release of ELKS on the HP 200LX. **ELKS boots to a usable
interactive shell on a real, stock-clock HP 200LX with working keyboard input —
via an external Apple Newton keyboard on the serial port.** The built-in HP
200LX keyboard does not work yet; this is a partial success and a workaround,
not a fix for that problem.

Based on upstream ELKS commit `69dfd4f2`. Kernel: `KERNBOP`, 58416 bytes,
sha256 `8941be7245707b17394b01c783084b6b3ca50ba4948e3327e7e5f5f99ce90094`.

## Works
- Boots to `/bin/sh` (BIOS console, RAM-root minix fs) on a stock-clock 200LX.
- Apple Newton serial keyboard types into the shell (Shift/CapsLock/Ctrl/Tab/
  Return/Backspace/arrows).
- `fork()`/`exec()` work; external commands such as `ls` and `cat` run; `cd`
  works as a shell builtin; root filesystem stable.

## Limitations
- Built-in HP 200LX keyboard does **not** work — external Newton keyboard only.
- Stock-clock units only (double-speed units need Hornet clock setup, not yet
  included).
- RAM-root ceiling is roughly ~150 KB in theory (~75 KB low pool plus a
  possible ~76 KB reclaimed above the ramdisk); the reclaimed high region is
  not yet stress-tested.
- No kernel timer (Hornet doesn't deliver IRQ0); input is polled from the idle
  loop.

## Install
Unzip `elks-hp200lx-v1-newton-N24.zip`, copy the `FIRSTTEST_NEWTON_N24/` files
to `C:\ELKS` on the palmtop, wire the Newton keyboard to the serial port, then
run `RUNN24` from DOS. Full details and wiring in the repository README.

## How it got here
A long diagnostic series (N0 → N24): proving the Newton serial protocol,
discovering that ELKS kernel timers never fire on this hardware (so input is
polled from the idle loop), then fixing a RAM-root/user-memory overlap that was
corrupting the root filesystem once `fork()` worked. The full log is in
`docs/hp200lx/BRINGUP_LOG.md`.

## Next
Get the built-in keyboard working (idle-loop BIOS-buffer poll, or an `Int 0Ah`
timer-hook to revive the tick), then disk-based root and double-speed support.
See `docs/hp200lx/STRATEGY.md`.

## Credits
ELKS / ghaerr and the ELKS authors (GPLv2); K. Adachi for the `NTKPAC05`
Newton-keyboard wiring/protocol reference; Stefan Peichl for `DSPEED.COM`
double-speed clock behavior reference.
