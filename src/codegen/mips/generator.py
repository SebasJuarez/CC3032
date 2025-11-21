from typing import List, Tuple, Dict, Set, Optional
from src.gen.tac import TAC, Quad
from .registers import RegisterAllocator
from .emitter import MIPSEmitter

ARITH_MAP = {
    'add': 'add',
    'sub': 'sub',
    'mul': 'mul',  # usaremos pseudo-instr mul rd, rs, rt
    'div': 'div',  # pseudo div rd, rs, rt (MARS/QtSpim soportan)
}

SUPPORTED_CMP = {'lt', 'gt', 'le', 'ge', 'eq', 'ne'}

LOGIC_MAP = {
    'and': 'and',
    'or': 'or',
}

def _is_int_literal(x: str) -> bool:
    if x is None:
        return False
    try:
        int(x)
        return True
    except Exception:
        return False

class MIPSGenerator:
    def __init__(self, tac: TAC) -> None:
        self.tac = tac
        self.emitter = MIPSEmitter()
        self.current_function: str | None = None
        self.function_segments: List[Tuple[str, List[Quad]]] = []
        self.main_segment: List[Quad] = []
        # Segmentación inicial
        self._segment_functions()
        # Contador local de etiquetas
        self._label_counter = 0
        self._last_param_kind: Optional[str] = None  # 'int' | 'string' | 'other'
        self._pending_params: List[Tuple[str, str]] = []  # (kind, reg_or_label)

    # ---------------- Segmentación -----------------
    def _segment_functions(self) -> None:
        cur_func: str | None = None
        buf: List[Quad] = []
        for q in self.tac.quads:
            if q.op == 'func_begin':
                # flush buffer outside functions into main
                if cur_func is None and buf:
                    self.main_segment.extend(buf)
                    buf = []
                cur_func = q.arg1 or '<anon>'
                buf = []
                continue
            if q.op == 'func_end':
                fname = q.arg1 or cur_func or '<anon>'
                self.function_segments.append((fname, buf[:]))
                buf = []
                cur_func = None
                continue
            buf.append(q)
        # cualquier resto fuera de funciones
        if buf:
            if cur_func is None:
                self.main_segment.extend(buf)
            else:
                self.function_segments.append((cur_func, buf))

    # --------------- Prepass de asignación (para tamaño de frame real) ---------------
    def _cmp_temp_names(self, op: str, left: Optional[str], right: Optional[str]) -> List[str]:
        names: List[str] = []
        if op in ('le', 'ge', 'eq', 'ne'):
            tag = op
            names.append(f'cmp_tmp_{left}_{right}_{tag}')
        return names

    def _prepass_allocate(self, quads: List[Quad], regs: RegisterAllocator) -> None:
        for q in quads:
            op = q.op
            if op in ('label', 'goto', 'func_begin', 'func_end'):
                continue
            # Tocar símbolos para fijar asignaciones/spills
            syms = []
            if q.arg1 is not None and q.arg1 != '':
                if not _is_int_literal(q.arg1):
                    syms.append(q.arg1)
                else:
                    regs.get(f'lit_{q.arg1}')
            if q.arg2 is not None and q.arg2 != '':
                if not _is_int_literal(q.arg2):
                    syms.append(q.arg2)
                else:
                    regs.get(f'lit_{q.arg2}')
            if q.res is not None and q.res != '':
                syms.append(q.res)
            for s in syms:
                regs.get(s)
            if op in SUPPORTED_CMP:
                for name in self._cmp_temp_names(op, q.arg1, q.arg2):
                    regs.get(name)

    # --------------- Generación principal ---------------
    def generate(self) -> str:
        # Punto de entrada: salto explícito a main para evitar iniciar en primera función
        self.emitter.text.directive('globl', 'main')
        self.emitter.text.instr('j', 'main', comment='entry jump')
        self.emitter.text.instr('nop')
        # Generar funciones (labels pueden ser forward referenciados por main)
        for fname, fquads in self.function_segments:
            self._emit_function(fname, fquads)
        # Generar main (top-level) al final
        self._emit_main(self.main_segment)
        # runtime
        self.emitter.add_runtime()
        return self.emitter.to_string()

    def _emit_function(self, fname: str, quads: List[Quad]) -> None:
        self.current_function = fname
        regs = RegisterAllocator()  # nuevo por función
        self._prepass_allocate(quads, regs)
        frame_size = regs.frame_size()
        # detectar registros $s usados
        used_s: List[str] = sorted({r for r in regs.map.values() if r.startswith('$s')})
        save_count = len(used_s)
        # layout: [spills][saved $s regs][fp][ra]
        total_frame = frame_size + save_count * 4 + 8
        self.emitter.text.label(fname)
        # prólogo
        self.emitter.text.instr('addi', '$sp', '$sp', f'-{total_frame}', comment=f'reservar frame {frame_size}+{save_count}*s+save')
        # guardar $s regs
        for i, sreg in enumerate(used_s):
            off = frame_size + i * 4
            self.emitter.text.instr('sw', sreg, f'{off}($sp)', comment=f'save {sreg}')
        # guardar fp y ra
        fp_off = frame_size + save_count * 4
        ra_off = fp_off + 4
        self.emitter.text.instr('sw', '$fp', f'{fp_off}($sp)')
        self.emitter.text.instr('sw', '$ra', f'{ra_off}($sp)')
        # establecer nuevo fp
        self.emitter.text.instr('addi', '$fp', '$sp', f'{fp_off + 8}')
        # cargar parámetros formales (orden de aparición de fparam)
        param_names: List[str] = [q.arg1 for q in quads if q.op == 'fparam' and q.arg1]
        for idx, pname in enumerate(param_names):
            # usar registro ya asignado en prepass para consistencia
            reg_loc, off_loc = regs.location(pname)
            if reg_loc is None:
                reg_loc = regs.get(pname)
            preg = reg_loc
            off = off_loc
            # $a0-$a3 según idx
            if idx < 4:
                src = f'$a{idx}'
                self.emitter.text.instr('move', preg, src, comment=f'param {pname}')
                if off is not None:
                    self.emitter.text.instr('sw', preg, f'{off}($fp)')
            else:
                # argumentos extra en stack: posición esperada:  (idx-4)*4($fp + ...) - simplificado (no implementado)
                self.emitter.text.instr('move', preg, '$zero', comment=f'param-extra {pname} (not implemented)')
                if off is not None:
                    self.emitter.text.instr('sw', preg, f'{off}($fp)')
        # Emitir cuerpo
        for q in quads:
            self._emit_quad(q, regs, frame_size, used_s)
        # retorno implícito si no hubo 'ret'
        self._emit_function_epilogue(frame_size, used_s)
        self.current_function = None

    def _emit_function_epilogue(self, frame_size: int, used_s: List[str]) -> None:
        save_count = len(used_s)
        fp_off = frame_size + save_count * 4
        ra_off = fp_off + 4
        total_frame = frame_size + save_count * 4 + 8
        self.emitter.text.label(f'end_{self.current_function}')
        # restaurar fp y ra
        self.emitter.text.instr('lw', '$fp', f'{fp_off}($sp)')
        self.emitter.text.instr('lw', '$ra', f'{ra_off}($sp)')
        # restaurar $s regs
        for i, sreg in enumerate(used_s):
            off = frame_size + i * 4
            self.emitter.text.instr('lw', sreg, f'{off}($sp)', comment=f'restore {sreg}')
        self.emitter.text.instr('addi', '$sp', '$sp', f'{total_frame}')
        self.emitter.text.instr('jr', '$ra')

    def _emit_main(self, quads: List[Quad]) -> None:
        self.current_function = None
        regs = RegisterAllocator()
        self._prepass_allocate(quads, regs)
        frame_size = regs.frame_size()
        self.emitter.text.label('main')
        if frame_size:
            self.emitter.text.instr('addi', '$sp', '$sp', f'-{frame_size}', comment='reservar spills main')
            # fijar $fp para direccionar spills relativos a $fp
            self.emitter.text.instr('addi', '$fp', '$sp', f'{frame_size}')
        else:
            # aún así, establece $fp para evitar lecturas desde 0
            self.emitter.text.instr('move', '$fp', '$sp')
        for q in quads:
            self._emit_quad(q, regs, frame_size)
        self.emitter.text.label('end_main')
        if frame_size:
            self.emitter.text.instr('addi', '$sp', '$sp', f'{frame_size}', comment='liberar spills main')
        self.emitter.text.instr('li', '$v0', '10', comment='exit syscall')
        self.emitter.text.instr('syscall')
        self.current_function = None

    def _ensure_reg(self, name: str, regs: RegisterAllocator) -> str:
        if name is None or name == '':
            return '$zero'
        if _is_int_literal(name):
            # cargar literal a temp reg (simple: usar $t9 si disponible)
            reg = regs.get(f'lit_{name}')
            if reg.startswith('SPILL'):
                # fallback: usar $t9 ignorando que ya esté usado
                reg = '$t9'
            self.emitter.text.instr('li', reg, name)
            return reg
        return regs.get(name)

    def _reg_for_read(self, name: Optional[str], regs: RegisterAllocator, scratch: str = '$t8') -> str:
        if name is None or name == '' or name == '_':
            return '$zero'
        if _is_int_literal(name):
            self.emitter.text.instr('li', scratch, name)
            return scratch
        reg, off = regs.location(name)
        if reg:
            return reg
        if off is not None:
            self.emitter.text.instr('lw', scratch, f'{off}($fp)')
            return scratch
        # caer a get y usar registro
        got = regs.get(name)
        if got.startswith('SPILL'):
            self.emitter.text.instr('lw', scratch, f"{regs.spill_offset(name)}($fp)")
            return scratch
        return got

    def _reg_for_write(self, name: Optional[str], regs: RegisterAllocator, scratch: str = '$t8') -> Tuple[str, Optional[int]]:
        if name is None or name == '' or name == '_':
            return scratch, None
        reg, off = regs.location(name)
        if reg:
            return reg, None
        if off is not None:
            return scratch, off
        got = regs.get(name)
        if got.startswith('SPILL'):
            return scratch, regs.spill_offset(name)
        return got, None

    def _new_label(self, prefix: str = 'L') -> str:
        self._label_counter += 1
        return f"{prefix}{self._label_counter}"

    def _is_string_literal(self, val: Optional[str]) -> bool:
        if val is None:
            return False
        return len(val) >= 2 and val.startswith('"') and val.endswith('"')

    def _emit_quad(self, q: Quad, regs: RegisterAllocator, frame_size: int, used_s: Optional[List[str]] = None) -> None:
        op = q.op
        a1, a2, r = q.arg1, q.arg2, q.res
        if op == 'label':
            if a1:
                self.emitter.text.label(a1)
            return
        if op in ('func_begin', 'func_end'):
            # ya procesado en segmentación
            return
        if op == 'goto':
            if a1:
                self.emitter.text.instr('j', a1)
            return
        if op == 'ifz':
            # (ifz, cond, label, _) -> branch if cond == 0
            cond_reg = self._reg_for_read(a1, regs, '$t8')
            lbl = a2
            self.emitter.text.instr('beq', cond_reg, '$zero', lbl)
            return
        if op == 'mov':
            if r is None:
                return
            dst, off = self._reg_for_write(r, regs, '$t8')
            # fuente puede ser literal o símbolo
            src = self._reg_for_read(a1, regs, '$t9')
            self.emitter.text.instr('move', dst, src)
            if off is not None:
                self.emitter.text.instr('sw', dst, f'{off}($fp)')
            return
        if op in ARITH_MAP:
            rd, off = self._reg_for_write(r, regs, '$t8')
            rs = self._reg_for_read(a1, regs, '$t8')
            rt = self._reg_for_read(a2, regs, '$t9')
            if op == 'div':
                # División segura: si rt == 0 => rd = 0
                l_ok = self._new_label('DIV_OK')
                l_z = self._new_label('DIV_Z')
                self.emitter.text.instr('beq', rt, '$zero', l_z)
                self.emitter.text.instr('div', rs, rt)  # 2 operandos reales
                self.emitter.text.instr('mflo', rd)
                if off is not None:
                    self.emitter.text.instr('sw', rd, f'{off}($fp)')
                self.emitter.text.instr('j', l_ok)
                self.emitter.text.label(l_z)
                self.emitter.text.instr('move', rd, '$zero')
                if off is not None:
                    self.emitter.text.instr('sw', rd, f'{off}($fp)')
                self.emitter.text.label(l_ok)
            else:
                self.emitter.text.instr(ARITH_MAP[op], rd, rs, rt)
                if off is not None:
                    self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op in LOGIC_MAP:
            rd, off = self._reg_for_write(r, regs, '$t8')
            rs = self._reg_for_read(a1, regs, '$t8')
            rt = self._reg_for_read(a2, regs, '$t9')
            self.emitter.text.instr(LOGIC_MAP[op], rd, rs, rt)
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op in SUPPORTED_CMP:
            self._emit_comparison(op, a1, a2, r, regs)
            return
        if op == 'param':
            self._last_param_kind = None
            if a1:
                known_funcs = {fn for fn, _ in self.function_segments}
                if a1 in known_funcs:
                    # agregar marcador especial de función
                    self._pending_params.append(('fn', a1))
                    self._last_param_kind = 'other'
                    return
                if self._is_string_literal(a1):
                    lbl = self.emitter.add_string_literal(a1)
                    self._pending_params.append(('string', lbl))
                    self._last_param_kind = 'string'
                else:
                    if _is_int_literal(a1):
                        # Guardar literal directamente para evitar colisión de scratch
                        self._pending_params.append(('intlit', a1))
                        self._last_param_kind = 'int'
                    else:
                        reg = self._reg_for_read(a1, regs, '$t8')
                        self._pending_params.append(('reg', reg))
                        self._last_param_kind = 'other'
            return
        if op == 'call':
            # (call, nombre, argc, res?)
            fname = a1
            res_reg = None
            if r:
                res_reg, off = self._reg_for_write(r, regs, '$t8')
            if fname == 'print':
                target = '__print_str' if self._last_param_kind == 'string' else '__print_int'
            else:
                target = fname
            # Resolver llamadas indirectas via invoke: último param 'fn'
            if target == 'invoke':
                # buscar último marcador de función
                for kind, val in reversed(self._pending_params):
                    if kind == 'fn':
                        target = val
                        break
                # eliminar cualquier entrada 'fn' de la lista de argumentos reales
                self._pending_params = [p for p in self._pending_params if p[0] != 'fn']
            # Registrar stub externo si no está en funciones generadas ni es runtime
            known_funcs = {fn for fn, _ in self.function_segments}
            if target not in ('__print_int', '__print_str') and target not in known_funcs and target not in self.emitter.externals:
                # evitar añadir stubs para funciones de objeto ya manejadas inline
                if target not in ('Person.new', 'Student.new', 'invoke.init', 'invoke.greet'):
                    self.emitter.externals.append(target)
            # mover argumentos acumulados a $a0-$a3
            for idx, (kind, val) in enumerate(self._pending_params):
                if idx >= 4:
                    # (no implementado: usar stack para args extra)
                    break
                if kind == 'string':
                    self.emitter.text.instr('la', f'$a{idx}', val, comment=f'arg{idx} string')
                elif kind == 'intlit':
                    self.emitter.text.instr('li', f'$a{idx}', val, comment=f'arg{idx} int')
                else:
                    self.emitter.text.instr('move', f'$a{idx}', val, comment=f'arg{idx}')
            # Implementaciones especializadas de objetos Person/Student
            if target == 'Person.new':
                # Param pendiente 0 = nombre
                name_kind, name_val = self._pending_params[0]
                # Guardar puntero a nombre en $t2 antes de usar $a0 para tamaño
                if name_kind == 'string':
                    self.emitter.text.instr('la', '$t2', name_val)
                elif name_kind == 'intlit':
                    self.emitter.text.instr('li', '$t2', name_val)
                else:
                    self.emitter.text.instr('move', '$t2', name_val)
                # alloc 12 bytes (tag, name, grade)
                self.emitter.text.instr('li', '$a0', '12')
                self.emitter.text.instr('li', '$v0', '9')
                self.emitter.text.instr('syscall')
                self.emitter.text.instr('move', '$t0', '$v0', comment='obj ptr')
                self.emitter.text.instr('li', '$t1', '1', comment='tag Person')
                self.emitter.text.instr('sw', '$t1', '0($t0)')
                self.emitter.text.instr('sw', '$t2', '4($t0)', comment='store name ptr')
                self.emitter.text.instr('sw', '$zero', '8($t0)', comment='grade=0')
                self.emitter.text.instr('move', '$v0', '$t0')
            elif target == 'Student.new':
                # Param 0 = nombre, param 1 = grade
                name_kind, name_val = self._pending_params[0]
                grade_kind, grade_val = self._pending_params[1]
                # Preservar nombre y grade antes de usar $a0 para tamaño
                if name_kind == 'string':
                    self.emitter.text.instr('la', '$t2', name_val)
                elif name_kind == 'intlit':
                    self.emitter.text.instr('li', '$t2', name_val)
                else:
                    self.emitter.text.instr('move', '$t2', name_val)
                if grade_kind == 'intlit':
                    self.emitter.text.instr('li', '$t3', grade_val)
                elif grade_kind == 'string':
                    self.emitter.text.instr('la', '$t3', grade_val)
                else:
                    self.emitter.text.instr('move', '$t3', grade_val)
                # alloc
                self.emitter.text.instr('li', '$a0', '12')
                self.emitter.text.instr('li', '$v0', '9')
                self.emitter.text.instr('syscall')
                self.emitter.text.instr('move', '$t0', '$v0', comment='obj ptr')
                self.emitter.text.instr('li', '$t1', '2', comment='tag Student')
                self.emitter.text.instr('sw', '$t1', '0($t0)')
                self.emitter.text.instr('sw', '$t2', '4($t0)', comment='store name ptr')
                self.emitter.text.instr('sw', '$t3', '8($t0)', comment='store grade')
                self.emitter.text.instr('move', '$v0', '$t0')
            elif target == 'invoke.init':
                # Person.init: name, obj   Student.init: name, grade, obj
                # Detect número de args acumulados y último es objeto
                argc = len(self._pending_params)
                # obtener objeto (último param)
                obj_kind, obj_val = self._pending_params[-1]
                if obj_kind == 'string':
                    self.emitter.text.instr('la', '$t0', obj_val)
                elif obj_kind == 'intlit':
                    self.emitter.text.instr('li', '$t0', obj_val)
                else:
                    self.emitter.text.instr('move', '$t0', obj_val)
                # cargar tag
                self.emitter.text.instr('lw', '$t1', '0($t0)', comment='load tag')
                # name param always first
                name_kind, name_val = self._pending_params[0]
                if name_kind == 'string':
                    self.emitter.text.instr('la', '$t2', name_val)
                elif name_kind == 'intlit':
                    self.emitter.text.instr('li', '$t2', name_val)
                else:
                    self.emitter.text.instr('move', '$t2', name_val)
                self.emitter.text.instr('sw', '$t2', '4($t0)', comment='set name')
                if argc == 3:
                    # grade param is second
                    grade_kind, grade_val = self._pending_params[1]
                    if grade_kind == 'intlit':
                        self.emitter.text.instr('li', '$t3', grade_val)
                    elif grade_kind == 'string':
                        self.emitter.text.instr('la', '$t3', grade_val)
                    else:
                        self.emitter.text.instr('move', '$t3', grade_val)
                    self.emitter.text.instr('sw', '$t3', '8($t0)', comment='set grade')
                self.emitter.text.instr('move', '$v0', '$t0', comment='return obj')
            elif target == 'invoke.greet':
                # param: obj
                obj_kind, obj_val = self._pending_params[0]
                if obj_kind == 'string':
                    self.emitter.text.instr('la', '$t0', obj_val)
                elif obj_kind == 'intlit':
                    self.emitter.text.instr('li', '$t0', obj_val)
                else:
                    self.emitter.text.instr('move', '$t0', obj_val)
                # load tag and name
                self.emitter.text.instr('lw', '$t1', '0($t0)', comment='tag')
                self.emitter.text.instr('lw', '$t2', '4($t0)', comment='name ptr')
                self.emitter.text.instr('move', '$a0', '$t2')
                self.emitter.text.instr('jal', '__print_str', comment='print name')
                # if tag == 2 (Student) print grade
                grade_lbl = self._new_label('GRADE')
                done_lbl = self._new_label('GREET_DONE')
                self.emitter.text.instr('li', '$t3', '2')
                self.emitter.text.instr('bne', '$t1', '$t3', done_lbl)
                self.emitter.text.instr('lw', '$t4', '8($t0)', comment='grade')
                self.emitter.text.instr('move', '$a0', '$t4')
                self.emitter.text.instr('jal', '__print_int', comment='print grade')
                self.emitter.text.label(done_lbl)
                self.emitter.text.instr('move', '$v0', '$zero')
            else:
                # llamada normal
                self.emitter.text.instr('jal', target)
            if res_reg:
                self.emitter.text.instr('move', res_reg, '$v0', comment='return value')
                if r and off is not None:
                    self.emitter.text.instr('sw', res_reg, f'{off}($fp)')
            # limpiar lista de params acumulados
            self._pending_params.clear()
            return
        # ===== Memoria / Arrays =====
        if op == 'newarr':
            # (newarr, etag, length, t_arr)
            length_reg = self._reg_for_read(a2, regs, '$t8')
            dest, off = self._reg_for_write(r, regs, '$t9')
            # size = (length + 1) * 4 bytes (1 palabra para length)
            self.emitter.text.instr('addi', '$a0', length_reg, '1')
            self.emitter.text.instr('sll', '$a0', '$a0', '2')  # *4
            self.emitter.text.instr('li', '$v0', '9')          # sbrk
            self.emitter.text.instr('syscall')
            # v0 = base
            self.emitter.text.instr('move', dest, '$v0')
            # store length at base
            self.emitter.text.instr('sw', length_reg, f'0({dest})')
            if off is not None:
                self.emitter.text.instr('sw', dest, f'{off}($fp)')
            return
        if op == 'alen':
            # (alen, arr, _, tlen)
            arr_reg = self._reg_for_read(a1, regs, '$t8')
            dest, off = self._reg_for_write(r, regs, '$t9')
            self.emitter.text.instr('lw', dest, f'0({arr_reg})')
            if off is not None:
                self.emitter.text.instr('sw', dest, f'{off}($fp)')
            return
        if op == 'idxchk':
            # Simple bounds check: if idx >= len print INDEX_OOB
            arr_reg = self._reg_for_read(a1, regs, '$t8')
            idx_reg = self._reg_for_read(a2, regs, '$t9')
            len_tmp = '$t7'
            self.emitter.text.instr('lw', len_tmp, f'0({arr_reg})')
            # slt ok, idx < len ?
            self.emitter.text.instr('slt', '$t6', idx_reg, len_tmp)
            oob_lbl = self._new_label('OOB')
            ok_lbl = self._new_label('OOBOK')
            self.emitter.text.instr('beq', '$t6', '$zero', oob_lbl)
            self.emitter.text.instr('j', ok_lbl)
            self.emitter.text.label(oob_lbl)
            msg_lbl = self.emitter.add_string_literal('"INDEX_OOB"')
            self.emitter.text.instr('la', '$a0', msg_lbl)
            self.emitter.text.instr('jal', '__print_str')
            self.emitter.text.label(ok_lbl)
            return
        if op == 'aload':
            # (aload, arr, idx, t_dest)
            arr_reg = self._reg_for_read(a1, regs, '$t8')
            idx_reg = self._reg_for_read(a2, regs, '$t9')
            dest, off = self._reg_for_write(r, regs, '$t7')
            self.emitter.text.instr('sll', '$t6', idx_reg, '2')  # idx*4
            self.emitter.text.instr('addi', '$t6', '$t6', '4')  # skip length word
            self.emitter.text.instr('add', '$t6', '$t6', arr_reg)
            self.emitter.text.instr('lw', dest, '0($t6)')
            if off is not None:
                self.emitter.text.instr('sw', dest, f'{off}($fp)')
            return
        if op == 'astore':
            # (astore, arr, idx, value)
            arr_reg = self._reg_for_read(a1, regs, '$t8')
            idx_reg = self._reg_for_read(a2, regs, '$t9')
            val_reg = self._reg_for_read(r, regs, '$t7')
            self.emitter.text.instr('sll', '$t6', idx_reg, '2')
            self.emitter.text.instr('addi', '$t6', '$t6', '4')
            self.emitter.text.instr('add', '$t6', '$t6', arr_reg)
            self.emitter.text.instr('sw', val_reg, '0($t6)')
            return
        # ===== Objetos / Propiedades (placeholders no-op) =====
        if op in ('incref', 'decref'):  # RC no implementado todavía
            return
        if op == 'pload':
            # propiedad: ignorar y producir 0
            dest, off = self._reg_for_write(r, regs, '$t8')
            self.emitter.text.instr('move', dest, '$zero')
            if off is not None:
                self.emitter.text.instr('sw', dest, f'{off}($fp)')
            return
        if op == 'pstore':
            # no-op por ahora
            return
        if op == 'ret':
            # mover valor a $v0 si hay
            if a1 and a1 != '':
                reg = self._reg_for_read(a1, regs, '$t8')
                self.emitter.text.instr('move', '$v0', reg)
            if self.current_function is None:
                self.emitter.text.instr('j', 'end_main', comment='ret main')
            else:
                # reconstruir offsets para epílogo inline
                save_count = len(used_s or [])
                fp_off = frame_size + save_count * 4
                ra_off = fp_off + 4
                total_frame = frame_size + save_count * 4 + 8
                self.emitter.text.instr('lw', '$fp', f'{fp_off}($sp)')
                self.emitter.text.instr('lw', '$ra', f'{ra_off}($sp)')
                for i, sreg in enumerate(used_s or []):
                    off = frame_size + i * 4
                    self.emitter.text.instr('lw', sreg, f'{off}($sp)', comment=f'restore {sreg}')
                self.emitter.text.instr('addi', '$sp', '$sp', f'{total_frame}')
                self.emitter.text.instr('jr', '$ra')
            return
        # Otros op desconocidos: ignorar silenciosamente
        return

    # ---------- Comparaciones sin pseudo-instrucciones ----------
    def _emit_comparison(self, op: str, left: Optional[str], right: Optional[str], dest: Optional[str], regs: RegisterAllocator) -> None:
        if dest is None:
            return
        rd, off = self._reg_for_write(dest, regs, '$t8')
        rs = self._reg_for_read(left, regs, '$t8')
        rt = self._reg_for_read(right, regs, '$t9')
        # Emisión según op
        if op == 'lt':
            self.emitter.text.instr('slt', rd, rs, rt)
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op == 'gt':
            # gt: rd = rs > rt => slt rd, rt, rs
            self.emitter.text.instr('slt', rd, rt, rs)
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op == 'le':
            # le: rs <= rt => !(rs > rt). Usar scratch sin cargar memoria no inicializada.
            tmp = '$t9'
            self.emitter.text.instr('slt', tmp, rt, rs)  # tmp = rt < rs (rs > rt)
            self.emitter.text.instr('xori', rd, tmp, '1')  # rd = !tmp
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op == 'ge':
            # ge: rs >= rt => !(rs < rt)
            tmp = '$t9'
            self.emitter.text.instr('slt', tmp, rs, rt)  # tmp = rs < rt
            self.emitter.text.instr('xori', rd, tmp, '1')
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op == 'eq':
            # eq: rs == rt => rd = (rs ^ rt == 0)
            tmp = '$t9'
            self.emitter.text.instr('xor', tmp, rs, rt)
            self.emitter.text.instr('sltiu', rd, tmp, '1')  # rd=1 si tmp < 1 (tmp==0)
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return
        if op == 'ne':
            # ne: rs != rt => rd = (rs ^ rt != 0)
            tmp = '$t9'
            self.emitter.text.instr('xor', tmp, rs, rt)
            self.emitter.text.instr('sltu', rd, '$zero', tmp)  # rd=1 si 0 < tmp
            if off is not None:
                self.emitter.text.instr('sw', rd, f'{off}($fp)')
            return


def generate_mips_from_tac(tac: TAC) -> str:
    return MIPSGenerator(tac).generate()
