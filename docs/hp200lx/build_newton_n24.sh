#!/usr/bin/env bash
set -euo pipefail

# N24: N23 (Newton keyboard works, ls forks) + FIX the ramdisk/user-memory
# overlap that corrupts the root fs. Builds on N23 (CONFIG_FS_NR_EXT_BUFFERS=8).
#
# The overlap bug (proven from source, see NOTES_N8_BASELINE.md):
#  - setup.S fills SETUP_MEM_KBYTES from BIOS INT 0x12 = 636K (whole
#    conventional memory). The BIOS does not know the DOS loader carved a
#    ramdisk out of the MIDDLE of it.
#  - arch/i86/kernel/system.c then does memend = 636K<<6 (=0x9F00); then,
#    because a ramdisk is configured, memend -= ramdisk_size (=0x5A00) ->
#    0x4500. THIS ASSUMES THE RAMDISK IS AT THE TOP OF MEMORY.
#  - But CONFIG_RAMDISK_SEGMENT=0x3200 puts the ramdisk at 0x3200-0x8C00
#    (mid-RAM; ROOTEND=8C00). Nothing reserves that region. So the user pool
#    [membase,0x4500] overlaps the ramdisk [0x3200,0x8C00] in [0x3200,0x4500]
#    ~ 76K = the minix superblock/inode-bitmap/inode-table. Once fork()
#    allocates past 0x3200 it eats the root fs -> "free_inode already cleared",
#    "can't cd to etc", "permission denied".
#
# N24 fix (two kernel patches, no loader change):
#  1) system.c: cap memend at the ramdisk START (CONFIG_RAMDISK_SEGMENT)
#     instead of subtracting the ramdisk size from the BIOS top. This makes
#     the main user pool [membase,0x3200] never overlap the ramdisk.
#  2) main.c kernel_init(): seg_add the conventional RAM ABOVE the ramdisk
#     [ramdisk_end=0x8C00, BIOS_top=0x9F00] ~ 76K back into the free pool.
#     That region is used by the DOS loader only transiently (the "SaveHigh"
#     boot-copy buffer) and is free once ELKS is running. Without it, the pool
#     below the ramdisk (~50K) is too small to fork ash.
#
# Net: no overlap (fs safe) AND a ~76K contiguous chunk above the ramdisk for
# fork(). One variable vs N23: the memory map only (buffers stay at 8).
#
# N24: N8-derived Apple Newton Keyboard idle-loop shell input for ELKS.
#
# Why idle-loop polling (see NOTES_N8_BASELINE.md, 2026-06-12 source review):
#  - ELKS kernel timers never fire on the HP 200LX (no IRQ0 from the Hornet,
#    and CONFIG_TIMER_INT0F/INT1C are disabled in these builds), so the
#    N19/N20 timer-based handoffs never executed after boot.
#  - A tty_ops.read hook (N21) forces nonblock in tty_read(); an empty queue
#    returns -EAGAIN, which ash treats as EOF, so the shell exits.
#  - The idle loop in init/main.c runs exactly when the shell is blocked in
#    tty_read(). Console_conin() -> chq_addch() -> wake_up() makes the shell
#    runnable and the idle loop's next schedule() resumes it. Blocking tty
#    semantics are preserved and no timers are needed.
#
# IMPORTANT: main.c warns that printk from the idle loop can overflow the
# small idle stack. The idle poll therefore never calls printk; its liveness
# marker is a direct pokeb() of '*' into CGA text memory (row 0, col 79).
#
# 2026-06-12 discovery: the earlier scripts' setup.S no-HMA patch and
# irqtab.S nohlt patch NEVER applied (anchors assumed tabs / code that is not
# in this tree), so every tested kernel N0-N21 was built without them.
# Therefore:
#  - The no-HMA patch is dropped entirely; the proven boot shape never had it
#    (HMA relocation only activates via /bootopts hma=kernel anyway).
#  - The nohlt patch is ESSENTIAL for N24 and now uses the real bytes:
#    idle_halt is hlt/ret with 8-space indent. Without this fix the idle task
#    sleeps in hlt waiting for interrupts that never come on this machine,
#    and the idle poll would run at most once.
#
# Boot shape otherwise matches the proven N20/N21 packages: bounded TYPE:
# capture window in kbd_init().

