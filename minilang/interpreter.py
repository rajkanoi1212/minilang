"""
Tree-walking interpreter for MiniLang.

Given an AST (see ast_nodes.py), walks it and evaluates it directly —
no bytecode or VM, just recursive evaluation of the tree. This is the
simplest interpreter design and the one most textbooks (e.g. "Crafting
Interpreters") start with.
"""

from . import ast_nodes as ast


class MiniLangError(Exception):
    """Runtime error in a MiniLang program."""


class ReturnSignal(Exception):
    """Used internally to unwind the call stack on `return`."""
    def __init__(self, value):
        self.value = value


class Environment:
    """A single lexical scope, chained to its parent for variable lookup."""

    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def define(self, name, value):
        self.vars[name] = value

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise MiniLangError(f"Undefined variable '{name}'")

    def assign(self, name, value):
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise MiniLangError(f"Cannot assign to undefined variable '{name}'")


class Function:
    """A user-defined MiniLang function, closing over the scope it was declared in."""

    def __init__(self, decl: ast.FnDecl, closure: Environment):
        self.decl = decl
        self.closure = closure

    def call(self, interpreter, args):
        if len(args) != len(self.decl.params):
            raise MiniLangError(
                f"Function '{self.decl.name}' expects {len(self.decl.params)} "
                f"argument(s), got {len(args)}"
            )
        scope = Environment(parent=self.closure)
        for param, value in zip(self.decl.params, args):
            scope.define(param, value)
        try:
            interpreter.exec_block(self.decl.body, scope)
        except ReturnSignal as r:
            return r.value
        return None


class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self._install_builtins()

    def _install_builtins(self):
        # Builtins are plain Python callables stored like any other value;
        # `call_value` below knows how to invoke either kind.
        self.globals.define("len", lambda args: _builtin_len(args))
        self.globals.define("str", lambda args: _stringify(args[0]))

    # --- public API ---

    def run(self, program: ast.Block):
        self.exec_block(program, self.globals)

    # --- statement execution ---

    def exec_block(self, block: ast.Block, scope: Environment):
        for stmt in block.statements:
            self.exec_stmt(stmt, scope)

    def exec_stmt(self, stmt, scope: Environment):
        method = "stmt_" + type(stmt).__name__
        getattr(self, method)(stmt, scope)

    def stmt_LetStmt(self, stmt: ast.LetStmt, scope):
        scope.define(stmt.name, self.eval(stmt.value, scope))

    def stmt_PrintStmt(self, stmt: ast.PrintStmt, scope):
        print(_stringify(self.eval(stmt.value, scope)))

    def stmt_ExprStmt(self, stmt: ast.ExprStmt, scope):
        self.eval(stmt.expr, scope)

    def stmt_Block(self, stmt: ast.Block, scope):
        inner = Environment(parent=scope)
        self.exec_block(stmt, inner)

    def stmt_IfStmt(self, stmt: ast.IfStmt, scope):
        if _truthy(self.eval(stmt.condition, scope)):
            self.exec_stmt(stmt.then_branch, scope)
        elif stmt.else_branch is not None:
            self.exec_stmt(stmt.else_branch, scope)

    def stmt_WhileStmt(self, stmt: ast.WhileStmt, scope):
        while _truthy(self.eval(stmt.condition, scope)):
            self.exec_stmt(stmt.body, scope)

    def stmt_FnDecl(self, stmt: ast.FnDecl, scope):
        scope.define(stmt.name, Function(stmt, scope))

    def stmt_ReturnStmt(self, stmt: ast.ReturnStmt, scope):
        value = self.eval(stmt.value, scope) if stmt.value is not None else None
        raise ReturnSignal(value)

    # --- expression evaluation ---

    def eval(self, node, scope: Environment):
        method = "eval_" + type(node).__name__
        return getattr(self, method)(node, scope)

    def eval_NumberLit(self, node, scope):
        return node.value

    def eval_StringLit(self, node, scope):
        return node.value

    def eval_BoolLit(self, node, scope):
        return node.value

    def eval_NilLit(self, node, scope):
        return None

    def eval_Identifier(self, node, scope):
        return scope.get(node.name)

    def eval_Assign(self, node, scope):
        value = self.eval(node.value, scope)
        scope.assign(node.name, value)
        return value

    def eval_UnaryOp(self, node, scope):
        val = self.eval(node.operand, scope)
        if node.op == "-":
            _check_number(val, "-")
            return -val
        if node.op == "not":
            return not _truthy(val)
        raise MiniLangError(f"Unknown unary operator '{node.op}'")

    def eval_BinaryOp(self, node, scope):
        if node.op == "and":
            left = self.eval(node.left, scope)
            return self.eval(node.right, scope) if _truthy(left) else left
        if node.op == "or":
            left = self.eval(node.left, scope)
            return left if _truthy(left) else self.eval(node.right, scope)

        left = self.eval(node.left, scope)
        right = self.eval(node.right, scope)
        op = node.op

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return _stringify(left) + _stringify(right)
            _check_number(left, op); _check_number(right, op)
            return left + right
        if op == "-":
            _check_number(left, op); _check_number(right, op)
            return left - right
        if op == "*":
            _check_number(left, op); _check_number(right, op)
            return left * right
        if op == "/":
            _check_number(left, op); _check_number(right, op)
            if right == 0:
                raise MiniLangError("Division by zero")
            return left / right
        if op == "%":
            _check_number(left, op); _check_number(right, op)
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right

        raise MiniLangError(f"Unknown binary operator '{op}'")

    def eval_Call(self, node: ast.Call, scope: Environment):
        callee = scope.get(node.callee)
        args = [self.eval(a, scope) for a in node.args]
        if isinstance(callee, Function):
            return callee.call(self, args)
        if callable(callee):
            return callee(args)
        raise MiniLangError(f"'{node.callee}' is not callable")


# --- helpers ---

def _truthy(value):
    if value is None or value is False:
        return False
    return True


def _check_number(value, op):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise MiniLangError(f"Operator '{op}' requires a number, got {_stringify(value)}")


def _stringify(value):
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _builtin_len(args):
    if len(args) != 1 or not isinstance(args[0], str):
        raise MiniLangError("len() expects a single string argument")
    return float(len(args[0]))
