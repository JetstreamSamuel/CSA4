from isa import MASK, Ints, header, signed


class Machine:
    def __init__(self, program: bytes):
        self.memory = bytearray(program)
        self.regs = [0] * 16

        self.pc = 0

        self.halted = False

        self.n = False
        self.z = False
        self.v = False

    def compare(self, left: int, right: int) -> None:
        diff = signed(left) - signed(right)
        res = diff & MASK

        self.z = res == 0
        self.n = bool(res & (1 << 31))
        self.v = diff != signed(res)


    def read_word(self, address: int) -> int:
        if address < 0 or address + 4 > len(self.memory):
            raise ValueError(f"неполное слово по адресу {address:#x}")

        return int.from_bytes(self.memory[address : address + 4], "little")

    def fetch(self) -> Ints:
        word = self.read_word(self.pc)
        op, regs, count = header(word)

        ext = tuple(
            self.read_word(self.pc + 4 * (i + 1))
            for i in range(count)
        )

        return Ints(pc=self.pc, op=op, regs=regs, ext=ext)

    def step(self) -> Ints:
        if self.halted:
            raise RuntimeError("Процессор уже остановлен")

        ints = self.fetch()

        if ints.op == "li":
            dst, = ints.regs
            self.regs[dst] = ints.ext[0]
        elif ints.op == "mov":
            dst, src = ints.regs
            self.regs[dst] = self.regs[src]
        elif ints.op == "halt":
            self.halted = True
        elif ints.op == "add":
            dst, src = ints.regs
            self.regs[dst] = (self.regs[dst] + self.regs[src]) & MASK
        elif ints.op == "sub":
            dst, src = ints.regs
            self.regs[dst] = (self.regs[dst] - self.regs[src]) & MASK
        elif ints.op == "and":
            dst, src = ints.regs
            self.regs[dst] = self.regs[dst] & self.regs[src]
        elif ints.op == "or":
            dst, src = ints.regs
            self.regs[dst] = self.regs[dst] | self.regs[src]
        elif ints.op == "min":
            dst, src = ints.regs
            if signed(self.regs[src]) < signed(self.regs[dst]):
                self.regs[dst] = self.regs[src]
        elif ints.op == "max":
            dst, src = ints.regs
            if signed(self.regs[src]) > signed(self.regs[dst]):
                self.regs[dst] = self.regs[src]
        elif ints.op in ("divu", "modu"):
            dst, src = ints.regs
            dividend = self.regs[dst]
            divisor = self.regs[src]

            if divisor == 0:
                raise ValueError(f"{ints.op}: деление на ноль")
            if ints.op == "divu":
                self.regs[dst] = dividend // divisor
            else:
                self.regs[dst] = dividend % divisor
        elif ints.op == "addi":
            dst, = ints.regs
            self.regs[dst] = (self.regs[dst] + ints.ext[0]) & MASK
        elif ints.op == "cmp":
            left, right = ints.regs
            self.compare(self.regs[left], self.regs[right])
        elif ints.op == "cmpi":
            left, ints.regs
            self.compare(self.regs[left], ints.ext[0])


        else:
            raise ValueError(f"исполнение команды {ints.op!r} не реализовано")

        self.pc = ints.end
        return ints