# Compiscript — Semantic Analysis

Este sistema conecta el archivo de Compiscript.g3 con el program.cps usando un sistema de analizador sintactico con ANTLR en python. Este codigo, el de Compiscript.g4, fue dado a nosotros por los catedraticos.

## 1) Instalar dependencias
```bash
python -m venv .venv
source .venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Generamos el parser/lexer usando ANTLR

Se tiene que tener el comando e antlr en el path para que funcione correctamente

**Mac/Linux:**
```bash
antlr4 -Dlanguage=Python3 -visitor -o src/gen Compiscript.g4
```

**Windows (PowerShell/CMD):**
```powershell
antlr4 -Dlanguage=Python3 -visitor -o src\gen Compiscript.g4

```

Esto va a generar los archivos de CompiscriptLexer.py, CompiscriptParser.py y CompiscriptVisitor.py en src/gen.

## 3) Corremos el analizador en nuestro programa de prueba
```bash
python -m src.run program.cps
```

Se deberia ver un "Semantic analysis completed successfully." o una lista de errores.

## 4) Para correr los tests (si es que no hubo algun error)
```bash
pytest -q
```
