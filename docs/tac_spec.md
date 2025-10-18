# TAC (Three Address Code) - Especificación para Compiscript

Este documento describe la representación de código intermedio (CI) en formato de **cuádruplos** para el proyecto Compiscript, diseñada para facilitar la traducción a MIPS y soportar garbage collection por conteo de referencias.

## Formato de cuádruplo

Cada instrucción TAC es un cuádruplo: **(op, arg1, arg2, res)**

- **op**: código de operación (add, sub, mov, ifz, call, etc.)
- **arg1**: primer operando (puede ser variable, literal, etiqueta o `_` si no aplica)
- **arg2**: segundo operando (o `_` si la op es binaria/monádica)
- **res**: resultado/destino (o `_` si no hay resultado)

Formato textual: `(op, arg1, arg2, res)`

Ejemplos:
- `(add, x, 2, t0)` — t0 = x + 2
- `(mov, t0, _, y)` — y = t0
- `(ifz, t1, L2, _)` — if t1 == 0 goto L2
- `(label, L0, _, _)` — marca de salto
- `(call, print, 1, _)` — llamada a función con 1 arg

## Convenciones

### Temporales
- Formato: `t0`, `t1`, `t2`, ...
- Gestionados por `TempManager` en `src/codegen/temp_manager.py`
- Reciclables mediante free-list (llamar a `free_temp(t)` cuando ya no se necesita)
- Se resetean al inicio de cada función con `reset()`

### Etiquetas
- Formato: `L0`, `L1`, `L2`, ...
- Generadas por `TACGenerator._new_label()`
- Usadas para control de flujo (if, while, funciones)

### Variables
- Variables globales/locales se referencian por nombre
- La tabla de símbolos incluye metadatos para direccionamiento:
  - `offset`: desplazamiento en bytes dentro del registro de activación
  - `is_local`: True para locales/params, False para globales
  - `mem_size`: tamaño en bytes (4 para int/bool/ref, 8 para float)
  - `label`: etiqueta única para globales/funciones
  - `is_param`: True si es parámetro de función

### Tipos de referencia
- Strings, arrays (dims > 0) y objetos de clase son tipos de referencia
- Requieren gestión de memoria con conteo de referencias (RC)

## Activación y memoria

Cada símbolo en la tabla incluye metadatos para generación de código:
- **offset**: desplazamiento en bytes desde el frame pointer
- **mem_size**: tamaño en bytes
- **is_param**: True si es parámetro
- **is_local**: True si es local/param, False si global
- **label**: etiqueta para variables globales y funciones

## Garbage Collection: Conteo de Referencias

Para tipos de referencia (strings, arrays, objetos), se emiten cuádruplos de RC:

- **incref**: incrementa el contador de referencias
  - Formato: `(incref, var, _, _)`
  - Se emite cuando:
    - Una variable de referencia se inicializa: `let s: string = "hola"`
    - Se asigna un valor ref a otra variable ref
  
- **decref**: decrementa el contador y libera si llega a 0
  - Formato: `(decref, var, _, _)`
  - Se emite cuando:
    - Una variable ref sale de scope (al final de bloque/función)
    - Se reasigna una variable ref (decref del valor anterior)

### Ejemplo con RC:
```compiscript
let s: string = "hola";  // string es tipo ref
let t: string = s;       // copia de referencia
```

TAC generado:
```
(mov, "hola", _, s)
(incref, s, _, _)        # incrementar ref count de s
(incref, s, _, _)        # incrementar antes de copiar
(decref, t, _, _)        # decrementar ref anterior de t (si existía)
(mov, s, _, t)
```

## Operaciones soportadas

### Aritméticas y lógicas
- `(add, a, b, res)` — res = a + b
- `(sub, a, b, res)` — res = a - b
- `(mul, a, b, res)` — res = a * b
- `(div, a, b, res)` — res = a / b
- `(mod, a, b, res)` — res = a % b
- `(and, a, b, res)` — res = a && b
- `(or, a, b, res)` — res = a || b
- `(not, a, _, res)` — res = !a

