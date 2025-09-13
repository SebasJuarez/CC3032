from __future__ import annotations
from typing import Optional, List, Tuple
from antlr4 import ParserRuleContext
from src.gen.CompiscriptVisitor import CompiscriptVisitor
from src.gen.CompiscriptParser import CompiscriptParser
from src.semantic.types import Type, Integer, Float, String, Boolean, Void
from src.semantic.symbols import (
    SymbolTable, Symbol, FunctionSymbol, FieldSymbol, ClassSymbol
)
from src.semantic.errors import SemanticErrorReport

def _pos(ctx: ParserRuleContext) -> Tuple[int, int]:
    tok = ctx.start
    return tok.line, tok.column

def _widen_numeric(a: Type, b: Type) -> Type:
    if a.tag == "float" or b.tag == "float":
        return Float
    return Integer

class SemanticAnalyzer(CompiscriptVisitor):
    def __init__(self, errors: SemanticErrorReport) -> None:
        self.errors = errors
        self.symtab = SymbolTable()
        self._inside_loop = 0
        self._inside_function: List[Type] = []
        self._current_class: Optional[ClassSymbol] = None

    # =============== Programa / Bloques ===============
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        for st in ctx.statement():
            self.visit(st)
        return None

    def visitBlock(self, ctx: CompiscriptParser.BlockContext):
        self.symtab.push("block")
        for st in ctx.statement():
            self.visit(st)
        self.symtab.pop()
        return None

    # =============== Declaraciones ===============
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        # En var/const, el tipo está dentro de typeAnnotation -> typeSpec
        decl_type = self._type_from(ctx.typeAnnotation().typeSpec()) if ctx.typeAnnotation() else None
        init = ctx.initializer().expression() if ctx.initializer() else None

        if decl_type is None and init is None:
            self.errors.add(*_pos(ctx), f"Variable '{name}' must have a type or initializer.")
            return None

        if decl_type is None and init is not None:
            decl_type = self.visit(init)

        # ¿Campo de clase?
        if self._current_class is not None:
            field_sym = FieldSymbol(name, decl_type or Void, is_const=False)
            if name in self._current_class.fields:
                self.errors.add(*_pos(ctx), f"Field '{name}' already defined in class '{self._current_class.name}'.")
            else:
                self._current_class.fields[name] = field_sym
            return None

        if not self.symtab.current.define(Symbol(name, decl_type, is_const=False)):
            self.errors.add(*_pos(ctx), f"Redeclaration of '{name}' in the same scope.")
            return None

        if init is not None:
            t_init = self.visit(init)
            if not self._type_compatible(decl_type, t_init):
                self.errors.add(*_pos(ctx), f"Type mismatch in initializer of '{name}': expected {decl_type}, got {t_init}.")
        return None

    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        decl_type = self._type_from(ctx.typeAnnotation().typeSpec()) if ctx.typeAnnotation() else None
        init = ctx.expression()
        if init is None:
            self.errors.add(*_pos(ctx), f"Constant '{name}' must be initialized.")
            return None
        t_init = self.visit(init)

        if decl_type and not self._type_compatible(decl_type, t_init):
            self.errors.add(*_pos(ctx), f"Type mismatch in constant '{name}': expected {decl_type}, got {t_init}.")
        if decl_type is None:
            decl_type = t_init

        if self._current_class is not None:
            field_sym = FieldSymbol(name, decl_type, is_const=True)
            if name in self._current_class.fields:
                self.errors.add(*_pos(ctx), f"Field '{name}' already defined in class '{self._current_class.name}'.")
            else:
                self._current_class.fields[name] = field_sym
            return None

        if not self.symtab.current.define(Symbol(name, decl_type, is_const=True)):
            self.errors.add(*_pos(ctx), f"Redeclaration of '{name}' in the same scope.")
        return None

    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        """
        Dos formas según gramática:
          1) Identifier '=' expression ';'
          2) expression '.' Identifier '=' expression ';'
        Heurística robusta: contar expressions().
            - 1 expr  -> asignación simple a variable (rhs)
            - 2 exprs -> base '.' prop = rhs
        """
        expr_count = len(ctx.expression())

        if expr_count == 1:
            # Asignación simple a variable
            name = ctx.Identifier().getText()
            sym = self.symtab.current.resolve(name)
            if sym is None:
                self.errors.add(*_pos(ctx), f"Undeclared variable '{name}'.")
                return None
            if getattr(sym, "is_const", False):
                self.errors.add(*_pos(ctx), f"Cannot assign to constant '{name}'.")
                return None
            rhs = self.visit(ctx.expression(0))
            if not self._type_compatible(sym.typ, rhs):
                self.errors.add(*_pos(ctx), f"Type mismatch in assignment to '{name}': expected {sym.typ}, got {rhs}.")
            return None

        # Asignación a propiedad base.prop = rhs
        base_t = self.visit(ctx.expression(0))
        prop = ctx.Identifier().getText()   # único Identifier en esta alternativa
        rhs_t = self.visit(ctx.expression(1))
        base_cls = self.symtab.get_class(base_t.tag) if base_t else None
        if base_cls:
            mem = base_cls.resolve_member(prop)
            if isinstance(mem, FieldSymbol):
                if getattr(mem, "is_const", False):
                    self.errors.add(*_pos(ctx), f"Cannot assign to const field '{prop}'.")
                elif not self._type_compatible(mem.typ, rhs_t):
                    self.errors.add(*_pos(ctx), f"Type mismatch for field '{prop}': expected {mem.typ}, got {rhs_t}.")
            else:
                self.errors.add(*_pos(ctx), f"Unknown field '{prop}' in class '{base_cls.name}'.")
        # Si no es clase conocida, lo dejamos permisivo.
        return None

    # =============== Control de flujo ===============
    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        cond_t = self.visit(ctx.expression())
        if not cond_t or not cond_t.is_boolean():
            self.errors.add(*_pos(ctx), "Condition in 'if' must be boolean.")
        self.visit(ctx.block(0))
        if ctx.block(1):
            self.visit(ctx.block(1))
        return None

    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        cond_t = self.visit(ctx.expression())
        if not cond_t or not cond_t.is_boolean():
            self.errors.add(*_pos(ctx), "Condition in 'while' must be boolean.")
        self._inside_loop += 1
        self.visit(ctx.block())
        self._inside_loop -= 1
        return None

    def visitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        self._inside_loop += 1
        self.visit(ctx.block())
        self._inside_loop -= 1
        cond_t = self.visit(ctx.expression())
        if not cond_t or not cond_t.is_boolean():
            self.errors.add(*_pos(ctx), "Condition in 'do-while' must be boolean.")
        return None

    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        self.symtab.push("for")
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())
        if ctx.expression(0):
            cond_t = self.visit(ctx.expression(0))
            if not cond_t or not cond_t.is_boolean():
                self.errors.add(*_pos(ctx), "Condition in 'for' must be boolean.")
        if ctx.expression(1):
            self.visit(ctx.expression(1))
        self._inside_loop += 1
        self.visit(ctx.block())
        self._inside_loop -= 1
        self.symtab.pop()
        return None

    def visitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        iter_t = self.visit(ctx.expression())
        elem_t = Void
        if isinstance(iter_t, Type) and iter_t.dims > 0:
            elem_t = Type(iter_t.tag, dims=iter_t.dims - 1)
        self.symtab.push("foreach")
        self.symtab.current.define(Symbol(ctx.Identifier().getText(), elem_t))
        self._inside_loop += 1
        self.visit(ctx.block())
        self._inside_loop -= 1
        self.symtab.pop()
        return None

    def visitBreakStatement(self, ctx: CompiscriptParser.BreakStatementContext):
        if self._inside_loop <= 0:
            self.errors.add(*_pos(ctx), "'break' used outside of a loop.")
        return None

    def visitContinueStatement(self, ctx: CompiscriptParser.ContinueStatementContext):
        if self._inside_loop <= 0:
            self.errors.add(*_pos(ctx), "'continue' used outside of a loop.")
        return None

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        if not self._inside_function:
            self.errors.add(*_pos(ctx), "'return' used outside of a function.")
            return None
        expected = self._inside_function[-1]
        if ctx.expression():
            got = self.visit(ctx.expression())
            if not self._type_compatible(expected, got):
                self.errors.add(*_pos(ctx), f"Return type mismatch: expected {expected}, got {got}.")
        else:
            if expected != Void:
                self.errors.add(*_pos(ctx), f"Return type mismatch: expected {expected}, got void.")
        return None

    # =============== Funciones y Clases ===============
    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        # Para funciones, tu gramática expone typeSpec() directamente
        ret_t = self._type_from(ctx.typeSpec()) if ctx.typeSpec() else Void
        params: List[Symbol] = []
        if ctx.parameters():
            for p in ctx.parameters().parameter():
                pname = p.Identifier().getText()
                ptype = self._type_from(p.typeSpec()) if p.typeSpec() else None
                if ptype is None:
                    self.errors.add(*_pos(p), f"Parameter '{pname}' must have a type.")
                    ptype = Void
                params.append(Symbol(pname, ptype))

        fn = FunctionSymbol(name=name, typ=ret_t, return_type=ret_t, params=params)

        if self._current_class is not None:
            if name in self._current_class.methods:
                self.errors.add(*_pos(ctx), f"Method '{name}' already declared in class '{self._current_class.name}'.")
                return None
            self._current_class.methods[name] = fn
        else:
            if not self.symtab.current.define(fn):
                self.errors.add(*_pos(ctx), f"Function '{name}' already declared in this scope.")
                return None

        # Scope de función
        self.symtab.push(f"fn:{name}")
        for ps in params:
            if not self.symtab.current.define(ps):
                self.errors.add(*_pos(ctx), f"Parameter '{ps.name}' redeclared.")
        self._inside_function.append(ret_t)
        self.visit(ctx.block())
        self._inside_function.pop()
        self.symtab.pop()
        return None

    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        cname = ctx.Identifier(0).getText()
        base_cls: Optional[ClassSymbol] = None
        if ctx.Identifier(1):  # herencia
            bname = ctx.Identifier(1).getText()
            base_cls = self.symtab.get_class(bname)
            if bname and base_cls is None:
                base_cls = ClassSymbol(name=bname, typ=Type(bname))
                self.symtab.define_class(base_cls)

        cls = ClassSymbol(name=cname, typ=Type(cname), base_class=base_cls)
        if not self.symtab.define_class(cls):
            self.errors.add(*_pos(ctx), f"Class '{cname}' already defined.")
            return None

        prev = self._current_class
        self._current_class = cls
        self.symtab.push(f"class:{cname}")

        for m in ctx.classMember():
            self.visit(m)

        self.symtab.pop()
        self._current_class = prev
        return None

    # =============== Statements simples ===============
    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        self.visit(ctx.expression())
        return None

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        self.visit(ctx.expression())
        return None

    # =============== Expresiones ===============
    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():
            return self.eval_lhs(ctx.leftHandSide())
        return self.visit(ctx.expression())

    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        sym = self.symtab.current.resolve(name)
        if sym is None:
            self.errors.add(*_pos(ctx), f"Undeclared identifier '{name}'.")
            return Void
        return sym.typ

    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        text = ctx.getText()
        if text == "true" or text == "false":
            return Boolean
        if text == "null":
            return Void
        if ctx.Literal():
            lit = ctx.Literal().getText()
            if len(lit) >= 2 and lit[0] == '"' and lit[-1] == '"':
                return String
            else:
                return Integer
        if ctx.arrayLiteral():
            exprs = ctx.arrayLiteral().expression()
            if not exprs:
                # [] → arreglo 1D de tipo desconocido (void)
                return Type(Void.tag, dims=1)

            elem_types = [self.visit(e) for e in exprs]

            # Caso A: elementos escalares
            if all(t.dims == 0 for t in elem_types):
                base = elem_types[0]
                if all(t.same_base(base) for t in elem_types):
                    return Type(base.tag, dims=1)
                if all(t.tag in ("integer", "float") for t in elem_types):
                    return Type(Float.tag, dims=1)
                return Type(Void.tag, dims=1)

            # Caso B: elementos son a su vez arreglos (soporta anidados)
            if all(t.dims >= 1 for t in elem_types):
                inner_dim = elem_types[0].dims
                # exigimos misma dimensionalidad interna
                if not all(t.dims == inner_dim for t in elem_types):
                    return Type(Void.tag, dims=1)
                # unificar tipo base
                base_tag = elem_types[0].tag
                if all(t.tag == base_tag for t in elem_types):
                    pass
                elif all(t.tag in ("integer", "float") for t in elem_types):
                    base_tag = "float"
                else:
                    return Type(Void.tag, dims=1)
                # el literal externo agrega una dimensión más
                return Type(base_tag, dims=inner_dim + 1)

            # Mezcla de escalares y arreglos ⇒ inválido
            return Type(Void.tag, dims=1)

        return Void


    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        left = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            right = self.visit(ctx.multiplicativeExpr(i))
            op = ctx.getChild(2 * i - 1).getText()
            if op == "+":
                if left.is_string() or right.is_string():
                    left = String
                else:
                    if not (left.is_numeric() and right.is_numeric()):
                        self.errors.add(*_pos(ctx), "Invalid operands for '+': expected numeric or string concatenation.")
                        return Void
                    left = _widen_numeric(left, right)
            else:
                if not (left.is_numeric() and right.is_numeric()):
                    self.errors.add(*_pos(ctx), "Invalid operands for '-': expected numeric.")
                    return Void
                left = _widen_numeric(left, right)
        return left

    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        left = self.visit(ctx.unaryExpr(0))
        for i in range(1, len(ctx.unaryExpr())):
            right = self.visit(ctx.unaryExpr(i))
            if not (left.is_numeric() and right.is_numeric()):
                self.errors.add(*_pos(ctx), "Invalid operands for '*', '/', '%': expected numeric.")
                return Void
            left = _widen_numeric(left, right)
        return left

    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        # Si no hay operador relacional, propaga el tipo del operando
        if len(ctx.additiveExpr()) == 1:
            return self.visit(ctx.additiveExpr(0))
        # Con operadores: ambos numéricos
        left = self.visit(ctx.additiveExpr(0))
        for i in range(1, len(ctx.additiveExpr())):
            right = self.visit(ctx.additiveExpr(i))
            if not (left.is_numeric() and right.is_numeric()):
                self.errors.add(*_pos(ctx), "Relational operators require numeric operands.")
            left = right
        return Boolean

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        # Si no hay operador de igualdad, propaga el tipo del operando
        if len(ctx.relationalExpr()) == 1:
            return self.visit(ctx.relationalExpr(0))
        # Con operadores: tipos compatibles
        left = self.visit(ctx.relationalExpr(0))
        for i in range(1, len(ctx.relationalExpr())):
            right = self.visit(ctx.relationalExpr(i))
            ok = (left.is_numeric() and right.is_numeric()) or left.same_base(right)
            if not ok:
                self.errors.add(*_pos(ctx), "Equality requires compatible types.")
            left = right
        return Boolean

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        n = len(ctx.equalityExpr())
        # si no hay '&&', solo propaga el tipo del único operando
        if n == 1:
            return self.visit(ctx.equalityExpr(0))
        # con '&&' sí exigimos booleanos
        ok = True
        for i in range(n):
            t = self.visit(ctx.equalityExpr(i))
            if not t.is_boolean():
                self.errors.add(*_pos(ctx), "Operands of '&&' must be boolean.")
                ok = False
        return Boolean if ok else Void

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        n = len(ctx.logicalAndExpr())
        # si no hay '||', solo propaga el tipo del único operando
        if n == 1:
            return self.visit(ctx.logicalAndExpr(0))
        # con '||' sí exigimos booleanos
        ok = True
        for i in range(n):
            t = self.visit(ctx.logicalAndExpr(i))
            if not t.is_boolean():
                self.errors.add(*_pos(ctx), "Operands of '||' must be boolean.")
                ok = False
        return Boolean if ok else Void

    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.getChildCount() == 2:
            op = ctx.getChild(0).getText()
            t = self.visit(ctx.unaryExpr())
            if op == "-" and not t.is_numeric():
                self.errors.add(*_pos(ctx), "Unary '-' expects numeric operand.")
                return Void
            if op == "!" and not t.is_boolean():
                self.errors.add(*_pos(ctx), "Unary '!' expects boolean operand.")
                return Void
            return t
        else:
            return self.visit(ctx.primaryExpr())

    def visitConditionalExpr(self, ctx: CompiscriptParser.ConditionalExprContext):
        _ = self.visit(ctx.logicalOrExpr())
        if ctx.getChildCount() > 1:
            t1 = self.visit(ctx.expression(0))
            t2 = self.visit(ctx.expression(1))
            if t1.same_base(t2):
                return t1
            if (t1.tag, t2.tag) in (("integer", "float"), ("float", "integer")):
                return Float
            if t1.is_string() or t2.is_string():
                return String
            return Void
        return _
    
    def visitTryCatchStatement(self, ctx: CompiscriptParser.TryCatchStatementContext):
        # try { ... }  -> el block ya maneja su propio scope
        self.visit(ctx.block(0))

        # catch (Identifier) { ... }
        # Creamos un scope para el catch y definimos la variable del parámetro.
        self.symtab.push("catch")
        name = ctx.Identifier().getText()
        # Tipo del error: usamos string para permitir "texto" + err en print/concat.
        self.symtab.current.define(Symbol(name, String))
        self.visit(ctx.block(1))
        self.symtab.pop()
        return None


    # =============== LHS chaining ===============
    def eval_lhs(self, ctx: CompiscriptParser.LeftHandSideContext) -> Type:
        """
        leftHandSide: primaryAtom (suffixOp)*;
        suffixOp: '(' arguments? ')' | '[' expression ']' | '.' Identifier ;
        """
        base_t, base_sym = self.eval_primary_atom(ctx.primaryAtom())

        for so in ctx.suffixOp():
            text = so.getText()
            # Llamada f(...), obj.m(...), (expr)(...)
            if text.startswith("("):
                arg_types = []
                if so.arguments():
                    for e in so.arguments().expression():
                        arg_types.append(self.visit(e))
                if isinstance(base_sym, FunctionSymbol):
                    self._check_call(so, base_sym, arg_types)
                    base_t = base_sym.return_type
                    base_sym = None
                else:
                    if isinstance(base_sym, FunctionSymbol):
                        self._check_call(so, base_sym, arg_types)
                        base_t = base_sym.return_type
                        base_sym = None
                    else:
                        base_t = Void

            # Indexación [...]
            elif text.startswith("["):
                idx_t = self.visit(so.expression())
                if not idx_t.is_numeric() or idx_t.tag != "integer":
                    self.errors.add(*_pos(so), "List index must be integer.")
                if not isinstance(base_t, Type) or base_t.dims == 0:
                    self.errors.add(*_pos(so), "Indexing requires an array value.")
                    base_t = Void
                else:
                    base_t = Type(base_t.tag, base_t.dims - 1)
                    base_sym = None

            # Acceso propiedad .Identifier
            else:
                member = so.Identifier().getText() if hasattr(so, "Identifier") and so.Identifier() else text[1:]
                base_cls = self.symtab.get_class(base_t.tag) if base_t else None
                if base_cls is None:
                    base_t = Void
                    base_sym = None
                else:
                    mem = base_cls.resolve_member(member)
                    if mem is None:
                        self.errors.add(*_pos(so), f"'{member}' is not a member of class '{base_cls.name}'.")
                        base_t = Void
                        base_sym = None
                    else:
                        if isinstance(mem, FieldSymbol):
                            base_t = mem.typ
                            base_sym = mem
                        elif isinstance(mem, FunctionSymbol):
                            base_t = mem.return_type
                            base_sym = mem
                        else:
                            base_t = Void
                            base_sym = None

        return base_t

    # =============== Helpers ===============
    def _type_from(self, type_spec_ctx) -> Type:
        """
        Convierte el nodo typeSpec de la gramática en un Type interno.
        Soporta primitivos: integer, float, string, boolean, void
        y arreglos con sufijos [] (p.ej., integer[], float[][]).
        Si el nombre no coincide con primitivo, se asume nombre de clase.
        """
        if type_spec_ctx is None:
            return Void

        text = type_spec_ctx.getText()  # p.ej. 'integer', 'integer[]', 'float[][]'
        dims = 0
        while text.endswith("[]"):
            dims += 1
            text = text[:-2]

        base = text.lower()
        if base in ("int", "integer"):
            tag = "integer"
        elif base in ("float",):
            tag = "float"
        elif base in ("string",):
            tag = "string"
        elif base in ("bool", "boolean"):
            tag = "boolean"
        elif base in ("void",):
            tag = "void"
        else:
            # Tratar como nombre de clase
            tag = base

        return Type(tag=tag, dims=dims)

    def _type_compatible(self, target: Type, value: Type) -> bool:
        # Igual base (ignorando mayúsculas/minúsculas para clases) y misma dimensionalidad
        if target.dims == value.dims and target.tag.lower() == value.tag.lower():
            return True
        # Promoción numérica int -> float (solo escalares)
        if target.dims == 0 and value.dims == 0 and target.tag == "float" and value.tag == "integer":
            return True
        return False


    def eval_primary_atom(self, pctx) -> Tuple[Type, Optional[Symbol]]:
        """
        Resuelve el tipo base de un primaryAtom:
        - Identifier → variable/campo/función/clase
        - this → tipo de clase actual
        - new Clase(...) → tipo Clase (si existe)
        """
        text = pctx.getText()

        # this
        if text == "this":
            if self._current_class is None:
                self.errors.add(*_pos(pctx), "'this' used outside of a class.")
                return (Void, None)
            return (Type(self._current_class.name), None)

        # Identificador simple en scopes
        sym = self.symtab.current.resolve(text)
        if sym is not None:
            if isinstance(sym, FunctionSymbol):
                return (sym.return_type, sym)
            return (sym.typ, sym)

        # Nombre de clase conocida
        cls = self.symtab.get_class(text)
        if cls is not None:
            return (Type(cls.name), None)

        # newClase(...)
        if text.startswith("new"):
            rest = text[3:].lstrip()
            cname = rest.split("(", 1)[0].strip()
            if cname:
                cls = self.symtab.get_class(cname)
                if cls is None:
                    cls = ClassSymbol(name=cname, typ=Type(cname))
                    self.symtab.define_class(cls)
                return (Type(cname), None)

        self.errors.add(*_pos(pctx), f"Undeclared identifier '{text}'.")
        return (Void, None)

    def _check_call(self, ctx, fn: FunctionSymbol, arg_types: List[Type]) -> None:
        if len(arg_types) != len(fn.params):
            self.errors.add(*_pos(ctx), f"Function '{fn.name}' expects {len(fn.params)} args, got {len(arg_types)}.")
            return
        for i, (a, p) in enumerate(zip(arg_types, fn.params)):
            if not self._type_compatible(p.typ, a):
                self.errors.add(*_pos(ctx), f"Argument {i+1} type mismatch: expected {p.typ}, got {a}.")
