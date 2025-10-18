# Compiscript — Análisis Semántico y Generación de TAC

Este sistema conecta el archivo de `Compiscript.g4` con el `program.cps` usando un sistema de analizador sintáctico con ANTLR en Python. El código de la gramática (`Compiscript.g4`) fue provisto por los catedráticos y define toda la sintaxis base del lenguaje **Compiscript**, un subconjunto de TypeScript diseñado para propósitos académicos.

## 1) Instalación de dependencias

Si ya existe un entorno virtual:

```bash
Remove-Item -Recurse -Force .venv
```

Para crear un entorno nuevo e instalar dependencias:

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Dependencias principales:

```
antlr4-python3-runtime>=4.13
pytest>=8
streamlit>=1.24
```

## 2) Generación del parser y lexer (ANTLR)

**Requerimiento:** Java instalado (para ejecutar el JAR de ANTLR incluido en el proyecto).

**Comando (PowerShell/CMD en Windows):**

```powershell
java -jar antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor -o src\gen Compiscript.g4
```

**Comando (Linux/Mac):**

```bash
java -jar antlr-4.13.1-complete.jar -Dlanguage=Python3 -visitor -o src/gen Compiscript.g4
```

**Nota:** Si tienes `antlr4` en el PATH, puedes usar:
```bash
antlr4 -Dlanguage=Python3 -visitor -o src/gen Compiscript.g4
```

Esto generará los archivos `CompiscriptLexer.py`, `CompiscriptParser.py` y `CompiscriptVisitor.py` dentro de `src/gen`.

## 3) Ejecución del compilador

Existen dos formas principales de ejecutar el compilador.

### a) Modo consola

```bash
python -m src.run program.cps
```

Si el código es válido, se mostrará:

```
Semantic analysis completed successfully.
```

Si existen errores semánticos, se listarán con el formato:

```
(linea, columna) Descripción del error
```

### b) Modo IDE (Streamlit)

```bash
python -m streamlit run src/ide.py
```

Esto abrirá una página web local (`localhost:8501`) en la que se puede:

* Cargar archivos `.cps`
* Ver el **árbol sintáctico**
* Consultar la **tabla de símbolos**
* Observar los **errores semánticos**
* Generar y descargar el **código intermedio TAC**

## 4) Estructura general del compilador

El proceso completo de compilación se divide en tres etapas:

1. **Análisis Sintáctico** — usando ANTLR para construir el árbol.
2. **Análisis Semántico** — validación de tipos, variables, clases, ámbitos, herencia, etc.
3. **Generación de Código Intermedio (TAC)** — traducción del árbol a una secuencia de instrucciones de tres direcciones.

## 5) Análisis Semántico

El **SemanticAnalyzer** recorre el árbol de ANTLR validando:

* Tipos (`integer`, `string`, `boolean`, `void`, `float`)
* Declaraciones (`let`, `const`, `function`, `class`)
* Estructuras de control (`if`, `while`, `for`, `foreach`, `switch`, `try/catch`)
* Reglas de ámbito (scopes, variables globales/locales)
* Retornos correctos dentro de funciones
* Herencia simple y acceso mediante `this`

Los errores se almacenan en `SemanticErrorReport` y detienen la generación TAC si existen.


## 6) Generación de Código Intermedio (TAC)

### ¿Qué es el TAC?

El **TAC (Three Address Code)** o **código de tres direcciones** es una representación intermedia entre el código fuente y el código ensamblador.
Cada instrucción tiene la forma de un **cuádruplo**:

```
(op, arg1, arg2, result)
```

Por ejemplo:

```
(+, a, b, t0)
(print, t0, _, _)
```

El código intermedio de Compiscript se genera dentro del módulo `src/gen/tac_generator.py`.

### Clases y estructuras involucradas

| Archivo                       | Función                                                                                                  |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| `src/gen/tac.py`              | Define la estructura `Quad` y la clase `TAC`, encargadas de almacenar las instrucciones.                 |
| `src/gen/tac_generator.py`    | Implementa el visitor `TACGenerator`, que recorre el árbol sintáctico y emite TAC según el tipo de nodo. |
| `src/codegen/temp_manager.py` | Gestiona los temporales (`t0`, `t1`, `t2`, ...) mediante asignación y reciclaje.                         |