SRC=${SRC:-$HOME/elks}
OUT=${OUT:-$HOME/KERNN24}
WORK=${WORK:-$HOME/elks-newton-n24}

rm -rf "$WORK"
mkdir -p "$WORK"
rsync -a --delete \
    --exclude '.git' \
    --exclude '*.o' \
    --exclude 'elks/arch/i86/boot/Image' \
    "$SRC"/ "$WORK"/
cd "$WORK"
export MAKEFLAGS="${MAKEFLAGS-}"
set +u
. ./env.sh
set -u

python3 - <<'PY'
from pathlib import Path

root = Path(".")

def write(path, data):
    path.write_text(data, newline="\n")

cfg = root / ".config"
text = cfg.read_text()
repls = {
    "CONFIG_CONSOLE_DIRECT=y": "# CONFIG_CONSOLE_DIRECT is not set",
    "# CONFIG_CONSOLE_BIOS is not set": "CONFIG_CONSOLE_BIOS=y",
    "CONFIG_KEYBOARD_SCANCODE=y": "# CONFIG_KEYBOARD_SCANCODE is not set",
    "CONFIG_FS_XMS=y": "# CONFIG_FS_XMS is not set",
    "CONFIG_XMS=y": "# CONFIG_XMS is not set",
    "CONFIG_TIMER_INT0F=y": "# CONFIG_TIMER_INT0F is not set",
    "CONFIG_TIMER_INT1C=y": "# CONFIG_TIMER_INT1C is not set",
    "CONFIG_FS_FAT=y": "# CONFIG_FS_FAT is not set",
    # N24: cut external buffers 64 -> 8 to free ~56K of main memory for fork().
    # N22 reached the shell (Newton keyboard works) but external commands die
    # with "Cannot fork" = -ENOMEM: a 636K machine minus a 360K ramdisk minus
    # 64K of ext buffers leaves too little to seg_dup() ash. External buffers
    # are seg_alloc'd from main memory (fs/buffer.c), the same pool fork uses,
    # so cutting them returns memory 1:1 to the fork pool. The ramdisk cannot
    # shrink (its minix fs is 360K) and XMS breaks boot on this hardware, so
    # buffers are the one safe conventional-memory lever.
    "CONFIG_FS_NR_EXT_BUFFERS=64": "CONFIG_FS_NR_EXT_BUFFERS=8",
}
for old, new in repls.items():
    text = text.replace(old, new)
assert "CONFIG_FS_NR_EXT_BUFFERS=8" in text, "ext buffer cut did not apply"
for line in [
    "CONFIG_CONSOLE_BIOS=y",
    "# CONFIG_CONSOLE_DIRECT is not set",
    "# CONFIG_KEYBOARD_SCANCODE is not set",
    "# CONFIG_FS_XMS is not set",
    "# CONFIG_XMS is not set",
    "# CONFIG_TIMER_INT0F is not set",
    "# CONFIG_TIMER_INT1C is not set",
    "# CONFIG_FS_FAT is not set",
]:
    key = line.split("=")[0].replace("# ", "").replace(" is not set", "")
    if key not in text:
        text += "\n" + line + "\n"
write(cfg, text)

# No setup.S patch: see header. N0-N21 all booted with unpatched setup.S.

irqtab = root / "elks/arch/i86/kernel/irqtab.S"
text = irqtab.read_text()
if "hp200lx_n24_nohlt" not in text:
    old = "idle_halt:\n        hlt\n        ret"
    new = ("idle_halt:\n"
           "        sti     // hp200lx_n24_nohlt: no IRQs on HP200LX, never hlt\n"
           "        ret")
    assert old in text, "idle_halt hlt/ret anchor not found in irqtab.S"
    text = text.replace(old, new, 1)
write(irqtab, text)

