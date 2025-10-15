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
        # Optionally generate TAC if requested via argv
        if "--tac" in argv:
            try:
                from src.gen.tac_generator import generate_tac_from_parser
                from pathlib import Path
                tac = generate_tac_from_parser(tree)
                out = Path(source_path).with_suffix('.tac')
                out.write_text(str(tac), encoding='utf-8')
                print(f"TAC written to: {out}")
            except Exception as e:
                print(f"Failed to generate TAC: {e}")

if __name__ == "__main__":
    main(sys.argv)
