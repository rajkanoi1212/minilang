"""
Basic tests for MiniLang. Run with: python -m pytest tests/ -v
(or python tests/test_interpreter.py to run without pytest)
"""

import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minilang.lexer import Lexer
from minilang.parser import Parser
from minilang.interpreter import Interpreter, MiniLangError


def run(source: str) -> str:
    """Run MiniLang source and return whatever it printed, as a string."""
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    interpreter = Interpreter()

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        interpreter.run(program)
    finally:
        sys.stdout = old_stdout
    return captured.getvalue()


def test_arithmetic():
    assert run("print 2 + 3 * 4;") == "14\n"
    assert run("print (2 + 3) * 4;") == "20\n"
    assert run("print 7 % 3;") == "1\n"


def test_variables_and_assignment():
    assert run("let x = 5; x = x + 1; print x;") == "6\n"


def test_string_concat():
    assert run('print "a" + "b" + "c";') == "abc\n"
    assert run('print "n=" + str(42);') == "n=42\n"


def test_if_else():
    assert run("if (1 < 2) { print \"yes\"; } else { print \"no\"; }") == "yes\n"
    assert run("if (1 > 2) { print \"yes\"; } else { print \"no\"; }") == "no\n"


def test_while_loop():
    src = "let i = 0; while (i < 3) { print i; i = i + 1; }"
    assert run(src) == "0\n1\n2\n"


def test_functions_and_recursion():
    src = """
    fn fact(n) {
        if (n <= 1) { return 1; }
        return n * fact(n - 1);
    }
    print fact(5);
    """
    assert run(src) == "120\n"


def test_logical_operators():
    assert run("print true and false;") == "false\n"
    assert run("print true or false;") == "true\n"
    assert run("print not true;") == "false\n"


def test_undefined_variable_raises():
    try:
        run("print x;")
        assert False, "expected MiniLangError"
    except MiniLangError:
        pass


def test_division_by_zero_raises():
    try:
        run("print 1 / 0;")
        assert False, "expected MiniLangError"
    except MiniLangError:
        pass


def test_closures():
    src = """
    fn make_adder(n) {
        fn add(x) {
            return x + n;
        }
        return add(10);
    }
    print make_adder(5);
    """
    assert run(src) == "15\n"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
