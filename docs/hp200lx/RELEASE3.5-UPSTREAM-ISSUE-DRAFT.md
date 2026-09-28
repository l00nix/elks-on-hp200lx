# HP 200LX update: upstream-based ELKS with HP firmware keyboard support

Since the earlier Newton-keyboard report, the downstream port gained a working
built-in keyboard and persistent PCMCIA/CF root filesystem. The latest step is
Release 3.5: rebuilding the HP support on a clean ELKS baseline rather than carrying
forward the experimental direct matrix scanner.

Release 3.5 starts at upstream `69dfd4f274139ef1f533c646711db84902b0cfe4`, with separate
patches for the HP firmware platform, PCMCIA/CF quirks and DOS kernel load address.
It is our closest build to vanilla ELKS so far, although still a downstream port.

The working GentleOS port and historical MINIX-on-HP-200LX work suggested keeping
the HP firmware services alive. ELKS now preserves the firmware NMI vector and
calls the original ROM IRQ2 service, which handles keyboard scanning/debounce
and produces scan codes for ELKS's standard IRQ1 keyboard/TTY path. This is not
INT 16h polling. The ROM owns IRQ2 acknowledgement; firmware RAM is reserved,
and incompatible PC keyboard-controller operations are suppressed under the HP
configuration. No Mack MINIX source was copied; the existing DOS loader chain
does retain its historical MINIX-on-HP-200LX provenance.

The timer work also produced a narrowly guarded, one-time IRQ0 handoff, replacing
the earlier reliance on idle-loop input polling. CF waits use upstream jiffies
again, and the standard ELKS allocator replaces the experimental split-pool
workaround. Release 3.5 restores the working `0340h` DOS kernel load address after the
first clean extraction exposed an early-boot regression at `00B0h`. The exact
underlying low-memory conflict and inherited IRQ0 state are still being investigated.

On the real HP 200LX, Release 3.5 reaches a shell, mounts `/dev/cfa1` as Minix root,
and accepts basic built-in keyboard input. Zoom and panning have also been
confirmed on Release 3.5. Testing is still in progress for modifiers/repeat, Ctrl-C,
timer accuracy and sustained writes;
power management is not established. Earlier FW1D3 successes are not being
claimed for this exact binary. The existing Release 3/3.1 userland is reused.

- [Release 3.5](https://github.com/l00nix/elks-on-hp200lx/releases/tag/hp200lx-release-3.5)
- [Source branch](https://github.com/l00nix/elks-on-hp200lx/tree/hp200lx-release-3.5)
- [Changes from the upstream base](https://github.com/l00nix/elks-on-hp200lx/compare/69dfd4f274139ef1f533c646711db84902b0cfe4...hp200lx-release-3.5)
- [Architecture, reproduction and validation notes](https://github.com/l00nix/elks-on-hp200lx/blob/hp200lx-release-3.5/docs/hp200lx/RELEASE3.5.md)

Thanks for the earlier pointers toward the timer, interrupt controller and HP
documentation. This gives us a much smaller platform-specific change to review.