# N24 fix part 1: cap memend at the ramdisk START instead of subtracting the
# ramdisk size from the BIOS-reported top. The stock code assumes the ramdisk
# is at the top of memory; on this loader it is at a fixed mid-RAM segment, so
# the stock math leaves the user pool overlapping the root fs.
system = root / "elks/arch/i86/kernel/system.c"
text = system.read_text()
if "hp200lx_n24_memcap" not in text:
    old = (
        "#if defined(CONFIG_RAMDISK_SEGMENT) && (CONFIG_RAMDISK_SEGMENT > 0)\n"
        "    if (CONFIG_RAMDISK_SEGMENT <= memend) {\n"
        "        /* reduce top of memory by size of ram disk*/\n"
        "        memend -= CONFIG_RAMDISK_SECTORS << 5;\n"
        "    }\n"
        "#endif"
    )
    new = (
        "#if defined(CONFIG_RAMDISK_SEGMENT) && (CONFIG_RAMDISK_SEGMENT > 0)\n"
        "    /* hp200lx_n24_memcap: the preloaded ramdisk sits at a FIXED segment\n"
        "     * in the MIDDLE of BIOS-reported conventional memory (not at the\n"
        "     * top). Cap the main user pool at the ramdisk start so processes\n"
        "     * never allocate over the root fs. The conventional RAM above the\n"
        "     * ramdisk is added back to the free pool in kernel_init(). */\n"
        "    if (CONFIG_RAMDISK_SEGMENT < memend)\n"
        "        memend = CONFIG_RAMDISK_SEGMENT;\n"
        "#endif"
    )
    assert old in text, "system.c ramdisk-subtract anchor not found"
    text = text.replace(old, new, 1)
write(system, text)

kbd = root / "elks/arch/i86/drivers/char/kbd-poll.c"
text = kbd.read_text()
if "#include <linuxmt/debug.h>" not in text:
    text = text.replace(
        '#include "conio.h"\n',
        '#include "conio.h"\n#include <linuxmt/debug.h>\n#include <linuxmt/kernel.h>\n#include <arch/io.h>\n#include <arch/segment.h>\n',
        1,
    )

