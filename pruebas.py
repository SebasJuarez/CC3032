from src.parse_utils import parse_string
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport
p = parse_string("let x: integer = 5; x = 7;")
tree = p.program()
errs = SemanticErrorReport()
SemanticAnalyzer(errs).visit(tree)
print("OK" if not errs.has_errors() else errs.errors)
