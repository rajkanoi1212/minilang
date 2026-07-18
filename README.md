# MiniLang

A tree-walking interpreter for a small dynamically-typed language, built from
scratch in Python — no parser generator, no external libraries. Every stage
of the pipeline (lexer → parser → interpreter) is hand-written.

```
let x = 10;
let y = 3;
print x + y;          # 13

fn fib(n) {
    if (n < 2) { return n; }
    return fib(n - 1) + fib(n - 2);
}
print fib(10);         # 55
```

## Why this project

Most CRUD/ML projects call libraries; this one builds the thing libraries are
usually built on top of. It's a hands-on way to demonstrate how source code
actually becomes a running program — tokenization, grammar, scoping, and
recursive evaluation.

## Features

- Variables (`let`), assignment, and lexical scoping
- Arithmetic (`+ - * / %`), comparison, and logical operators (`and` `or` `not`)
- Control flow: `if` / `else`, `while`
- Functions with parameters, `return`, recursion, and closures
- Strings, numbers, booleans, `nil`
- Comments (`# ...`)
- A REPL and a script runner

## Architecture

```
source text
    │
    ▼
  Lexer        (lexer.py)        text -> tokens
    │
    ▼
  Parser       (parser.py)       tokens -> AST  (recursive descent)
    │
    ▼
Interpreter    (interpreter.py)  AST -> result  (tree-walking evaluator)
```

- **Lexer**: hand-written scanner, no regex — walks the source character by
  character, handling numbers, strings (with escapes), identifiers,
  keywords, comments, and multi-character operators.
- **Parser**: recursive-descent parser implementing standard operator
  precedence (`or` < `and` < equality < comparison < `+ -` < `* / %` <
  unary < call < primary). Produces an AST of dataclass nodes.
- **Interpreter**: walks the AST directly. Variable scoping is implemented
  with a chain of `Environment` objects (each function call and block gets
  its own scope, linked to its parent) — this is also what makes closures
  work.

## Usage

```bash
# Run a script
python main.py examples/basics.ml

# Start a REPL
python main.py
>>> let x = 5;
>>> print x * 2;
10
```

## Browser playground

`web/index.html` is a live playground — write MiniLang code, run it, and
watch the lexer's actual token stream update as you type. No build step,
no dependencies: it's a JavaScript port of the same lexer/parser/interpreter
pipeline as the Python version, so what you see running in the browser is
the same architecture described above, not a simplified stand-in.

```bash
cd web && python3 -m http.server 8000
# then open http://localhost:8000
```

Or just double-click `web/index.html` — it works opened directly as a file too.

## Example programs

- [`examples/basics.ml`](examples/basics.ml) — variables, arithmetic, conditionals, loops
- [`examples/functions.ml`](examples/functions.ml) — functions and recursion (Fibonacci)

## Tests

```bash
python tests/test_interpreter.py
```

10 tests covering arithmetic, control flow, functions, recursion, closures,
and error handling (undefined variables, division by zero).

## Known limitations / next steps

- No arrays or dictionaries yet — only numbers, strings, booleans, `nil`
- No static type checking — errors surface at runtime
- Error messages report the line number but not a full stack trace
- Planned: array/list support, `for` loops, better error messages with
  source snippets

## License

MIT
