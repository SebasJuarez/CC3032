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

def _pos(ctx: ParserRuleContext) -> Tuple[int,int]:
    tok = ctx.start
    return tok.line, tok.column

def _widen_numeric(a: Type, b: Type) -> Type:
    if a.tag == 'float' or b.tag == 'float':
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
        decl_type = self._type_from(ctx.typeSpec()) if ctx.typeAnnotation() else None
        init = ctx.initializer().expression() if ctx.initializer() else None

        if decl_type is None and init is None:
            self.errors.add(*_pos(ctx), f"Variable '{name}' must have a type or initializer.")
            return None

        if decl_type is None and init is not None:
            decl_type = self.visit(init)

        # ¿Campo de clase?
        if self._current_class is not None:
            # Campos dentro del class body
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
        decl_type = self._type_from(ctx.type()) if ctx.typeAnnotation() else None
        init = ctx.expression()
        if init is None:
            self.errors.add(*_pos(ctx), f"Constant '{name}' must be initialized.")
            return None
        t_init = self.visit(init)

        if decl_type and not self._type_compatible(decl_type, t_init):
            self.errors.add(*_pos(ctx), f"Type mismatch in constant '{name}': expected {decl_type}, got {t_init}.")
        if decl_type is None:
            decl_type = t_init

        # ¿Constante de clase?
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
        # Identifier '=' expression ';'
        if ctx.Identifier():
            name = ctx.Identifier(0).getText()
            sym = self.symtab.current.resolve(name)
            if sym is None:
                self.errors.add(*_pos(ctx), f"Undeclared variable '{name}'.")
                return None
            if getattr(sym, 'is_const', False):
                self.errors.add(*_pos(ctx), f"Cannot assign to constant '{name}'.")
                return None
            rhs = self.visit(ctx.expression(0))
            if not self._type_compatible(sym.typ, rhs):
                self.errors.add(*_pos(ctx), f"Type mismatch in assignment to '{name}': expected {sym.typ}, got {rhs}.")
            return None
        # expression '.' Identifier '=' expression ';' (propiedad)
        base_t = self.visit(ctx.expression(0))
        prop = ctx.Identifier(0).getText()
        rhs_t = self.visit(ctx.expression(1))
        # Si base es clase conocida, valida el tipo del campo
        base_cls = self.symtab.get_class(base_t.tag) if base_t else None
        if base_cls:
            mem = base_cls.resolve_member(prop)
            if isinstance(mem, FieldSymbol):
                if getattr(mem, 'is_const', False):
                    self.errors.add(*_pos(ctx), f"Cannot assign to const field '{prop}'.")
                elif not self._type_compatible(mem.typ, rhs_t):
                    self.errors.add(*_pos(ctx), f"Type mismatch for field '{prop}': expected {mem.typ}, got {rhs_t}.")
        # Si no, lo dejamos permisivo por ahora.
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

        # ¿Método de clase o función libre?
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
                # Si base no definida aún, la registramos como "forward" vacía
                base_cls = ClassSymbol(name=bname, typ=Type(bname))
                self.symtab.define_class(base_cls)

        cls = ClassSymbol(name=cname, typ=Type(cname), base_class=base_cls)
        if not self.symtab.define_class(cls):
            self.errors.add(*_pos(ctx), f"Class '{cname}' already defined.")
            return None

        # Entrar a contexto de clase
        prev = self._current_class
        self._current_class = cls
        self.symtab.push(f"class:{cname}")

        # Procesar miembros: la gramática usa functionDeclaration | variableDeclaration | constantDeclaration
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

    # =============== LHS y Expresiones ===============
    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():
            return self.eval_lhs(ctx.leftHandSide())
        # '(' expression ')'
        return self.visit(ctx.expression())

    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        # Este no se llama si usamos eval_lhs en bloque, pero lo dejamos por compat
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
                return Type(Void.tag, dims=1)
            elem_types = [self.visit(e) for e in exprs]
            base = elem_types[0]
            if all(t.same_base(base) and t.dims == 0 for t in elem_types):
                return Type(base.tag, dims=1)
            if all((t.tag in ('integer','float') and t.dims==0) for t in elem_types):
                return Type(Float.tag, dims=1)
            return Type(Void.tag, dims=1)
        return Void

    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        left = self.visit(ctx.multiplicativeExpr(0))
        for i in range(1, len(ctx.multiplicativeExpr())):
            right = self.visit(ctx.multiplicativeExpr(i))
            op = ctx.getChild(2*i-1).getText()
            if op == '+':
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
        for i in range(len(ctx.additiveExpr())):
            self.visit(ctx.additiveExpr(i))
        return Boolean

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        for i in range(len(ctx.relationalExpr())):
            self.visit(ctx.relationalExpr(i))
        return Boolean

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        for i in range(len(ctx.equalityExpr())):
            t = self.visit(ctx.equalityExpr(i))
            if not t.is_boolean():
                self.errors.add(*_pos(ctx), "Operands of '&&' must be boolean.")
                return Void
        return Boolean

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        for i in range(len(ctx.logicalAndExpr())):
            t = self.visit(ctx.logicalAndExpr(i))
            if not t.is_boolean():
                self.errors.add(*_pos(ctx), "Operands of '||' must be boolean.")
                return Void
        return Boolean

    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.getChildCount() == 2:
            op = ctx.getChild(0).getText()
            t = self.visit(ctx.unaryExpr())
            if op == '-' and not t.is_numeric():
                self.errors.add(*_pos(ctx), "Unary '-' expects numeric operand.")
                return Void
            if op == '!' and not t.is_boolean():
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
            if (t1.tag, t2.tag) in (('integer','float'), ('float','integer')):
                return Float
            if t1.is_string() or t2.is_string():
                return String
            return Void
        return _

    # =============== LHS chaining ===============
    def eval_lhs(self, ctx: CompiscriptParser.LeftHandSideContext) -> Type:
        """
        leftHandSide: primaryAtom (suffixOp)*;
        suffixOp: '(' arguments? ')' | '[' expression ']' | '.' Identifier ;
        """
        # 1) Tipo base por primaryAtom
        base_t, base_sym = self.eval_primary_atom(ctx.primaryAtom())

        # 2) Caminar sufijos en orden
        for so in ctx.suffixOp():
            text = so.getText()
            if text.startswith('('):  # CallExpr
                arg_types = []
                if so.arguments():
                    for e in so.arguments().expression():
                        arg_types.append(self.visit(e))
                # Llamada a función libre
                if isinstance(base_sym, FunctionSymbol):
                    self._check_call(so, base_sym, arg_types)
                    base_t = base_sym.return_type
                    base_sym = None
                # Llamada a método (cuando base_t es clase y base_sym no es función)
                else:
                    # Si el "base" era un miembro método resuelto previamente:
                    if isinstance(base_sym, FunctionSymbol):
                        self._check_call(so, base_sym, arg_types)
                        base_t = base_sym.return_type
                        base_sym = None
                    else:
                        # Permisivo: no sabemos la firma → deja Void
                        base_t = Void
