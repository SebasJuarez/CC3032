# TAC (Three Address Code) - Especificación para Compiscript

Este documento describe una especificación clara y mínima de código intermedio (TAC) para el proyecto Compiscript, con convenciones, ejemplos y decisiones de diseño.

## Formato de instrucción

Cada instrucción TAC tendrá una forma textual sencilla: una operación seguida de sus operandos y un resultado opcional.

- Operaciones binarias: op arg1, arg2 -> res
  - Ejemplo: add t1, t2 -> t3
- Operaciones unarias: op arg -> res
  - Ejemplo: neg t1 -> t2
- Asignación: assign src -> dest
  - Ejemplo: assign 5 -> a
- Salto condicional: ifz arg -> label
  - Significa: si arg == 0 saltar a label
- Salto incondicional: goto label
- Llamada y retorno:
  - param arg  (poner argumento para la llamada)
  - call func_name, n_args -> res  (res opcional si la función retorna)
  - ret arg  (en función)
- Labels: label:
- Comentarios: # texto (opcional)

## Convenciones

- Temporales: t0, t1, t2, ... gestionados por un `TempManager`.
- Labels: L0, L1, L2, ... para saltos.
- Variables globales y locales se referencian por nombre; la tabla de símbolos añadirá `offset` y `is_local` para direccionamiento posterior.
- Las instrucciones se almacenan como una lista ordenada. Cada función tendrá su propio bloque TAC con prologue/epilogue:
  - func f:
    - # prologue (reserva espacio, guardar RA)
    - ... instrucciones ...
    - # epilogue (restaura RA, return)

## Activación y memoria

- Para generación posterior a assembler, cada símbolo en la tabla tendrá:
  - offset: desplazamiento dentro del registro de activación
  - mem_size: tamaño en bytes (int, bool, arrays si aplica)
  - is_param/is_local
  - label (nombre único para globals)

- El generador TAC añadirá NOTAS (pseudo-instrucciones) para prologue/epilogue como `enter size` y `leave`.

## Gestión de temporales

- API mínima:
  - new_temp() -> "tN"
  - free_temp("tN")
- Política: temporales se asignan por evaluación de expresión y se liberan tan pronto como ya no son necesarios en la generación de la instrucción que los consume.
- Estrategia de reciclaje: free-list; se reinserta el índice de la temporal para reutilización.

## Ejemplos

1) Asignación simple:

  a = b + 3

TAC:
  add b, 3 -> t0
  assign t0 -> a

2) If-else:

  if (x < y) { z = 1; } else { z = 2; }

TAC:
  lt x, y -> t0
  ifz t0 -> L1
  assign 1 -> z
  goto L2
L1:
  assign 2 -> z
L2:

3) While loop:

L0:
  lt i, 10 -> t0
  ifz t0 -> L1
  ...body...
  goto L0
L1:

4) Function call:

  r = f(1, x)

TAC:
  param 1
  param x
  call f, 2 -> t0
  assign t0 -> r

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