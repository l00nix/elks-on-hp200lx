ENTRY(hp200lx_fw_detect)
SECTIONS {
 . = 0x100;
 .text : { *(.text) }
 "hpfw_rom_vector!" = 0;
 hpfw_rom_vector = 0x800;
}
