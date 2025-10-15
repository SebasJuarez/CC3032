from typing import List

class TempManager:
    def __init__(self) -> None:
        self._next = 0
        self._free: List[int] = []

    def new_temp(self) -> str:
        if self._free:
            idx = self._free.pop()
        else:
            idx = self._next
            self._next += 1
        return f"t{idx}"

    def free_temp(self, name: str) -> None:
        if name.startswith("t"):
            try:
                idx = int(name[1:])
            except ValueError:
                return
            self._free.append(idx)


_global_temp_manager = TempManager()

def new_temp() -> str:
    return _global_temp_manager.new_temp()

def free_temp(t: str) -> None:
    _global_temp_manager.free_temp(t)
