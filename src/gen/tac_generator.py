from __future__ import annotations
from typing import Optional
from src.gen.CompiscriptVisitor import CompiscriptVisitor
from src.gen.CompiscriptParser import CompiscriptParser

# Se intenta importar TAC desde la ruta principal (src/gen/tac.py);
# si no existe, se crea una versión mínima para evitar errores.
try:
    from src.gen.tac import TAC
except Exception:
    try:
        from tac import TAC
    except Exception:
        from dataclasses import dataclass
        from typing import Optional as _Opt
        @dataclass
        class Quad:
            op: str
            arg1: _Opt[str] = None
            arg2: _Opt[str] = None
            res: _Opt[str] = None
            def __str__(self):
                def fmt(x):
                    return x if isinstance(x, str) and x != "" else "_"
                return f"({self.op}, {fmt(self.arg1)}, {fmt(self.arg2)}, {fmt(self.res)})"
        class TAC:
            def __init__(self): self.quads = []
            def emit(self, op: str, arg1: _Opt[str] = None, arg2: _Opt[str] = None, res: _Opt[str] = None):
                self.quads.append(Quad(op, None if arg1 is None else str(arg1),
                                       None if arg2 is None else str(arg2),
                                       None if res is None else str(res)))
            def extend(self, other: 'TAC'): self.quads.extend(other.quads)
            def __str__(self): return "\n".join(str(q) for q in self.quads)

# Carga el gestor de temporales (src/codegen/temp_manager.py).
# Si no está disponible, crea un contador simple local.
try:
    from src.codegen.temp_manager import new_temp, free_temp
except Exception:
    from itertools import count
    _temp_counter = count(1)
    def new_temp():
        return f"t{next(_temp_counter)}"
    def free_temp(_):
        pass