### Ejemplo de generación TAC

Código fuente en `program.cps`:

```cps
let a: integer = 3;
let b: integer = 5;

if (a < b) {
  print(a);
} else {
  print(b);
}
```

Salida generada (`program.tac`):

```
(mov, 3, _, a)
(mov, 5, _, b)
(<, a, b, t0)
(ifz, t0, L0, _)
(param, a, _, _)
(call, print, 1, _)
(goto, L1, _, _)
(label, L0, _, _)
(param, b, _, _)
(call, print, 1, _)
(label, L1, _, _)
```

### Cómo funciona el generador TAC

1. El visitor `TACGenerator` recorre el árbol generado por ANTLR.
2. Cada expresión o instrucción emite cuádruplos según su operación.
3. Los valores temporales (`tN`) son administrados por `TempManager`.
4. Se crean etiquetas (`L0`, `L1`, `L2`) para los saltos condicionales y ciclos.
5. Al finalizar, el objeto `TAC` se imprime o se guarda en un archivo `.tac`.

### Instrucciones TAC soportadas

* **Asignación / Movimiento**

  ```
  (mov, src, _, dst)
  ```
* **Aritméticas y relacionales**

  ```
  +, -, *, /, %, <, >, <=, >=, ==, !=
  ```
* **Print / Llamadas**

  ```
  (param, valor, _, _)
  (call, print, 1, _)
  ```
* **Condicionales**

  ```
  (ifz, cond, L_else, _)
  (goto, L_end, _, _)
  (label, L_else, _, _)
  ```
* **Bucles**

  ```
  (label, L_start, _, _)
  (ifz, cond, L_end, _)
  ...
  (goto, L_start, _, _)
  (label, L_end, _, _)
  ```
* **Return**

  ```
  (ret, valor, _, _)
  ```

### Ejecución del generador TAC

Para generar el TAC desde la terminal:

```bash
python -m src.run program.cps --tac
```

Salida esperada:

```
Semantic analysis completed successfully.
TAC written to: program.tac
```

El archivo `program.tac` se crea en la misma carpeta que el fuente.

También puede ejecutarse desde el IDE, donde se mostrará directamente el TAC generado.

## 7) Pruebas unitarias

Puedes ejecutar los tests definidos para validación semántica y generación de código intermedio:

```bash
pytest -q
```

Esto corre los casos básicos de prueba y reporta errores si alguno falla.

## 8) Estructura del proyecto

```
src/
│
├── codegen/                # Generación de TAC y temporales
│   ├── __init__.py
│   └── temp_manager.py     # Gestor de temporales con free-list
│
├── gen/                    # Archivos generados por ANTLR
│   ├── CompiscriptLexer.py
│   ├── CompiscriptParser.py
│   ├── CompiscriptVisitor.py
│   ├── tac.py              # Definición de cuádruplos
│   └── tac_generator.py    # Generador de código intermedio
│
├── semantic/               # Análisis semántico
│   ├── analyzer.py         # Visitor de análisis semántico
│   ├── errors.py           # Manejo de errores semánticos
│   ├── symbols.py          # Tabla de símbolos extendida
│   └── types.py            # Sistema de tipos
│
├── parse_utils.py          # Funciones de parsing (archivo o string)
└── run.py                  # Punto de entrada CLI

docs/
├── tac_spec.md             # Especificación de TAC (cuádruplos)
├── architecture.md         # Arquitectura del compilador
└── todo_notes.md           # Notas de implementación

tests/
├── test_semantic.py        # Tests unitarios semánticos
├── ok_*.cps                # Casos válidos
└── fail_*.cps              # Casos con errores

ide.py                       # IDE web (Streamlit)
Driver.py                    # Script de pruebas rápidas
Compiscript.g4               # Gramática ANTLR
program.cps                  # Programa de prueba
```

## 9) Documentación adicional

- **[Especificación TAC](docs/tac_spec.md)** — Formato de cuádruplos, operaciones, ejemplos
- **[Arquitectura](docs/architecture.md)** — Diseño del compilador, flujo de datos, decisiones
- **[Requerimientos TAC](README_TAC_GENERATION.md)** — Objetivos de la fase 2 del proyecto
