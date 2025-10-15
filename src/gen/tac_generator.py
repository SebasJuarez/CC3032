# tac_generator.py  — versión robusta a rutas y con wrapper generate_tac_text
from __future__ import annotations
from typing import Optional

# --- Imports ANTLR (como ya usabas) ---
from src.gen.CompiscriptVisitor import CompiscriptVisitor
from src.gen.CompiscriptParser import CompiscriptParser

# --- Importar TAC con fallback (src.gen.tac ó tac.py en raíz) ---
try:
    from src.gen.tac import TAC
except Exception:
    try:
        from tac import TAC  # archivo tac.py en raíz del proyecto
    except Exception:
        # Fallback ultra-minimal por si no se encuentra nada
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
            def __init__(self): self.quads=[]
            def emit(self, op:str, arg1:_Opt[str]=None, arg2:_Opt[str]=None, res:_Opt[str]=None):
                self.quads.append(Quad(op, None if arg1 is None else str(arg1), None if arg2 is None else str(arg2), None if res is None else str(res)))
            def extend(self, other:'TAC'): self.quads.extend(other.quads)
            def __str__(self): return "\n".join(str(q) for q in self.quads)

# --- Temp manager con fallback (si no tienes src.codegen.temp_manager) ---
try:
    from src.codegen.temp_manager import new_temp, free_temp
except Exception:
    from itertools import count
    _temp_counter = count(1)

    def new_temp():
        return f"t{next(_temp_counter)}"

    def free_temp(_):
        # no-op; deja el hook por si luego implementas un pool de temporales
        pass

