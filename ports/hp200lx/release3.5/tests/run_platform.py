#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
p=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 for f in ['linuxmt/config.h','linuxmt/kernel.h','linuxmt/memory.h','linuxmt/sched.h','arch/io.h','arch/irq.h','arch/system.h']:
  q=t/f;q.parent.mkdir(exist_ok=True,parents=True);q.write_text('')
 (t/'linuxmt/hp200lx-fw.h').write_bytes((p.parent/'hp200lx-fw.h').read_bytes())
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Wno-unused-parameter','-I',str(t),str(p/'test_platform.c'),'-o',str(t/'test')],check=True)
 subprocess.run([str(t/'test')],check=True)
