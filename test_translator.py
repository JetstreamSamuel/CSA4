import unittest

from isa import header
from translator import encode_line

class TranslatorTest(unittest.TestCase):
    def test_halt(self):
        self.assertEqual(encode_line("halt"), bytes.fromhex("00 00 00 00"))

    def test_mov(self):
        self.assertEqual(encode_line("mov r2, r5"), bytes.fromhex("01 02 05 00"))

    def test_li(self):
        data = encode_line("li r3, 42")
        self.assertEqual(data, bytes.fromhex("02 03 00 01 2a 00 00 00"))

        word = int.from_bytes(data[4:], "little")
        self.assertEqual(header(word), ("li", (3,), 1))

    def test_negative_immediate(self):
        self.assertEqual(encode_line("li r0, -1")[4:], b"\xff" * 4)

    def test_invalid_operands(self):
        for line in ("mov r2", "halt r1", "li r16, 42"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                encode_line(line)
