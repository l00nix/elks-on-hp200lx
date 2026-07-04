BASEDIR=..

include $(BASEDIR)/Makefile-rules

###############################################################################

###############################################################################

PRGS = ramdisk mkfs mkfat fsck partype fdisk df cfprobe ataprobe

all: $(PRGS)

install: all
	$(INSTALL) $(PRGS) $(DESTDIR)/bin

df: df.o $(TINYPRINTF)
	$(LD) $(LDFLAGS) -o df df.o $(TINYPRINTF) $(LDLIBS)

fsck: fsck.o
	$(LD) $(LDFLAGS) -o fsck -maout-heap=0xffff fsck.o $(LDLIBS)

fdisk: fdisk.o $(TINYPRINTF)
	$(LD) $(LDFLAGS) -o fdisk fdisk.o $(TINYPRINTF) $(LDLIBS)

cfprobe: cfprobe.o $(TINYPRINTF)
	$(LD) $(LDFLAGS) -o cfprobe cfprobe.o $(TINYPRINTF) $(LDLIBS)

ataprobe: ataprobe.o $(TINYPRINTF)
	$(LD) $(LDFLAGS) -o ataprobe ataprobe.o $(TINYPRINTF) $(LDLIBS)

mkfs: mkfs.o $(TINYPRINTF)
	$(LD) $(LDFLAGS) -o mkfs mkfs.o $(TINYPRINTF) $(LDLIBS)

mkfat: mkfat.o $(TINYPRINTF)
	$(LD) $(LDFLAGS) -o mkfat mkfat.o $(TINYPRINTF) $(LDLIBS)

partype: partype.o
	$(LD) $(LDFLAGS) -o partype partype.o $(LDLIBS)

ramdisk: ramdisk.o
	$(LD) $(LDFLAGS) -o ramdisk ramdisk.o $(LDLIBS)

clean:
	$(RM) *.o $(PRGS)
