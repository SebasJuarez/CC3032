import sys
from pathlib import Path
from antlr4 import FileStream, CommonTokenStream
from src.parse_utils import make_parser
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport

def main(argv):
    if len(argv) < 2:
        print("Usage: python -m src.run <source.cps>")
        sys.exit(1)

    source_path = Path(argv[1])
    if not source_path.exists():
        print(f"Source file not found: {source_path}")
        sys.exit(1)

    parser = make_parser(str(source_path))
    tree = parser.program()

    errors = SemanticErrorReport()
    analyzer = SemanticAnalyzer(errors=errors)
    analyzer.visit(tree)

    if errors.has_errors():
        print("Semantic errors found:")
        for e in errors.errors:
            print(f"- {e}")
        sys.exit(2)
    else:
        print("Semantic analysis completed successfully.")

if __name__ == "__main__":
    main(sys.argv)
