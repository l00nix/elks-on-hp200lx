/*
 * Polling keyboard driver
 *
 * Calls conio_poll to get kbd input
 */
#include <linuxmt/types.h>
#include <linuxmt/config.h>
#include <linuxmt/timer.h>
#include <linuxmt/sched.h>
#include "console.h"
#include "conio.h"
#include <linuxmt/debug.h>
#include <linuxmt/kernel.h>
#include <arch/io.h>
#include <arch/segment.h>

char kbd_name[] = "polling";

static void restart_timer(void);

/*
 * Poll for keyboard character
 * Decodes non-zero high byte into arrow/fn keys
 */


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

static void kbd_timer(int data)
{
    hp200lx_newton_idle_poll_n24();
    restart_timer();
}

static void restart_timer(void)
{
    static struct timer_list timer;

    timer.tl_expires = jiffies + (8 * HZ/100);	/* every 8/100 second*/
    timer.tl_function = kbd_timer;
    add_timer(&timer);
}


void kbd_init(void)
{
    hp200lx_newton_raw_probe_n24();
    conio_init();
    restart_timer();
}
