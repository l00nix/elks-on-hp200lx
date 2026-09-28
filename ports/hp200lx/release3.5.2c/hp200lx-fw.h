/* HP 200LX firmware beta diagnostics. GPL-2.0-or-later. */
#ifndef ELKS_HP200LX_FW_H
#define ELKS_HP200LX_FW_H

#define MEM_GETHPFW 0x4850
#define HPFW_VERSION 1

struct hpfw_state {
    unsigned short version;
    unsigned short model_revision;
    unsigned short irq0, irq1, irq2;
    unsigned short last_scan;
    unsigned short pic_mask, ier0, ier1, ppi;
    unsigned short rom_off, rom_seg;
};

#ifdef __KERNEL__
extern volatile unsigned short hpfw_irq0, hpfw_irq1, hpfw_irq2;
extern volatile unsigned short hpfw_last_scan;
extern unsigned short hpfw_rom_vector[2];
void hp200lx_fw_prepare(void);
void hp200lx_fw_start(void);
void hp200lx_fw_state(struct hpfw_state *state);
#ifdef CONFIG_HP200LX_STACK_DIAG
void hp200lx_stack_report(void);
#endif
#endif
#endif
