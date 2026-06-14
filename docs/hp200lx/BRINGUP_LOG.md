# N8 baseline decision

As of 2026-06-11, the real HP 200LX tests show:

- `FIRSTTEST_NEWTON_N8` still boots and shows the original N8 behavior.
- `FIRSTTEST_NEWTON_N9` fails before ELKS proper with `No ELKS setup signature found`.
- `FIRSTTEST_NEWTON_N10` also fails with `No ELKS setup signature found`, even though its local kernel image is smaller than N8.
- `FIRSTTEST_NEWTON_N11` reused the exact local N8 `KERNBOP` bytes, but the field result still failed in the N11 package.

Conclusion: stop treating N9/N10/N11 as forward progress on keyboard decoding.
The only trustworthy baseline is the original `FIRSTTEST_NEWTON_N8` package as
tested on the HP 200LX.

Likely trap
-----------

The DOS loader path is fragile. `BTGVD67.COM` contains image-layout diagnostics
such as:

```text
BAD IMAGE LAYOUT - no jump
Need END<=3000 SIG=AA55 SET=0004 H=0301 0430
```

The observed failure is printed by the ELKS setup code, which means the loader
started the image, but setup did not see the expected secondary setup
signature. Since original N8 still boots, future work should avoid changing
multiple variables at once.

Next useful approach
--------------------

1. Use the original `FIRSTTEST_NEWTON_N8` package for hardware observation.
2. Collect clean N8 output from exact key sequences before building more
   kernels.
3. When a new kernel is needed, first create a zero-feature rebuild that proves
   the build/output/copy path still boots before adding Newton changes.
4. Do not create more "known-good copy" folders unless there is a concrete
   reason; N11 showed that this can waste test cycles.

2026-06-11 update: root cause of the garbled N8 output found
------------------------------------------------------------

The original test unit is a double-speed (crystal-modded) HP 200LX. Without
Stefan Peichl's DSPEED.COM driver loaded, the Hornet clock registers are wrong
for serial timing, so COM1 at divisor 12 does not produce a real 9600 baud.
Under DOS on that unit, NTKEY2LX only works after DSPEED is loaded. DSPEED
(disassembled, no source) writes Hornet index registers via ports 0x22/0x23:
at install index 0x1E |= 0x30 and index 0x80 = 0x22; on every INT 0Ah while
active index 0x21 = 0x0E and index 0x22 = 0x29.

On a second, stock-speed HP 200LX, the unchanged FIRSTTEST_NEWTON_N8 package
boots and prints the expected sequence for the printable keys in its 50-entry
keymap (ids 0x00-0x31), in press order:

```text
1234567890-=<TAB>qwertyuiop[]\asdfghjkl;'<CR>
zxcvbnm,./
```

Silent keys are expected for the N8 diagnostic: backquote 0x32, Delete 0x33,
modifiers 0x36-0x3C, and arrows 0x7B-0x7E are not implemented in N8.

Conclusions:

1. N8's serial code, wiring, 9600 8N1, polling path, and printable keymap are
   correct on the stock-speed unit. N4-N8 garbage ("a l z") on the first unit
   was the double-speed clock chain.
2. The stock unit is now the primary ELKS development target.
3. For the double-speed unit, an ELKS-side port of DSPEED's register writes
   (with periodic re-assert, mirroring its INT 0Ah hook) is needed later.
4. Next kernel (N12): first prove a zero-feature N8 rebuild still boots on
   the stock unit, then extend the keymap (Delete=backspace, backquote,
   shift/caps state for upper case and symbols, arrows) and feed decoded keys
   into the ELKS TTY input path instead of the boot-time printk window.

2026-06-11 update: N12 hit the setup-signature loader trap
----------------------------------------------------------

N12 built successfully and is smaller than N8, but the full N12 package failed
on hardware with `No ELKS setup signature found`. This means the failure occurs
before the N12 Newton input code can run.

Because N11 also failed despite using local bytes identical to N8, treat this
as a DOS/FAT loader/copy-layout issue until proven otherwise. The next N12 test
should use `FIRSTTEST_NEWTON_N12_DROPIN`: keep the exact working N8 directory
on the HP 200LX and replace only `KERNBOP`.

2026-06-12 update: N12 drop-in still fails before the shell
-----------------------------------------------------------

