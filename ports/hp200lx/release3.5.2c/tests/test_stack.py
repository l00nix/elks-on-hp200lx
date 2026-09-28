#!/usr/bin/env python3
"""Execute the freshly linked production probe against synthetic ROM stack use.
Not an HP ROM emulator; written watermarks do not measure unwritten SP movement.
"""
from pathlib import Path
import re, struct, unittest
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_CODE
from unicorn.x86_const import *
P=Path(__file__).resolve().parent.parent
SYMS={s[2]:int(s[0],16) for line in (P/'build/stack.map').read_text().splitlines() if len(s:=line.split())==3}
OFF=int(re.search(r'#define\s+HP_TASK_KSTACK\s+(\d+)',(P/'build/asm-offsets.h').read_text())[1])
REGS={UC_X86_REG_BP:0x5555,UC_X86_REG_BX:0x1111,UC_X86_REG_SI:0x2222,UC_X86_REG_DI:0x3333,UC_X86_REG_DS:0x3000,UC_X86_REG_ES:0x4000}
def word(u,off,v):u.mem_write(0x30000+off,struct.pack('<H',v))
def words(u,off,n=5):return struct.unpack('<'+'H'*n,bytes(u.mem_read(0x30000+off,2*n)))
def setup(kind='task',entry=100,depth=80,sp=None,guard=0x5476,damage=False):
 u=Uc(UC_ARCH_X86,UC_MODE_16);u.mem_map(0,0x100000)
 u.mem_write(0x10100,(P/'build/stack.bin').read_bytes())
 base=0x5000+OFF if kind=='task' else 0x4000;top=base+(700 if kind=='task' else 1024)
 u.mem_write(0x30000+base-16,b'\xcc'*(top-base+32));word(u,base-2,guard)
 word(u,0x810,0x5000);word(u,0x812,0x6000)
 u.mem_write(0x30800,struct.pack('<HH',0x1000,0xf000))
 for r,v in REGS.items():u.reg_write(r,v)
 u.reg_write(UC_X86_REG_CS,0x1000);u.reg_write(UC_X86_REG_SS,0x3000)
 sp=top-entry if sp is None else sp
 u.reg_write(UC_X86_REG_SP,sp);u.reg_write(UC_X86_REG_EFLAGS,0x203);word(u,sp,0xf000)
 # Allocate and WRITE a chosen depth below the six-byte fake interrupt frame.
 rom=b'\x81\xec'+struct.pack('<H',depth)
 if depth:rom+=b'\x89\xe5\x36\xc7\x46\x00\x34\x12'
 if damage:rom+=b'\x36\xc7\x06'+struct.pack('<H',base-2)+b'\x00\x00'
 rom+=b'\x81\xc4'+struct.pack('<H',depth)
 # BIOS clobbers all callee saved regs, including segments. Wrapper restores them.
 rom+=bytes.fromhex('b877778ed88ec0bb4444be6666bf8888bdaaaacf')
 u.mem_write(0xf1000,rom)
 u.hook_add(UC_HOOK_CODE,lambda uc,a,s,d:uc.emu_stop() if a==0x1f000 else None)
 return u,base,top,sp

def run(u):
 u.emu_start(0x10000+SYMS['hp200lx_fw_rom_irq2'],0x1f001,count=100000)
 assert u.reg_read(UC_X86_REG_CS)==0x1000 and u.reg_read(UC_X86_REG_IP)==0xf000, 'Bridge did not return'

