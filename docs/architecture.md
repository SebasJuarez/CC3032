# Arquitectura del Compilador Compiscript

Este documento describe la arquitectura y el flujo de compilación del compilador de Compiscript, desde el código fuente hasta la generación de código intermedio (TAC).

## Visión General

El compilador sigue una arquitectura de **pipeline de múltiples fases**:

```
Código fuente (.cps)
    ↓
┌─────────────────────┐
│  Análisis Léxico    │ ← ANTLR (CompiscriptLexer)
└─────────────────────┘
    ↓ tokens
┌─────────────────────┐
│ Análisis Sintáctico │ ← ANTLR (CompiscriptParser)
└─────────────────────┘
    ↓ AST
┌─────────────────────┐
│ Análisis Semántico  │ ← SemanticAnalyzer
└─────────────────────┘
    ↓ AST + Tabla de Símbolos
┌─────────────────────┐
│ Generación TAC      │ ← TACGenerator
└─────────────────────┘
    ↓ Cuádruplos (CI)
┌─────────────────────┐
│ [Fase Futura]       │
│ Backend MIPS        │
└─────────────────────┘
    ↓ Código MIPS
```

## Componentes Principales

### 1. Frontend: Análisis Léxico y Sintáctico (ANTLR)

**Archivos:**
- `Compiscript.g4` — Gramática ANTLR4
- `src/gen/CompiscriptLexer.py` — Lexer generado
- `src/gen/CompiscriptParser.py` — Parser generado
- `src/gen/CompiscriptVisitor.py` — Visitor base generado

**Función:**
- Tokeniza el código fuente
- Construye el árbol sintáctico abstracto (AST)
- Detecta errores de sintaxis

**Regeneración:**
```bash
java -jar antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor -o src/gen Compiscript.g4
```

### 2. Análisis Semántico

**Archivos:**
- `src/semantic/analyzer.py` — SemanticAnalyzer (visitor del AST)
- `src/semantic/symbols.py` — Tabla de símbolos y definiciones
- `src/semantic/types.py` — Sistema de tipos
- `src/semantic/errors.py` — Manejo de errores semánticos

**Función:**
- Valida tipos (type checking)
- Gestiona scopes y símbolos
- Verifica consistencia semántica:
  - Declaraciones y redeclaraciones
  - Asignaciones compatibles por tipo
  - Control de flujo (break/continue en loops, return en funciones)
  - Herencia y acceso a miembros de clases
- Construye y mantiene la tabla de símbolos global

**Tabla de Símbolos:**
Estructura de scopes anidados con metadatos extendidos para generación de código:
```python
Symbol(
    name: str,
    typ: Type,
    is_const: bool,
    offset: int,       # desplazamiento en el stack frame
    is_local: bool,    # local/param vs global
    mem_size: int,     # tamaño en bytes
    label: str,        # etiqueta para globales/funciones
    is_param: bool     # True si es parámetro
)
```

### 3. Generación de Código Intermedio (TAC)

**Archivos:**
- `src/gen/tac.py` — Definición de cuádruplos (Quad) y contenedor (TAC)
- `src/gen/tac_generator.py` — TACGenerator (visitor del AST)
- `src/codegen/temp_manager.py` — Gestor de variables temporales

**Función:**
- Recorre el AST post-análisis semántico
- Genera cuádruplos (op, arg1, arg2, res)
- Emite instrucciones de:
  - Aritmética y lógica
  - Control de flujo (labels, goto, ifz)
  - Llamadas a función (param, call, ret)
  - Gestión de memoria (incref, decref para GC)
- Gestiona temporales con reciclaje (free-list)

**Formato de cuádruplos:**
```
(op, arg1, arg2, res)
```
Ejemplo: `(add, x, 2, t0)` significa `t0 = x + 2`

### 4. Soporte de Garbage Collection

**Estrategia:** Conteo de referencias (Reference Counting)

**Implementación:**
- Tipos de referencia: strings, arrays, objetos
- Cuádruplos RC:
  - `(incref, var, _, _)` — incrementa ref count
  - `(decref, var, _, _)` — decrementa y libera si llega a 0
- Emisión automática:
  - `incref` al inicializar variables ref
  - `incref` antes de copiar referencias
  - `decref` antes de reasignar variables ref
  - `decref` al salir de scope (futuro)

### 5. IDE y Herramientas

**Archivos:**
- `ide.py` — IDE web con Streamlit
- `src/run.py` — CLI para compilar desde terminal
- `Driver.py` — Script de pruebas rápidas

**Funcionalidades del IDE:**
- Editor de código con syntax highlighting (Streamlit)
- Compilación en tiempo real
- Visualización de:
  - Árbol de parseo
  - Tabla de símbolos
  - Código intermedio (TAC)
  - Errores de sintaxis/semántica
- Descarga de artefactos (.tac, tabla de símbolos)
- Preservación opcional de entorno entre compilaciones

## Flujo de Datos

### 1. Entrada
Usuario escribe código en `program.cps` o en el IDE.

### 2. Parsing
```python
from src.parse_utils import parse_string
parser = parse_string(source_code)
tree = parser.program()  # AST raíz
```

### 3. Análisis Semántico
```python
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport

errors = SemanticErrorReport()
analyzer = SemanticAnalyzer(errors)
analyzer.visit(tree)

if errors.has_errors():
    # Mostrar errores y detener
    for e in errors.errors:
        print(e)
else:
    # AST validado, tabla de símbolos lista
    symtab = analyzer.symtab
```

### 4. Generación TAC
```python
from src.gen.tac_generator import generate_tac_text

tac_code = generate_tac_text(tree, analyzer=analyzer)
print(tac_code)  # muestra cuádruplos
```

### 5. Salida
- Código intermedio en formato de texto (cuádruplos)
- Opcionalmente guardado en archivo `.tac`

## Decisiones de Diseño

### Cuádruplos vs. Triples
- Elegimos **cuádruplos** por:
  - Formato fijo facilita parsing en backend
  - Mapeo directo a instrucciones MIPS de 3 operandos
  - Explícito para temporales (facilita análisis de vida útil)

### Reference Counting vs. Tracing GC
- Elegimos **conteo de referencias** por:
  - Determinismo: liberación inmediata cuando ref count llega a 0
  - Simplicidad de implementación en MIPS
  - No requiere pausas de GC (no hay "stop-the-world")
  - Suficiente para el alcance académico del proyecto

### Temporales con Free-List
- Reutilización de temporales reduce presión de registros en MIPS
- Reset al inicio de función mantiene limpieza de namespace
- API simple: `new_temp()`, `free_temp(t)`, `reset()`

### Metadatos en Símbolos
- `offset` y `mem_size` permiten cálculo directo de direcciones de stack
- `is_local` vs global ayuda a elegir entre memoria estática y dinámica
- `is_param` facilita convención de llamada (registros vs stack)
- `label` provee nombres únicos para globales y funciones

## Testing

**Archivos:**
- `tests/test_semantic.py` — Tests unitarios de análisis semántico
- `tests/ok_*.cps` — Casos válidos
- `tests/fail_*.cps` — Casos con errores esperados

**Ejecución:**
```bash
python -m pytest tests/ -v
```

**Coverage esperado:**
- Declaraciones y asignaciones
- Control de flujo (if, while, for)
- Funciones y llamadas
- Clases y herencia
- Manejo de tipos y errores

## Referencias

- Gramática: `Compiscript.g4`, `Compiscript.bnf`
- Especificación TAC: `docs/tac_spec.md`
- README principal: `README.md`
- Requerimientos fase TAC: `README_TAC_GENERATION.md`

