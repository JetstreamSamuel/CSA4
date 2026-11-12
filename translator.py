import argparse
from pathlib import Path

from isa import OPS


OPCODES = {name: code for code, (name, _) in enumerate(OPS)}


def parse_register(text: str) -> int:
    if not text.startswith("r") or not text[1:].isdecimal():
        raise ValueError(f"ожидается регистр: {text!r}")

    number = int(text[1:])
    if not 0 <= number < 16:
        raise ValueError(f"регистр вне диапозона r0..r15: {text!r}")

    return number

def encode_line(line: str) -> bytes:
    text = line.partition(";")[0].strip()
    if not text:
        return b""

    parts = text.split(maxsplit=1)
    name = parts[0].lower()

    if name not in OPCODES:
        raise ValueError(f"неизвестная команда: {name}")

    operands = []
    if len(parts) == 2:
        operands = [item.strip() for item in parts[1].split(",")]
    code = OPCODES[name]
    _, form = OPS[code]
    if len(operands) != len(form):
        raise ValueError(f"{name}: ожидается операндов: {len(form)}")

    register = [0, 0]
    extension = b""

    for index, (kind, operand) in enumerate(zip(form, operands, strict=True)):
        if kind == "r":
            register[index] = parse_register(operand.lower())
        elif kind == "i":
            value = int(operand, 0)
            if not -(1 << 31) <= value < (1 << 32):
                raise ValueError(f"значение не помещается в слово: {operand}")
            extension = (value & 0xFFFFFFFF).to_bytes(4, "little")
        else:
            raise ValueError(f"неподдерживаемый тип операнда: {kind}")

    header_bytes = bytes((code, register[0], register[1], len(extension) // 4))
    return header_bytes + extension

def assemble(source: str) -> bytes:
    program = bytearray()

    for line_number, line in enumerate(source.splitlines(), start=1):
        try:
            encoded = encode_line(line)
        except ValueError as error:
            raise ValueError(f"строка {line_number}: {error}") from error

        program.extend(encoded)

    return bytes(program)

def main():
    parser = argparse.ArgumentParser(description="Собрать исходник в машинный код")
    parser.add_argument("source", type=Path, help="исходник .asm")
    parser.add_argument("output", type=Path, help="выход .bin")
    args = parser.parse_args()

    try:
        source = args.source.read_text(encoding="utf-8")
        program = assemble(source)
        args.output.write_bytes(program)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{args.source}: {error}\n")

if __name__ == "__main__":
    main()