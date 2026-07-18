"""
Recursive-descent parser for MiniLang.

Consumes the token list produced by the Lexer and builds an AST (see
ast_nodes.py). Grammar (roughly, in precedence order from low to high):

    program     -> statement* EOF
    statement   -> letStmt | printStmt | ifStmt | whileStmt
                 | fnDecl | returnStmt | block | exprStmt
    expression  -> assignment
    assignment  -> IDENT "=" assignment | logic_or
    logic_or    -> logic_and ( "or" logic_and )*
    logic_and   -> equality ( "and" equality )*
    equality    -> comparison ( ("=="|"!=") comparison )*
    comparison  -> term ( ("<"|">"|"<="|">=") term )*
    term        -> factor ( ("+"|"-") factor )*
    factor      -> unary ( ("*"|"/"|"%") unary )*
    unary       -> ("not"|"-") unary | call
    call        -> primary ( "(" arguments? ")" )?
    primary     -> NUMBER | STRING | "true" | "false" | "nil"
                 | IDENT | "(" expression ")"
"""

from . import ast_nodes as ast
from .lexer import Token


class ParseError(Exception):
    def __init__(self, message, line):
        super().__init__(f"[line {line}] Parse error: {message}")
        self.line = line


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # --- token helpers ---

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.kind != "EOF":
            self.pos += 1
        return tok

    def check(self, kind, value=None):
        tok = self.peek()
        if tok.kind != kind:
            return False
        return value is None or tok.value == value

    def match(self, kind, value=None):
        if self.check(kind, value):
            return self.advance()
        return None

    def expect(self, kind, value=None, message=None):
        if self.check(kind, value):
            return self.advance()
        tok = self.peek()
        raise ParseError(message or f"Expected {value or kind}, got {tok.value!r}", tok.line)

    # --- entry point ---

    def parse(self):
        statements = []
        while not self.check("EOF"):
            statements.append(self.statement())
        return ast.Block(statements)

    # --- statements ---

    def statement(self):
        if self.match("KEYWORD", "let"):
            return self.let_stmt()
        if self.match("KEYWORD", "print"):
            return self.print_stmt()
        if self.match("KEYWORD", "if"):
            return self.if_stmt()
        if self.match("KEYWORD", "while"):
            return self.while_stmt()
        if self.match("KEYWORD", "fn"):
            return self.fn_decl()
        if self.match("KEYWORD", "return"):
            return self.return_stmt()
        if self.check("SYMBOL", "{"):
            return self.block()
        return self.expr_stmt()

    def let_stmt(self):
        name = self.expect("IDENT").value
        self.expect("SYMBOL", "=")
        value = self.expression()
        self.expect("SYMBOL", ";")
        return ast.LetStmt(name, value)

    def print_stmt(self):
        value = self.expression()
        self.expect("SYMBOL", ";")
        return ast.PrintStmt(value)

    def if_stmt(self):
        self.expect("SYMBOL", "(")
        condition = self.expression()
        self.expect("SYMBOL", ")")
        then_branch = self.block()
        else_branch = None
        if self.match("KEYWORD", "else"):
            else_branch = self.block()
        return ast.IfStmt(condition, then_branch, else_branch)

    def while_stmt(self):
        self.expect("SYMBOL", "(")
        condition = self.expression()
        self.expect("SYMBOL", ")")
        body = self.block()
        return ast.WhileStmt(condition, body)

    def fn_decl(self):
        name = self.expect("IDENT").value
        self.expect("SYMBOL", "(")
        params = []
        if not self.check("SYMBOL", ")"):
            params.append(self.expect("IDENT").value)
            while self.match("SYMBOL", ","):
                params.append(self.expect("IDENT").value)
        self.expect("SYMBOL", ")")
        body = self.block()
        return ast.FnDecl(name, params, body)

    def return_stmt(self):
        value = None
        if not self.check("SYMBOL", ";"):
            value = self.expression()
        self.expect("SYMBOL", ";")
        return ast.ReturnStmt(value)

    def block(self):
        self.expect("SYMBOL", "{")
        statements = []
        while not self.check("SYMBOL", "}"):
            statements.append(self.statement())
        self.expect("SYMBOL", "}")
        return ast.Block(statements)

    def expr_stmt(self):
        expr = self.expression()
        self.expect("SYMBOL", ";")
        return ast.ExprStmt(expr)

    # --- expressions (precedence climbing) ---

    def expression(self):
        return self.assignment()

    def assignment(self):
        if self.check("IDENT") and self.tokens[self.pos + 1].kind == "SYMBOL" and self.tokens[self.pos + 1].value == "=":
            name = self.advance().value
            self.advance()  # '='
            value = self.assignment()
            return ast.Assign(name, value)
        return self.logic_or()

    def logic_or(self):
        expr = self.logic_and()
        while self.match("KEYWORD", "or"):
            right = self.logic_and()
            expr = ast.BinaryOp("or", expr, right)
        return expr

    def logic_and(self):
        expr = self.equality()
        while self.match("KEYWORD", "and"):
            right = self.equality()
            expr = ast.BinaryOp("and", expr, right)
        return expr

    def equality(self):
        expr = self.comparison()
        while self.check("SYMBOL") and self.peek().value in ("==", "!="):
            op = self.advance().value
            right = self.comparison()
            expr = ast.BinaryOp(op, expr, right)
        return expr

    def comparison(self):
        expr = self.term()
        while self.check("SYMBOL") and self.peek().value in ("<", ">", "<=", ">="):
            op = self.advance().value
            right = self.term()
            expr = ast.BinaryOp(op, expr, right)
        return expr

    def term(self):
        expr = self.factor()
        while self.check("SYMBOL") and self.peek().value in ("+", "-"):
            op = self.advance().value
            right = self.factor()
            expr = ast.BinaryOp(op, expr, right)
        return expr

    def factor(self):
        expr = self.unary()
        while self.check("SYMBOL") and self.peek().value in ("*", "/", "%"):
            op = self.advance().value
            right = self.unary()
            expr = ast.BinaryOp(op, expr, right)
        return expr

    def unary(self):
        if self.match("KEYWORD", "not"):
            return ast.UnaryOp("not", self.unary())
        if self.check("SYMBOL", "-"):
            self.advance()
            return ast.UnaryOp("-", self.unary())
        return self.call()

    def call(self):
        expr = self.primary()
        if isinstance(expr, ast.Identifier) and self.check("SYMBOL", "("):
            self.advance()
            args = []
            if not self.check("SYMBOL", ")"):
                args.append(self.expression())
                while self.match("SYMBOL", ","):
                    args.append(self.expression())
            self.expect("SYMBOL", ")")
            return ast.Call(expr.name, args)
        return expr

    def primary(self):
        tok = self.peek()

        if self.match("NUMBER"):
            return ast.NumberLit(float(tok.value))
        if self.match("STRING"):
            return ast.StringLit(tok.value)
        if self.match("KEYWORD", "true"):
            return ast.BoolLit(True)
        if self.match("KEYWORD", "false"):
            return ast.BoolLit(False)
        if self.match("KEYWORD", "nil"):
            return ast.NilLit()
        if self.check("IDENT"):
            self.advance()
            return ast.Identifier(tok.value)
        if self.match("SYMBOL", "("):
            expr = self.expression()
            self.expect("SYMBOL", ")")
            return expr

        raise ParseError(f"Unexpected token {tok.value!r}", tok.line)