class Probe(unittest.TestCase):
 def preserved(self,u,sp):
  for r,v in REGS.items():self.assertEqual(u.reg_read(r),v)
  self.assertEqual(u.reg_read(UC_X86_REG_SP),sp+2)
  self.assertEqual(u.reg_read(UC_X86_REG_IP),0xf000)
  self.assertEqual(u.reg_read(UC_X86_REG_EFLAGS)&0x200,0)
 def test_both_stack_types_exact_depth_and_live_data(self):
  for kind,stats in [('task',0x820),('irq',0x830)]:
   with self.subTest(kind=kind):
    u,b,t,sp=setup(kind);run(u);self.preserved(u,sp)
    self.assertEqual(words(u,stats),(1,204,86,100,0))
    self.assertEqual(words(u,b-2,1),(0x5476,))
    self.assertEqual(bytes(u.mem_read(0x30000+sp+2,t-sp)),b'\xcc'*(t-sp))
    self.assertEqual(bytes(u.mem_read(0x30000+b-16,14)),b'\xcc'*14)
 def test_peak_and_count_saturation(self):
  u,b,t,sp=setup();word(u,0x820,65535);word(u,0x822,350);word(u,0x824,180);word(u,0x826,200)
  run(u);self.assertEqual(words(u,0x820),(65535,350,180,200,0))
 def test_guard_before_and_after_are_sticky(self):
  for guard,damage,expected in [(0,False,3),(0x5476,True,2),(0x5476,False,0)]:
   u,b,t,sp=setup(guard=guard,damage=damage);run(u);self.assertEqual(words(u,0x820)[4],expected)
  u,b,t,sp=setup();word(u,0x828,3);run(u);self.assertEqual(words(u,0x820)[4],3)
 def test_unknown_or_too_low_stack_is_not_painted(self):
  b=0x5000+OFF
  for sp in [0x7000,b+60,b+701,b+699]:
   u,base,t,_=setup(sp=sp,depth=0);run(u);self.preserved(u,sp)
   self.assertEqual(words(u,0x840,1),(1,));self.assertEqual(words(u,0x820),(0,0,0,0,0))
   self.assertEqual(bytes(u.mem_read(0x30000+b,16)),b'\xcc'*16)
 def test_idle_stack_excluded_and_unknown_saturates(self):
  u,b,t,sp=setup();word(u,0x812,0x5000);word(u,0x840,65535);run(u)
  self.assertEqual(words(u,0x840,1),(65535,));self.assertEqual(words(u,0x820),(0,0,0,0,0))
 def test_ds_ss_mismatch_uses_plain_bridge(self):
  u,b,t,sp=setup();u.reg_write(UC_X86_REG_DS,0x2000)
  u.mem_write(0x20800,struct.pack('<HH',0x1000,0xf000));run(u)
  self.assertEqual(u.reg_read(UC_X86_REG_DS),0x2000)
  self.assertEqual(words(u,0x820),(0,0,0,0,0));self.assertEqual(words(u,0x840,1),(0,))
 def test_nested_call_keeps_per_call_metadata(self):
  for kind in ['task','irq']:
   with self.subTest(kind=kind):
    u,b,t,sp=setup(kind,depth=40)
    saved=[];done=[]
    regs=list(REGS)+[UC_X86_REG_AX,UC_X86_REG_CX,UC_X86_REG_DX,UC_X86_REG_CS,UC_X86_REG_SS,UC_X86_REG_SP,UC_X86_REG_IP,UC_X86_REG_EFLAGS]
    def nested(uc,a,s,d):
     if a==0xf1000 and not saved and not done:
      saved.append({r:uc.reg_read(r) for r in regs})
      word(uc,0x83a,0) # force nested shared sample to exercise full nested probe
      nsp=0x4400-100 if kind=='task' else uc.reg_read(UC_X86_REG_SP)-48
      word(uc,0x3ffe,0x5476)
      word(uc,nsp,0xe000);uc.reg_write(UC_X86_REG_SP,nsp)
      uc.reg_write(UC_X86_REG_CS,0x1000);uc.reg_write(UC_X86_REG_IP,SYMS['hp200lx_fw_rom_irq2'])
     elif a==0x1e000:
      for r,v in saved.pop().items():uc.reg_write(r,v)
      done.append(1)
    u.hook_add(UC_HOOK_CODE,nested);run(u);self.preserved(u,sp);self.assertEqual(done,[1])
    if kind=='task':
     self.assertEqual(words(u,0x820),(1,164,46,100,0));self.assertEqual(words(u,0x830),(1,164,46,100,0))
    else:self.assertEqual(words(u,0x830),(2,236,118,172,0))

class Sampling(unittest.TestCase):
 preserved = Probe.preserved
 def test_skipped_calls_preserve_unused_stack_and_check_guards(self):
  for kind,stats in [('irq',0x830)]:
   for guard,damage,expected in [(0x5476,False,0),(0,False,3),(0x5476,True,2)]:
    u,b,t,sp=setup(kind,guard=guard,damage=damage);word(u,stats+10,1)
    run(u);self.preserved(u,sp)
    self.assertEqual(words(u,stats),(0,0,0,100,expected))
    self.assertEqual(words(u,stats+10,2),(2,1))
    self.assertEqual(bytes(u.mem_read(0x30000+b,16)),b'\xcc'*16)
 def test_all_task_calls_and_one_in_32_shared_calls(self):
  for kind,stats in [('task',0x820),('irq',0x830)]:
   u,b,t,sp=setup(kind)
   for count in range(1,66):
    u.reg_write(UC_X86_REG_SP,sp);run(u);self.preserved(u,sp)
    self.assertEqual(words(u,stats)[0],count if kind=='task' else 1+(count-1)//32)
    self.assertEqual(words(u,stats+10,2),(0 if kind=='task' else count%32,count))
 def test_sampling_continues_after_both_counters_saturate(self):
  u,b,t,sp=setup('irq');word(u,0x830,65535);word(u,0x83c,65535);word(u,0x83a,31)
  run(u);self.assertEqual(words(u,0x830)[1],0)
  u.reg_write(UC_X86_REG_SP,sp);run(u)
  self.assertEqual(words(u,0x830),(65535,204,86,100,0))
  self.assertEqual(words(u,0x83a,2),(1,65535))
 def test_task_phase_never_skips_even_after_saturation(self):
  for phase in [0,1,31]:
   u,b,t,sp=setup();word(u,0x820,65535);word(u,0x82c,65535);word(u,0x82a,phase)
   run(u);self.preserved(u,sp)
   self.assertEqual(words(u,0x820),(65535,204,86,100,0))
   self.assertEqual(words(u,0x82a,2),(phase,65535))
 def test_skipped_path_executes_far_fewer_instructions(self):
  counts=[]
  for phase in [0,1]:
   u,b,t,sp=setup('irq');word(u,0x83a,phase);counter=[0]
   def tick(uc,a,s,d):counter[0]+=1
   u.hook_add(UC_HOOK_CODE,tick);run(u);counts.append(counter[0])
  self.assertLess(counts[1],counts[0]//10)
  print('Synthetic IRQ probe instruction counts, sampled/skipped:',*counts)

if __name__=='__main__':unittest.main(verbosity=2)
