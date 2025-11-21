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

# -------------------------------------------------------------------
# Función auxiliar para obtener el número de errores sintácticos del parser.
# Se hace compatible con diferentes versiones del runtime de ANTLR.
# -------------------------------------------------------------------
def get_syntax_errors(parser: Parser) -> int:
    try:
        if hasattr(parser, "getNumberOfSyntaxErrors"):
            return int(parser.getNumberOfSyntaxErrors())
    except Exception:
        pass
    try:
        return int(getattr(parser, "_syntaxErrors", 0))
    except Exception:
        return 0

# -------------------------------------------------------------------
# Ejecuta el proceso completo de compilación:
# 1. Analiza el código fuente con ANTLR.
# 2. Ejecuta el análisis semántico.
# 3. Retorna un diccionario con los resultados (errores, árbol, etc.).
# -------------------------------------------------------------------
def compile_source(source: str, analyzer: SemanticAnalyzer):
    parser = parse_string(source)
    tree = parser.program()

    syn_errs = get_syntax_errors(parser)
    if syn_errs:
        return {
            "syntax_errors": syn_errs,
            "semantic_errors": [],
            "ok": False,
            "parse_tree": tree.toStringTree(recog=parser) if hasattr(tree, "toStringTree") else "(parse tree unavailable)",
        }

    errors = SemanticErrorReport()
    analyzer.errors = errors
    analyzer.visit(tree)

    return {
        "syntax_errors": 0,
        "semantic_errors": list(errors.errors),
        "ok": not errors.has_errors(),
        "parse_tree": tree.toStringTree(recog=parser) if hasattr(tree, "toStringTree") else "(parse tree unavailable)",
        "parse_tree_obj": tree,
        "parser_obj": parser,
    }

# -------------------------------------------------------------------
# Genera una representación textual de la tabla de símbolos.
# Si el analizador tiene un método dump(), lo usa directamente.
# Si no, crea una salida básica con los símbolos actuales.
# -------------------------------------------------------------------
def symtab_text(analyzer: SemanticAnalyzer) -> str:
    """
    Devuelve la tabla de símbolos con formato tabular.
    Si SymbolTable.dump() existe, lo usa; de lo contrario,
    genera una tabla legible con nombres, tipos y alcances.
    """
    stab = analyzer.symtab

    # Si existe un método dump() definido, se usa directamente.
    if hasattr(stab, "dump"):
        try:
            return stab.dump()
        except Exception:
            pass

    # Fallback manual si no hay dump() implementado.
    lines = []
    header = f"{'Nombre':<15} | {'Tipo':<15} | {'Ámbito':<10}"
    sep = "-" * len(header)
    lines.append("[Tabla de Símbolos]")
    lines.append(sep)
    lines.append(header)
    lines.append(sep)

    # Recorre los símbolos del scope actual si existen.
    if hasattr(stab, "current") and hasattr(stab.current, "symbols"):
        for name, sym in stab.current.symbols.items():
            typ = getattr(sym, "typ", "—")
            scope = getattr(sym, "scope", None)
            scope_name = getattr(scope, "name", "global")
            lines.append(f"{name:<15} | {str(typ):<15} | {scope_name:<10}")
    else:
        lines.append("(No hay símbolos registrados)")

    lines.append(sep)
    return "\n".join(lines)

# -------------------------------------------------------------------
# Carga el archivo por defecto (program.cps) o genera una plantilla inicial.
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# Inicialización del estado de la aplicación (variables persistentes).
# -------------------------------------------------------------------
if "analyzer" not in st.session_state:
    st.session_state.analyzer = SemanticAnalyzer(errors=SemanticErrorReport())

if "code" not in st.session_state:
    st.session_state.code = load_default_code()

st.session_state.setdefault("parse_tree_obj", None)
st.session_state.setdefault("last_compile", None)
st.session_state.setdefault("tac_text", "")
st.session_state.setdefault("tac_error", "")
st.session_state.setdefault("tac_rows", [])
st.session_state.setdefault("tac_table_md", "")
st.session_state.setdefault("tac_csv", "")
st.session_state.setdefault("mips_text", "")
st.session_state.setdefault("mips_error", "")

# -------------------------------------------------------------------
# Panel lateral (sidebar) con acciones del usuario.
# Permite reiniciar el entorno, cargar o descargar código fuente.
# -------------------------------------------------------------------
st.sidebar.title("Acciones")

