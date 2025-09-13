from antlr4 import FileStream, CommonTokenStream, InputStream
from pathlib import Path
from src.gen.CompiscriptLexer import CompiscriptLexer
from src.gen.CompiscriptParser import CompiscriptParser

def make_parser(path: str) -> CompiscriptParser:
    input_stream = FileStream(path, encoding='utf-8')
    lexer = CompiscriptLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    return parser

def parse_string(source: str) -> CompiscriptParser:
    input_stream = InputStream(source)
    lexer = CompiscriptLexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    return parser
