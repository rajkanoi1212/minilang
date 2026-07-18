#!/usr/bin/env python3
"""
MiniLang CLI.

Usage:
    python main.py script.ml     # run a script file
    python main.py               # start an interactive REPL
"""

import sys

from minilang.lexer import Lexer, LexError
from minilang.parser import Parser, ParseError
from minilang.interpreter import Interpreter, MiniLangError


def run_source(source: str, interpreter: Interpreter):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    interpreter.run(program)


def run_file(path: str):
    with open(path, "r") as f:
        source = f.read()
    interpreter = Interpreter()
    try:
        run_source(source, interpreter)
    except (LexError, ParseError, MiniLangError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def repl():
    print("MiniLang REPL — type 'exit' to quit")
    interpreter = Interpreter()
    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip() in ("exit", "quit"):
            break
        if not line.strip():
            continue
        # Allow bare expressions without a trailing ';' for convenience.
        if not line.strip().endswith((";", "}")):
            line += ";"
        try:
            run_source(line, interpreter)
        except (LexError, ParseError, MiniLangError) as e:
            print(f"Error: {e}")


def main():
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()


if __name__ == "__main__":
    main()
