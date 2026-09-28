/* HP firmware ABI bridges. GPL-2.0-or-later. */
#include <linuxmt/config.h>
#include <linuxmt/limits.h>
#ifdef CONFIG_HP200LX_STACK_DIAG
#include <arch/asm-offsets.h>
#endif
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
#ifdef CONFIG_HP200LX_STACK_DIAG
        /* Paint only unused words below SP. Do not change either stack size
         * or route the ROM to a different stack. All metadata is per call,
         * so nested service cannot overwrite another invocation's bounds.
         * DS=SS is the ELKS kernel calling convention; refuse unknown bounds.
         */
        mov %ss,%ax
        mov %ds,%dx
        cmp %dx,%ax
        jne .Lplain
        mov %sp,%di
        mov $endistack,%si
        mov $istack,%dx
        mov $hpfw_stack_irq,%bx
        cmp %si,%di
        jb .Ltask
        cmp %dx,%di
        jbe .Lbounds
.Ltask:
        mov current,%si
        cmp idle_task,%si
        je .Lunknown
        add $HP_TASK_KSTACK,%si
        mov %si,%dx
        add $KSTACK_BYTES,%dx
        mov $hpfw_stack_task,%bx
.Lbounds:
        test $1,%di
        jnz .Lunknown
        cmp %dx,%di
        ja .Lunknown
        mov %si,%ax
        add $64,%ax
        cmp %ax,%di
        jb .Lunknown
        cmpw $0x5476,-2(%si)
        je .Lguardok
        orw $1,8(%bx)
.Lguardok:
        /* entry = use before the original bridge's six saved registers. */
        mov %dx,%ax
        sub %di,%ax
        cmp $12,%ax
        jb .Lunknown
        sub $12,%ax
        cmp 6(%bx),%ax
        jbe .Lentryok
        mov %ax,6(%bx)
.Lentryok:
        /* Measure every task-stack call; shared stack first and every 32nd.
         * Keep cheap guard checks on EVERY recognized call. Counters saturate;
         * cadence is separate so measurement continues after saturation.
         */
        cmpw $0xffff,12(%bx)
        je .Lcounted
        incw 12(%bx)
.Lcounted:
        cmp $hpfw_stack_task,%bx
        je .Lsample
        mov 10(%bx),%ax
        incw 10(%bx)
        andw $31,10(%bx)
        or %ax,%ax
        je .Lsample
        push %si                /* skipped sample: guard base and record only */
        push %bx
        pushf
        lcall *hpfw_rom_vector
        cli
        mov %ss,%ax
        mov %ax,%ds
        pop %bx
        pop %si
        cmpw $0x5476,-2(%si)
        je .Ldone
        orw $2,8(%bx)
        jmp .Ldone
.Lsample:
        push %si                /* lower bound */
        push %dx                /* upper bound */
        push %bx                /* statistics record */
        mov %sp,%bp             /* ceiling of painted region */
        mov %si,%di
        mov %bp,%cx
        sub %di,%cx
        shr $1,%cx
        mov %ss,%ax
        mov %ax,%es
        mov $0xa55a,%ax
        cld
        rep stosw
        pushf
        lcall *hpfw_rom_vector
        cli
        /* BIOS need not preserve DS/ES. Recover them from the ELKS SS. */
        mov %ss,%ax
        mov %ax,%ds
        mov %ax,%es
        pop %bx
        pop %dx
        pop %si
        mov %sp,%di
        sub $6,%di              /* original painted ceiling */
        cmpw $0x5476,-2(%si)
        je .Lpostguard
        orw $2,8(%bx)
.Lpostguard:
        /* Scan without calls/pushes: do not contaminate the measurement. */
.Lscan:
        cmp %di,%si
        jae .Lfound
        cmpw $0xa55a,(%si)
        jne .Lfound
        add $2,%si
        jmp .Lscan
.Lfound:
        mov %dx,%ax
        sub %si,%ax
        cmp 2(%bx),%ax
        jbe .Ltotalok
        mov %ax,2(%bx)
.Ltotalok:
        sub %si,%di
        cmp 4(%bx),%di
        jbe .Lromok
        mov %di,4(%bx)
.Lromok:
        cmpw $0xffff,(%bx)
        je .Ldone
        incw (%bx)
        jmp .Ldone
.Lunknown:
        /* Unknown/near-exhausted stack: no painting, retain original call. */
        cmpw $0xffff,hpfw_stack_unknown
        je .Lplain
        incw hpfw_stack_unknown
.Lplain:
#endif
        pushf
        lcall *hpfw_rom_vector
        cli
#ifdef CONFIG_HP200LX_STACK_DIAG
.Ldone:
#endif
        pop %es
        pop %ds
        pop %di
        pop %si
        pop %bx
        pop %bp
        ret
