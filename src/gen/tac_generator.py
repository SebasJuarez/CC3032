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
        # Pilas para manejar break/continue en bucles y switch
        self._break_stack = []
        self._continue_stack = []

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

    # No generamos TAC dentro de declaraciones de clases ni funciones en la pasada principal.
    # Esto evita instrucciones con 'this' sin contexto y código de métodos en top-level.
    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        return None

    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        """Emite delimitadores de función para permitir backend MIPS.
        Estructura esperada (simplificada): 'function' Identifier '(' params? ')' block
        Generamos:
          (func_begin, name, _, _)
          ... cuerpo ...
          (func_end, name, _, _)
        No generamos código para parámetros aquí; se asume que la tabla de símbolos
        ya los contiene tras el análisis semántico. Añadimos cuádruplos 'fparam'
        por cada parámetro formal para facilitar la carga en el backend.
        """
        try:
            name = ctx.Identifier().getText()
        except Exception:
            name = '<anon_func>'
        self.tac.emit('func_begin', name, '', '')
        # parámetros formales
        try:
            params_ctx = ctx.parameters()
            if params_ctx:
                # grammar assumption: parameters: (param (',' param)*)?
                for i in range(params_ctx.getChildCount()):
                    ch = params_ctx.getChild(i)
                    # heurística: un identificador podría ser el nombre
                    try:
                        if hasattr(ch, 'getText'):
                            txt = ch.getText()
                            # Saltar comas y tipos (simplificado); cuando detectamos un identificador aislado lo emitimos
                            if txt == ',':
                                continue
                            # Evitar tipos primitivos repetidos
                            if txt in ('integer', 'string', 'boolean', 'void'):  # añade otros tipos si existen
                                continue
                            # Normalizar identificador con posible anotación ":tipo"
                            if ':' in txt:
                                txt = txt.split(':', 1)[0]
                            # Emitir parámetro formal
                            self.tac.emit('fparam', txt, '', '')
                    except Exception:
                        pass
        except Exception:
            pass
        # Visitar bloque de la función (asumimos último hijo es el bloque)
        try:
            # Algunas gramáticas podrían tener ctx.block(), en otras el cuerpo es child específico
            if hasattr(ctx, 'block') and ctx.block() is not None:
                ctx.block().accept(self)
            else:
                # fallback: iterar hijos y visitar el que parezca bloque
                for i in range(ctx.getChildCount()):
                    ch = ctx.getChild(i)
                    txt = getattr(ch, 'getText', lambda: '')()
                    if txt.startswith('{'):
                        try:
                            ch.accept(self)
                            break
                        except Exception:
                            pass
        except Exception:
            pass
        # Si el cuerpo no contiene un 'ret' explícito, el backend añadirá retorno implícito.
        self.tac.emit('func_end', name, '', '')
        return None

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        """Genera mov para inicialización, con RC si aplica."""
        name = ctx.Identifier().getText()
        init_ctx = ctx.initializer()
        if init_ctx is not None:
            expr_ctx = init_ctx.expression()
            val_tmp = self.visit(expr_ctx) or "<error>"
            sym = self._resolve_var(name)
            if sym and self._is_ref_type(getattr(sym, 'typ', None)):
                self.tac.emit('incref', str(val_tmp), '', '')
                self.tac.emit('decref', name, '', '')
            self.tac.emit('mov', str(val_tmp), '', name)
            if isinstance(val_tmp, str) and val_tmp.startswith('t'):
                free_temp(val_tmp)
        return name

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        """Genera llamadas TAC equivalentes a print(expr)."""
        val_tmp = self.visit(ctx.expression()) or "<error>"
        self.tac.emit('param', str(val_tmp), '', '')
        self.tac.emit('call', 'print', '1', '')
        if isinstance(val_tmp, str) and val_tmp.startswith('t'):
            free_temp(val_tmp)
        return None

    def visitTryCatchStatement(self, ctx: CompiscriptParser.TryCatchStatementContext):
        """Por ahora, sólo generamos TAC para el bloque try y omitimos el catch.
        Evita que el código del catch se ejecute incondicionalmente.
        """
        # try block es block(0), catch block es block(1)
        self.visit(ctx.block(0))
        return None

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        """Genera saltos condicionales y etiquetas para if/else. Simplifica el caso sin else."""
        cond = self.visit(ctx.expression()) or '<error>'
        # Detectar si hay rama else (block(1) o if anidado)
        has_else_block = bool(ctx.block(1))
        has_else_if = hasattr(ctx, 'ifStatement') and ctx.ifStatement() is not None
        if not has_else_block and not has_else_if:
            end_lbl = self._new_label('L')
            self.tac.emit('ifz', str(cond), end_lbl, '')
            self.visit(ctx.block(0))
            self.tac.emit('label', end_lbl, '', '')
            return None
        # Con else/else-if
        else_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        self.tac.emit('ifz', str(cond), else_lbl, '')
        self.visit(ctx.block(0))
        self.tac.emit('goto', end_lbl, '', '')
        self.tac.emit('label', else_lbl, '', '')
        if has_else_block:
            self.visit(ctx.block(1))
        elif has_else_if:
            self.visit(ctx.ifStatement())
        self.tac.emit('label', end_lbl, '', '')
        return None

    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        """Emite etiquetas y saltos para bucles while."""
        start_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        # continue salta a reevaluar la condición
        self._continue_stack.append(start_lbl)
        self._break_stack.append(end_lbl)
        self.tac.emit('label', start_lbl, '', '')
        cond = self.visit(ctx.expression()) or '<error>'
        self.tac.emit('ifz', str(cond), end_lbl, '')
        self.visit(ctx.block())
        self.tac.emit('goto', start_lbl, '', '')
        self.tac.emit('label', end_lbl, '', '')
        self._continue_stack.pop()
        self._break_stack.pop()
        return None

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        """Emite la instrucción ret con o sin valor."""
        if ctx.expression():
            val = self.visit(ctx.expression()) or '<error>'
            self.tac.emit('ret', str(val), '', '')
            if isinstance(val, str) and val.startswith('t'):
                free_temp(val)
        else:
            self.tac.emit('ret', '', '', '')
        return None

    def visitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        """Bucle do-while: ejecuta cuerpo, luego evalúa condición y repite si verdadera."""
        start_lbl = self._new_label('L')
        cond_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        # continue salta a evaluar condición
        self._continue_stack.append(cond_lbl)
        self._break_stack.append(end_lbl)
        self.tac.emit('label', start_lbl, '', '')
        self.visit(ctx.block())
        self.tac.emit('label', cond_lbl, '', '')
        cond = self.visit(ctx.expression()) or '<error>'
        # si cond != 0, saltar al inicio
        # Implementado como ifz cond end; goto start
        self.tac.emit('ifz', str(cond), end_lbl, '')
        self.tac.emit('goto', start_lbl, '', '')
        self.tac.emit('label', end_lbl, '', '')
        self._continue_stack.pop()
        self._break_stack.pop()
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
        """Traduce asignaciones: var, propiedad y arreglo."""
        if len(ctx.expression()) == 1:
            name = ctx.Identifier().getText()
            val_tmp = self.visit(ctx.expression(0)) or "<error>"
            sym = self._resolve_var(name)
            is_ref = sym and self._is_ref_type(getattr(sym, 'typ', None))
            if is_ref:
                self.tac.emit('incref', str(val_tmp), '', '')
                self.tac.emit('decref', name, '', '')
            self.tac.emit('mov', str(val_tmp), '', name)
            if isinstance(val_tmp, str) and val_tmp.startswith('t'):
                free_temp(val_tmp)
            return name
        # property assignment: base.expr '.' id = rhs
        base = self.visit(ctx.expression(0)) or '<error>'
        prop = ctx.Identifier().getText()
        rhs = self.visit(ctx.expression(1)) or '<error>'
        # Para ahora, emitir un store genérico a propiedad
        self.tac.emit('pstore', str(base), prop, str(rhs))
        if isinstance(base, str) and base.startswith('t'): free_temp(base)
        if isinstance(rhs, str) and rhs.startswith('t'): free_temp(rhs)
        return prop

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

    # ====== Assignment expressions (expression-level) ======
    def _lhs_base_and_last(self, lhs_ctx: CompiscriptParser.LeftHandSideContext):
        """Devuelve (base_val, last_suffix_op) evaluando la cadena hasta el penúltimo sufijo.
        Si no hay sufijos, base_val es el valor de primaryAtom y last_suffix_op es None.
        """
        base = self.visit(lhs_ctx.primaryAtom()) or '<error>'
        sufs = list(lhs_ctx.suffixOp())
        if not sufs:
            return base, None
        # reproduce efectos hasta el penúltimo sufijo
        for so in sufs[:-1]:
            txt = so.getText()
            if txt.startswith('('):
                argc = 0
                if so.arguments():
                    for e in so.arguments().expression():
                        a = self.visit(e) or '<error>'
                        self.tac.emit('param', str(a), '', '')
                        argc += 1
                        if isinstance(a, str) and a.startswith('t'): free_temp(a)
                self.tac.emit('param', str(base), '', '')
                argc += 1
                tret = new_temp()
                self.tac.emit('call', 'invoke', str(argc), tret)
                if isinstance(base, str) and base.startswith('t'): free_temp(base)
                base = tret
            elif txt.startswith('['):
                idx = self.visit(so.expression()) or '<error>'
                self.tac.emit('idxchk', str(base), str(idx), '')
                t = new_temp()
                self.tac.emit('aload', str(base), str(idx), t)
                if isinstance(base, str) and base.startswith('t'): free_temp(base)
                if isinstance(idx, str) and idx.startswith('t'): free_temp(idx)
                base = t
            else:
                pid = so.Identifier().getText() if hasattr(so, 'Identifier') and so.Identifier() else txt[1:]
                t = new_temp()
                self.tac.emit('pload', str(base), pid, t)
                if isinstance(base, str) and base.startswith('t'): free_temp(base)
                base = t
        return base, sufs[-1]

    def visitAssignExpr(self, ctx: CompiscriptParser.AssignExprContext):
        # lhs = assignmentExpr
        rhs = self.visit(ctx.assignmentExpr()) or '<error>'
        lhs_ctx = ctx.lhs
        base, last = self._lhs_base_and_last(lhs_ctx)
        if last is None:
            # Asignación a identificador simple
            name = lhs_ctx.primaryAtom().getText()
            sym = self._resolve_var(name)
            is_ref = sym and self._is_ref_type(getattr(sym, 'typ', None))
            if is_ref:
                self.tac.emit('incref', str(rhs), '', '')
                self.tac.emit('decref', name, '', '')
            self.tac.emit('mov', str(rhs), '', name)
            if isinstance(rhs, str) and rhs.startswith('t'): free_temp(rhs)
            return name
        txt = last.getText()
        if txt.startswith('['):
            # arr[index] = rhs
            idx = self.visit(last.expression()) or '<error>'
            # Determinar si el elemento es de tipo de referencia para aplicar RC
            is_ref_elem = False
            try:
                if self.analyzer is not None and hasattr(self.analyzer, 'eval_lhs'):
                    elem_t = self.analyzer.eval_lhs(ctx.lhs)
                    is_ref_elem = self._is_ref_type(elem_t)
            except Exception:
                is_ref_elem = False

            # Chequeo de índice
            self.tac.emit('idxchk', str(base), str(idx), '')

            if is_ref_elem:
                # Cargar valor antiguo, aplicar RC y luego almacenar el nuevo valor
                told = new_temp()
                self.tac.emit('aload', str(base), str(idx), told)
                # incref(rhs) primero para manejar aliasing seguro
                self.tac.emit('incref', str(rhs), '', '')
                # decref(old)
                self.tac.emit('decref', told, '', '')
                # store
                self.tac.emit('astore', str(base), str(idx), str(rhs))
                if isinstance(told, str) and told.startswith('t'):
                    free_temp(told)
            else:
                # Elemento escalar: solo almacenar
                self.tac.emit('astore', str(base), str(idx), str(rhs))

            if isinstance(idx, str) and idx.startswith('t'): free_temp(idx)
            if isinstance(base, str) and base.startswith('t'): free_temp(base)
            if isinstance(rhs, str) and rhs.startswith('t'): free_temp(rhs)
            return '<arr-assign>'
        else:
            # propiedad .id = rhs (aunque hay alternativa específica)
            pid = last.Identifier().getText() if hasattr(last, 'Identifier') and last.Identifier() else txt[1:]
            self.tac.emit('pstore', str(base), pid, str(rhs))
            if isinstance(base, str) and base.startswith('t'): free_temp(base)
            if isinstance(rhs, str) and rhs.startswith('t'): free_temp(rhs)
            return pid

    def visitPropertyAssignExpr(self, ctx: CompiscriptParser.PropertyAssignExprContext):
        # lhs '.' id = assignmentExpr
        base = self.visit(ctx.lhs) or '<error>'
        rhs = self.visit(ctx.assignmentExpr()) or '<error>'
        pid = ctx.Identifier().getText()
        self.tac.emit('pstore', str(base), pid, str(rhs))
        if isinstance(base, str) and base.startswith('t'): free_temp(base)
        if isinstance(rhs, str) and rhs.startswith('t'): free_temp(rhs)
        return pid

    # ====== LHS: cadenas de llamadas, indexación y propiedades ======
    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        return self.visit(ctx.expression())

    def visitNewArrayExpr(self, ctx: CompiscriptParser.NewArrayExprContext):
        # 'new' baseType '[' expression ']'
        etag = ctx.baseType().getText()
        length = self.visit(ctx.expression()) or '<error>'
        t_arr = new_temp()
        self.tac.emit('newarr', etag, str(length), t_arr)
        if isinstance(length, str) and length.startswith('t'):
            free_temp(length)
        return t_arr

    def visitNewObjectExpr(self, ctx: CompiscriptParser.NewObjectExprContext):
        # 'new' Identifier '(' arguments? ')'
        argc = 0
        if ctx.arguments():
            for e in ctx.arguments().expression():
                av = self.visit(e) or '<error>'
                self.tac.emit('param', str(av), '', '')
                argc += 1
                if isinstance(av, str) and av.startswith('t'):
                    free_temp(av)
        cname = ctx.Identifier().getText()
        tret = new_temp()
        self.tac.emit('call', f'{cname}.new', str(argc), tret)
        return tret

    def visitLeftHandSide(self, ctx: CompiscriptParser.LeftHandSideContext):
        base = self.visit(ctx.primaryAtom()) or '<error>'
        sufs = list(ctx.suffixOp())
        i = 0
        while i < len(sufs):
            so = sufs[i]
            txt = so.getText()
            # Lookahead: next suffix to detect method call pattern '.id' followed by '()'
            nxt = sufs[i+1] if i+1 < len(sufs) else None
            if not txt.startswith('(') and not txt.startswith('[') and nxt is not None and nxt.getText().startswith('('):
                # Pattern: .id followed by call => method call on receiver 'base'
                pid = so.Identifier().getText() if hasattr(so, 'Identifier') and so.Identifier() else txt[1:]
                # Emit args from nxt
                argc = 0
                if nxt.arguments():
                    for e in nxt.arguments().expression():
                        argv = self.visit(e) or '<error>'
                        self.tac.emit('param', str(argv), '', '')
                        argc += 1
                        if isinstance(argv, str) and argv.startswith('t'):
                            free_temp(argv)
                # Implicit receiver
                self.tac.emit('param', str(base), '', '')
                argc += 1
                tret = new_temp()
                # Generic dynamic dispatch
                self.tac.emit('call', f'invoke.{pid}', str(argc), tret)
                if isinstance(base, str) and base.startswith('t'):
                    free_temp(base)
                base = tret
                i += 2
                continue
            if txt.startswith('('):
                # Llamada: si 'base' es función global conocida, emitir call directo; si no, usar invoke con receptor/closure en 'base'.
                argc = 0
                args = []
                if so.arguments():
                    for e in so.arguments().expression():
                        argv = self.visit(e) or '<error>'
                        args.append(argv)
                # ¿Es función global?
                is_direct_fn = False
                fn_name = None
                if isinstance(base, str) and self.symtab is not None:
                    try:
                        sym = self._resolve_var(base)
                        # Heurística: función si tiene atributos de función
                        if sym is not None and hasattr(sym, 'return_type') and hasattr(sym, 'params'):
                            is_direct_fn = True
                            fn_name = base
                    except Exception:
                        pass
                # Emitir params
                for argv in args:
                    self.tac.emit('param', str(argv), '', '')
                    if isinstance(argv, str) and argv.startswith('t'):
                        free_temp(argv)
                tret = new_temp()
                if is_direct_fn and fn_name:
                    # Llamada directa: no pasamos 'base' como param implícito
                    self.tac.emit('call', fn_name, str(len(args)), tret)
                else:
                    # First-class/invoke: pasamos la función/closure como último param
                    self.tac.emit('param', str(base), '', '')
                    self.tac.emit('call', 'invoke', str(len(args) + 1), tret)
                    if isinstance(base, str) and base.startswith('t'):
                        free_temp(base)
                base = tret
            elif txt.startswith('['):
                idx = self.visit(so.expression()) or '<error>'
                self.tac.emit('idxchk', str(base), str(idx), '')
                t_elem = new_temp()
                self.tac.emit('aload', str(base), str(idx), t_elem)
                if isinstance(base, str) and base.startswith('t'):
                    free_temp(base)
                if isinstance(idx, str) and idx.startswith('t'):
                    free_temp(idx)
                base = t_elem
            else:
                # property access .id (no call immediately after)
                pid = so.Identifier().getText() if hasattr(so, 'Identifier') and so.Identifier() else txt[1:]
                t_prop = new_temp()
                self.tac.emit('pload', str(base), pid, t_prop)
                if isinstance(base, str) and base.startswith('t'):
                    free_temp(base)
                base = t_prop
            i += 1
        return base

    def visitPrimaryAtom(self, ctx: CompiscriptParser.PrimaryAtomContext):
        if ctx.Identifier():
            return ctx.Identifier().getText()
        if ctx.getText().startswith('new'):
            # new obj o new array
            txt = ctx.getText()
            if '[' in txt and ']' in txt and '(' not in txt:
                # new T[expr]
                # Obtener la expresión de tamaño del AST, no por string
                if ctx.baseType():
                    et = ctx.baseType().getText()
                else:
                    et = 'unknown'
                length = self.visit(ctx.expression()) if ctx.expression() else '<error>'
                t_arr = new_temp()
                self.tac.emit('newarr', et, str(length or '<error>'), t_arr)
                if isinstance(length, str) and length.startswith('t'): free_temp(length)
                return t_arr
            else:
                # new Class(args)
                argc = 0
                if ctx.arguments():
                    for e in ctx.arguments().expression():
                        av = self.visit(e) or '<error>'
                        self.tac.emit('param', str(av), '', '')
                        argc += 1
                        if isinstance(av, str) and av.startswith('t'): free_temp(av)
                cname = ctx.Identifier().getText() if ctx.Identifier() else 'Object'
                tret = new_temp()
                self.tac.emit('call', f'{cname}.new', str(argc), tret)
                return tret
        if ctx.getText() == 'this':
            return 'this'
        if ctx.getText().startswith('('):
            return self.visitChildren(ctx)
        return self.visitChildren(ctx)

    # ====== For (versión básica basada en grammar forStatement) ======
    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        # for '(' (variableDeclaration | assignment | ';') expression? ';' expression? ')' block;
        start_lbl = self._new_label('L')
        step_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        # init
        init = ctx.getChild(2)
        try:
            init.accept(self)
        except Exception:
            pass
        # cond
        self.tac.emit('label', start_lbl, '', '')
        cond_val = ''
        if ctx.expression(0):
            cond = self.visit(ctx.expression(0)) or '<error>'
            self.tac.emit('ifz', str(cond), end_lbl, '')
            cond_val = cond
            if isinstance(cond, str) and cond.startswith('t'): free_temp(cond)
        # body
        # configurar break/continue
        self._continue_stack.append(step_lbl)
        self._break_stack.append(end_lbl)
        self.visit(ctx.block())
        # step (destino de continue)
        self.tac.emit('label', step_lbl, '', '')
        if ctx.expression(1):
            step = self.visit(ctx.expression(1)) or '<error>'
            if isinstance(step, str) and step.startswith('t'): free_temp(step)
        self.tac.emit('goto', start_lbl, '', '')
        self.tac.emit('label', end_lbl, '', '')
        self._continue_stack.pop()
        self._break_stack.pop()
        return None

    def visitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        """Lower foreach (v in arr) to index-based loop with alen/aload."""
        it_name = ctx.Identifier().getText()
        arr = self.visit(ctx.expression()) or '<error>'
        # Determinar si el elemento es tipo de referencia usando el analizador
        is_ref_elem = False
        try:
            if self.analyzer is not None and hasattr(self.analyzer, 'visit'):
                t_arr = self.analyzer.visit(ctx.expression())
                # Derivar elemento: dims-1 si es arreglo
                elem_t = None
                if getattr(t_arr, 'dims', 0) > 0:
                    from src.semantic.types import Type
                    elem_t = Type(getattr(t_arr, 'tag', ''), getattr(t_arr, 'dims', 0) - 1)
                is_ref_elem = self._is_ref_type(elem_t)
        except Exception:
            is_ref_elem = False

        # i = 0; len = alen(arr)
        self.tac.emit('mov', '0', '', f"{it_name}__idx")
        tlen = new_temp()
        self.tac.emit('alen', str(arr), '', tlen)
        start_lbl = self._new_label('L')
        end_lbl = self._new_label('L')
        step_lbl = self._new_label('L')
        # break/continue configuración
        self._continue_stack.append(step_lbl)
        self._break_stack.append(end_lbl)
        self.tac.emit('label', start_lbl, '', '')
        tcmp = new_temp()
        self.tac.emit('lt', f"{it_name}__idx", tlen, tcmp)
        self.tac.emit('ifz', tcmp, end_lbl, '')
        # v = aload(arr, i)
        vtmp = new_temp()
        self.tac.emit('aload', str(arr), f"{it_name}__idx", vtmp)
        if is_ref_elem:
            self.tac.emit('incref', vtmp, '', '')
            self.tac.emit('decref', it_name, '', '')
        self.tac.emit('mov', vtmp, '', it_name)
        # body
        self.visit(ctx.block())
        # step (continue target)
        self.tac.emit('label', step_lbl, '', '')
        ti = new_temp()
        self.tac.emit('add', f"{it_name}__idx", '1', ti)
        self.tac.emit('mov', ti, '', f"{it_name}__idx")
        self.tac.emit('goto', start_lbl, '', '')
        # end
        self.tac.emit('label', end_lbl, '', '')
        # liberar temps
        for t in (tlen, tcmp, vtmp, ti):
            try:
                if isinstance(t, str) and t.startswith('t'):
                    free_temp(t)
            except Exception:
                pass
        self._continue_stack.pop()
        self._break_stack.pop()
        return None

    def visitBreakStatement(self, ctx: CompiscriptParser.BreakStatementContext):
        dest = self._break_stack[-1] if self._break_stack else None
        if dest:
            self.tac.emit('goto', dest, '', '')
        return None

    def visitContinueStatement(self, ctx: CompiscriptParser.ContinueStatementContext):
        dest = self._continue_stack[-1] if self._continue_stack else None
        if dest:
            self.tac.emit('goto', dest, '', '')
        return None

    def visitSwitchStatement(self, ctx: CompiscriptParser.SwitchStatementContext):
        """Lower switch with fall-through semantics. 'break' jumps to end label."""
        val = self.visit(ctx.expression()) or '<error>'
        end_lbl = self._new_label('L')
        self._break_stack.append(end_lbl)
        cases = list(ctx.switchCase()) if hasattr(ctx, 'switchCase') else []
        def_case = ctx.defaultCase() if hasattr(ctx, 'defaultCase') else None
        # Generar cadena de comparaciones
        next_check_lbl = None
        case_labels = []
        for sc in cases:
            Lc = self._new_label('L')
            case_labels.append((sc, Lc))
        # Checks
        for i, (sc, Lc) in enumerate(case_labels):
            cval = self.visit(sc.expression()) or '<error>'
            tcmp = new_temp()
            self.tac.emit('eq', str(val), str(cval), tcmp)
            next_lbl = self._new_label('L') if i < len(case_labels) - 1 or def_case is not None else end_lbl
            self.tac.emit('ifz', tcmp, next_lbl, '')
            self.tac.emit('goto', Lc, '', '')
            self.tac.emit('label', next_lbl, '', '')
            if isinstance(tcmp, str) and tcmp.startswith('t'):
                free_temp(tcmp)
        # Si no hubo match, saltar a default o end
        if def_case is not None:
            Ld = self._new_label('L')
            self.tac.emit('goto', Ld, '', '')
        else:
            self.tac.emit('goto', end_lbl, '', '')
        # Cuerpos de cases
        for sc, Lc in case_labels:
            self.tac.emit('label', Lc, '', '')
            for st in sc.statement():
                try:
                    st.accept(self)
                except Exception:
                    pass
        # Default
        if def_case is not None:
            Ld = None
            # Encontrar la etiqueta creada para default (último goto antes)
            # Simplemente emitimos una nueva etiqueta consistente
            Ld = self._new_label('L')
            self.tac.emit('label', Ld, '', '')
            for st in def_case.statement():
                try:
                    st.accept(self)
                except Exception:
                    pass
        # Fin del switch
        self.tac.emit('label', end_lbl, '', '')
        self._break_stack.pop()
        return None


def generate_tac_from_parser(tree, analyzer: Optional[object] = None) -> TAC:
    """Genera el objeto TAC completo desde el árbol sintáctico."""
    return TACGenerator(analyzer=analyzer).generate(tree)

def generate_tac_text(tree, analyzer: Optional[object] = None) -> str:
    """Devuelve la representación textual del TAC generado."""
    tac = generate_tac_from_parser(tree, analyzer=analyzer)
    return str(tac)
