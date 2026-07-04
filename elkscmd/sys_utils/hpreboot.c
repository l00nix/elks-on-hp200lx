/*
 * HP 200LX reboot helper.
 *
 * This intentionally follows the tiny DOS reboot.com-style behavior:
 * flush buffered writes, then jump directly to the BIOS reset vector.
 */

#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    sync();

    asm("ljmp $0xFFFF,$0\n\t");

    perror("hpreboot");
    return 1;
}
