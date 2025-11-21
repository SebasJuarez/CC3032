from typing import Dict, Optional, List

T_VOLATILES = [f"$t{i}" for i in range(10)]  # $t0-$t9
S_SAVED = [f"$s{i}" for i in range(8)]       # $s0-$s7

class RegisterAllocationError(Exception):
    pass

class RegisterAllocator:
    """Asignador de registros muy simple: mapea símbolos a registros.
    - Temporales TAC (tN) usan $t* primero.
    - Variables (identificadores) intentan usar $s* para mayor vida.
    - Si se agotan, crea spill en stack asignando offset negativo relativo a $fp.
    """
    def __init__(self) -> None:
        self.map: Dict[str, str] = {}
        self.spills: Dict[str, int] = {}
        self._t_free: List[str] = T_VOLATILES.copy()
        self._s_free: List[str] = S_SAVED.copy()
        self._next_spill_offset = 0  # crecer hacia - (negativo)

    def is_temp(self, name: str) -> bool:
        return name.startswith("t")

    def get(self, symbol: str) -> str:
        """Devuelve el registro asignado o marcador de spill.
        Mantiene compatibilidad con generador actual que detecta 'SPILL('.
        """
        if symbol in self.map:
            return self.map[symbol]
        pool = self._t_free if self.is_temp(symbol) else self._s_free
        if pool:
            reg = pool.pop(0)
            self.map[symbol] = reg
            return reg
        offset = self._alloc_spill(symbol)
        return f"SPILL({offset})"

    def is_spilled(self, symbol: str) -> bool:
        loc = self.map.get(symbol)
        if loc is None:
            # Puede no haberse pedido aún; consultar spills dict
            return symbol in self.spills and symbol not in self.map
        return False  # si ya está mapeado a registro no es spill

    def location(self, symbol: str):
        """Si símbolo tiene registro devuelve (reg, None). Si está spill devuelve (None, offset)."""
        if symbol in self.map:
            reg = self.map[symbol]
            if reg.startswith('SPILL('):
                # no se guarda en map como SPILL normalmente, pero por compatibilidad
                try:
                    off = int(reg.split('(')[1].split(')')[0])
                except Exception:
                    off = None
                return None, off
            return reg, None
        if symbol in self.spills:
            return None, self.spills[symbol]
        return None, None

    def _alloc_spill(self, symbol: str) -> int:
        self._next_spill_offset += 4
        off = -self._next_spill_offset  # negativo respecto a $fp
        self.spills[symbol] = off
        return off

    def release(self, symbol: str) -> None:
        if symbol not in self.map:
            return
        reg = self.map.pop(symbol)
        if reg.startswith("$"):
            if reg in T_VOLATILES and reg not in self._t_free:
                self._t_free.insert(0, reg)
            elif reg in S_SAVED and reg not in self._s_free:
                self._s_free.insert(0, reg)
        # spills se mantienen (no reciclamos offsets para simplicidad)

    def frame_size(self) -> int:
        # espacio para spills (redondear a múltiplo de 8)
        sz = ((self._next_spill_offset + 7) // 8) * 8
        return sz

    def spill_offset(self, symbol: str) -> Optional[int]:
        return self.spills.get(symbol)
