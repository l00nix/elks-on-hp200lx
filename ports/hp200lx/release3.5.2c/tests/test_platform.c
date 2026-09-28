/* Execute production platform code with a mock PIC/Hornet/IVT.
 * This validates guards and ordering, not firmware timing or HP hardware.
 */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <setjmp.h>
#include <string.h>
#define CONFIG_HP200LX_STACK_DIAG 1
#define KSTACK_BYTES 700
#define INTRSTACK_BYTES 1024
#define KSTACK_MAGIC 0x5476
#define DEF_INITSEG 0x100
#define DEF_SYSSEG 0x1400
#define REL_SYSSEG 0x340
typedef unsigned short flag_t;
static unsigned short flags_word=0x202;
unsigned short hpfw_istack_guard;
#define save_flags(f) ((f)=flags_word)
#define clr_irq() (flags_word &= ~0x200)
#define restore_flags(f) (flags_word=(f))
#define __KERNEL__ 1
#define CONFIG_ARCH_IBMPC 1
#define CONFIG_KEYBOARD_SCANCODE 1
#define CONFIG_CONSOLE_BIOS 1
#define CAP_KBD_LEDS 4
#define CAP_IRQ2MAP9 32
#define CAP_IRQ8TO15 16
#define INT_GENERIC 0
struct pt_regs { int unused; };
static unsigned short sys_caps, model, bad_vector;
static unsigned char selector, hornet[256], pic_mask, pic_isr, pic_select, ppi;
static unsigned eoi, registered, irq2_calls, calls;
static int panicked, expect_panic;
static jmp_buf fault;
static void panic(const char *fmt, ...) { assert(expect_panic); panicked=1; longjmp(fault,1); }
static char output[2048];
static void printk(const char *fmt, ...) {
    va_list ap; va_start(ap,fmt);
    vsnprintf(output+strlen(output),sizeof(output)-strlen(output),fmt,ap);
    va_end(ap);
}
static unsigned short peekw(unsigned short off, unsigned short seg) {
    if (!seg) {
        if (off%4 == 2) return off/4 == bad_vector ? 0x1234 : 0xf000;
        return 0x8000+off;
    }
    assert(seg==0x9000 && off>=0xf7ac && off<=0xf7ea);
    return (off-0xf7ac)%4 == 2 ? (bad_vector==99 ? 0x9000 : 0xf000) : 0x8100;
}
static unsigned short inb(unsigned port) {
    switch(port) {
    case 0x20: return pic_select==0x0b ? pic_isr : 5;
    case 0x21: return pic_mask;
    case 0x22: return selector;
    case 0x23: return hornet[selector];
    case 0x61: return ppi;
    default: assert(0); return 0;
    }
}
static void outb(unsigned value,unsigned port) {
    switch(port) {
    case 0x20:
        if(value==0x60) { assert(registered); ++eoi; pic_isr&=~1; }
        else { assert(value==0x0a || value==0x0b); pic_select=value; }
        break;
    case 0x22: selector=value; break;
    case 0x23:
        assert(selector==0x18 || selector==0x19); /* never clear sources */
        hornet[selector]=value; break;
    case 0x61: ppi=value; break;
    default: assert(0);
    }
}
static void disable_irq(unsigned irq) { pic_mask|=1<<irq; }
static void enable_irq(unsigned irq) { pic_mask&=~(1<<irq); }
static int request_irq(int irq, void (*fn)(int,struct pt_regs*),int type) {
    assert(irq==2 && type==INT_GENERIC); assert(!registered); registered=1;
    enable_irq(irq); return 0;
}
unsigned short hp200lx_fw_detect(void) { return model; }
void hp200lx_fw_rom_irq2(void) { ++irq2_calls; }
#include "../hp200lx-fw.c"
static void reset(void) {
    output[0]=0; hpfw_istack_guard=0; sys_caps=0xff; model=0x0201; bad_vector=0; selector=0x55;
    memset(hornet,0,sizeof hornet); hornet[0x18]=0xf6; hornet[0x19]=0x47;
    hornet[0x1a]=0x4a; pic_mask=0xbf; pic_isr=1; pic_select=0x0a; ppi=0x88;
    eoi=registered=irq2_calls=panicked=expect_panic=0;
    hpfw_irq0=hpfw_irq1=hpfw_irq2=hpfw_last_scan=0;
}
static void check(unsigned isr,unsigned i0,unsigned i1,unsigned i2,unsigned expected) {
    reset(); hp200lx_fw_prepare();
    assert(hpfw_istack_guard==KSTACK_MAGIC);
    assert(strstr(output,"HPBOOT initial=100 staging=1400 reloc=340 stacks=700/1024"));
    assert(!(sys_caps & (CAP_KBD_LEDS|CAP_IRQ2MAP9|CAP_IRQ8TO15)));
    assert((pic_mask & 6)==6); assert(selector==0x55);
    pic_isr=isr; hpfw_irq0=i0; hpfw_irq1=i1; hpfw_irq2=i2;
    hp200lx_fw_start();
    assert(eoi==expected && registered==1 && pic_select==0x0a);
    assert(pic_isr==(expected ? (isr&~1) : isr));
    assert(pic_mask==0xb8 && selector==0x55 && ppi==0x48);
    assert(hornet[0x18]==0xf7 && hornet[0x19]==0x4f && hornet[0x1a]==0x4a);
    hp_irq2(2,0); assert(irq2_calls==1 && hpfw_irq2==i2+1);
    struct hpfw_state s; hp200lx_fw_state(&s);
    assert(s.version==1 && s.model_revision==0x0201 && s.irq2==i2+1);
    assert(s.rom_seg==0xf000 && s.rom_off==0x8028);
    ++calls;
}
static void reject(unsigned m,unsigned bad) {
    reset(); model=m; bad_vector=bad; expect_panic=1;
    if (!setjmp(fault)) hp200lx_fw_prepare();
    assert(panicked && !registered && !eoi); ++calls;
}
int main(void) {
    check(1,0,0,0,1); check(0,0,0,0,0); check(5,0,0,0,0);
    check(1,1,0,0,0); check(1,0,1,0,0); check(1,0,0,1,0);
    reject(0xffff,0); reject(1,0); reject(0x0201,10);
    reject(0x0201,2); reject(0x0201,6); reject(0x0201,99);
    output[0]=0;
    hpfw_stack_task[0]=12; hpfw_stack_task[1]=220; hpfw_stack_task[2]=60;
    hpfw_stack_task[3]=142; hpfw_stack_task[4]=2;
    hpfw_stack_irq[0]=3; hpfw_stack_irq[1]=440; hpfw_stack_irq[2]=200;
    hpfw_stack_irq[3]=222; hpfw_stack_irq[4]=1;
    hpfw_stack_unknown=9; hpfw_stack_task[6]=123; hpfw_stack_irq[6]=456;
    hp200lx_stack_report();
    assert(flags_word==0x202);
    assert(strstr(output,"task n=12 entry=142 used=220/700 rom=60 guard=2"));
    assert(strstr(output,"irq  n=3 entry=222 used=440/1024 rom=200 guard=1"));
    assert(strstr(output,"calls task=123 irq=456 sample=all/32 guard=each"));
    assert(strstr(output,"unknown=9")); ++calls;
    flags_word=2; output[0]=0; hp200lx_stack_report(); assert(flags_word==2); ++calls;
    printf("PASS: %u platform cases (handoff guards, ROM rejection, dispatch, I/O preservation)\n",calls);
}