class TACGenerator(CompiscriptVisitor):
    """
    Genera código intermedio TAC a partir del árbol de sintaxis de Compiscript.
    Usa el visitor de ANTLR y emite cuádruplos en formato (op, arg1, arg2, res).
    """

    def __init__(self, analyzer: Optional[object] = None) -> None:
        self.tac = TAC()                           # Contenedor de cuádruplos generados
        self.analyzer = analyzer                   # Referencia al analizador semántico
        self.symtab = getattr(analyzer, 'symtab', None) if analyzer else None
        from itertools import count
        self._label_counter = count(0)             # Contador de etiquetas únicas

    def _new_label(self, prefix: str = 'L') -> str:
        """Crea etiquetas únicas para estructuras de control."""
        return f"{prefix}{next(self._label_counter)}"

    def _resolve_var(self, name: str):
        """Busca una variable en el scope actual de la tabla de símbolos."""
        if self.symtab is None:
            return None
        return self.symtab.current.resolve(name)

    def _is_ref_type(self, typ) -> bool:
        """Determina si un tipo requiere manejo de referencias (strings, arrays, clases)."""
        try:
            from src.semantic.types import String, Type
            if typ is None:
                return False
            if isinstance(typ, Type):
                if typ.is_string() or getattr(typ, 'dims', 0) > 0:
                    return True
                if self.symtab and self.symtab.get_class(typ.tag):
                    return True
            return False
        except Exception:
            return False

    def generate(self, tree) -> TAC:
        """Recorre el árbol sintáctico y devuelve el objeto TAC resultante."""
        self.visit(tree)
        return self.tac

    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        """Procesa el bloque raíz del programa recorriendo sus declaraciones."""
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            try:
                child.accept(self)
            except Exception:
                pass
        return None

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        """Genera una instrucción mov para asignar el valor inicial de una variable."""
        name = ctx.Identifier().getText()
        init_ctx = ctx.initializer()
        if init_ctx is not None:
            expr_ctx = init_ctx.expression()
            val_tmp = self.visit(expr_ctx) or "<error>"
            self.tac.emit('mov', str(val_tmp), None, name)
            sym = self._resolve_var(name)
            if sym and self._is_ref_type(getattr(sym, 'typ', None)):
                self.tac.emit('incref', name, None, None)
            if isinstance(val_tmp, str) and val_tmp.startswith('t'):
                free_temp(val_tmp)
        return name

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        """Genera llamadas TAC equivalentes a print(expr)."""
        val_tmp = self.visit(ctx.expression()) or "<error>"
        self.tac.emit('param', str(val_tmp), None, None)
        self.tac.emit('call', 'print', '1', None)
        if isinstance(val_tmp, str) and val_tmp.startswith('t'):
            free_temp(val_tmp)
        return None

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        """Genera saltos condicionales y etiquetas para if/else."""
        else_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        cond = self.visit(ctx.expression()) or '<error>'
        self.tac.emit('ifz', str(cond), else_lbl, None)
        self.visit(ctx.block(0))
        self.tac.emit('goto', end_lbl, None, None)
        self.tac.emit('label', else_lbl, None, None)
        if ctx.block(1):
            self.visit(ctx.block(1))
        self.tac.emit('label', end_lbl, None, None)
        return None

    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        """Emite etiquetas y saltos para bucles while."""
        start_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        self.tac.emit('label', start_lbl, None, None)
        cond = self.visit(ctx.expression()) or '<error>'
        self.tac.emit('ifz', str(cond), end_lbl, None)
        self.visit(ctx.block())
        self.tac.emit('goto', start_lbl, None, None)
        self.tac.emit('label', end_lbl, None, None)
        return None

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        """Emite la instrucción ret con o sin valor."""
        if ctx.expression():
            val = self.visit(ctx.expression()) or '<error>'
            self.tac.emit('ret', str(val), None, None)
            if isinstance(val, str) and val.startswith('t'):
                free_temp(val)
        else:
            self.tac.emit('ret', None, None, None)
        return None

    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        """Traduce comparaciones (<, <=, >, >=) en cuádruplos TAC."""
        left = self.visit(ctx.additiveExpr(0)) or '<error>'
        for i in range(1, len(ctx.additiveExpr())):
            right = self.visit(ctx.additiveExpr(i)) or '<error>'
            op_tok = ctx.getChild(2*i - 1).getText()
            op = {'<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge'}.get(op_tok, 'cmp')
            t = new_temp()
            self.tac.emit(op, str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        """Genera comparaciones de igualdad (==, !=)."""
        left = self.visit(ctx.relationalExpr(0)) or '<error>'
        for i in range(1, len(ctx.relationalExpr())):
            right = self.visit(ctx.relationalExpr(i)) or '<error>'
            op_tok = ctx.getChild(2*i - 1).getText()
            op = {'==': 'eq', '!=': 'ne'}.get(op_tok, 'cmp')
            t = new_temp()
            self.tac.emit(op, str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        """Traduce operaciones lógicas AND (&&)."""
        left = self.visit(ctx.equalityExpr(0)) or '<error>'
        for i in range(1, len(ctx.equalityExpr())):
            right = self.visit(ctx.equalityExpr(i)) or '<error>'
            t = new_temp()
            self.tac.emit('and', str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        """Traduce operaciones lógicas OR (||)."""
        left = self.visit(ctx.logicalAndExpr(0)) or '<error>'
        for i in range(1, len(ctx.logicalAndExpr())):
            right = self.visit(ctx.logicalAndExpr(i)) or '<error>'
            t = new_temp()
            self.tac.emit('or', str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        """Traduce asignaciones (x = expr) con control de referencias."""
        if len(ctx.expression()) == 1:
            name = ctx.Identifier().getText()
            val_tmp = self.visit(ctx.expression(0)) or "<error>"
            sym = self._resolve_var(name)
            is_ref = sym and self._is_ref_type(getattr(sym, 'typ', None))
            if is_ref:
                self.tac.emit('incref', str(val_tmp), None, None)
                self.tac.emit('decref', name, None, None)
            self.tac.emit('mov', str(val_tmp), None, name)
            if isinstance(val_tmp, str) and val_tmp.startswith('t'):
                free_temp(val_tmp)
        return name

    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        """Evalúa expresiones sueltas (no asignadas a variable)."""
        val = self.visit(ctx.expression())
        return val if val is not None else "<error>"

    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        """Devuelve el nombre del identificador (variable o símbolo)."""
        return ctx.Identifier().getText() or "<error>"

    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        """Devuelve el valor literal como texto (número, string, booleano, etc.)."""
        return ctx.getText() or "<error>"

    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        """Traduce sumas y restas en cuádruplos TAC."""
        left = self.visit(ctx.multiplicativeExpr(0)) or "<error>"
        for i in range(1, len(ctx.multiplicativeExpr())):
            right = self.visit(ctx.multiplicativeExpr(i)) or "<error>"
            op = ctx.getChild(2*i - 1).getText()
            t = new_temp()
            self.tac.emit('add' if op == '+' else 'sub', str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        """Traduce multiplicaciones, divisiones y módulos en TAC."""
        left = self.visit(ctx.unaryExpr(0)) or "<error>"
        for i in range(1, len(ctx.unaryExpr())):
            right = self.visit(ctx.unaryExpr(i)) or "<error>"
            op = ctx.getChild(2*i - 1).getText()
            opc = 'mul' if op == '*' else ('div' if op == '/' else 'mod')
            t = new_temp()
            self.tac.emit(opc, str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitChildren(self, node):
        """Fallback: visita genérica para nodos no definidos explícitamente."""
        last_val = None
        for i in range(node.getChildCount()):
            child = node.getChild(i)
            try:
                val = child.accept(self)
                if isinstance(val, str):
                    last_val = val
            except Exception:
                pass
        return last_val if last_val is not None else "<error>"


def generate_tac_from_parser(tree, analyzer: Optional[object] = None) -> TAC:
    """Genera el objeto TAC completo desde el árbol sintáctico."""
    return TACGenerator(analyzer=analyzer).generate(tree)

def generate_tac_text(tree, analyzer: Optional[object] = None) -> str:
    """Devuelve la representación textual del TAC generado."""
    tac = generate_tac_from_parser(tree, analyzer=analyzer)
    return str(tac)
