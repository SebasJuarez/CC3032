
# Análisis de la Gramática ANTLR y Archivo de Driver
### Sebastian Juarez 21471
### Link al video: https://youtu.be/nOuFOG81E50

Este Laboratorio se hizo utilizando los recursos proporcionados por el catedratico como una base de las pruebas. Estos fueron realmente utiles ya que nos dieron a entender de una manera sencilla el proceso de creacion y manejo de ANTLR

##  Archivo de Gramática: `MiniLang.g4`

En este archivo se define la gramatica del lenguaje y este se llama MiniLang. Este archivo esta hecho usando ANTLR. En este caso la extensión .g4 es usada en ANTLR para definir gramaticas que luego generan el lexer y el parser, siendo este como su metodo predefinido.

Un archivo .g4 tiene típicamente dos secciones principales:

1. **Gramática léxica:** Se definen cómo se ven los símbolos del lenguaje. Estos son los tokens.
2. **Gramática sintáctica:** Se definen cómo se combinan esos símbolos para que tengan sentido y sean formas validas del lenguaje. Estas son las reglas.

###  Elementos del archivo .g4

- **Regla inicial:**  
  ```antlr
  prog: stat+ ;
  ```
  Esta regla es el inicio del parser y esto significa que todo el analisis empieza desde acá. stat+ nos dice que el programa consiste en una o más instrucciones (stat).

- **Reglas para expresiones e instrucciones:**
  ```antlr
  stat: expr NEWLINE
      | ID '=' expr NEWLINE ;
  expr: expr op=('*'|'/') expr
      | expr op=('+'|'-') expr
      | INT
      | ID
      | '(' expr ')' ;
  ```
  - stat permite tanto expresiones simples como asignaciones.
  - expr permite operaciones basicas, paréntesis, variables y números enteros.

- **Tokens léxicos:**
  ```antlr
  ID: [a-zA-Z]+ ;
  INT: [0-9]+ ;
  NEWLINE: [\r\n]+ ;
  WS: [ \t]+ -> skip ;
  ```
  - ID define identificadores formados por letras.
  - INT define números enteros.
  - NEWLINE detecta líneas nuevas.
  - WS ignora espacios en blanco y tabulaciones.

- **Comentarios útiles:**
  Se pueden usar comentarios como "//" en ANTLR para documentar partes de la gramática.

---

##  Archivo de Driver: `Driver.py`

Este arcihvo se encarga de ejecutar el parser que se genera usanndo ANTLR y se procesa con un archivo de entrada, en este caso el `program_test.txt`.

###  Descripción de las partes:

```python
from antlr4 import *
from MiniLangLexer import MiniLangLexer
from MiniLangParser import MiniLangParser
```
Importa las clases generadas automáticamente por ANTLR usando MiniLang.g4.

```python
input_stream = FileStream(argv[1])
```
Lee el archivo de entrada.

```python
lexer = MiniLangLexer(input_stream)
```
Inicializa el analizador léxico.

```python
stream = CommonTokenStream(lexer)
parser = MiniLangParser(stream)
```
Transforma los tokens del lexer en una secuencia que el parser pueda lograr entender.

```python
tree = parser.prog()
```
Inicia el análisis desde la regla prog.

---

## Pruebas

Se realizaron diferentes pruebas para explorar como es que reacciona este analizador a diferentes combinaciones correctas e incorrectas. 

Un cao correcto seria algo como:
```
a = 4
b = 6
c = a + b
```
Donde se espera que no se genere ningun mensaje al ejecutar.

También hay casos donde no compila por errores léxicos o sintácticos

```
x = 3
y = x @ 2
```
o 
```
a = 1 +
b = 2
```