if "hp200lx_newton_raw_probe_n24" not in text:
    probe = r'''

#define N24_COM1          0x03f8
#define N24_UART_RX       0
#define N24_UART_IER      1
#define N24_UART_FCR      2
#define N24_UART_LCR      3
#define N24_UART_MCR      4
#define N24_UART_LSR      5
#define N24_UART_MSR      6
#define N24_UART_DLL      0
#define N24_UART_DLM      1
#define N24_LCR_DLAB      0x80
#define N24_LSR_DR        0x01
#define N24_LSR_ERR       0x1e
#define N24_DIV_9600      12

#define N24_ID_BACKQUOTE  0x32
#define N24_ID_DELETE     0x33
#define N24_ID_APPLE      0x37
#define N24_ID_SHIFT_L    0x38
#define N24_ID_CAPS       0x39
#define N24_ID_OPTION     0x3a
#define N24_ID_CTRL       0x3b
#define N24_ID_SHIFT_R    0x3c
#define N24_ID_LEFT       0x7b
#define N24_ID_RIGHT      0x7c
#define N24_ID_DOWN       0x7d
#define N24_ID_UP         0x7e

static unsigned char n24_map[] = {
    'a', 's', 'd', 'f',
    'h', 'g', 'z', 'x',
    'c', 'v', 0,   'b',
    'q', 'w', 'e', 'r',
    'y', 't', '1', '2',
    '3', '4', '6', '5',
    '=', '9', '7', '-',
    '8', '0', ']', 'o',
    'u', '[', 'i', 'p',
    '\r','l', 'j', '\'',
    'k', ';', '\\', ',',
    '/', 'n', 'm', '.',
    '\t',' ', '`', '\b'
};

static unsigned char n24_shift_map[] = {
    'A', 'S', 'D', 'F',
    'H', 'G', 'Z', 'X',
    'C', 'V', 0,   'B',
    'Q', 'W', 'E', 'R',
    'Y', 'T', '!', '@',
    '#', '$', '^', '%',
    '+', '(', '&', '_',
    '*', ')', '}', 'O',
    'U', '{', 'I', 'P',
    '\r','L', 'J', '"',
    'K', ':', '|', '<',
    '?', 'N', 'M', '>',
    '\t',' ', '~', '\b'
};

static unsigned char n24_shift;
static unsigned char n24_caps;
static unsigned char n24_ctrl;

static void n24_iodelay(void)
{
    __asm__ __volatile__("jmp 1f\n1:");
}

static void n24_hp_com_power_on(void)
{
    unsigned char old, v;

    old = inb(0x22);
    n24_iodelay();

    outb(0x10, 0x22);
    n24_iodelay();
    outb(0x00, 0x23);
    n24_iodelay();

    outb(0x51, 0x22);
    n24_iodelay();
    v = inb(0x23);
    n24_iodelay();
    v &= ~0x01;
    v |= 0x20;
    outb(v, 0x23);
    n24_iodelay();

    outb(0x52, 0x22);
    n24_iodelay();
    v = inb(0x23);
    n24_iodelay();
    v &= ~0x80;
    outb(v, 0x23);
    n24_iodelay();

    outb(old, 0x22);
    n24_iodelay();
}

static void n24_com1_init(void)
{
    unsigned char x;

    outb(0x00, N24_COM1 + N24_UART_IER);
    n24_iodelay();
    outb(0x03 | N24_LCR_DLAB, N24_COM1 + N24_UART_LCR);
    n24_iodelay();
    outb(N24_DIV_9600, N24_COM1 + N24_UART_DLL);
    n24_iodelay();
    outb(0x00, N24_COM1 + N24_UART_DLM);
    n24_iodelay();
    outb(0x03, N24_COM1 + N24_UART_LCR);
    n24_iodelay();
    outb(0x00, N24_COM1 + N24_UART_FCR);
    n24_iodelay();
    outb(0x09, N24_COM1 + N24_UART_MCR);
    n24_iodelay();

    x = inb(N24_COM1 + N24_UART_LSR);
    n24_iodelay();
    x = inb(N24_COM1 + N24_UART_MSR);
    n24_iodelay();
    x = inb(N24_COM1 + N24_UART_RX);
    (void)x;
}

static void n24_print_char(unsigned char asc)
{
    if (asc == '\r')
        printk("<CR>\n");
    else if (asc == '\t')
        printk("<TAB>");
    else if (asc == '\b')
        printk("<BS>");
    else if (asc)
        printk("%c", asc);
}

/* Capture-window decoder: prints tokens, used only from kbd_init(). */
static void n24_handle_raw(unsigned char raw)
{
    unsigned char id = raw & 0x7f;
    unsigned char make = raw & 0x80;
    unsigned char asc;

    if (id == N24_ID_SHIFT_L || id == N24_ID_SHIFT_R) {
        n24_shift = make ? 1 : 0;
        printk(make ? "<SH>" : "</SH>");
        return;
    }
    if (id == N24_ID_CAPS) {
        if (make) {
            n24_caps ^= 1;
            printk(n24_caps ? "<CAPS>" : "</CAPS>");
        }
        return;
    }
    if (id == N24_ID_CTRL) {
        n24_ctrl = make ? 1 : 0;
        printk(make ? "<CTRL>" : "</CTRL>");
        return;
    }
    if (id == N24_ID_OPTION) {
        printk(make ? "<OPT>" : "</OPT>");
        return;
    }
    if (id == N24_ID_APPLE) {
        printk(make ? "<APPLE>" : "</APPLE>");
        return;
    }

    if (!make)
        return;

    if (id == N24_ID_LEFT) {
        printk("<LEFT>");
        return;
    }
    if (id == N24_ID_RIGHT) {
        printk("<RIGHT>");
        return;
    }
    if (id == N24_ID_DOWN) {
        printk("<DOWN>");
        return;
    }
    if (id == N24_ID_UP) {
        printk("<UP>");
        return;
    }

    if (id < sizeof(n24_map)) {
        asc = n24_shift ? n24_shift_map[id] : n24_map[id];
        if (!n24_shift && n24_caps && asc >= 'a' && asc <= 'z')
            asc = asc - 'a' + 'A';
        if (n24_shift && n24_caps && asc >= 'A' && asc <= 'Z')
            asc = asc - 'A' + 'a';
        n24_print_char(asc);
    } else {
        printk("<%x>", id);
    }
}

static void n24_send_ansi(unsigned char final)
{
    Console_conin(033);
#ifdef CONFIG_EMUL_ANSI
    Console_conin('[');
#endif
    Console_conin(final);
}

/* Shell-input decoder: feeds the console tty queue. NEVER calls printk;
 * it runs on the small idle stack (see init/main.c idle stack warning). */
static void n24_feed_raw(unsigned char raw)
{
    unsigned char id = raw & 0x7f;
    unsigned char make = raw & 0x80;
    unsigned char asc;

    if (id == N24_ID_SHIFT_L || id == N24_ID_SHIFT_R) {
        n24_shift = make ? 1 : 0;
        return;
    }
    if (id == N24_ID_CAPS) {
        if (make)
            n24_caps ^= 1;
        return;
    }
    if (id == N24_ID_CTRL) {
        n24_ctrl = make ? 1 : 0;
        return;
    }

    if (!make)
        return;

    if (id == N24_ID_LEFT) {
        n24_send_ansi('D');
        return;
    }
    if (id == N24_ID_RIGHT) {
        n24_send_ansi('C');
        return;
    }
    if (id == N24_ID_DOWN) {
        n24_send_ansi('B');
        return;
    }
    if (id == N24_ID_UP) {
        n24_send_ansi('A');
        return;
    }

    if (id < sizeof(n24_map)) {
        asc = n24_shift ? n24_shift_map[id] : n24_map[id];
        if (!n24_shift && n24_caps && asc >= 'a' && asc <= 'z')
            asc = asc - 'a' + 'A';
        if (n24_shift && n24_caps && asc >= 'A' && asc <= 'Z')
            asc = asc - 'A' + 'a';
        if (n24_ctrl) {
            if (asc >= 'a' && asc <= 'z')
                asc = asc - 'a' + 1;        /* ^A..^Z */
            else if (asc >= 'A' && asc <= 'Z')
                asc = asc - 'A' + 1;
            else
                return;                     /* ignore other Ctrl combos */
        }
        if (asc)
            Console_conin(asc);
    }
}

/* Called from the idle loop in init/main.c after every schedule().
 * Runs on the small idle stack: no printk allowed here. The liveness
 * marker is a direct write of '*' to CGA text memory, row 0 col 79. */
void hp200lx_newton_idle_poll_n24(void)
{
    unsigned char lsr, ch;
    unsigned char limit = 4;

    pokeb(158, 0xb800, '*');

    while (limit--) {
        lsr = inb(N24_COM1 + N24_UART_LSR);
        if (!(lsr & N24_LSR_DR))
            break;
        ch = inb(N24_COM1 + N24_UART_RX);
        if (!(lsr & N24_LSR_ERR))
            n24_feed_raw(ch);
    }
}

static void n24_uart_drain(void)
{
    unsigned char lsr, ch;
    unsigned char limit = 64;

    while (limit--) {
        lsr = inb(N24_COM1 + N24_UART_LSR);
        if (!(lsr & N24_LSR_DR))
            break;
        ch = inb(N24_COM1 + N24_UART_RX);
        (void)ch;
    }
}

static void hp200lx_newton_raw_probe_n24(void)
{
    unsigned int outer, inner;
    unsigned char lsr, ch;

    printk(" N24E");
    n24_hp_com_power_on();
    n24_com1_init();
    printk(" N24R\nTYPE:");

    for (outer = 0; outer < 2000; outer++) {
        lsr = inb(N24_COM1 + N24_UART_LSR);
        if (lsr & N24_LSR_DR) {
            ch = inb(N24_COM1 + N24_UART_RX);
            if (!(lsr & N24_LSR_ERR))
                n24_handle_raw(ch);
        }
        for (inner = 0; inner < 200; inner++)
            n24_iodelay();
    }

    printk("\nN24END\n");
    n24_uart_drain();
    n24_shift = n24_caps = n24_ctrl = 0;
}
'''
    text = text.replace("static void kbd_timer(int data)\n{\n", probe + "\nstatic void kbd_timer(int data)\n{\n", 1)
    start = text.index("static void kbd_timer(int data)\n{")
    end = text.index("\nstatic void restart_timer(void)", start)
    text = text[:start] + """static void kbd_timer(int data)\n{\n    hp200lx_newton_idle_poll_n24();\n    restart_timer();\n}\n""" + text[end:]
    text = text.replace("void kbd_init(void)\n{", "void kbd_init(void)\n{\n    hp200lx_newton_raw_probe_n24();", 1)

