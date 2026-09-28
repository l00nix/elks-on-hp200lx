/* HP 200LX firmware platform port. GPL-2.0-or-later.
 * Based on the HP Developer's Guide hardware interface; no Mack code copied.
 * The original ROM IRQ2 service owns source acknowledgement and PIC EOI.
 */
#include <linuxmt/config.h>
#include <linuxmt/kernel.h>
#include <linuxmt/memory.h>
#include <linuxmt/sched.h>
#include <linuxmt/hp200lx-fw.h>
#include <arch/io.h>
#include <arch/irq.h>
#include <arch/system.h>
#ifdef CONFIG_HP200LX_STACK_DIAG
#include <linuxmt/limits.h>
/* Assembly record: samples, peak total writes, peak ROM writes, peak entry,
 * sticky guard flags, sampling phase, calls. Seven 16-bit words per record. */
unsigned short hpfw_stack_task[7], hpfw_stack_irq[7];
unsigned short hpfw_stack_unknown;
extern unsigned short hpfw_istack_guard;

void hp200lx_stack_report(void)
{
    unsigned short t[7], i[7], unknown, n;
    flag_t flags;
    save_flags(flags);
    clr_irq();
    for (n = 0; n < 7; ++n) {
        t[n] = hpfw_stack_task[n];
        i[n] = hpfw_stack_irq[n];
    }
    unknown = hpfw_stack_unknown;
    restore_flags(flags);
    printk("HPST task n=%u entry=%u used=%u/%u rom=%u guard=%x\n",
        t[0], t[3], t[1], KSTACK_BYTES, t[2], t[4]);
    printk("HPST irq  n=%u entry=%u used=%u/%u rom=%u guard=%x\n",
        i[0], i[3], i[1], INTRSTACK_BYTES, i[2], i[4]);
    printk("HPST calls task=%u irq=%u sample=1/32 guard=each\n", t[6], i[6]);
    printk("HPST unknown=%u watermark writes; +6B probe; n saturates\n", unknown);
}
#endif

#if !defined(CONFIG_ARCH_IBMPC) || !defined(CONFIG_KEYBOARD_SCANCODE) || \
    !defined(CONFIG_CONSOLE_BIOS) || defined(CONFIG_TIMER_INT0F) || \
    defined(CONFIG_TIMER_INT1C) || defined(CONFIG_BLK_DEV_BFD) || \
    defined(CONFIG_BLK_DEV_BHD) || defined(CONFIG_HW_MK88) || \
    (CONFIG_RAMDISK_SECTORS != 0) || defined(CONFIG_FS_XMS)
#error HP firmware beta requires IBM PC, BIOS console, scan-code keyboard, native IRQ0, CF root, no XMS
#endif

volatile unsigned short hpfw_irq0, hpfw_irq1, hpfw_irq2, hpfw_last_scan;
unsigned short hpfw_rom_vector[2];
static unsigned short hp_model_revision;
extern unsigned short hp200lx_fw_detect(void);
extern void hp200lx_fw_rom_irq2(void);

/* Caller holds interrupts disabled. Restore the shared indexed I/O selector. */
static unsigned char hornet_read(unsigned char index)
{
    unsigned char saved = inb(0x22), value;
    outb(index, 0x22);
    value = inb(0x23);
    outb(saved, 0x22);
    return value;
}

static void hornet_write(unsigned char index, unsigned char value)
{
    unsigned char saved = inb(0x22);
    outb(index, 0x22);
    outb(value, 0x23);
    outb(saved, 0x22);
}

/* Refuse DOS-resident hooks: ELKS cannot keep their reclaimed memory alive.
 * Segment F000 is the documented HP BIOS ROM window for this first beta.
 */
static void require_rom(unsigned short offset, unsigned short segment)
{
    if (segment != 0xf000 || offset == 0xffff)
        panic("HPFW non-ROM hook %x:%x", segment, offset);
}