### Relacionales
- `(lt, a, b, res)` — res = a < b
- `(le, a, b, res)` — res = a <= b
- `(gt, a, b, res)` — res = a > b
- `(ge, a, b, res)` — res = a >= b
- `(eq, a, b, res)` — res = a == b
- `(ne, a, b, res)` — res = a != b

### Movimiento y control
- `(mov, src, _, dest)` — dest = src
- `(label, L, _, _)` — marca de salto
- `(goto, L, _, _)` — salto incondicional a L
- `(ifz, cond, L, _)` — if cond == 0 goto L
- `(ret, val, _, _)` — retorno de función (val opcional)

### Llamadas a función
- `(param, arg, _, _)` — pasar argumento (se acumulan antes del call)
- `(call, fn, nargs, res)` — llamar fn con nargs argumentos, resultado en res (opcional)
- `(enter, size, _, _)` — prologue: reservar size bytes de stack
- `(leave, _, _, _)` — epilogue: restaurar frame anterior

### Garbage Collection
- `(incref, var, _, _)` — incrementar contador de referencias
- `(decref, var, _, _)` — decrementar y liberar si llega a 0

## Ejemplos completos

### 1) Asignación simple
```compiscript
let x: integer = 5;
let y: integer = x + 2;
print(y);
```

TAC:
```
(mov, 5, _, x)
(add, x, 2, t0)
(mov, t0, _, y)
(param, y, _, _)
(call, print, 1, _)
```

### 2) If-else
```compiscript
if (x < y) {
    z = 1;
} else {
    z = 2;
}
```

TAC:
```
(lt, x, y, t0)
(ifz, t0, L0, _)
(mov, 1, _, z)
(goto, L1, _, _)
(label, L0, _, _)
(mov, 2, _, z)
(label, L1, _, _)
```

### 3) While loop
```compiscript
while (i < 10) {
    sum = sum + i;
    i = i + 1;
}
```

TAC:
```
(label, L0, _, _)
(lt, i, 10, t0)
(ifz, t0, L1, _)
(add, sum, i, t1)
(mov, t1, _, sum)
(add, i, 1, t2)
(mov, t2, _, i)
(goto, L0, _, _)
(label, L1, _, _)
```

### 4) Function call con parámetros
```compiscript
let r: integer = sum(5, 10);
```

TAC:
```
(param, 5, _, _)
(param, 10, _, _)
(call, sum, 2, t0)
(mov, t0, _, r)
```

### 5) Tipos de referencia con RC
```compiscript
let s: string = "hello";
let t: string = s;
```

TAC:
```
(mov, "hello", _, s)
(incref, s, _, _)
(incref, s, _, _)      # antes de copiar
(decref, t, _, _)      # liberar ref anterior de t
(mov, s, _, t)
```

## Mapeo AST -> TAC (resumen)

- Expr Binary: generar TAC para subexprs, luego `op lhs, rhs -> t` y devolver temporal.
- Expr Unary: generar subexpr y `op arg -> t`.
- Assignment: generar RHS -> rtemp; `assign rtemp -> lvalue`.
- If: generar cond -> tcond; `ifz tcond -> L_else` etc.
- While: labels para inicio y fin, cond y cuerpo.
- FuncDef: abrir bloque `func name:`, generar prologue (enter), generar body y epilogue (leave).
- Call: generar args (evaluate left-to-right), emitir `param` por cada arg, luego `call name, n -> t`.

## Supuestos y límites iniciales

- TAC no gestiona todavía optimizaciones (const folding, copy propagation). Se diseñará para soportarlas luego.
- Manejo de arrays y punteros queda explícito como futura extensión; por ahora se asume variables escalares.
- Tipos de datos mínimos: int y bool (representados como enteros).

## Formato de salida

- Archivo `.tac` por cada archivo fuente o por función, con texto legible. Ejemplo:

  # file program.tac
  func main:
  enter 32
  t0 = add 1, 2
  assign t0 -> a
  leave


---

Referencias: formato inspirado en TAC clásico (3-address code) y adaptado a las necesidades del curso.