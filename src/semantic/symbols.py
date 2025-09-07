from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from src.semantic.types import Type

@dataclass
class Symbol:
    name: str
    typ: Type
    is_const: bool = False

@dataclass
class FunctionSymbol(Symbol):
    params: List[Symbol] = field(default_factory=list)
    return_type: Type = field(default=None)

@dataclass
class FieldSymbol(Symbol):
    pass

@dataclass
class ClassSymbol(Symbol):
    # typ.tag == class name
    fields: Dict[str, FieldSymbol] = field(default_factory=dict)
    methods: Dict[str, FunctionSymbol] = field(default_factory=dict)
    base_class: Optional['ClassSymbol'] = None

    def resolve_member(self, name: str) -> Optional[Symbol]:
        """Busca campo o método con herencia."""
        if name in self.fields:
            return self.fields[name]
        if name in self.methods:
            return self.methods[name]
        if self.base_class:
            return self.base_class.resolve_member(name)
        return None

class Scope:
    def __init__(self, name: str, parent: Optional['Scope']=None) -> None:
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def define(self, sym: Symbol) -> bool:
        if sym.name in self.symbols:
            return False
        self.symbols[sym.name] = sym
        return True

    def resolve(self, name: str) -> Optional[Symbol]:
        s = self.symbols.get(name)
        if s is not None:
            return s
        if self.parent is not None:
            return self.parent.resolve(name)
        return None

class SymbolTable:
    def __init__(self) -> None:
        self.globals = Scope("global", None)
        self.current = self.globals
        self._stack: List[Scope] = [self.globals]
        # Registro de clases por nombre
        self.classes: Dict[str, ClassSymbol] = {}

    def push(self, name: str) -> Scope:
        scope = Scope(name, self.current)
        self.current = scope
        self._stack.append(scope)
        return scope

    def pop(self) -> Scope:
        if self.current.parent is None:
            return self.current
        popped = self._stack.pop()
        self.current = self._stack[-1]
        return popped

    # Helpers para clases
    def define_class(self, cls: ClassSymbol) -> bool:
        if cls.name in self.classes:
            return False
        self.classes[cls.name] = cls
        return True

    def get_class(self, name: str) -> Optional[ClassSymbol]:
        return self.classes.get(name)
