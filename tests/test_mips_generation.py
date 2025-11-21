import re
from src.parse_utils import parse_string
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport
from src.gen.tac_generator import generate_tac_from_parser
from src.codegen.mips.generator import generate_mips_from_tac


def compile_to_mips(source: str) -> str:
    parser = parse_string(source)
    tree = parser.program()
    errors = SemanticErrorReport()
    analyzer = SemanticAnalyzer(errors=errors)
    analyzer.visit(tree)
    assert not errors.has_errors(), f"Semantic errors: {errors.errors}"
    tac = generate_tac_from_parser(tree, analyzer=analyzer)
    asm = generate_mips_from_tac(tac)
    return asm


def test_basic_arithmetic():
    src = """
    let x: integer = 5;
    let y: integer = 2;
    let z: integer = x + y;
    print(z);
    """
    asm = compile_to_mips(src)
    assert 'add' in asm, "Debe existir instrucción add"
    assert re.search(r'jal\s+__print_int', asm), "Debe llamar a rutina de impresión"


def test_branch_generation():
    src = """
    let a: integer = 1;
    let b: integer = 2;
    if (a < b) { a = b; }
    """
    asm = compile_to_mips(src)
    # Esperamos etiqueta L y un beq cond,$zero,L...
    assert 'beq' in asm, "Debe generarse beq para ifz"
    assert re.search(r'L\d+:', asm), "Debe existir al menos una etiqueta L*"


def test_comparisons():
    src = """
    let a: integer = 1;
    let b: integer = 2;
    let c: boolean = a < b;
    let d: boolean = a > b;
    let e: boolean = a <= b;
    let f: boolean = a >= b;
    let g: boolean = a == b;
    let h: boolean = a != b;
    """
    asm = compile_to_mips(src)
    # Verificar patrones clave
    assert 'slt ' in asm, 'Debe usar slt para <'
    assert re.search(r'slt\s+\$\w+, \$\w+, \$\w+', asm), 'Formato slt esperado'
    # gt usa slt con argumentos invertidos
    assert re.search(r'slt\s+\$\w+, \$\w+, \$\w+', asm), 'slts para gt'
    # le/ge usan xori y slt
    assert 'xori' in asm, 'Debe usar xori para invertir'
    # eq usa xor + sltiu
    assert 'xor' in asm and 'sltiu' in asm, 'Debe usar xor+sltiu para eq'
    # ne usa xor + sltu
    assert 'sltu' in asm, 'Debe usar sltu para ne'


def test_ret_instruction():
    # El retorno en esta etapa salta a end_main
    src = """
    let a: integer = 3;
    print(a);
    """
    asm = compile_to_mips(src)
    assert 'end_main:' in asm, "Debe existir etiqueta end_main"
    assert 'li\t$v0, 10' in asm, "Debe existir syscall de salida"

if __name__ == '__main__':
    test_basic_arithmetic()
    test_branch_generation()
    test_ret_instruction()
    print('MIPS generation smoke tests passed.')
