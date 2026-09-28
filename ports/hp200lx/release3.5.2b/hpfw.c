/* Read-only HP firmware beta diagnostic. GPL-2.0-or-later. */
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linuxmt/hp200lx-fw.h>

int main(int argc, char **argv)
{
    struct hpfw_state s;
    int fd;
    if (argc == 2 && !strcmp(argv[1], "spin")) {
        volatile unsigned short n = 0;
        puts("CPU loop running. Press Ctrl-C; the shell must return promptly.");
        fflush(stdout);
        for (;;) ++n;
    }
    if (argc != 1) {
        fprintf(stderr, "Usage: hpfw [spin]\n");
        return 1;
    }
    fd = open("/dev/kmem", O_RDONLY);
    if (fd < 0) { perror("/dev/kmem"); return 1; }
    if (ioctl(fd, MEM_GETHPFW, &s) < 0) {
        perror("HPFW ioctl (requires FW1 kernel)");
        close(fd);
        return 1;
    }
    close(fd);
    if (s.version != HPFW_VERSION) {
        fprintf(stderr, "Unsupported HPFW diagnostic version\n");
        return 1;
    }
    printf("HPFW1 model/revision=%04x ROM IRQ2=%04x:%04x\n",
        s.model_revision, s.rom_seg, s.rom_off);
    printf("IRQ0=%u IRQ1=%u IRQ2=%u last_scan=%02x\n",
        s.irq0, s.irq1, s.irq2, s.last_scan);
    printf("PIC=%02x IER18=%02x IER19=%02x PPI61=%02x\n",
        s.pic_mask, s.ier0, s.ier1, s.ppi);
    puts("Counters wrap at 65536. IRQ0 should advance about 100/sec.");
    return 0;
}
