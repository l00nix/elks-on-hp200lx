#!/usr/bin/env python3
"""Compile-check the HP load-base regression and unaffected PC/PC98 defaults."""
from pathlib import Path
import subprocess,tempfile,sys
p=Path(__file__).resolve().parent
header=Path(sys.argv[1]) if len(sys.argv)>1 else p/'build/elks/include/linuxmt/config.h'
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp); (t/'linuxmt').mkdir()
 (t/'linuxmt/config.h').write_bytes(header.read_bytes())
 # config.h includes major.h for unrelated device-number macros only.
 (t/'linuxmt/major.h').write_text('')
 for arch,hp,expected in [('CONFIG_ARCH_IBMPC',True,0x340),('CONFIG_ARCH_IBMPC',False,0xb0),('CONFIG_ARCH_PC98',False,0xc0)]:
  (t/'autoconf.h').write_text('#define '+arch+' 1\n'+('#define CONFIG_HP200LX_FW 1\n' if hp else ''))
  source='#include <linuxmt/config.h>\n_Static_assert(REL_SYSSEG == '+str(expected)+', "kernel load base regression");\n'
  subprocess.run(['cc','-std=c11','-x','c','-fsyntax-only','-I',str(t),'-'],input=source,text=True,check=True)
 print('PASS: HP=0340h, non-HP PC=00B0h, PC98=00C0h')
