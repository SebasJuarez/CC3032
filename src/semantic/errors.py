from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SemanticError:
    line: int
    column: int
    message: str

    def __str__(self) -> str:
        return f"(line {self.line}, col {self.column}) {self.message}"

class SemanticErrorReport:
    def __init__(self) -> None:
        self.errors: List[SemanticError] = []

    def add(self, line: int, column: int, message: str) -> None:
        self.errors.append(SemanticError(line, column, message))

    def has_errors(self) -> bool:
        return len(self.errors) > 0
