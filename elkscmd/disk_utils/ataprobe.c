/*
 * HP 200LX direct ATA port probe for ELKS.
 *
 * This bypasses /dev/cfa and talks to the standard ATA window at 1f0/3f6
 * directly from userland. It is read-only: IDENTIFY and READ sector 0 only.
 */
#include <stdio.h>
#include <unistd.h>
#include <arch/io.h>

#define BASE        0x1f0
#define ALTSTAT     0x3f6

#define REG_DATA    (BASE + 0)
#define REG_FEAT    (BASE + 1)
#define REG_COUNT   (BASE + 2)
#define REG_LBA0    (BASE + 3)
#define REG_LBA1    (BASE + 4)
#define REG_LBA2    (BASE + 5)
#define REG_SELECT  (BASE + 6)
#define REG_STATUS  (BASE + 7)
#define REG_CMD     (BASE + 7)

#define ST_ERR      0x01
#define ST_DRQ      0x08
#define ST_DF       0x20
#define ST_BSY      0x80

static unsigned char last_status;
static unsigned char data[64];

static void small_delay(void)
{
    volatile unsigned int i;

    for (i = 0; i < 0x400; i++)
        ;
}

static void dump_regs(const char *label)
{
    unsigned int p;

    printf("%s cmd:", label);
    for (p = BASE; p < BASE + 8; p++)
        printf(" %02x", inb(p));
    printf(" alt:%02x\n", inb(ALTSTAT));
}

static void poll_status(const char *label, int max)
{
    int i;
    unsigned char st;

    printf("%s:", label);
    for (i = 0; i < max; i++) {
        st = inb(REG_STATUS);
        last_status = st;
        if (i < 32)
            printf(" %02x", st);
        if (!(st & ST_BSY) && (st & (ST_ERR | ST_DF | ST_DRQ)))
            break;
        small_delay();
    }
    printf(" final=%02x i=%d\n", last_status, i);
}

static void read_words(void)
{
    int i;
    unsigned short w;

    for (i = 0; i < 256; i++) {
        w = inw(REG_DATA);
        if (i < 32) {
            data[i * 2] = w & 0xff;
            data[i * 2 + 1] = w >> 8;
        }
    }
}

static void print_first32(const char *label)
{
    int i;

    printf("%s:", label);
    for (i = 0; i < 32; i++)
        printf(" %02x", data[i]);
    printf("\n");
}

static void identify(void)
{
    printf("IDENTIFY EC\n");
    outb(0xa0, REG_SELECT);
    small_delay();
    outb(0xec, REG_CMD);
    poll_status("id poll", 512);
    if (last_status & ST_DRQ) {
        read_words();
        print_first32("id first32");
    }
}

static void read_sector0(void)
{
    printf("READ 20 LBA0\n");
    outb(0xa0, REG_SELECT);
    small_delay();
    outb(0x00, REG_FEAT);
    outb(0x01, REG_COUNT);
    outb(0x00, REG_LBA0);
    outb(0x00, REG_LBA1);
    outb(0x00, REG_LBA2);
    outb(0xe0, REG_SELECT);
    small_delay();
    outb(0x20, REG_CMD);
    poll_status("rd poll", 1024);
    if (last_status & ST_DRQ) {
        read_words();
        print_first32("rd first32");
    }
}

int main(void)
{
    printf("ATAPROBE HP200LX direct 1f0/3f6\n");
    dump_regs("initial");
    identify();
    dump_regs("after id");
    read_sector0();
    dump_regs("after rd");
    return 0;
}
