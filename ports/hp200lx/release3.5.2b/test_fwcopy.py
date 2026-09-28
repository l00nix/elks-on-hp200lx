#!/usr/bin/env python3
"""Run the actual B352BCPY.COM in an 8086-mode emulator with mocked DOS file I/O."""
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR
from unicorn.x86_const import *

def run(fault=None, size=62736):
    u = Uc(UC_ARCH_X86, UC_MODE_16)
    u.mem_map(0, 0x100000)
    u.mem_write(0x10100, (HERE/'B352BCPY.COM').read_bytes())
    for reg in [UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS]:
        u.reg_write(reg, 0x1000)
    u.reg_write(UC_X86_REG_SP, 0xfffe)
    payload = bytes((i*17+3) % 256 for i in range(size))
    files = {'K352B': bytearray(payload), 'KERNBOP': bytearray(b'old kernel')}
    handles = {}
    output, exits = [], []
    def reg(r): return u.reg_read(r)
    def string(addr, terminator):
        result = bytearray()
        while (b := bytes(u.mem_read(addr, 1))) != terminator:
            result.extend(b); addr += 1
        return result.decode('ascii')
    def interrupt(uc, number, data):
        assert number == 0x21
        ax, bx, cx, dx = [reg(r) for r in [UC_X86_REG_AX, UC_X86_REG_BX, UC_X86_REG_CX, UC_X86_REG_DX]]
        ah = ax >> 8
        addr = 16*reg(UC_X86_REG_DS)+dx
        uc.reg_write(UC_X86_REG_EFLAGS, reg(UC_X86_REG_EFLAGS) & ~1)
        def error():
            uc.reg_write(UC_X86_REG_EFLAGS, reg(UC_X86_REG_EFLAGS) | 1)
            uc.reg_write(UC_X86_REG_AX, 5)
        if ah in (0x3d, 0x3c):
            name = string(addr, b'\0')
            if fault == 'open' and name == 'K352B': return error()
            if fault == 'create' and ah == 0x3c: return error()
            if ah == 0x3c: files[name] = bytearray()
            if name not in files: return error()
            handle = max([4] + list(handles)) + 1
            handles[handle] = [name, 0]
            uc.reg_write(UC_X86_REG_AX, handle)
        elif ah == 0x42:
            if fault == 'seek': return error()
            entry = handles[bx]
            entry[1] = len(files[entry[0]]) if (ax & 255) == 2 else 0
            uc.reg_write(UC_X86_REG_AX, entry[1] & 65535)
            uc.reg_write(UC_X86_REG_DX, entry[1] >> 16)
        elif ah == 0x3f:
            name, pos = handles[bx]
            if fault == 'read': return error()
            chunk = bytes(files[name][pos:pos+cx])
            if fault == 'corrupt' and name == 'KERNBOP' and chunk:
                chunk = bytes([chunk[0] ^ 1]) + chunk[1:]
            if chunk: uc.mem_write(addr, chunk)
            handles[bx][1] += len(chunk)
            uc.reg_write(UC_X86_REG_AX, len(chunk))
        elif ah == 0x40:
            if fault == 'write': return error()
            name, pos = handles[bx]
            n = cx-1 if fault == 'shortwrite' else cx
            files[name][pos:pos+n] = bytes(uc.mem_read(addr, n))
            handles[bx][1] += n
            uc.reg_write(UC_X86_REG_AX, n)
        elif ah == 0x3e:
            if fault == 'close': return error()
            del handles[bx]
        elif ah == 9:
            output.append(string(addr, b'$'))
            uc.reg_write(UC_X86_REG_AX, (ax & 0xff00) | 0x24)
        elif ah == 0x4c:
            exits.append(ax & 255)
            uc.emu_stop()
        else:
            raise AssertionError(hex(ax))
    u.hook_add(UC_HOOK_INTR, interrupt)
    u.emu_start(0x10100, 0x20000, count=500000)
    assert len(exits) == 1, 'Program failed to terminate'
    return exits[0], bytes(files['KERNBOP']), payload, ''.join(output)

class CopyChecks(unittest.TestCase):
    def test_complete_copy_and_readback(self):
        status, dest, source, out = run()
        self.assertEqual(status, 0)
        self.assertEqual(dest, source)
        self.assertIn('copied and verified', out)
    def test_file_errors_stop_boot(self):
        for fault in ['open', 'create', 'seek', 'read', 'write', 'shortwrite', 'close', 'corrupt']:
            with self.subTest(fault=fault):
                self.assertEqual(run(fault)[0], 1)
    def test_wrong_size_preserves_existing_target(self):
        for size in [0, 62735, 62737, 62624, 62032, 63320, 65536]:
            with self.subTest(size=size):
                status, dest, _, _ = run(size=size)
                self.assertEqual(status, 1)
                self.assertEqual(dest, b'old kernel')

if __name__ == '__main__': unittest.main(verbosity=2)
