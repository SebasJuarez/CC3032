from dataclasses import dataclass
from typing import Optional

@dataclass
class MIPSInstruction:
    """Representa una instrucción MIPS genérica o pseudo-instrucción."""
    opcode: str
    op1: Optional[str] = None
    op2: Optional[str] = None
    op3: Optional[str] = None
    comment: Optional[str] = None

    def to_text(self) -> str:
        parts = [self.opcode]
        ops = [o for o in (self.op1, self.op2, self.op3) if o is not None and o != ""]
        if ops:
            parts.append(", ".join(ops))
        line = "\t" + (" ".join(parts))
        if self.comment:
            line = f"{line:<40} # {self.comment}"
        return line

@dataclass
class MIPSLabel:
    name: str
    comment: Optional[str] = None

    def to_text(self) -> str:
        if self.comment:
            return f"{self.name}:\t# {self.comment}"
        return f"{self.name}:"

@dataclass
class MIPSDirective:
    name: str
    args: Optional[str] = None
    comment: Optional[str] = None

    def to_text(self) -> str:
        base = f"\t.{self.name}" + (f" {self.args}" if self.args else "")
        if self.comment:
            base = f"{base:<40} # {self.comment}"
        return base

class AssemblySection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.items = []  # mezcla de instrucciones, etiquetas y directivas

    def label(self, name: str, comment: Optional[str] = None) -> None:
        self.items.append(MIPSLabel(name, comment))

    def instr(self, opcode: str, op1: Optional[str] = None, op2: Optional[str] = None, op3: Optional[str] = None, comment: Optional[str] = None) -> None:
        self.items.append(MIPSInstruction(opcode, op1, op2, op3, comment))

    def directive(self, name: str, args: Optional[str] = None, comment: Optional[str] = None) -> None:
        self.items.append(MIPSDirective(name, args, comment))

    def extend(self, other: 'AssemblySection') -> None:
        self.items.extend(other.items)

    def to_text(self) -> str:
        lines = [f"\t.{self.name}"]
        for it in self.items:
            lines.append(it.to_text())
        return "\n".join(lines)
