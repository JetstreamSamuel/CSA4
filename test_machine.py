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

    def test_register_arithmetic(self):
        cases = [
            ("add", 10, 4, 14),
            ("sub", 10, 4, 6),
            ("add", 0xFFFFFFFF, 1, 0),
            ("sub", 0, 1, 0xFFFFFFFF)
        ]

        for op, left, right, expected in cases:
            with self.subTest(op=op, left=left, right=right):
                source = f"li r2, {left}\nli r3, {right}\n{op} r2, r3\nhalt"
                cpu = Machine(assemble(source))

                while not cpu.halted:
                    cpu.step()

                self.assertEqual(cpu.regs[2], expected)
                self.assertEqual(cpu.regs[3], right)

    def test_bit_operations(self):
        source = (
            "li r2, 0x123456AB\n"
            "li r3, 0xFF\n"
            "and r2, r3\n"
            "li r3, 0x80000001\n"
            "or r2, r3\n"
            "halt\n"
        )

        cpu = Machine(assemble(source))

        cpu.step()
        cpu.step()
        cpu.step()
        self.assertEqual(cpu.regs[2], 0xAB)
        self.assertEqual(cpu.regs[3], 0xFF)

        cpu.step()
        cpu.step()
        self.assertEqual(cpu.regs[2], 0x800000AB)
        self.assertEqual(cpu.regs[3], 0x80000001)

        cpu.step()
        self.assertTrue(cpu.halted)

    def test_signed_min_max(self):
        cases = [
            ("min", 5, -1, 0xFFFFFFFF),
            ("max", -5, 5, 5),
            ("min", -7, -3, 0xFFFFFFF9),
            ("max", -2147483648, 2147483647, 0x7FFFFFFF)
        ]

        for op, left, right, expected in cases:
            with self.subTest(op=op, left=left, right=right):
                source = (
                    f"li r2, {left}\n"
                    f"li r3, {right}\n"
                    f"{op} r2, r3\n"
                    "halt\n"
                )

                cpu = Machine(assemble(source))

                while not cpu.halted:
                    cpu.step()

                self.assertEqual(cpu.regs[2], expected)
                self.assertEqual(cpu.regs[3], right & 0xFFFFFFFF)