The N12 drop-in test changes the failure mode but still does not reach the
ELKS shell. This means we are still failing before the N12 Newton input path can
matter.

As a control, the original N8 binary from `/home/arau/KERNN8` was compared with
a current rebuild from the same N8 build script:

```text
original /home/arau/KERNN8
  size:   57696
  sha256: 83f106be3d8ae10c5c55f025e5bf3b615f69e648f9849b6aacd783036961aa40

rebuild /home/arau/KERNN8_REBUILD
  size:   57696
  sha256: d1847c088b15765616dfd4ad5a4d6583d83a0fdd9b5ebb3dd53374167f627f70
```

The two images have the same size and same build-summary layout:

```text
Setup  1576 bytes / 4 sectors
System 55136 bytes / 0xd76 paragraphs
Final  57696 bytes
```

Only a few bytes differ near the end of the image, likely build metadata. The
next package, `FIRSTTEST_NEWTON_N13`, is this rebuilt N8 control. It should
behave exactly like N8 on the stock-speed HP 200LX, including the N8E/N8R/TYPE
markers. If N13 fails before the shell, stop changing Newton keyboard code and
debug the image/build/copy/loader path. If N13 boots, the current build path is
usable and the N12 changes become the suspect.

2026-06-12 update: N13 boots, so build N14 as a map verifier
------------------------------------------------------------

Hardware testing showed that N13 behaves like N8: it boots, receives the
Newton keyboard, and reaches the shell afterward. Therefore the current build
path is usable. Treat N12 as the suspect rather than the builder or loader
package.

`FIRSTTEST_NEWTON_N14` keeps the proven N8/N13 boot-time capture method and
extends only the key decoder: Delete, backquote, Shift/Caps symbols and case,
modifier labels, and arrow labels. It is intentionally not shell input. If N14
boots and the map is correct, the next useful build is N15: a small shell-input
attempt that reuses the N8/N14 initialization path and changes only the handoff
from decoded Newton bytes into ELKS input.

2026-06-12 update: N14 map verifier passes, build N15 shell input
-----------------------------------------------------------------

Hardware testing showed that N14 boots and all tested Newton keyboard keys
respond in the capture window, including Delete, Tab, Return, modifiers,
shifted letters/symbols, and arrows. This proves the stock-speed serial path
and keymap.

`FIRSTTEST_NEWTON_N15` removes the TYPE: capture loop. It initializes COM1 in
`kbd_init()`, prints `N15K`, then polls the Newton UART from the normal ELKS
keyboard timer at the original 8/100-second cadence. Decoded characters are
fed to `Console_conin()`. This keeps the N15 delta focused on the input handoff
and avoids the N12 timer-rate change.

2026-06-12 update: N15 repeats the setup-signature failure
----------------------------------------------------------

N15 failed before reaching ELKS shell with `No ELKS setup signature found`.
The `N15K` marker did not appear, so the Newton shell-input code did not run.
This matches N12 and suggests that the fragile boot image/layout dislikes the
no-capture shell-input shape, even though the N15 image is smaller than N14.

`FIRSTTEST_NEWTON_N16` keeps the N14-style capture first, then adds shell-input
polling after `N16END`. This tests whether preserving the boot shape that
worked for N14 allows the same decoded Newton path to feed `Console_conin()`
after the shell starts.

2026-06-12 update: N16 reaches a new failure, build N17 throttled input
-----------------------------------------------------------------------

N16 no longer looked like the earlier pre-shell setup-signature failures. The
reported behavior was that keystrokes printed vertically instead of
horizontally. That is forward progress because it suggests the Newton path is
running during or after the shell handoff, but the bytes are not being consumed
as normal typed input.

`FIRSTTEST_NEWTON_N17` keeps the same N16 boot/capture shape and keymap, but
tries a gentler shell handoff:

1. Drain any leftover UART bytes after the `TYPE:` capture window.
2. Feed at most one Newton byte per ELKS keyboard timer tick.

If N17 still prints vertically, the key observation is whether that happens
during the `TYPE:` capture window or only after `N17END` at the shell.

2026-06-12 update: build N18 BIOS-buffer input
----------------------------------------------

There was some ambiguity in the N16/N17 hardware run because an earlier build
may have been run by mistake. To test a different handoff path, build N18.

