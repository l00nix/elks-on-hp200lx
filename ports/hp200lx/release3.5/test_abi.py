#!/usr/bin/env python3
"""Execute the actual linked 16-bit firmware bridges with simulated BIOS handlers.

This checks ABI behavior, not Hornet hardware or ELKS boot success.
Install unicorn in testdeps, then run with the bundled Python runtime.
"""
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR, UC_HOOK_CODE, UC_HOOK_INSN
from unicorn.x86_const import *

REGS = {UC_X86_REG_BP: 0x5555, UC_X86_REG_BX: 0x1111,
        UC_X86_REG_SI: 0x2222, UC_X86_REG_DI: 0x3333,
        UC_X86_REG_DS: 0x2000, UC_X86_REG_ES: 0x4000}

def machine():
    u = Uc(UC_ARCH_X86, UC_MODE_16)
    u.mem_map(0, 0x100000)
    u.mem_write(0x10100, (HERE / 'build/abi.bin').read_bytes())
    for reg, value in REGS.items():
        u.reg_write(reg, value)
    u.reg_write(UC_X86_REG_CS, 0x1000)
    u.reg_write(UC_X86_REG_SS, 0x3000)
    u.reg_write(UC_X86_REG_SP, 0x7ffe)
    u.reg_write(UC_X86_REG_EFLAGS, 0x603)  # IF, DF, CF
    u.mem_write(0x37ffe, struct.pack('<H', 0xf000))  # near return sentinel
    u.hook_add(UC_HOOK_CODE, lambda uc, addr, size, data:
               uc.emu_stop() if addr == 0x1f000 else None)
    return u

class FirmwareABI(unittest.TestCase):
    def preserved(self, u):
        for reg, value in REGS.items():
            self.assertEqual(u.reg_read(reg), value)
        self.assertEqual(u.reg_read(UC_X86_REG_SP), 0x8000)
        self.assertEqual(u.reg_read(UC_X86_REG_SS), 0x3000)
        self.assertEqual(u.reg_read(UC_X86_REG_CS), 0x1000)
        self.assertEqual(u.reg_read(UC_X86_REG_IP), 0xf000)

    def detect(self, bx, cx, dx, expected):
        u = machine()
        def bios(uc, number, data):
            self.assertEqual(number, 0x15)
            self.assertEqual(uc.reg_read(UC_X86_REG_AX), 0x4dd4)
            uc.reg_write(UC_X86_REG_BX, bx)
            uc.reg_write(UC_X86_REG_CX, cx)
            uc.reg_write(UC_X86_REG_DX, dx)
            # Simulate firmware clobbering everything the bridge promises to save.
            for r in [UC_X86_REG_BP, UC_X86_REG_SI, UC_X86_REG_DI,
                      UC_X86_REG_DS, UC_X86_REG_ES]:
                uc.reg_write(r, 0x1234)
            uc.reg_write(UC_X86_REG_EFLAGS, 2)
        u.hook_add(UC_HOOK_INTR, bios)
        u.emu_start(0x10100, 0x1f001, count=100)
        self.preserved(u)
        self.assertEqual(u.reg_read(UC_X86_REG_AX), expected)
        self.assertEqual(u.reg_read(UC_X86_REG_EFLAGS) & 0x603, 0x603)

    def test_hp200_model_revision(self):
        self.detect(0x4850, 0x0102, 0x0203, 0x0203)

    def test_hp100_model_is_returned_for_c_side_rejection(self):
        self.detect(0x4850, 0x0102, 0x0001, 0x0001)

    def test_wrong_signature(self):
        self.detect(0, 0x0102, 0x0203, 0xffff)

    def test_wrong_family(self):
        self.detect(0x4850, 0x0101, 0x0203, 0xffff)

    def test_rom_iret_frame_registers_and_interrupt_mask(self):
        u = machine()
        u.mem_write(0x20800, struct.pack('<HH', 0x1000, 0xf000))
        # mov ax,7777; mov ds,ax; mov es,ax; clobber bx/si/di/bp; iret
        rom = bytes.fromhex('b877778ed88ec0bb4444be6666bf8888bdaaaa cf')
        u.mem_write(0xf1000, rom)
        visits = []
        def at_rom(uc, addr, size, data):
            if addr == 0xf1000:
                visits.append(addr)
                self.assertEqual(uc.reg_read(UC_X86_REG_EFLAGS) & 0x200, 0)
                sp = uc.reg_read(UC_X86_REG_SP)
                ip, cs, flags = struct.unpack('<HHH', bytes(uc.mem_read(0x30000+sp, 6)))
                self.assertEqual((ip, cs), (0x131, 0x1000))
                self.assertEqual(flags & 0x200, 0)
        u.hook_add(UC_HOOK_CODE, at_rom)
        u.emu_start(0x10125, 0x1f001, count=100)
        self.assertEqual(len(visits), 1)
        self.preserved(u)
        self.assertEqual(u.reg_read(UC_X86_REG_EFLAGS) & 0x200, 0)

