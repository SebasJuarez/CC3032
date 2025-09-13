import io
import pathlib
import streamlit as st
from antlr4 import Parser
from src.parse_utils import parse_string
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.errors import SemanticErrorReport

PAGE_TITLE = "Compiscript IDE"
DEFAULT_FILE = "program.cps"

st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# ---------- Helpers ----------
def get_syntax_errors(parser: Parser) -> int:
    # Compatible con diferentes runtimes de ANTLR
    try:
        if hasattr(parser, "getNumberOfSyntaxErrors"):
            return int(parser.getNumberOfSyntaxErrors())
    except Exception:
        pass
    try:
        return int(getattr(parser, "_syntaxErrors", 0))
    except Exception:
        return 0

def compile_source(source: str, analyzer: SemanticAnalyzer):
    parser = parse_string(source)
    tree = parser.program()

    # 1) Errores de sintaxis
    syn_errs = get_syntax_errors(parser)
    if syn_errs:
        return {
            "syntax_errors": syn_errs,
            "semantic_errors": [],
            "ok": False,
            "parse_tree": tree.toStringTree(recog=parser) if hasattr(tree, "toStringTree") else "(parse tree unavailable)",
        }

    # 2) Análisis semántico
    errors = SemanticErrorReport()
    analyzer.errors = errors
    analyzer.visit(tree)

    return {
        "syntax_errors": 0,
        "semantic_errors": list(errors.errors),
        "ok": not errors.has_errors(),
        "parse_tree": tree.toStringTree(recog=parser) if hasattr(tree, "toStringTree") else "(parse tree unavailable)",
    }

def symtab_text(analyzer: SemanticAnalyzer) -> str:
    stab = analyzer.symtab
    if hasattr(stab, "dump"):
        try:
            return stab.dump()
        except Exception:
            pass
    # Fallback minimalista si no hay dump()
    lines = ["[symbol table dump not available: add SymbolTable.dump() for richer output]"]
    if hasattr(stab, "current"):
        cur = stab.current
        if hasattr(cur, "symbols"):
            lines.append("Current scope:")
            for name, sym in cur.symbols.items():
                typ = getattr(sym, "typ", None)
                lines.append(f"  - {name}: {typ}")
    return "\n".join(lines)

def load_default_code() -> str:
    p = pathlib.Path(DEFAULT_FILE)
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            pass
    return """// Escribe tu Compiscript aquí…
let x: integer = 1;
print(x);
"""

# ---------- Estado ----------
if "analyzer" not in st.session_state:
    st.session_state.analyzer = SemanticAnalyzer(errors=SemanticErrorReport())

if "code" not in st.session_state:
    st.session_state.code = load_default_code()

# ---------- Sidebar ----------
st.sidebar.title("Acciones")
preserve_env = st.sidebar.checkbox(
    "Preservar símbolos entre compilaciones",
    value=False,
    help="Si está desmarcado, cada compilación crea un entorno limpio."
)

if st.sidebar.button("Resetear entorno (símbolos)"):
    st.session_state.analyzer = SemanticAnalyzer(errors=SemanticErrorReport())
    st.success("Entorno reiniciado.")

uploaded = st.sidebar.file_uploader("Abrir .cps", type=["cps"])
if uploaded is not None:
    try:
        st.session_state.code = uploaded.read().decode("utf-8")
        st.info(f"Cargado: {uploaded.name}")
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")

st.sidebar.download_button(
    "Descargar código",
    data=st.session_state.code,
    file_name="program.cps",
    mime="text/plain",
)

# ---------- Main UI ----------
st.title(PAGE_TITLE)

col_editor, col_actions = st.columns([2, 1])

with col_editor:
    st.subheader("Editor")
    st.session_state.code = st.text_area(
        "Código fuente",
        value=st.session_state.code,
        height=400,
        label_visibility="collapsed",
        placeholder="// Escribe tu Compiscript aquí…",
    )

with col_actions:
    st.subheader("Compilación")
    do_compile = st.button("Compilar", type="primary")
    if do_compile:
        if not preserve_env:
            st.session_state.analyzer = SemanticAnalyzer(errors=SemanticErrorReport())

        result = compile_source(st.session_state.code, st.session_state.analyzer)

        if result["syntax_errors"]:
            st.error(f"{result['syntax_errors']} errores de sintaxis.")
        elif not result["ok"]:
            st.error("Errores semánticos encontrados:")
            for e in result["semantic_errors"]:
                st.write(f"- {e}")
        else:
            st.success("Análisis semántico completado con éxito.")

        with st.expander("Árbol de parseo (toStringTree)", expanded=False):
            st.code(result["parse_tree"])

        table_text = symtab_text(st.session_state.analyzer)
        with st.expander("Tabla de símbolos", expanded=True):
            st.code(table_text)
            st.download_button("Descargar tabla de símbolos", data=table_text, file_name="symbols.txt")