`FIRSTTEST_NEWTON_N18` keeps the same N14-style capture window and keymap, but
changes the shell handoff more substantially. Instead of calling
`Console_conin()` directly, N18 inserts decoded Newton keypresses into the
standard PC BIOS keyboard buffer at 0040:001e, updating the head/tail pointers
at 0040:001a/001c. The unchanged ELKS polling keyboard code should then read
the injected key through its normal `conio_poll()` / BIOS int 16h path.

If N18 types normally, the right integration path is probably a small Newton
poller that feeds ELKS through the existing keyboard driver shape. If N18 does
not type at all, the HP 200LX BIOS may not use the standard PC keyboard buffer
for int 16h reads.

2026-06-12 update: N18 stays in TYPE:, build N19 bounded capture
----------------------------------------------------------------

N18 showed `N18E`, `N18R`, and `TYPE:`, and the Newton keyboard printed decoded
diagnostic tokens there. However, after waiting more than a minute, `N18END`
did not appear. Commands typed during this phase were still only capture text,
not shell input.

This means the N18 BIOS-buffer handoff was not really tested. The capture loop
was waiting on BIOS data-area tick 0040:006c, and that tick is not trustworthy
at this early point in this ELKS boot path.

`FIRSTTEST_NEWTON_N19` keeps the N18 BIOS-buffer input method but replaces the
tick-based capture timeout with a short bounded spin. Expected result: N19
prints `N19END`, reaches the shell, and then tests whether BIOS-buffer-injected
Newton keystrokes are consumed by ELKS's normal `conio_poll()` path.

2026-06-12 update: N19 reaches shell but BIOS-buffer input is dead
------------------------------------------------------------------

N19 printed `N19E`, `N19R`, and `TYPE:`, then dropped into the ELKS shell after
a couple of seconds. At the shell, neither the native HP 200LX keyboard nor the
Newton keyboard worked. This suggests the BIOS keyboard-buffer injection path
is not useful on this HP 200LX/ELKS boot path, and/or the original BIOS/native
keyboard polling path is still able to block progress once the shell is up.

`FIRSTTEST_NEWTON_N20` keeps the bounded TYPE: capture and switches back to
direct `Console_conin()` injection, but replaces the timer body completely:
after boot the timer polls only the Newton UART, feeds decoded keypresses to
`Console_conin()`, and calls `restart_timer()`. It does not call the original
`conio_poll()` path. The native HP keyboard is expected to remain dead in N20;
the test is whether Newton input works when the BIOS poller is removed from
the loop.

2026-06-12 update: N20 reaches shell but direct timer input is dead
------------------------------------------------------------------

N20 printed `N20E`, `N20R`, `TYPE:`, and `N20END`, then reached the normal ELKS
shell prompt. At that prompt, neither the native HP 200LX keyboard nor the
Newton keyboard worked. This means the fragile boot side is now stable again,
but timer-only direct `Console_conin()` injection is not being consumed as
shell input.

`FIRSTTEST_NEWTON_N21` keeps the N20 boot shape and timer poll, then adds a
BIOS console `read` hook. ELKS calls this hook from `tty_read()` when the shell
asks for console input. The hook polls the Newton UART a few times and feeds
decoded keypresses to `Console_conin()`. If N21 works, the driver likely needs
to poll from the console/TTY read path. If N21 reaches the shell but still has
no input, the next experiment should inject decoded Newton keys directly into
the TTY input queue instead of the BIOS console path.

2026-06-12 update: source review predicts N21 fails; N22 should poll from idle
------------------------------------------------------------------------------

Reading the actual ELKS source on shop (`~/elks`) explains N19, N20, and
predicts N21, all from one root cause plus one API misunderstanding.

Root cause of N19/N20 dead input: ELKS kernel timers never fire on this
HP 200LX. `kbd_timer()` is rescheduled with `add_timer()`, and kernel timers
only run from the timer interrupt path. The related investigation
(`hp200lx-elks-investigation`) established that the Hornet does not deliver
IRQ0/Int 08h the PC way, and these Newton builds explicitly disable both
`CONFIG_TIMER_INT0F` and `CONFIG_TIMER_INT1C` alternates. So after boot,
`kbd_timer()` never runs at all: N19's BIOS-buffer was never drained (that
drain happens in the timer), and N20's timer-only UART poll never executed.
The native HP keyboard is dead at the ELKS shell for the same reason. These
were never three bugs; they are one bug.