void hp200lx_fw_prepare(void)
{
    unsigned short i, off, seg;

#ifdef CONFIG_HP200LX_STACK_DIAG
    hpfw_istack_guard = KSTACK_MAGIC;
    printk("HPBOOT initial=%x staging=%x reloc=%x stacks=%u/%u\n",
        DEF_INITSEG, DEF_SYSSEG, REL_SYSSEG, KSTACK_BYTES, INTRSTACK_BYTES);
#endif

    hp_model_revision = hp200lx_fw_detect();
    if ((hp_model_revision >> 8) != 2)
        panic("HPFW requires HP 200LX, model %x", hp_model_revision);

    hpfw_rom_vector[0] = peekw(0x0a * 4, 0);
    hpfw_rom_vector[1] = peekw(0x0a * 4 + 2, 0);
    require_rom(hpfw_rom_vector[0], hpfw_rom_vector[1]);
    /* These firmware vectors must remain executable after DOS is reclaimed. */
    for (i = 0; i < 2; ++i) {
        unsigned short vector = i ? 6 : 2;
        require_rom(peekw(vector * 4, 0), peekw(vector * 4 + 2, 0));
    }
    for (i = 0; i < 16; ++i) {
        off = peekw(0xf7ac + 4 * i, 0x9000);
        seg = peekw(0xf7ae + 4 * i, 0x9000);
        require_rom(off, seg);
    }
    sys_caps &= ~(CAP_KBD_LEDS | CAP_IRQ2MAP9 | CAP_IRQ8TO15);
    disable_irq(1);
    disable_irq(2);
    printk("HPR352B ROM %x IRQ2 %x:%x IER %x/%x PIC %x\n",
        hp_model_revision, hpfw_rom_vector[1], hpfw_rom_vector[0],
        hornet_read(0x18), hornet_read(0x19), inb(0x21));
}

static void hp_irq2(int irq, struct pt_regs *regs)
{
    ++hpfw_irq2;
    hp200lx_fw_rom_irq2();
}

/* One boot-time handoff, called with IF=0 after IRQ0/1/2 installation.
 * FW1D3 found inherited ISR=01 with no ELKS IRQ activity. Acknowledge only
 * that exact stale IRQ0, never another interrupt or ongoing ELKS service.
 * Returning the PIC to IRR read selection matches the BIOS convention.
 */
static void hp200lx_fw_handoff(void)
{
    unsigned short isr;
    outb(0x0b, 0x20);
    isr = inb(0x20);
    if (isr == 1 && !hpfw_irq0 && !hpfw_irq1 && !hpfw_irq2) {
        outb(0x60, 0x20); /* specific IRQ0 EOI */
    }
    outb(0x0a, 0x20);
}

/* kbd_init calls this with IF=0, after installing the ELKS IRQ1 handler. */
void hp200lx_fw_start(void)
{
    if (request_irq(2, hp_irq2, INT_GENERIC))
        panic("HPFW cannot claim IRQ2");
    /* 18/19 are positive register indices. Preserve pending firmware work;
     * do not clear interrupt-source flags, reset TIMER1, or scan the matrix.
     * TIMER1 alone is forced on: BIOS owns KBD enable during debounce.
     */
    hornet_write(0x18, hornet_read(0x18) | 0x01);
    hornet_write(0x19, hornet_read(0x19) | 0x08);
    outb((inb(0x61) | 0x40) & ~0x80, 0x61);
    enable_irq(0);
    enable_irq(1);
    enable_irq(2);
    hp200lx_fw_handoff();
}

void hp200lx_fw_state(struct hpfw_state *s)
{
    /* Called by /dev/kmem ioctl with IF=0 for a coherent snapshot. */
    s->version = HPFW_VERSION;
    s->model_revision = hp_model_revision;
    s->irq0 = hpfw_irq0;
    s->irq1 = hpfw_irq1;
    s->irq2 = hpfw_irq2;
    s->last_scan = hpfw_last_scan;
    s->pic_mask = inb(0x21);
    s->ier0 = hornet_read(0x18);
    s->ier1 = hornet_read(0x19);
    s->ppi = inb(0x61);
    s->rom_off = hpfw_rom_vector[0];
    s->rom_seg = hpfw_rom_vector[1];
}
