Notas rápidas y puntos de extensión para generación de CI

Objetivo: Documentar los archivos a inspeccionar y los nodos AST que debemos soportar para la generación TAC.

Archivos clave (leer antes de implementar):
- `src/semantic/analyzer.py`  -> cómo se recorren y verifican tipos
- `src/semantic/symbols.py`   -> estructura actual de símbolos (extender con offset/label/temp)
- `src/semantic/types.py`     -> tipos soportados y utilidades de conversión/coerción
- `src/gen/CompiscriptParser.py` -> clases de nodos del parser (identificar nombres de nodos y métodos visit)
- `src/gen/CompiscriptVisitor.py` o `CompiscriptListener.py` -> si hay visitor/listener generado
- `src/parse_utils.py`        -> utilidades existentes de parsing que pueden ser reutilizadas
- `src/run.py` / `ide.py`     -> puntos donde exponer la opción `--tac`

Nodos AST y manejadores sugeridos (función generadora de TAC por nodo):
- Program / CompilationUnit -> iterar funciones y declaraciones globales
- FunctionDecl -> enter new TAC function block; asignar offsets a parámetros y locales
- VarDecl -> registrar en tabla de símbolos con `offset` y `mem_size` (si aún no existe)
- Block -> nuevo scope para temporales y símbolos locales
- Assignment -> generar RHS, luego `assign` a LHS (soportar LHS simple: id)
- IfStatement -> generar cond, ifz -> elseLabel, thenBlock, goto endLabel, elseBlock, endLabel
- WhileStatement -> labelStart, cond, ifz -> labelEnd, body, goto labelStart
- ReturnStatement -> generar expr (si hay) y `ret` / `assign` a return reg
- Expr BinaryOp (+, -, *, /, <, >, ==, etc.) -> generar operand temporales, emitir op -> temp
- Expr UnaryOp (!, -) -> emitir un op
- CallExpr -> evaluar args, emitir param x (in order), call name, n -> temp

Extensiones en `src/semantic/symbols.py` (campos recomendados):
- name: str
- type: Type
- scope_level: int
- offset: int | None
- is_param: bool
- is_local: bool
- mem_size: int
- label: Optional[str]  # para símbolos globales o temporales

Pruebas iniciales a crear en `tests/`:
- `test_tac_basic.py`: expresiones y asignaciones (comparar con strings/golden files)
- `test_tac_control.py`: if/else y while
- `test_tac_functions.py`: llamadas y retornos
- Tests de errores semánticos: llamadas con args incorrectas, uso de variables no declaradas (debe fallar antes de generar TAC)

Notas de integración:
- Mantener la API `generate_tac(ast_root)` que devuelve una lista de instrucciones (objetos o strings).
- Mantener separación entre generación TAC (frontend) y la posterior traducción a assembler (backend).

Siguientes pasos inmediatos (manualmente):
1. Abrir `src/semantic/symbols.py` y evaluar cómo añadir campos `offset` y `label`.
2. Diseñar `src/gen/tac_generator.py` con una clase `TACGenerator(Visitor)` que visite nodos relevantes.
3. Implementar `src/codegen/temp_manager.py` con `new_temp()` y `free_temp()`.

---

Agregar aquí hallazgos concretos tras leer los archivos mencionados.