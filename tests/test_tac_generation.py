"""
Tests unitarios para generación de código intermedio (TAC).
Valida que los cuádruplos se generen correctamente para diferentes construcciones del lenguaje.
"""
import pytest
from src.parse_utils import parse_string
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport
from src.gen.tac_generator import generate_tac_text


def compile_and_generate_tac(source: str) -> tuple[bool, str, list]:
    """
    Compila código fuente y genera TAC.
    Retorna: (success, tac_text, errors)
    """
    parser = parse_string(source)
    tree = parser.program()
    
    errors = SemanticErrorReport()
    analyzer = SemanticAnalyzer(errors)
    analyzer.visit(tree)
    
    if errors.has_errors():
        return False, "", list(errors.errors)
    
    tac_text = generate_tac_text(tree, analyzer=analyzer)
    return True, tac_text, []


def test_simple_assignment():
    """Test: asignación simple de variable"""
    source = """
    let x: integer = 5;
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    assert "(mov, 5, _, x)" in tac
    print(f"\n--- Simple Assignment TAC ---\n{tac}")


def test_arithmetic_expression():
    """Test: expresión aritmética con temporales"""
    source = """
    let x: integer = 5;
    let y: integer = x + 2;
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    assert "(mov, 5, _, x)" in tac
    assert "(add, x, 2, t" in tac  # temporal t0 o similar
    assert "mov, t" in tac  # mov del temporal a y
    print(f"\n--- Arithmetic Expression TAC ---\n{tac}")


def test_print_statement():
    """Test: instrucción print como param + call"""
    source = """
    let x: integer = 10;
    print(x);
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    assert "(param, x, _, _)" in tac or "(param, t" in tac
    assert "(call, print, 1, _)" in tac
    print(f"\n--- Print Statement TAC ---\n{tac}")


def test_if_statement():
    """Test: if con etiquetas y saltos"""
    source = """
    let x: integer = 5;
    let y: integer = 10;
    if (x < y) {
        x = 1;
    }
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    assert "(lt, x, y, t" in tac  # comparación
    assert "(ifz, t" in tac  # salto condicional
    assert "(label, L" in tac  # etiquetas
    assert "(goto, L" in tac  # salto incondicional
    print(f"\n--- If Statement TAC ---\n{tac}")


def test_while_loop():
    """Test: while con etiquetas de inicio y fin"""
    source = """
    let i: integer = 0;
    while (i < 10) {
        i = i + 1;
    }
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    # Debe haber label de inicio, comparación, ifz, body, goto
    tac_lines = tac.split('\n')
    label_count = sum(1 for line in tac_lines if "(label, L" in line)
    assert label_count >= 2, "While debe tener al menos 2 labels (inicio y fin)"
    assert "(lt, i, 10, t" in tac
    assert "(ifz, t" in tac
    assert "(goto, L" in tac
    print(f"\n--- While Loop TAC ---\n{tac}")


def test_complex_expression():
    """Test: expresión compleja con múltiples operadores"""
    source = """
    let result: integer = (5 + 3) * 2 - 1;
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    # Debe generar múltiples temporales para subexpresiones
    tac_lines = tac.split('\n')
    temp_count = sum(1 for line in tac_lines if ", t" in line and " -> t" not in line)
    assert temp_count >= 2, "Expresión compleja debe generar múltiples temporales"
    assert "(add, 5, 3, t" in tac or "(add, 3, 5, t" in tac
    assert "(mul, " in tac
    assert "(sub, " in tac
    print(f"\n--- Complex Expression TAC ---\n{tac}")


def test_logical_operators():
    """Test: operadores lógicos y relacionales"""
    source = """
    let a: boolean = true;
    let b: boolean = false;
    let c: boolean = a and b;
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    assert "(and, " in tac
    print(f"\n--- Logical Operators TAC ---\n{tac}")


def test_relational_operators():
    """Test: operadores relacionales"""
    source = """
    let x: integer = 5;
    let y: integer = 10;
    let result: boolean = x < y;
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    assert "(lt, x, y, t" in tac
    print(f"\n--- Relational Operators TAC ---\n{tac}")


def test_multiple_statements():
    """Test: múltiples statements en secuencia"""
    source = """
    let x: integer = 1;
    let y: integer = 2;
    let z: integer = x + y;
    print(z);
    """
    success, tac, errors = compile_and_generate_tac(source)
    
    assert success, f"Compilation failed: {errors}"
    # Verificar que se generen todas las instrucciones en orden
    assert "(mov, 1, _, x)" in tac
    assert "(mov, 2, _, y)" in tac
    assert "(add, x, y, t" in tac
    assert "(call, print, 1, _)" in tac
    print(f"\n--- Multiple Statements TAC ---\n{tac}")


if __name__ == "__main__":
    # Ejecutar tests individuales para debugging
    test_simple_assignment()
    test_arithmetic_expression()
    test_print_statement()
    test_if_statement()
    test_while_loop()
    test_complex_expression()
    test_logical_operators()
    test_relational_operators()
    test_multiple_statements()
    print("\n✅ Todos los tests de TAC pasaron!")
