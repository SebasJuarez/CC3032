from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Quad:
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    res: Optional[str] = None

    def __str__(self) -> str:
        # Formato cuadruplo fijo para facilitar backends: (op, a1, a2, res)
        def fmt(x: Optional[str]) -> str:
            return x if isinstance(x, str) and x != "" else "_"
        return f"({self.op}, {fmt(self.arg1)}, {fmt(self.arg2)}, {fmt(self.res)})"

class TAC:
    def __init__(self) -> None:
        self.quads: List[Quad] = []

    def emit(self, op: str, arg1: Optional[str] = None, arg2: Optional[str] = None, res: Optional[str] = None) -> None:
        # Normaliza a strings
        a1 = None if arg1 is None else str(arg1)
        a2 = None if arg2 is None else str(arg2)
        r = None if res is None else str(res)
        self.quads.append(Quad(op, a1, a2, r))

    def extend(self, other: 'TAC') -> None:
        self.quads.extend(other.quads)

    def __str__(self) -> str:
        return "\n".join(str(q) for q in self.quads)