preserve_env = st.sidebar.checkbox(
    "Preservar símbolos entre compilaciones",
    value=False,
    help="Si está desmarcado, cada compilación crea un entorno limpio."
)

if st.sidebar.button("Resetear entorno (símbolos)"):
    st.session_state.analyzer = SemanticAnalyzer(errors=SemanticErrorReport())
    st.session_state.parse_tree_obj = None
    st.session_state.tac_text = ""
    st.session_state.tac_error = ""
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

# -------------------------------------------------------------------
# Interfaz principal del IDE: editor y panel de compilación.
# -------------------------------------------------------------------
st.title(PAGE_TITLE)
col_editor, col_actions = st.columns([2, 1], gap="large")

# ---------------- Editor de código ----------------
with col_editor:
    st.subheader("Editor")
    st.session_state.code = st.text_area(
        "Código fuente",
        value=st.session_state.code,
        height=380,
        label_visibility="collapsed",
        placeholder="// Escribe tu Compiscript aquí…",
    )

# ---------------- Panel de compilación ----------------
with col_actions:
    st.subheader("Compilación")
    do_compile = st.button("Compilar", type="primary")

    if do_compile:
        st.session_state.tac_text = ""
        st.session_state.tac_error = ""
        st.session_state.mips_text = ""
        st.session_state.mips_error = ""

        if not preserve_env:
            st.session_state.analyzer = SemanticAnalyzer(errors=SemanticErrorReport())

        result = compile_source(st.session_state.code, st.session_state.analyzer)
        st.session_state.last_compile = result
        st.session_state.parse_tree_obj = result.get("parse_tree_obj") if result.get("ok") else None

        # Muestra los errores o el resultado del análisis
        if result["syntax_errors"]:
            st.error(f"{result['syntax_errors']} errores de sintaxis.")
        elif not result["ok"]:
            st.error("Errores semánticos encontrados:")
            for e in result["semantic_errors"]:
                st.write(f"- {e}")
        else:
            st.success("Análisis semántico completado con éxito.")

            # Generación del TAC si no hay errores
            try:
                from src.gen.tac_generator import generate_tac_text, generate_tac_from_parser
                from src.codegen.mips.generator import generate_mips_from_tac
                # Texto de TAC (cuádruplos en paréntesis)
                tac_text = generate_tac_text(st.session_state.parse_tree_obj, analyzer=st.session_state.analyzer)
                st.session_state.tac_text = tac_text
                # Objeto TAC para tabla
                tac_obj = generate_tac_from_parser(st.session_state.parse_tree_obj, analyzer=st.session_state.analyzer)
                rows = []
                for q in getattr(tac_obj, 'quads', []):
                    # Cada fila como dict para la tabla/csv
                    rows.append({
                        'op': getattr(q, 'op', ''),
                        'arg1': getattr(q, 'arg1', '') or '',
                        'arg2': getattr(q, 'arg2', '') or '',
                        'res': getattr(q, 'res', '') or '',
                    })
                st.session_state.tac_rows = rows
                # Markdown table (sin depender de pandas)
                md_lines = ["| op | arg1 | arg2 | res |", "|---|---|---|---|"]
                for r in rows:
                    md_lines.append(f"| {r['op']} | {r['arg1']} | {r['arg2']} | {r['res']} |")
                st.session_state.tac_table_md = "\n".join(md_lines)
                # CSV para descarga
                csv_lines = ["op,arg1,arg2,res"]
                def esc(x: str) -> str:
                    x = str(x)
                    return '"' + x.replace('"', '""') + '"' if (',' in x or '"' in x or '\n' in x) else x
                for r in rows:
                    csv_lines.append(
                        f"{esc(r['op'])},{esc(r['arg1'])},{esc(r['arg2'])},{esc(r['res'])}"
                    )
                st.session_state.tac_csv = "\n".join(csv_lines)
                # Generar MIPS ensamblador
                try:
                    mips_code = generate_mips_from_tac(tac_obj)
                    st.session_state.mips_text = mips_code
                except Exception as em:
                    st.session_state.mips_error = f"No se pudo generar MIPS: {em}"
            except Exception as e:
                st.session_state.tac_error = f"No se pudo generar TAC: {e}"

        # Árbol de parseo y tabla de símbolos
        with st.expander("Árbol de parseo (toStringTree)", expanded=False):
            st.code(result["parse_tree"])

        table_text = symtab_text(st.session_state.analyzer)
        with st.expander("Tabla de símbolos", expanded=True):
            st.code(table_text)
            st.download_button("Descargar tabla de símbolos", data=table_text, file_name="symbols.txt")

