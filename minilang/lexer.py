"""
Lexer for MiniLang.

Turns raw source text into a flat list of Token objects. This is the first
stage of the interpreter pipeline:

    source text --[Lexer]--> tokens --[Parser]--> AST --[Interpreter]--> result
"""

from dataclasses import dataclass


KEYWORDS = {
    "let", "if", "else", "while", "fn", "return",
    "true", "false", "nil", "print", "and", "or", "not",
}

# Multi-character operators must be listed before their single-character prefixes.
SYMBOLS = [
    "==", "!=", "<=", ">=",
    "+", "-", "*", "/", "%",
    "=", "<", ">", "(", ")", "{", "}", ",", ";",
]


@dataclass
class Token:
    kind: str   # NUMBER, STRING, IDENT, KEYWORD, SYMBOL, EOF
    value: str
    line: int

    def __repr__(self):
        return f"Token({self.kind}, {self.value!r}, line={self.line})"


class LexError(Exception):
    def __init__(self, message, line):
        super().__init__(f"[line {line}] Lex error: {message}")
        self.line = line


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.tokens = []

    def error(self, message):
        raise LexError(message, self.line)

    def peek(self, offset=0):
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else ""

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def tokenize(self):
        while self.pos < len(self.source):
            ch = self.peek()

            if ch in " \t\r\n":
                self.advance()
                continue

            if ch == "#":  # comment to end of line
                while self.pos < len(self.source) and self.peek() != "\n":
                    self.advance()
                continue

            if ch.isdigit():
                self.tokens.append(self._number())
                continue

            if ch.isalpha() or ch == "_":
                self.tokens.append(self._identifier())
                continue

            if ch == '"':
                self.tokens.append(self._string())
                continue

            symbol = self._match_symbol()
            if symbol:
                self.tokens.append(Token("SYMBOL", symbol, self.line))
                continue

            self.error(f"Unexpected character {ch!r}")

        self.tokens.append(Token("EOF", "", self.line))
        return self.tokens

    def _number(self):
        start_line = self.line
        start = self.pos
        seen_dot = False
        while self.pos < len(self.source) and (self.peek().isdigit() or (self.peek() == "." and not seen_dot)):
            if self.peek() == ".":
                seen_dot = True
            self.advance()
        text = self.source[start:self.pos]
        return Token("NUMBER", text, start_line)

    def _identifier(self):
        start_line = self.line
        start = self.pos
        while self.pos < len(self.source) and (self.peek().isalnum() or self.peek() == "_"):
            self.advance()
        text = self.source[start:self.pos]
        kind = "KEYWORD" if text in KEYWORDS else "IDENT"
        return Token(kind, text, start_line)

    def _string(self):
        start_line = self.line
        self.advance()  # consume opening quote
        chars = []
        while True:
            if self.pos >= len(self.source):
                self.error("Unterminated string")
            ch = self.advance()
            if ch == '"':
                break
            if ch == "\\":
                if self.pos >= len(self.source):
                    self.error("Unterminated string escape")
                esc = self.advance()
                chars.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
            else:
                chars.append(ch)
        return Token("STRING", "".join(chars), start_line)

    def _match_symbol(self):
        for sym in SYMBOLS:
            if self.source.startswith(sym, self.pos):
                for _ in sym:
                    self.advance()
                return sym
        return None
