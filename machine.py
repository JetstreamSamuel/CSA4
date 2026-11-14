from isa import RAM_SIZE, MASK, Inst, header, signed


class Machine:
    def __init__(self, program: bytes):
        if len(program) > RAM_SIZE:
            raise ValueError("программа не помещается в памяти")
        
        self.memory = bytearray(RAM_SIZE)
        self.memory[:len(program)] = program
        self.program_size = len(program)

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

    def check_address(self, address: int, size: int) -> None:
        if address < 0 or address + size > len(self.memory):
            raise ValueError(f"адрес вне RAM: {address:#x}")
        if size == 4 and address % 4 != 0:
            raise ValueError(f"невыровненный адрес слова: {address:#x}")


    def read_word(self, address: int) -> int:
        self.check_address(address, 4)
        return int.from_bytes(self.memory[address : address + 4], "little")

    def write_word(self, address: int, value: int) -> None:
        self.check_address(address, 4)
        self.memory[address : address + 4] = value.to_bytes(4, "little")

    def fetch_word(self, address: int) -> int:
        if address + 4 > self.program_size:
            raise ValueError(f"неполное слово по адресу: {address:#x}")
        return self.read_word(address)

    def fetch(self) -> Inst:
        word = self.fetch_word(self.pc)
        op, regs, count = header(word)

        ext = tuple(
            self.fetch_word(self.pc + 4 * (i + 1))
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
        elif inst.op == "mul":
            dst, src = inst.regs

            prod = signed(self.regs[dst]) * signed(self.regs[src])
            res = prod & MASK

            self.regs[dst] = res
            self.z = res == 0
            self.n = bool(res & (1 << 31))
            self.v = prod != signed(res)
            self.c = False
        elif inst.op in ("ld.l", "ld.b"):
            dst, base = inst.regs
            address = self.regs[base]

            if inst.op == "ld.l":
                self.regs[dst] = self.read_word(address)
            else:
                self.check_address(address, 1)
                self.regs[dst] = self.memory[address]
        elif inst.op in ("st.l", "st.b"):
            base, src = inst.regs
            address = self.regs[base]
            value = self.regs[src]
            if inst.op == "st.l":
                self.write_word(address, value)
            else:
                self.check_address(address, 1)
                self.memory[address] = value & 0xFF
        else:
            raise ValueError(f"исполнение команды {inst.op!r} не реализовано")

        self.pc = inst.end
        return inst