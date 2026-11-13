from isa import MASK, Inst, header, signed


class Machine:
    def __init__(self, program: bytes):
        self.memory = bytearray(program)
        self.regs = [0] * 16

        self.pc = 0

        self.halted = False

        self.n = False
        self.z = False
        self.v = False
        self.c = False

    def compare(self, left: int, right: int) -> None:
        diff = signed(left) - signed(right)
        res = diff & MASK

        self.z = res == 0
        self.n = bool(res & (1 << 31))
        self.v = diff != signed(res)

    def add_with_flags(self, left: int, right: int, carry_in: int) -> int:
        total = left + right + carry_in
        result = total & MASK

        self.z = result == 0
        self.n = bool(result & (1 << 31))
        self.c = total > MASK

        signed_total = signed(left) + signed(right) + carry_in
        self.v = signed_total != signed(result)

        return result


    def read_word(self, address: int) -> int:
        if address < 0 or address + 4 > len(self.memory):
            raise ValueError(f"неполное слово по адресу {address:#x}")

        return int.from_bytes(self.memory[address : address + 4], "little")

    def fetch(self) -> Inst:
        word = self.read_word(self.pc)
        op, regs, count = header(word)

        ext = tuple(
            self.read_word(self.pc + 4 * (i + 1))
            for i in range(count)
        )

        return Inst(pc=self.pc, op=op, regs=regs, ext=ext)

    def step(self) -> Inst:
        if self.halted:
            raise RuntimeError("Процессор уже остановлен")

        inst = self.fetch()

        if inst.op == "li":
            dst, = inst.regs
            self.regs[dst] = inst.ext[0]
        elif inst.op == "mov":
            dst, src = inst.regs
            self.regs[dst] = self.regs[src]
        elif inst.op == "halt":
            self.halted = True
        elif inst.op == "add":
            dst, src = inst.regs
            self.regs[dst] = (self.regs[dst] + self.regs[src]) & MASK
        elif inst.op == "sub":
            dst, src = inst.regs
            self.regs[dst] = (self.regs[dst] - self.regs[src]) & MASK
        elif inst.op == "and":
            dst, src = inst.regs
            self.regs[dst] = self.regs[dst] & self.regs[src]
        elif inst.op == "or":
            dst, src = inst.regs
            self.regs[dst] = self.regs[dst] | self.regs[src]
        elif inst.op == "min":
            dst, src = inst.regs
            if signed(self.regs[src]) < signed(self.regs[dst]):
                self.regs[dst] = self.regs[src]
        elif inst.op == "max":
            dst, src = inst.regs
            if signed(self.regs[src]) > signed(self.regs[dst]):
                self.regs[dst] = self.regs[src]
        elif inst.op in ("divu", "modu"):
            dst, src = inst.regs
            dividend = self.regs[dst]
            divisor = self.regs[src]

            if divisor == 0:
                raise ValueError(f"{inst.op}: деление на ноль")
            if inst.op == "divu":
                self.regs[dst] = dividend // divisor
            else:
                self.regs[dst] = dividend % divisor
        elif inst.op == "addi":
            dst, = inst.regs
            self.regs[dst] = (self.regs[dst] + inst.ext[0]) & MASK
        elif inst.op == "cmp":
            left, right = inst.regs
            self.compare(self.regs[left], self.regs[right])
        elif inst.op == "cmpi":
            left, = inst.regs
            self.compare(self.regs[left], inst.ext[0])
        elif inst.op in ("addf", "addc"):
            dst, src = inst.regs
            carry_in = int(self.c) if inst.op == "addc" else 0
            self.regs[dst] = self.add_with_flags(self.regs[dst], self.regs[src], carry_in)
        else:
            raise ValueError(f"исполнение команды {inst.op!r} не реализовано")

        self.pc = inst.end
        return inst