# -------------------------------------------------------------------
# Sección inferior: vista del código intermedio TAC generado.
# -------------------------------------------------------------------
st.markdown("---")
st.subheader("Código intermedio (TAC)")

if st.session_state.tac_error:
    st.error(st.session_state.tac_error)

tab_table, tab_text = st.tabs(["Tabla", "Texto"])

with tab_table:
    if st.session_state.tac_rows:
        st.markdown(st.session_state.tac_table_md)
        st.download_button(
            "Descargar TAC (CSV)",
            data=st.session_state.tac_csv,
            file_name="program_tac.csv",
            mime="text/csv",
        )
    else:
        st.info("Compila sin errores para ver la tabla de TAC…")

with tab_text:
    # Editor de TAC (solo lectura por defecto)
    st.session_state.tac_text = st.text_area(
        "TAC",
        value=st.session_state.tac_text,
        height=260,
        label_visibility="collapsed",
        placeholder="Compila sin errores para generar el TAC…",
        disabled=True,
    )

st.markdown("---")
st.subheader("Código ensamblador MIPS")

if st.session_state.mips_error:
    st.error(st.session_state.mips_error)

mips_col_view, mips_col_dl = st.columns([3,1])
with mips_col_view:
    st.session_state.mips_text = st.text_area(
        "MIPS",
        value=st.session_state.mips_text,
        height=300,
        label_visibility="collapsed",
        placeholder="Compila para ver el ensamblador MIPS…",
        disabled=True,
    )
with mips_col_dl:
    if st.session_state.mips_text:
        st.download_button(
            "Descargar .s",
            data=st.session_state.mips_text,
            file_name="program.s",
            mime="text/plain",
        )

# -------------------------------------------------------------------
# Acciones sobre el TAC: descarga o regeneración manual.
# -------------------------------------------------------------------
col_tac_dl, col_tac_regen = st.columns([1, 1])

with col_tac_dl:
    if st.session_state.tac_text:
        st.download_button(
            "Descargar TAC",
            data=st.session_state.tac_text,
            file_name="program.tac",
            mime="text/plain",
        )

with col_tac_regen:
    if st.session_state.parse_tree_obj is not None:
        if st.button("Regenerar TAC"):
            try:
                from src.gen.tac_generator import generate_tac_text, generate_tac_from_parser
                from src.codegen.mips.generator import generate_mips_from_tac
                st.session_state.tac_text = generate_tac_text(st.session_state.parse_tree_obj, analyzer=st.session_state.analyzer)
                tac_obj = generate_tac_from_parser(st.session_state.parse_tree_obj, analyzer=st.session_state.analyzer)
                rows = []
                for q in getattr(tac_obj, 'quads', []):
                    rows.append({
                        'op': getattr(q, 'op', ''),
                        'arg1': getattr(q, 'arg1', '') or '',
                        'arg2': getattr(q, 'arg2', '') or '',
                        'res': getattr(q, 'res', '') or '',
                    })
                st.session_state.tac_rows = rows
                md_lines = ["| op | arg1 | arg2 | res |", "|---|---|---|---|"]
                for r in rows:
                    md_lines.append(f"| {r['op']} | {r['arg1']} | {r['arg2']} | {r['res']} |")
                st.session_state.tac_table_md = "\n".join(md_lines)
                csv_lines = ["op,arg1,arg2,res"]
                def esc(x: str) -> str:
                    x = str(x)
                    return '"' + x.replace('"', '""') + '"' if (',' in x or '"' in x or '\n' in x) else x
                for r in rows:
                    csv_lines.append(
                        f"{esc(r['op'])},{esc(r['arg1'])},{esc(r['arg2'])},{esc(r['res'])}"
                    )
                st.session_state.tac_csv = "\n".join(csv_lines)
                st.session_state.tac_error = ""
                # Regenerar MIPS también
                try:
                    mips_code = generate_mips_from_tac(tac_obj)
                    st.session_state.mips_text = mips_code
                    st.session_state.mips_error = ""
                except Exception as em:
                    st.session_state.mips_error = f"No se pudo regenerar MIPS: {em}"
            except Exception as e:
                st.session_state.tac_error = f"No se pudo generar TAC: {e}"
                st.error(st.session_state.tac_error)
