"""
AST node definitions for MiniLang.

The parser builds a tree of these nodes; the interpreter walks the tree
and evaluates it directly (a "tree-walking interpreter" — no bytecode).
"""

from dataclasses import dataclass, field


# ---- Expressions ----

@dataclass
class NumberLit:
    value: float

@dataclass
class StringLit:
    value: str

@dataclass
class BoolLit:
    value: bool

@dataclass
class NilLit:
    pass

@dataclass
class Identifier:
    name: str

@dataclass
class BinaryOp:
    op: str
    left: object
    right: object

@dataclass
class UnaryOp:
    op: str
    operand: object

@dataclass
class Assign:
    name: str
    value: object

@dataclass
class Call:
    callee: str
    args: list


# ---- Statements ----

@dataclass
class LetStmt:
    name: str
    value: object

@dataclass
class PrintStmt:
    value: object

@dataclass
class ExprStmt:
    expr: object

@dataclass
class Block:
    statements: list

@dataclass
class IfStmt:
    condition: object
    then_branch: object
    else_branch: object  # Block or None

@dataclass
class WhileStmt:
    condition: object
    body: object

@dataclass
class FnDecl:
    name: str
    params: list
    body: object

@dataclass
class ReturnStmt:
    value: object  # may be None
