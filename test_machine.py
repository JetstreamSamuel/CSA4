import unittest

from machine import Machine
from translator import assemble

class MachineTest(unittest.TestCase):
    def test_first_program(self):
        cpu = Machine(assemble("li r3, 42\nmov r2, r3\nhalt"))

        self.assertEqual(cpu.step().op, "li")
        self.assertEqual((cpu.pc, cpu.regs[2], cpu.regs[3]), (8, 0, 42))

        self.assertEqual(cpu.step().op, "mov")
        self.assertEqual((cpu.pc, cpu.regs[2], cpu.regs[3]), (12, 42, 42))

        self.assertEqual(cpu.step().op, "halt")
        self.assertTrue(cpu.halted)

        with self.assertRaises(RuntimeError):
            cpu.step()

    def test_li_without_immediate(self):
        cpu = Machine(bytes.fromhex("02 03 00 01"))

        with self.assertRaisesRegex(ValueError, "неполное слово"):
            cpu.step()

        self.assertEqual(cpu.pc, 0)
        self.assertEqual(cpu.regs[3], 0)