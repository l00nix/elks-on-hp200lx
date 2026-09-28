ENTRY(hp200lx_fw_detect)
SECTIONS {
 . = 0x100;
 .text : { *(.text) }
 "hpfw_rom_vector!" = 0; hpfw_rom_vector = 0x800;
 "current!" = 0; current = 0x810;
 "idle_task!" = 0; idle_task = 0x812;
 "hpfw_stack_task!" = 0; hpfw_stack_task = 0x820;
 "hpfw_stack_irq!" = 0; hpfw_stack_irq = 0x830;
 "hpfw_stack_unknown!" = 0; hpfw_stack_unknown = 0x840;
 "endistack!" = 0; endistack = 0x4000;
 "istack!" = 0; istack = 0x4400;
}