Why N21 will fail (predicted, not yet hardware-tested): in
`elks/arch/i86/drivers/char/ntty.c`, `tty_read()` treats a non-NULL
`tty_ops.read` as "polled device" and forces `nonblock = 1`. With the queue
empty, `chq_wait_rd(..., 1)` returns -EAGAIN immediately and `tty_read()`
returns it to userspace. In `elkscmd/ash/input.c`, ash only retries EAGAIN if
O_NONBLOCK is actually set on fd 0 (it is not; the nonblock came from the
forced flag), so it falls through to `return PEOF`: the shell reads EOF and
exits at the prompt. Note that no tty driver in the entire ELKS tree populates
the `read` slot; it is effectively an unused API with hostile semantics for a
canonical console.

N22 design: poll the Newton UART from the idle loop instead.

- `elks/init/main.c` (~line 185) has the idle loop: `while (1) { schedule();
  idle_halt(); }`. Our builds already patch `idle_halt` to `sti; ret`, so this
  loop spins whenever no process is runnable, which is exactly when the shell
  is blocked in `tty_read()` waiting for input.
- Insert the N20/N21 UART poll (LSR check, read byte, decode via the existing
  feed path) into that loop. `Console_conin()` -> `chq_addch()` already calls
  `wake_up()`, so the blocked shell becomes runnable and the next
  `schedule()` resumes it. Full blocking tty semantics are preserved; no
  timers needed; no `tty_ops.read` hook (leave it NULL; remove the N21 hook).
- Keep the proven N20 boot shape (bounded TYPE: capture in kbd_init, no-HMA
  patch, nohlt patch). Add a one-shot `N22I` printk marker on the first idle
  poll so the hardware run proves the idle path executes.
- Worth adding while in there: Ctrl-key state in the feed path (Ctrl held ->
  asc &= 0x1f) so ^C/^D work once typing works.

Strategic note: `main.c` already shows the pattern `#ifdef CONFIG_TIMER_INT0F
int0F(); #else idle_halt(); #endif` - the INT0F mechanism IS an idle-driven
simulated timer interrupt. If N22 works, a follow-up could enable that (or the
investigation's proposed Int 0Ah hook; note DSPEED also hooks Int 0Ah, which
independently confirms Int 0Ah fires periodically on this hardware) to revive
kernel timers, jiffies, and possibly the native keyboard via the standard
`kbd_timer()`/`conio_poll()` path.

2026-06-12 update: N22 built; two patches in N0-N21 never actually applied
--------------------------------------------------------------------------

N22 added verification greps after its patch stage, and they immediately
caught something important: the setup.S no-HMA patch and the irqtab.S nohlt
patch in EVERY earlier build script (N0-N21) never matched this ELKS tree.
The no-HMA anchor `mov\t$0x4310, %ax` does not exist in this setup.S at all,
and the nohlt anchor assumed `hlt\n\tret` (tab) where the tree has 8-space
indentation. `~/elks` on shop was cloned 2026-05-14 and never changed, and
the N21 work tree contains neither marker, so all kernels tested so far -
including booting N8/N13/N14/N19/N20 - shipped without both patches.

Consequences:

1. The "no-HMA boot constraint" is a myth for this tree: every booting kernel
   lacked the patch. N22 drops it deliberately to match the proven shape.
   (Upstream setup.S only relocates to HMA when /bootopts has hma=kernel.)
2. idle_halt was a real hlt in every kernel. The idle task sleeps in hlt
   until an interrupt arrives, which explains why the machine goes quiet once
   the shell blocks on input. For N22's idle-loop polling this patch is
   load-bearing, so N22 fixes the anchor (8-space `idle_halt:/hlt/ret` ->
   `sti/ret`) and asserts it applied, plus rejects any remaining bare hlt
   instruction in irqtab.S.

N22 build (on shop, from the same 2026-05-14 tree):

  /home/arau/KERNN22
  size:   58352 bytes
  sha256: d9ed54cd4d8450efc9df3817510b14efabcebb14ba699fa17b8cadaf2a8494cc
  Setup 1576 bytes / 4 sectors, System 55792 B

Package `FIRSTTEST_NEWTON_N22` uses the N8 loader files. N22 contents:

- Same bounded TYPE: capture window as N20/N21 (proven boot shape).
- Idle loop in init/main.c calls hp200lx_newton_idle_poll_n22() after every
  schedule(); idle_halt now spins (sti/ret) instead of sleeping.
