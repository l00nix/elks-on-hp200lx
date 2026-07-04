/*
 * HP 200LX CF block-device probe.
 *
 * Small ELKS userland diagnostic for checking where /dev/cfa access fails:
 * stat, open, read, or geometry ioctl.
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <sys/stat.h>

#ifdef _M_I86
#include <arch/hdreg.h>
#endif

static void show_type(unsigned int mode)
{
    if (S_ISBLK(mode))
        printf(" blk");
    else if (S_ISCHR(mode))
        printf(" chr");
    else if (S_ISREG(mode))
        printf(" reg");
    else if (S_ISDIR(mode))
        printf(" dir");
    else
        printf(" other");
}

static void probe_one(const char *name)
{
    struct stat st;
    unsigned char buf[512];
    int fd;
    int n;
    int i;

    printf("%s\n", name);

    errno = 0;
    if (stat(name, &st) < 0) {
        printf(" stat=-1 errno=%d\n", errno);
        return;
    }

    printf(" stat=0 mode=%04o", st.st_mode);
    show_type(st.st_mode);
    printf(" rdev=%u,%u raw=%04x\n",
           (unsigned int)(st.st_rdev >> 8),
           (unsigned int)(st.st_rdev & 0xff),
           (unsigned int)st.st_rdev);

    errno = 0;
    fd = open(name, O_RDONLY);
    if (fd < 0) {
        printf(" open=-1 errno=%d\n", errno);
        return;
    }
    printf(" open=%d\n", fd);

    errno = 0;
    n = read(fd, buf, sizeof(buf));
    if (n < 0) {
        printf(" read=-1 errno=%d\n", errno);
    } else {
        printf(" read=%d", n);
        if (n >= 16) {
            printf(" first16:");
            for (i = 0; i < 16; i++)
                printf(" %02x", (unsigned int)buf[i]);
        }
        printf("\n");
    }

#ifdef _M_I86
    {
        struct hd_geometry geo;

        errno = 0;
        n = ioctl(fd, HDIO_GETGEO, &geo);
        if (n < 0) {
            printf(" geo=-1 errno=%d\n", errno);
        } else {
            printf(" geo=0 C=%u H=%u S=%u start=%lu\n",
                   (unsigned int)geo.cylinders,
                   (unsigned int)geo.heads,
                   (unsigned int)geo.sectors,
                   geo.start);
        }
    }
#endif

    close(fd);
}

int main(int argc, char **argv)
{
    int i;

    if (argc > 1) {
        for (i = 1; i < argc; i++)
            probe_one(argv[i]);
        return 0;
    }

    probe_one("/dev/cfa");
    probe_one("/dev/cfa1");
    probe_one("/dev/cfb");
    return 0;
}
