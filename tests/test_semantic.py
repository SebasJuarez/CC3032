import pytest
from src.parse_utils import parse_string
from src.semantic.errors import SemanticErrorReport
from src.semantic.analyzer import SemanticAnalyzer
import sys, pathlib


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def analyze(src: str):
    parser = parse_string(src)
    tree = parser.program()
    errors = SemanticErrorReport()
    SemanticAnalyzer(errors).visit(tree)
    return errors

def test_const_requires_init():
    code = """
    const PI: integer;
    """
    errs = analyze(code)
    assert errs.has_errors()

def test_var_redeclaration_same_scope():
    code = """
    let x: integer = 1;
    let x: integer = 2;
    """
    errs = analyze(code)
    assert errs.has_errors()

def test_assignment_type_mismatch():
    code = """
    let x: integer = 1;
    x = "oops";
    """
    errs = analyze(code)
    assert errs.has_errors()

def test_if_condition_must_be_boolean():
    code = """
    if (42) { print("no"); }
    """
    errs = analyze(code)
    assert errs.has_errors()

def test_return_type_mismatch():
    code = """
    function f(): integer { return; }
    """
    errs = analyze(code)
    assert errs.has_errors()
