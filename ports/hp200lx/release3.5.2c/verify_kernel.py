#!/usr/bin/env python3
"""Check a completed beta build, without emulating HP hardware."""
from pathlib import Path
import hashlib, json, re, struct, sys

work = Path(sys.argv[1])
b = (work/'elks/arch/i86/boot/Image').read_bytes()
config = (work/'include/autoconf.h').read_text()
symbols = (work/'elks/arch/i86/boot/system.map').read_text()
assert not re.search(r'^#define\s+CONFIG_(BLK_DEV_RAM|RAMDISK_SEGMENT|RAMDISK_SECTORS)\b', config, re.M)
for name in ['CONFIG_HP200LX_STACK_DIAG', 'CONFIG_HP200LX_FW', 'CONFIG_BLK_DEV_ATA_CF', 'CONFIG_MINIX_FS', 'CONFIG_BOOTOPTS']:
    assert re.search(r'^#define\s+'+name+r'\s+1\b', config, re.M), name
for name in ['CONFIG_SOCKET', 'CONFIG_INET', 'CONFIG_ETH', 'CONFIG_ETH_NE2K']:
    assert not re.search(r'^#define\s+'+name+r'\s+1\b', config, re.M), name
for name in ['rd_init', 'rd_open', 'rd_release', 'rd_ioctl', 'do_rd_request', 'rd_fops', 'rd_segment', 'rd_info']:
    assert not re.search(r'\b'+name+r'$', symbols, re.M), name
for name in ['hp200lx_fw_prepare', 'hp200lx_fw_start', 'hp200lx_fw_rom_irq2', 'ata_init', 'hp200lx_stack_report', 'hpfw_stack_task', 'hpfw_stack_irq', 'hpfw_istack_guard']:
    assert re.search(r'\b'+name+r'$', symbols, re.M), name
addresses = {x[2]: int(x[0],16) for line in symbols.splitlines() if len(x:=line.split()) == 3}
assert addresses['endistack'] - addresses['hpfw_istack_guard'] == 2
assert addresses['istack'] - addresses['endistack'] == 1024
assert b'sample=all/32 guard=each' in b
assert b'HPST task n=' in b and b'HPST irq  n=' in b and b'HPBOOT initial=' in b
assert not (work/'elks/arch/i86/drivers/block/rd.o').exists()
if (work/'ramdisk-audit.txt').exists():
    objects = (work/'ramdisk-audit.txt').read_text().splitlines()
    assert 'rd.o' not in objects and 'ata.o' in objects
assert len(b) < 65536 and b[497] == 4
assert b[0x824:0x828] == bytes.fromhex('55aa5a5a')
start = (1+b[497])*512
h = b[start:start+64]
assert h[:5] == bytes.fromhex('0103300440')
s = struct.unpack_from('<14I', h, 8)
length = 64+s[0]+s[1]+s[6]+s[7]+s[10]+s[11]
assert len(b) == start+length and s[1]+s[2] < 65536
assert struct.unpack_from('<H', b, 500)[0] == (length+15)//16
assert b'HPR352C ROM' in b and b'rd: %dK ramdisk' not in b
print(json.dumps({'image_bytes':len(b), 'near_text_bytes':s[0], 'far_text_bytes':s[10],
    'data_bytes':s[1], 'bss_bytes':s[2], 'relocation_bytes':s[6]+s[7]+s[11],
    'sha256':hashlib.sha256(b).hexdigest(), 'ramdisk_driver':'absent',
    'status':'build checks passed; real HP boot pending'}, indent=2))