class DOSSnapshot(unittest.TestCase):
    def snapshot(self, hp=True):
        u = Uc(UC_ARCH_X86, UC_MODE_16)
        u.mem_map(0, 0x100000)
        u.mem_write(0x10100, (HERE / 'HPSNAP.COM').read_bytes())
        for r in [UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS]:
            u.reg_write(r, 0x1000)
        u.reg_write(UC_X86_REG_SP, 0xfffe)
        for vector in [2, 6, 8, 9, 10, 16, 19, 21, 22, 28]:
            u.mem_write(4*vector, struct.pack('<HH', 0x1000+vector, 0xf000))
        for n in range(16):
            u.mem_write(0x9f7ac+4*n, struct.pack('<HH', 0x2000+n, 0xf000))
        u.mem_write(0x495, b'\x03')
        selector = [0x55]
        writes, output, exit_codes = [], [], []
        def readport(uc, port, size, data):
            return {0x22: selector[0], 0x23: selector[0] ^ 0xa5,
                    0x21: 0xf8, 0x61: 0x40}[port]
        def writeport(uc, port, size, value, data):
            self.assertEqual(port, 0x22)  # no register contents or PIC writes
            writes.append(value)
            selector[0] = value
        def interrupt(uc, num, data):
            ax = uc.reg_read(UC_X86_REG_AX)
            dx = uc.reg_read(UC_X86_REG_DX)
            if num == 0x15:
                self.assertEqual(ax, 0x4dd4)
                uc.reg_write(UC_X86_REG_BX, 0x4850 if hp else 0)
                uc.reg_write(UC_X86_REG_CX, 0x0102)
                uc.reg_write(UC_X86_REG_DX, 0x0203)
            elif num == 0x21 and ax >> 8 == 9:
                addr = 16 * uc.reg_read(UC_X86_REG_DS) + dx
                while (c := bytes(uc.mem_read(addr, 1))) != b'$':
                    output.append(c.decode('ascii')); addr += 1
            elif num == 0x21 and ax >> 8 == 2:
                output.append(chr(dx & 255))
            elif num == 0x21 and ax >> 8 == 0x4c:
                exit_codes.append(ax & 255)
                uc.emu_stop()
            else:
                self.fail(f'Unexpected INT {num:x} AX={ax:x}')
        u.hook_add(UC_HOOK_INTR, interrupt)
        u.hook_add(UC_HOOK_INSN, readport, None, 1, 0, UC_X86_INS_IN)
        u.hook_add(UC_HOOK_INSN, writeport, None, 1, 0, UC_X86_INS_OUT)
        u.emu_start(0x10100, 0x20000, count=100000)
        return ''.join(output), writes, selector[0], exit_codes

    def test_complete_snapshot_restores_selector(self):
        out, writes, selector, codes = self.snapshot()
        self.assertEqual(codes, [0])
        self.assertEqual(selector, 0x55)
        self.assertEqual(writes, [0x18,0x55,0x19,0x55,0x1a,0x55,0xe8,0x55,0xe7,0x55])
        self.assertIn('MODEL/REV DX=0203', out)
        self.assertIn('INT 000A = F000:100A', out)
        self.assertIn('IRQ2 TABLE 9000:F7E8 = F000:200F', out)
        self.assertIn('BIOS T1_STATE=0003', out)

    def test_non_hp_stops_before_hardware_reads(self):
        out, writes, selector, codes = self.snapshot(False)
        self.assertEqual(codes, [1])
        self.assertEqual(writes, [])
        self.assertIn('Not an HP 200LX', out)

if __name__ == '__main__':
    unittest.main(verbosity=2)
