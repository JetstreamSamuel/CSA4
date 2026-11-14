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

    def test_unsigned_division_module(self):
        cases = [
            (123, 10, 12, 3),
            (3, 10, 0, 3),
            (0xFFFFFFFF, 2, 0x7FFFFFFF, 1),
        ]

        for value, divisor, quotient, remainder in cases:
            with self.subTest(value=value, divisor=divisor):
                source = (
                    f"li r2, {value}\n"
                    "mov r4, r2\n"
                    f"li r3, {divisor}\n"
                    "divu r2, r3\n"
                    "modu r4, r3\n"
                    "halt\n"
                )
                cpu = Machine(assemble(source))

                while not cpu.halted:
                    cpu.step()

                self.assertEqual(cpu.regs[2], quotient)
                self.assertEqual(cpu.regs[4], remainder)
                self.assertEqual(cpu.regs[3], divisor)

    def test_zero_divisor(self):
        for op in ("divu", "modu"):
            with self.subTest(op=op):
                cpu = Machine(assemble(f"li r2, 17\n{op} r2, r3\nhalt"))
                cpu.step()

                with self.assertRaisesRegex(ValueError, "деление на ноль"):
                    cpu.step()

                self.assertEqual(cpu.regs[2], 17)

    def test_addi(self):
        cases = [
            (7, 5, 12),
            (7, -1, 6),
            (0, -1, 0xFFFFFFFF),
            (0xFFFFFFFF, 1, 0),
        ]

        for initial, immediate, expected in cases:
            with self.subTest(initial=initial, immediate=immediate):
                source = (
                    f"li r2, {initial}\n"
                    f"addi r2, {immediate}\n"
                    "halt\n"
                )
                cpu = Machine(assemble(source))

                cpu.step()
                cpu.step()

                self.assertEqual(cpu.regs[2], expected)
                self.assertEqual(cpu.pc, 16)
                self.assertEqual(cpu.step().op, "halt")

    def test_cmp_sets_flags_without_changing_registers(self):
        cpu = Machine(assemble("li r2, 3\nli r3, 5\ncmp r2, r3\nhalt"))

        cpu.step()
        cpu.step()
        cpu.step()

        self.assertEqual((cpu.z, cpu.n, cpu.v), (False, True, False))
        self.assertEqual((cpu.regs[2], cpu.regs[3]), (3, 5))

    def test_cmpi_overflow_then_equality(self):
        cpu = Machine(assemble(
            "li r2, 0x7FFFFFFF\n"
            "cmpi r2, -1\n"
            "cmpi r2, 0x7FFFFFFF\n"
            "halt\n"
        ))

        cpu.step()
        cpu.step()
        self.assertEqual((cpu.z, cpu.n, cpu.v), (False, True, True))

        cpu.step()
        self.assertEqual((cpu.z, cpu.n, cpu.v), (True, False, False))
        self.assertEqual(cpu.regs[2], 0x7FFFFFFF)

    def test_add_with_carry_across_two_words(self):
        source = (
            "li r2, 0xFFFFFFFF\n"
            "li r3, 0\n"
            "li r4, 1\n"
            "li r5, 0\n"
            "addf r2, r4\n"
            "addc r3, r5\n"
            "halt\n"
        )
        cpu = Machine(assemble(source))

        for _ in range(4):
            cpu.step()

        cpu.step()
        self.assertEqual(cpu.regs[2], 0)
        self.assertEqual((cpu.c, cpu.v), (True, False))

        cpu.step()
        self.assertEqual(cpu.regs[3], 1)
        self.assertFalse(cpu.c)

    def test_addf_signed_overflow_without_carry(self):
        cpu = Machine(assemble("li r2, 0x7FFFFFFF\nli r3, 1\naddf r2, r3\nhalt"))

        while not cpu.halted:
            cpu.step()

        self.assertEqual(cpu.regs[2], 0x80000000)
        self.assertEqual((cpu.z, cpu.n, cpu.v, cpu.c), (False, True, True, False))

    def test_signed_multiplication(self):
        cases = [
            (-3, 7, 0xFFFFFFEB, False),
            (-1073741824, 2, 0x80000000, False),
            (1073741824, 2, 0x80000000, True),
            (65536, 65536, 0, True),
        ]

        for left, right, expected, overflow in cases:
            with self.subTest(left=left, right=right):
                source = (
                    f"li r2, {left}\n"
                    f"li r3, {right}\n"
                    "mul r2, r3\n"
                    "halt\n"
                )
                cpu = Machine(assemble(source))
                cpu.c = True

                while not cpu.halted:
                    cpu.step()

                self.assertEqual(cpu.regs[2], expected)
                self.assertEqual(cpu.regs[3], right & 0xFFFFFFFF)
                self.assertEqual(cpu.v, overflow)
                self.assertEqual(cpu.z, expected == 0)
                self.assertEqual(cpu.n, bool(expected & 0x80000000))
                self.assertFalse(cpu.c)

    def test_word_and_byte_memory_access(self):
        source = (
            "li r3, 0x100\n"
            "li r2, 0x12345678\n"
            "st.l [r3], r2\n"
            "ld.l r4, [r3]\n"
            "li r5, 0x101\n"
            "li r6, 0xABCD\n"
            "st.b [r5], r6\n"
            "ld.b r7, [r5]\n"
            "halt\n"
        )
        cpu = Machine(assemble(source))

        while not cpu.halted:
            cpu.step()

        self.assertEqual(cpu.regs[3], 0x100)
        self.assertEqual(cpu.regs[4], 0x12345678)
        self.assertEqual(cpu.regs[7], 0xCD)
        self.assertEqual(cpu.memory[0x100:0x104], bytes.fromhex("78 cd 34 12"))