write(kbd, text)

mainc = root / "elks/init/main.c"
text = mainc.read_text()
if "hp200lx_newton_idle_poll_n24" not in text:
    text = text.replace(
        "/* the idle task loop, no return */",
        "extern void hp200lx_newton_idle_poll_n24(void);\n\n/* the idle task loop, no return */",
        1,
    )
    text = text.replace(
        "        schedule();\n#ifdef CONFIG_TIMER_INT0F",
        "        schedule();\n        hp200lx_newton_idle_poll_n24();\n#ifdef CONFIG_TIMER_INT0F",
        1,
    )

# N24 fix part 2: reclaim conventional RAM ABOVE the mid-RAM ramdisk.
# setup_arch() capped the main pool at the ramdisk start; add the gap from the
# ramdisk end up to the BIOS-reported top back to the free pool here, in
# kernel_init() right before the banner (same place the fartext-init region is
# released, so seg_add is known-safe to call here). Explicit unsigned math:
# int is 16-bit on ia16 and 0x3200+0x5A00=0x8C00 overflows signed 16-bit.
if "hp200lx_n24_topmem" not in text:
    old = "    kernel_banner(s, e - s);\n}"
    new = (
        "#if defined(CONFIG_RAMDISK_SEGMENT) && (CONFIG_RAMDISK_SEGMENT > 0)\n"
        "    /* hp200lx_n24_topmem: reclaim conventional RAM above the mid-RAM\n"
        "     * ramdisk (used only transiently by the DOS loader's SaveHigh\n"
        "     * boot-copy buffer, free once ELKS is running). */\n"
        "    {\n"
        "        seg_t rd_end = (seg_t)((unsigned)CONFIG_RAMDISK_SEGMENT\n"
        "                               + ((unsigned)CONFIG_RAMDISK_SECTORS << 5));\n"
        "        seg_t mem_top = (seg_t)((unsigned)SETUP_MEM_KBYTES << 6);\n"
        "        if (rd_end < mem_top)\n"
        "            seg_add(rd_end, mem_top);\n"
        "    }\n"
        "#endif\n\n"
        "    kernel_banner(s, e - s);\n}"
    )
    assert old in text, "main.c kernel_banner anchor not found"
    text = text.replace(old, new, 1)
