/* HP firmware ABI bridges. GPL-2.0-or-later. */
        .arch i8086, nojumps
        .code16
        .text

/* unsigned short hp200lx_fw_detect(void): model/revision DX, or FFFF.
 * Preserve C callee-saved registers, segments and incoming flags.
 */
        .global hp200lx_fw_detect
hp200lx_fw_detect:
        pushf
        push %bp
        push %bx
        push %si
        push %di
        push %ds
        push %es
        mov $0x4dd4,%ax
        int $0x15
        mov $0xffff,%ax
        cmp $0x4850,%bx
        jne 1f
        cmp $0x0102,%cx
        jne 1f
        mov %dx,%ax
1:      pop %es
        pop %ds
        pop %di
        pop %si
        pop %bx
        pop %bp
        popf
        ret

/* Invoke the saved hardware ISR with its expected interrupt stack frame.
 * _irqit has already switched to an ELKS kernel/interrupt stack.
 * IRQ2 EOI is issued by ROM; the ELKS return path skips its own IRQ2 EOI.
 * Leave IF clear until _irqit returns: ROM has already acknowledged IRQ2,
 * so restoring IF here could let another IRQ2 nest before the stack unwinds.
 */
        .global hp200lx_fw_rom_irq2
hp200lx_fw_rom_irq2:
        cli
        push %bp
        push %bx
        push %si
        push %di
        push %ds
        push %es
        pushf
        lcall *hpfw_rom_vector
        cli
        pop %es
        pop %ds
        pop %di
        pop %si
        pop %bx
        pop %bp
        ret