- Feed path: shift/caps/ctrl state, Ctrl+letter -> ^A..^Z, arrows -> ANSI,
  Delete -> backspace, Console_conin() -> chq_addch() -> wake_up().
- The idle poll never printks (idle stack overflow warning in main.c); its
  liveness marker is pokeb of '*' at CGA B800:009E (row 0, col 79).

Hardware expectations: '*' top-right after boot proves the idle poll runs;
typing `ls` + Return at the shell is the success test. The native keyboard
should remain dead (unchanged). If characters echo but commands do not run,
report whether Return echoes; if nothing echoes but '*' is present, the feed
path is suspect; if '*' is absent, the idle poll is not running.

2026-06-12 update: Codex second-opinion review of N22 - GO
----------------------------------------------------------

Codex reviewed build_newton_input_n22_remote.sh before hardware testing.
Verdict: GO for the narrow first test. Its three ranked risks were each
checked against the as-built ~/elks-newton-n22 tree on shop:

1. Arrows conditional on CONFIG_EMUL_ANSI: resolved, this build has
   CONFIG_EMUL_ANSI=y, so arrows send full ESC [ A/B/C/D as documented.
2. kbd_init/kbd_timer call sites not verified by the script: confirmed
   present in the as-built tree (kbd-poll.c lines 381 and 363-366); the
   script's verification greps now also check both call sites and scope the
   hlt check to the idle_halt label.
3. sti/ret affects all idle_halt callers incl. the printk.c HALT path:
   checked; that path is `while(1) idle_halt();` after SYSTEM HALTED, so it
   busy-spins instead of halting - functionally identical on this machine.

Known minor weakness for a later build (matches N21 behavior, harmless for
the first test): both Shift keys share one state flag, so pressing both
Shifts and releasing one drops shift while the other is still held.

2026-06-12 update: N22 WORKS on hardware; next issue is "Cannot fork"
---------------------------------------------------------------------

CONFIRMED on the stock-speed HP 200LX: the Apple Newton keyboard types into
the ELKS shell. `echo hi` prints `hi`. Milestone reached - the idle-loop input
mechanism is validated.

New issue exposed (was always latent, never visible before because no keyboard
worked at the shell): external commands fail with "Cannot fork".

  # ls            -> Cannot fork
  # echo hi       -> hi          (builtin, no fork)
  # cat /etc/issue-> Cannot fork

Diagnosis = -ENOMEM (not task slots; no "Only N task slots" message). ash
forkshell() calls fork(); fork() fails only on -EAGAIN (task slot, prints a
message) or -ENOMEM (seg_dup of the data segment fails). Boot banner:

  PC/XT class cpu 5, syscaps 0, 636K base ram
  64K ext buffers, 8K cache, 15 req hdrs
  rd: 360K ramdisk at 3200:0000   (ROOTEND=8C00)

arch/i86/kernel/system.c subtracts the whole ramdisk from usable memory:
`memend = SETUP_MEM_KBYTES<<6; if (RAMDISK_SEGMENT<=memend) memend -=
RAMDISK_SECTORS<<5;` So 636K - 360K, then the 64K of external buffers (which
fs/buffer.c seg_allocs from that same main-memory pool) leave too little to
duplicate ash. Confirmed external buffers come from main memory (buffer.c
comment: "total main memory used is BLOCK_SIZE * CONFIG_FS_NR_EXT_BUFFERS").

Constraints that rule out the obvious big fixes:
- Ramdisk cannot shrink: its minix fs is 360K (nzones=360) and 307K/360K is
  actually used (117 inodes). CONFIG_RAMDISK_SECTORS must stay >=720 or reads
  run off the end of the device.
- XMS/extended memory is the natural place for the ramdisk/buffers, but the
  timer investigation established "no HMA/no XMS required for clean boot" on
  this hardware. Off the table.

N23 = the one safe conventional-memory lever: CONFIG_FS_NR_EXT_BUFFERS 64 -> 8
(frees ~56K to the fork pool). Kernel code byte-identical to N22.
  size 58352, sha256 103372549c6dc016afa5cb869851845a1dff7ae0f3dced8c174398938efe7649
Hardware test: does `ls` run now? Read the banner "...K free" figure to size
the remaining headroom.

If 56K is not enough, N24 = build a smaller minix root fs (sh + a few
binaries) so the ramdisk can drop below 360K and free 150K+. More work
(regenerate ROOT092), which is why N23 tries the cheap lever first.

2026-06-12 update: N23 WORKS (ls forks) but exposed a ramdisk/memory OVERLAP
---------------------------------------------------------------------------

N23 on hardware: `ls` now runs (banner confirms "8K ext buffers"), printing
bin bootopts dev etc mnt root tmp. The buffer cut freed enough to fork. BUT
new errors appeared that are FILESYSTEM CORRUPTION, not missing files:
`cd etc` -> "can't cd to etc" (etc is in the ls listing!), and `cat /etc/issue`
-> "free_inode: already cleared 38" + "cat: permission denied".

Root cause (proven from source) - the ramdisk overlaps user memory:
- setup.S fills SETUP_MEM_KBYTES from BIOS INT 0x12 = 636K (whole conventional
  memory). The BIOS does not know the loader carved a ramdisk out of the middle.
- system.c: memend = 636<<6 = 0x9F00; then (ramdisk configured) memend -=
  720<<5 = 0x5A00 -> memend = 0x4500. This MATH ASSUMES THE RAMDISK IS AT THE
  TOP of memory.
- But CONFIG_RAMDISK_SEGMENT=0x3200 puts the ramdisk at 0x3200-0x8C00 (mid-RAM;
  ROOTEND=8C00 confirms). Nothing seg_adds/reserves that region.
- So the user pool [membase,0x4500] overlaps the ramdisk [0x3200,0x8C00] in
  [0x3200,0x4500] ~ 76K = the minix superblock/inode-bitmap/inode-table.
- With 64K buffers the pool filled before 0x3200 -> fork failed (ENOMEM). With
  8K buffers, fork allocates past 0x3200 INTO the root fs -> corruption.

This UNIFIES the whole memory story: "Cannot fork" and the fs corruption are
the SAME bug (ramdisk placed inside BIOS-reported conventional memory). It is
the real ceiling of the RAM-root design and strongly validates the disk-root
(HP C: drive) strategy, which removes the ramdisk from conventional RAM.

N24 = memory-map fix (config.h has a `#define SETUP_MEM_KBYTES <n>` override):
  Option A (loader-free): force memend down to the ramdisk start (0x3200) and
    skip the buggy subtraction; optionally seg_add(0x8C00,0x9F00) to reclaim
    the ~76K above the ramdisk. Clean, no overlap. Usable ~72K (+76K
    non-contiguous). Proves the diagnosis; may be tight for fork.
  Option B (loader change): move the ramdisk to the true top
    (CONFIG_RAMDISK_SEGMENT=0x4500 + loader loads ROOT092 there) -> one
    contiguous clean ~148K. Best RAM-root outcome, but touches the fragile
    loader chain.
Recommend Codex-reviewing the N24 patch before flashing (memory-map surgery is
easy to get subtly wrong; project is sensitive to wasted hardware cycles).
To size A vs B precisely, read the boot banner line "data X end Y top Z
N+M+KK free" (membase = Y).

2026-06-13 update: N24 built (memory-map fix), Codex-reviewed, ready to test
----------------------------------------------------------------------------

N24 = N23 + two kernel patches that fix the overlap (no loader change):
  1. system.c setup_arch(): replaced "memend -= CONFIG_RAMDISK_SECTORS<<5"
     (which assumes the ramdisk is at the top) with
     "if (CONFIG_RAMDISK_SEGMENT < memend) memend = CONFIG_RAMDISK_SEGMENT;"
     -> caps the user pool at the ramdisk start 0x3200 (no overlap).
  2. main.c kernel_init(): seg_add(0x8C00, 0x9F00) ~76K -- reclaims the
     conventional RAM above the ramdisk (the loader's transient SaveHigh
     buffer; BIOS INT12 already reports it as usable RAM). Without it the
     pool below the ramdisk (~50K, since IBMPC has no SETUP_HEAPSIZE so
     membase=kernel_ds+0x1000 reserves a full 64K kernel data seg) is too
     small to fork. Unsigned casts used (ia16 int is 16-bit; 0x3200+0x5A00
     and 636<<6 would overflow signed).
Buffers stay at 8 (one variable vs N23 = the memory map only). Build has
verify greps (markers present, call sites present, old subtract gone).
  KERNN24 size 58416, sha256
  8941be7245707b17394b01c783084b6b3ca50ba4948e3327e7e5f5f99ce90094

Codex review (2026-06-13) verdict: patches sound. Flagged: (1) guard against
membase>=memend inverting mm_init -- not added; membase~0x2400 is structurally
below 0x3200 for a 58K kernel and the banner prints it for confirmation;
(3) overflow casts confirmed sufficient; (4) the "SaveHigh region is free at
runtime" assumption is the main residual risk -- mitigated by the BIOS
reporting [0,0x9F00] as usable RAM and the cap-alone already fixing the
original corruption, so a bad assumption would show as a distinct hang/reboot,
not silent fs damage.

Hardware test reads: "top" should now be 3200 (was 4500); "free" should jump
vs N23; cd/cat/ls should work without corruption. Fallback if it hangs/reboots
or shows fresh corruption: drop patch #2 (the seg_add) and keep only the cap
(safe but ~50K, may return to "Cannot fork" -> then pursue smaller root /
disk-root, the strategic direction).

2026-06-13 update: N24 WORKS -- MILESTONE: usable ELKS shell on the 200LX
------------------------------------------------------------------------

Hardware result (banner): "...data f38 end 1f38 top 3200 75+4+0K free".
  - top 3200 (was 4500) -> the memend cap applied; no overlap.
  - end 1f38 (membase) below 0x3200 -> no map inversion (Codex's pt1 moot).
  - clean boot, no hang/reboot -> the seg_add of [0x8C00,0x9F00] was safe; the
    SaveHigh region was free as predicted.
Shell session (Newton keyboard): `ls` lists a full clean root (bin bootopts dev
etc home lib linux mnt root tmp); `cd etc` SUCCEEDS; `ls` in etc shows group
inittab issue mount.cfg passwd perror profile rc.sys termcap; `cat /etc/issue`
prints "ELKS 0.9.2-dev"; `echo hi` -> hi; '*' alive top-right. NO corruption,
fork/exec works. The "Cannot fork" + fs-corruption saga is closed.

Codex review of the result (2026-06-13): solid milestone. Caveats/next checks:
  - Patch 2 not stress-proven: fork may be served entirely by the 75K low pool;
    the reclaimed +76K high region isn't counted in the banner and may be
    untested. Prove it by restoring buffers / a memory-pressure test.
  - Corruption looks truly fixed (cd/ls/cat exercise superblock+inode table),
    but for high confidence: cold-boot several times, cat more files under
    /etc and /bin, and try create/remove in /tmp if root is writable.
  - "cpu 4" vs earlier "cpu 5" = CPU-detection noise, low risk.
  - Recommended next: cautiously restore CONFIG_FS_NR_EXT_BUFFERS upward from 8
    (improves usability AND stress-tests the reclaimed high memory) before the
    bigger disk-root / native-keyboard tracks.

Status: the RAM-root bring-up goal is essentially met. Time to write STRATEGY.md
and pick the forward track (disk-root for RAM+persistence+free PCMCIA slot;
native keyboard via idle-poll; HP200LX platform port w/ bootopts toggles).

2026-06-13: wrote STRATEGY.md (milestone state, hardware constraints, ranked
tracks A-D; built-in keyboard fix is Track B, explicitly flagged as still
unsolved). Wrote ISSUE_2236_UPDATE_NEWTON_PARTIAL_SUCCESS.md = a public GitHub
update for ghaerr/elks#2236 ("Partial Success": usable shell via Newton serial
keyboard on a stock-clock unit; built-in keyboard still dead). Both Codex-
reviewed; applied its fixes (cd is a builtin not fork evidence; softened "first
known"; marked the +76K reclaim as not-stress-proven in both docs; credited
K. Adachi for NTKPAC05; Stefan Peichl for DSPEED). The issue post references 3
images by filename (IMG_devsetup_newton_200lx.jpg, IMG_n24_wide.jpg,
IMG_n24_closeup.jpg) for the user to attach on GitHub.

Build-infra note: shop (56G SD card) hit 100% disk during the first N23 build;
each build rsyncs a full ~3.3G tree (includes cross/build/gcc-src). Removed
finished work trees elks-newton-n21 and the partial n23 to free space. Saved
kernels live at ~/KERNN21, KERNN22, KERNN23. Consider excluding cross/build
from the rsync in future scripts, or pruning old work trees routinely.