class TACGenerator(CompiscriptVisitor):
    def __init__(self, analyzer: Optional[object] = None) -> None:
        self.tac = TAC()
        self.analyzer = analyzer
        # symtab del analizador si está disponible
        self.symtab = getattr(analyzer, 'symtab', None) if analyzer is not None else None
        # Generador de etiquetas locales al archivo
        from itertools import count
        self._label_counter = count(0)

    def _new_label(self, prefix: str = 'L') -> str:
        return f"{prefix}{next(self._label_counter)}"

    # Helpers de tipos/RC
    def _resolve_var(self, name: str):
        if self.symtab is None:
            return None
        # Buscar desde el scope actual hacia arriba
        return self.symtab.current.resolve(name)

    def _is_ref_type(self, typ) -> bool:
        try:
            # Tipos referencia: strings, arrays (dims>0) y clases
            if typ is None:
                return False
            # import dinámico para evitar ciclos
            from src.semantic.types import String, Type
            if isinstance(typ, Type):
                if typ.is_string() or getattr(typ, 'dims', 0) > 0:
                    return True
                # Clases: si el tag existe en la tabla de clases
                if self.symtab and self.symtab.get_class(typ.tag):
                    return True
            return False
        except Exception:
            return False

    # Entry point (acepta el árbol raíz)
    def generate(self, tree) -> TAC:
        self.visit(tree)
        return self.tac

    # ---------------- Program ----------------
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        # Recorrer todos los statements del programa en orden
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            try:
                child.accept(self)
            except Exception:
                pass
        return None

    # ---------------- Statements ----------------
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        # let|var Identifier (":" type)? ("=" expr)? ";"
        name = ctx.Identifier().getText()
        init_ctx = ctx.initializer()
        if init_ctx is not None:
            expr_ctx = init_ctx.expression()
            val_tmp = self.visit(expr_ctx)
            if val_tmp is None:
                val_tmp = "<error>"
            # Emisión como mov (res = arg1)
            self.tac.emit('mov', str(val_tmp), None, name)
            # RC: si la variable es de tipo referencia -> incref(name)
            sym = self._resolve_var(name)
            if sym is not None and self._is_ref_type(getattr(sym, 'typ', None)):
                self.tac.emit('incref', name, None, None)
            if isinstance(val_tmp, str) and val_tmp.startswith('t'):
                free_temp(val_tmp)
        # si no hay inicializador, no emitimos nada (o podríamos asignar default)
        return name

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        # print("(") expression ")" ";"
        val_tmp = self.visit(ctx.expression())
        if val_tmp is None:
            val_tmp = "<error>"
        # Convención de llamada: param + call (facilita backend MIPS)
        self.tac.emit('param', str(val_tmp), None, None)
        self.tac.emit('call', 'print', '1', None)
        if isinstance(val_tmp, str) and val_tmp.startswith('t'):
            free_temp(val_tmp)
        return None

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        else_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        cond = self.visit(ctx.expression())
        if cond is None:
            cond = '<error>'
        # ifz cond -> else
        self.tac.emit('ifz', str(cond), else_lbl, None)
        # then
        self.visit(ctx.block(0))
        # salto al fin
        self.tac.emit('goto', end_lbl, None, None)
        # etiqueta else
        self.tac.emit('label', else_lbl, None, None)
        if ctx.block(1):
            self.visit(ctx.block(1))
        # etiqueta fin
        self.tac.emit('label', end_lbl, None, None)
        return None

    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        start_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        self.tac.emit('label', start_lbl, None, None)
        cond = self.visit(ctx.expression())
        if cond is None:
            cond = '<error>'
        self.tac.emit('ifz', str(cond), end_lbl, None)
        self.visit(ctx.block())
        self.tac.emit('goto', start_lbl, None, None)
        self.tac.emit('label', end_lbl, None, None)
        return None

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        if ctx.expression():
            val = self.visit(ctx.expression())
            if val is None:
                val = '<error>'
            self.tac.emit('ret', str(val), None, None)
            if isinstance(val, str) and val.startswith('t'):
                free_temp(val)
        else:
            self.tac.emit('ret', None, None, None)
        return None

    # ---- Operadores lógicos y relacionales ----
    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        left = self.visit(ctx.additiveExpr(0))
        if left is None:
            left = '<error>'
        for i in range(1, len(ctx.additiveExpr())):
            right = self.visit(ctx.additiveExpr(i))
            if right is None:
                right = '<error>'
            op_tok = ctx.getChild(2*i - 1).getText()
            op = {'<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge'}.get(op_tok, 'cmp')
            t = new_temp()
            self.tac.emit(op, str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        left = self.visit(ctx.relationalExpr(0))
        if left is None:
            left = '<error>'
        for i in range(1, len(ctx.relationalExpr())):
            right = self.visit(ctx.relationalExpr(i))
            if right is None:
                right = '<error>'
            op_tok = ctx.getChild(2*i - 1).getText()
            op = {'==': 'eq', '!=': 'ne'}.get(op_tok, 'cmp')
            t = new_temp()
            self.tac.emit(op, str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        left = self.visit(ctx.equalityExpr(0))
        if left is None:
            left = '<error>'
        for i in range(1, len(ctx.equalityExpr())):
            right = self.visit(ctx.equalityExpr(i))
            if right is None:
                right = '<error>'
            t = new_temp()
            self.tac.emit('and', str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        left = self.visit(ctx.logicalAndExpr(0))
        if left is None:
            left = '<error>'
        for i in range(1, len(ctx.logicalAndExpr())):
            right = self.visit(ctx.logicalAndExpr(i))
            if right is None:
                right = '<error>'
            t = new_temp()
            self.tac.emit('or', str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left
    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        # Soporta: Identifier '=' expression ';'
        if len(ctx.expression()) == 1:
            name = ctx.Identifier().getText()
            val_tmp = self.visit(ctx.expression(0))
            if val_tmp is None:
                val_tmp = "<error>"
            # RC: si LHS es ref: incref(rhs) y luego decref(old lhs) antes de mover
            sym = self._resolve_var(name)
            is_ref = sym is not None and self._is_ref_type(getattr(sym, 'typ', None))
            if is_ref:
                self.tac.emit('incref', str(val_tmp), None, None)
                self.tac.emit('decref', name, None, None)
            # mov para asignación simple
            self.tac.emit('mov', str(val_tmp), None, name)
            if isinstance(val_tmp, str) and val_tmp.startswith('t'):
                free_temp(val_tmp)
        return name

    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        val = self.visit(ctx.expression())
        return val if val is not None else "<error>"

    # ---------------- Expressions (devuelven temp o literal) ----------------
    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        name = ctx.Identifier().getText()
        if name is None:
            return "<error>"
        return name

    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        val = ctx.getText()
        if val is None:
            return "<error>"
        return val

    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        left = self.visit(ctx.multiplicativeExpr(0))
        if left is None:
            left = "<error>"
        for i in range(1, len(ctx.multiplicativeExpr())):
            right = self.visit(ctx.multiplicativeExpr(i))
            if right is None:
                right = "<error>"
            op = ctx.getChild(2*i - 1).getText()
            t = new_temp()
            self.tac.emit('add' if op == '+' else 'sub', str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        left = self.visit(ctx.unaryExpr(0))
        if left is None:
            left = "<error>"
        for i in range(1, len(ctx.unaryExpr())):
            right = self.visit(ctx.unaryExpr(i))
            if right is None:
                right = "<error>"
            op = ctx.getChild(2*i - 1).getText()
            opc = 'mul' if op == '*' else ('div' if op == '/' else 'mod')
            t = new_temp()
            self.tac.emit(opc, str(left), str(right), t)
            if isinstance(left, str) and left.startswith('t'): free_temp(left)
            if isinstance(right, str) and right.startswith('t'): free_temp(right)
            left = t
        return left

    # Fallback genérico (no rompe si hay nodos no manejados aún)
    def visitChildren(self, node):
        # Fallback robusto: si algún hijo retorna string, lo devolvemos
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

# ---- API pública esperada por tu IDE ----
def generate_tac_from_parser(tree, analyzer: Optional[object] = None) -> TAC:
    return TACGenerator(analyzer=analyzer).generate(tree)

def generate_tac_text(tree, analyzer: Optional[object] = None) -> str:
    """Wrapper que tu IDE espera: devuelve el TAC como string."""
    tac = generate_tac_from_parser(tree, analyzer=analyzer)
    return str(tac)