write(mainc, text)
PY

# Verify every patch landed before spending build time, including the call
# sites, not just the symbol definitions (Codex review 2026-06-12).
grep -q "hp200lx_newton_idle_poll_n24();" elks/init/main.c
grep -q "extern void hp200lx_newton_idle_poll_n24" elks/init/main.c
grep -q "hp200lx_newton_raw_probe_n24();" elks/arch/i86/drivers/char/kbd-poll.c
grep -A2 "void kbd_init(void)" elks/arch/i86/drivers/char/kbd-poll.c \
    | grep -q "hp200lx_newton_raw_probe_n24();"
grep -A3 "static void kbd_timer(int data)" elks/arch/i86/drivers/char/kbd-poll.c \
    | grep -q "hp200lx_newton_idle_poll_n24();"
grep -q "hp200lx_n24_nohlt" elks/arch/i86/kernel/irqtab.S
if grep -A2 "^idle_halt:" elks/arch/i86/kernel/irqtab.S \
        | grep -E -q "^[[:space:]]+hlt[[:space:]]*$"; then
    echo "idle_halt still contains a hlt instruction"
    exit 1
fi
# N24 memory-map fix landed?
grep -q "hp200lx_n24_memcap" elks/arch/i86/kernel/system.c
grep -q "memend = CONFIG_RAMDISK_SEGMENT;" elks/arch/i86/kernel/system.c
grep -q "hp200lx_n24_topmem" elks/init/main.c
grep -q "seg_add(rd_end, mem_top);" elks/init/main.c
# old buggy subtract must be gone
if grep -q "memend -= CONFIG_RAMDISK_SECTORS << 5;" elks/arch/i86/kernel/system.c; then
    echo "system.c still has the old ramdisk-subtract logic"
    exit 1
fi

make oldconfig >/dev/null || true
make kclean >/dev/null || true
yes '' | make include/autoconf.h >/dev/null 2>&1 || true
make kernel

cp -f elks/arch/i86/boot/Image "$OUT"
ls -l "$OUT"
wc -c "$OUT"
sha256sum "$OUT"
