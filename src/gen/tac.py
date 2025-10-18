from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Quad:
    op: str
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    res: Optional[str] = None

    def __str__(self) -> str:
        """
        Imprime el cuádruplo en formato fijo de 4 campos (op, arg1, arg2, res)
        dejando en blanco los campos vacíos, sin usar '_'.
        """
        def f(x: Optional[str]) -> str:
            return "" if (x is None or x == "_") else str(x)
        return f"({self.op}, {f(self.arg1)}, {f(self.arg2)}, {f(self.res)})"

class TAC:
    def __init__(self) -> None:
        self.quads: List[Quad] = []

    def emit(self, op: str, arg1: Optional[str] = None, arg2: Optional[str] = None, res: Optional[str] = None) -> None:
        """
        Agrega un cuádruplo a la lista de instrucciones TAC.
        Convierte todos los argumentos a string si existen.
        """
        a1 = None if arg1 is None else str(arg1)
        a2 = None if arg2 is None else str(arg2)
        r = None if res is None else str(res)
        self.quads.append(Quad(op, a1, a2, r))

    def extend(self, other: 'TAC') -> None:
        """Concatena otra secuencia TAC."""
        self.quads.extend(other.quads)

    def __str__(self) -> str:
        """Devuelve la representación textual de todos los cuádruplos."""
        return "\n".join(str(q) for q in self.quads)
