# HP 200LX ELKS — Strategy

Status as of 2026-06-13. This document captures where the project stands, the
hard-won hardware constraints, and the ranked forward plan. It complements the
chronological build log in [`BRINGUP_LOG.md`](BRINGUP_LOG.md).

Related work: the native-keyboard/timer investigation tracked in
`l00nix/hp200lx-elks-investigation` and ELKS issue **ghaerr/elks#2236**.

---

## 1. Where we are — milestone reached

ELKS runs as a **usable interactive shell on a real, stock-clock HP 200LX**,
driven by an **Apple Newton keyboard** over the serial port:

- Boots cleanly to `/bin/sh` (BIOS console, RAM-root minix fs).
- Newton keyboard **types into the shell** (letters, shift/caps, Ctrl, Tab,
  Return, Backspace, arrows).
- **fork()/exec works**: external commands such as `ls` and `cat` run (`cd`
  is a shell builtin, so it isn't itself fork evidence).
- Root filesystem is **stable** — no corruption under normal use.

This is a confirmed usable ELKS shell on this hardware with working input.

### How it works (the two key mechanisms)

1. **Idle-loop input.** ELKS kernel timers never fire on the 200LX (see
   constraints below), so the timer-driven keyboard path is dead. Instead we
   poll the serial UART from the kernel **idle loop** in `init/main.c` and feed
   decoded keystrokes into the console tty queue (`Console_conin()` →
   `chq_addch()` → `wake_up()`), which resumes the shell blocked in
   `tty_read()`. No timers, no IRQs required.
2. **Memory-map fix (N24).** The DOS loader preloads the 360K RAM-disk root at
   a fixed mid-RAM segment (`0x3200`), but ELKS sized usable memory from BIOS
   `INT 12h` (636K) and assumed the ramdisk was at the top — so the process
   pool overlapped the root fs and `fork()` corrupted it. N24 caps the pool at
   the ramdisk start and `seg_add`s the conventional RAM above the ramdisk back
   to the free list.

---

## 2. Hard-won hardware constraints (do not relearn these)

- **No timer interrupt.** The Hornet ASIC does not deliver `IRQ0`/`Int 08h` to
  ELKS; `timer_tick()`/`timer_bh()` never run. Consequence: **no kernel timers,
  no `jiffies`, and any timer-driven polling is stillborn.** Use the idle loop
  (or eventually an `Int 0Ah` hook) instead. This is the core of issue #2236.
- **`tty_ops.read` is a trap.** A non-NULL `read` hook makes `tty_read()`
  non-blocking → `-EAGAIN` → ash reads EOF and exits. Don't use it; feed the
  tty input queue from the idle loop instead.
- **Double-speed units need DSPEED.** On a crystal-upgraded ("double-speed")
  200LX, the Hornet clock registers must be programmed (as Stefan Peichl's
  `DSPEED.COM` does, re-asserted on `Int 0Ah`) or serial timing is wrong and
  the keyboard produces garbage. Stock-clock units work without it. The current
  milestone is on a **stock-clock** unit; double-speed support is a later port.
- **No XMS / no HMA.** Both break a clean boot on this hardware (established by
  the timer investigation). Extended memory is therefore not currently usable
  for buffers/ramdisk.
- **RAM-root theoretical memory ceiling ≈ 150K.** 636K conventional − 360K
  ramdisk − kernel leaves ~75K below the ramdisk plus a possible ~76K reclaimed
  above it (the high region is on the free list but not yet stress-proven — see
  §3). The ramdisk can't shrink (its minix fs is 360K, 307K used). This ceiling
  is the main argument for moving root off the RAM disk (see disk-root track).
- **Fragile DOS loader chain.** `BTGVD67`/`PUT13`/`MKINTS` + a fixed kernel
  command line. Silent failures (`No ELKS setup signature found`) come from
  image-layout/copy issues. Keep the proven boot shape; change one variable at
  a time; always verify patches actually applied (build-time greps).
- **Newton keyboard ↔ 200LX only.** The keyboard's cable ends in the
  proprietary HP serial plug, so all serial bring-up must be done on the
  palmtop itself, not a modern host.

---

## 3. Still broken / open

- **The built-in HP 200LX keyboard does not work under ELKS.** This is the
  original problem (#2236) and is *still unsolved* — the Newton keyboard is a
  workaround, not a fix. The unit is not truly self-contained until the local
  keyboard works. Root cause is the same dead timer/IRQ path: the native
  keyboard is polled from the timer bottom half, which never runs.
- **The +76K high-memory reclaim (N24 patch 2) is not yet stress-proven** — it
  is on the free list but the boot banner shows only the 75K low pool; fork may
  currently be served from the low pool alone.
- **Double-speed unit support** not yet ported to ELKS (DSPEED register writes).

---

## 4. Forward plan (ranked)

### Track A — Harden the current milestone (smallest, do first)
- **A1. Restore `CONFIG_FS_NR_EXT_BUFFERS` upward from 8** (e.g. 16–24). Two
  birds: better disk cache *and* it forces allocations onto the reclaimed
  high-memory region, stress-testing N24 patch 2.
- **A2. Filesystem confidence checks** (no rebuild): cold-boot several times,
  `cat` more files under `/etc` and `/bin`, create/remove in `/tmp`.

### Track B — Get the built-in HP 200LX keyboard working ⟵ explicitly wanted
The unit isn't self-contained until this works. Now that idle-loop input is
proven, apply the same mechanism to the native keyboard:
- **B1. Probe the BIOS keyboard buffer from the idle loop.** Read the BDA ring
  buffer head/tail at `0040:001a`/`0040:001c` and **first confirm the pointers
  move** when a key is pressed. The native keyboard works under DOS, so the
  BIOS keyboard ISR *should* still fill the buffer — but it depends on the same
  Hornet interrupt path that's broken for the timer, so verify before trusting.
- **B2. If the buffer fills,** feed `Int 16h` / BDA keystrokes into the console
  tty queue from the idle loop (exactly like the Newton path). If it does
  **not** fill, the native keyboard needs its own interrupt-path work — which
  loops back into the core #2236 timer/`Int 0Ah` investigation.
- **B3. Stretch goal:** revive a real periodic tick via an `Int 0Ah` hook
  (DSPEED proves `Int 0Ah` fires periodically; `CONFIG_TIMER_INT0F` shows ELKS
  already supports an idle-simulated tick). A working tick would resurrect
  `jiffies`, kernel timers, *and* the stock `kbd-poll.c` native-keyboard path
  in one move.

### Track C — Disk-root on the internal C: drive (durable RAM fix + networking)
Removes the 360K RAM-disk tax entirely, is persistent, and keeps the single
PCMCIA slot free for a network card. Sequence (cheapest-information-first):
- **C1.** Diagnostic: call BIOS `Int 13h` from ELKS to read drive `0x80`
  (sector 0 + later sectors) and confirm the C: drive is reachable *after* ELKS
  takes over (the loader proves it works pre-boot; surviving the handover is
  the open risk — `Int 13h` is synchronous so it should sidestep the dead IRQ
  path).
- **C2.** Mount C: read-only via the BIOS-HD driver; hammer repeated reads.
- **C3.** Read-only FAT root + a small RAM disk for `/tmp` (ELKS FAT writes are
  weak, so keep root read-only).
- **C4.** Only later: a dedicated minix area/partition on C: for a read-write
  root, with a non-destructive layout and recovery plan.

### Track D — Productize: HP 200LX platform port
Fold the above into a proper platform layer (a `CONFIG_ARCH_HP200LX`-style
option) rather than scattered IBM-PC conditionals: Hornet clock setup
(stock/double-speed), idle-loop input, timer revival, disk quirks. Expose the
*variable* features as `/bootopts` runtime switches (`dspeed`, `newtonkbd`,
clock speed) instead of a kernel build matrix. Defer double-speed
auto-detection until a clock-independent timebase exists.

---

## 5. Immediate next step

**Track A1** (restore buffers, stress-test the high-memory reclaim), then begin
**Track B1** (probe whether the native keyboard's BIOS buffer fills from the
idle loop) — the highest-value move toward a self-contained unit.
