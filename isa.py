from dataclasses import dataclass

MASK = 0xFFFFFFFF

OPS = (
    ("halt", ""),
    ("mov", "rr"),
    ("li", "ri"),
    ("add", "rr"),
    ("sub", "rr"),
    ("and", "rr"),
    ("or", "rr"),
    ("min", "rr"),
    ("max", "rr"),
    ("divu", "rr"),
    ("modu", "rr"),
    ("addi", "ri")
)

def signed(word: int) -> int:
    word &= MASK
    if word >= (1 << 31):
        return word - (1 << 32)
    return word


@dataclass(frozen=True)
class Ints:
    pc: int
    op: str
    regs: tuple[int, ...]
    ext: tuple[int, ...]

    @property
    def end(self) -> int:
        return self.pc + 4 * (1 + len(self.ext))


def header(word: int) -> tuple[str, tuple[int, ...], int]:
    code, a, b, count = word.to_bytes(4, "little")

    if code >= len(OPS):
        raise ValueError(f"illegal opcode {code}")

    name, form = OPS[code]
    register_count = form.count("r")

    if count != form.count("i"):
        raise ValueError("invalid extension count")


    if a >= 16 or b >= 16:
        raise ValueError("invalid register number")

    if (register_count < 2 and b != 0) or (register_count == 0 and a != 0):
        raise ValueError("unused register field must be zero")

    return name, (a, b)[:register_count], count