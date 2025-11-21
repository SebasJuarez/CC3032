import sys
from pathlib import Path
from antlr4 import FileStream, CommonTokenStream
from src.parse_utils import make_parser
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport
from src.gen.tac_generator import generate_tac_from_parser
from src.codegen.mips.generator import generate_mips_from_tac

def main(argv):
    if len(argv) < 2:
        print("Usage: python -m src.run <source.cps> [--tac] [--mips]")
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
        # Generación TAC
        tac = None
        if "--tac" in argv or "--mips" in argv:
            try:
                tac = generate_tac_from_parser(tree)
                if "--tac" in argv:
                    tac_out = Path(source_path).with_suffix('.tac')
                    tac_out.write_text(str(tac), encoding='utf-8')
                    print(f"TAC written to: {tac_out}")
            except Exception as e:
                print(f"Failed to generate TAC: {e}")
        # Generación MIPS (requiere TAC)
        if "--mips" in argv:
            if tac is None:
                print("MIPS generation skipped: TAC unavailable.")
            else:
                try:
                    asm = generate_mips_from_tac(tac)
                    mips_out = Path(source_path).with_suffix('.s')
                    mips_out.write_text(asm, encoding='utf-8')
                    print(f"MIPS written to: {mips_out}")
                except Exception as e:
                    print(f"Failed to generate MIPS: {e}")

if __name__ == "__main__":
    main(sys.argv)
