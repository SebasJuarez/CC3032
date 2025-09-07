from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List

# Basic type system for Compiscript
class TypeTag:
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    VOID = "void"

@dataclass(frozen=True)
class Type:
    tag: str
    # For arrays like integer[] or integer[][]
    dims: int = 0
    # For function types (if you want to extend): args: List[Type], ret: Type

    def is_numeric(self) -> bool:
        return self.tag in (TypeTag.INTEGER, TypeTag.FLOAT) and self.dims == 0

    def is_boolean(self) -> bool:
        return self.tag == TypeTag.BOOLEAN and self.dims == 0

    def is_string(self) -> bool:
        return self.tag == TypeTag.STRING and self.dims == 0

    def same_base(self, other: 'Type') -> bool:
        return self.tag == other.tag and self.dims == other.dims

    def __str__(self) -> str:
        return f"{self.tag}{'[]'*self.dims}"

# Helper constructors
Integer = Type(TypeTag.INTEGER)
Float   = Type(TypeTag.FLOAT)
String  = Type(TypeTag.STRING)
Boolean = Type(TypeTag.BOOLEAN)
Void    = Type(TypeTag.VOID)
