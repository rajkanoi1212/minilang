/* MiniLang interpreter — JavaScript port of the Python implementation.
   Same three-stage pipeline: Lexer -> Parser -> Interpreter. */

const KEYWORDS = new Set(["let","if","else","while","fn","return","true","false","nil","print","and","or","not"]);
const SYMBOLS = ["==","!=","<=",">=","+","-","*","/","%","=","<",">","(",")","{","}",",",";"];

class MiniLangError extends Error {}

/* ---------------- Lexer ---------------- */
function tokenize(source) {
  const tokens = [];
  let pos = 0, line = 1;
  const peek = (o = 0) => source[pos + o] ?? "";
  const advance = () => { const ch = source[pos++]; if (ch === "\n") line++; return ch; };

  while (pos < source.length) {
    const ch = peek();
    if (" \t\r\n".includes(ch)) { advance(); continue; }
    if (ch === "#") { while (pos < source.length && peek() !== "\n") advance(); continue; }
    if (/[0-9]/.test(ch)) {
      const startLine = line, start = pos; let seenDot = false;
      while (pos < source.length && (/[0-9]/.test(peek()) || (peek() === "." && !seenDot))) {
        if (peek() === ".") seenDot = true;
        advance();
      }
      tokens.push({ kind: "NUMBER", value: source.slice(start, pos), line: startLine });
      continue;
    }
    if (/[a-zA-Z_]/.test(ch)) {
      const startLine = line, start = pos;
      while (pos < source.length && /[a-zA-Z0-9_]/.test(peek())) advance();
      const text = source.slice(start, pos);
      tokens.push({ kind: KEYWORDS.has(text) ? "KEYWORD" : "IDENT", value: text, line: startLine });
      continue;
    }
    if (ch === '"') {
      const startLine = line; advance();
      let chars = [];
      while (true) {
        if (pos >= source.length) throw new MiniLangError(`[line ${line}] Lex error: Unterminated string`);
        const c = advance();
        if (c === '"') break;
        if (c === "\\") {
          const esc = advance();
          chars.push({ n: "\n", t: "\t", '"': '"', "\\": "\\" }[esc] ?? esc);
        } else chars.push(c);
      }
      tokens.push({ kind: "STRING", value: chars.join(""), line: startLine });
      continue;
    }
    const sym = SYMBOLS.find(s => source.startsWith(s, pos));
    if (sym) { for (let i = 0; i < sym.length; i++) advance(); tokens.push({ kind: "SYMBOL", value: sym, line }); continue; }
    throw new MiniLangError(`[line ${line}] Lex error: Unexpected character '${ch}'`);
  }
  tokens.push({ kind: "EOF", value: "", line });
  return tokens;
}

/* ---------------- Parser ---------------- */
class Parser {
  constructor(tokens) { this.tokens = tokens; this.pos = 0; }
  peek() { return this.tokens[this.pos]; }
  advance() { const t = this.tokens[this.pos]; if (t.kind !== "EOF") this.pos++; return t; }
  check(kind, value) { const t = this.peek(); return t.kind === kind && (value === undefined || t.value === value); }
  match(kind, value) { return this.check(kind, value) ? this.advance() : null; }
  expect(kind, value, message) {
    if (this.check(kind, value)) return this.advance();
    const t = this.peek();
    throw new MiniLangError(`[line ${t.line}] Parse error: ${message || `Expected ${value ?? kind}, got '${t.value}'`}`);
  }

  parse() {
    const statements = [];
    while (!this.check("EOF")) statements.push(this.statement());
    return { type: "Block", statements };
  }

  statement() {
    if (this.match("KEYWORD", "let")) return this.letStmt();
    if (this.match("KEYWORD", "print")) return this.printStmt();
    if (this.match("KEYWORD", "if")) return this.ifStmt();
    if (this.match("KEYWORD", "while")) return this.whileStmt();
    if (this.match("KEYWORD", "fn")) return this.fnDecl();
    if (this.match("KEYWORD", "return")) return this.returnStmt();
    if (this.check("SYMBOL", "{")) return this.block();
    return this.exprStmt();
  }

  letStmt() {
    const name = this.expect("IDENT").value;
    this.expect("SYMBOL", "=");
    const value = this.expression();
    this.expect("SYMBOL", ";");
    return { type: "LetStmt", name, value };
  }
  printStmt() {
    const value = this.expression();
    this.expect("SYMBOL", ";");
    return { type: "PrintStmt", value };
  }
  ifStmt() {
    this.expect("SYMBOL", "(");
    const condition = this.expression();
    this.expect("SYMBOL", ")");
    const thenBranch = this.block();
    let elseBranch = null;
    if (this.match("KEYWORD", "else")) elseBranch = this.block();
    return { type: "IfStmt", condition, thenBranch, elseBranch };
  }
  whileStmt() {
    this.expect("SYMBOL", "(");
    const condition = this.expression();
    this.expect("SYMBOL", ")");
    const body = this.block();
    return { type: "WhileStmt", condition, body };
  }
  fnDecl() {
    const name = this.expect("IDENT").value;
    this.expect("SYMBOL", "(");
    const params = [];
    if (!this.check("SYMBOL", ")")) {
      params.push(this.expect("IDENT").value);
      while (this.match("SYMBOL", ",")) params.push(this.expect("IDENT").value);
    }
    this.expect("SYMBOL", ")");
    const body = this.block();
    return { type: "FnDecl", name, params, body };
  }
  returnStmt() {
    let value = null;
    if (!this.check("SYMBOL", ";")) value = this.expression();
    this.expect("SYMBOL", ";");
    return { type: "ReturnStmt", value };
  }
  block() {
    this.expect("SYMBOL", "{");
    const statements = [];
    while (!this.check("SYMBOL", "}")) statements.push(this.statement());
    this.expect("SYMBOL", "}");
    return { type: "Block", statements };
  }
  exprStmt() {
    const expr = this.expression();
    this.expect("SYMBOL", ";");
    return { type: "ExprStmt", expr };
  }

  expression() { return this.assignment(); }
  assignment() {
    if (this.check("IDENT") && this.tokens[this.pos + 1].kind === "SYMBOL" && this.tokens[this.pos + 1].value === "=") {
      const name = this.advance().value;
      this.advance();
      const value = this.assignment();
      return { type: "Assign", name, value };
    }
    return this.logicOr();
  }
  logicOr() {
    let expr = this.logicAnd();
    while (this.match("KEYWORD", "or")) expr = { type: "BinaryOp", op: "or", left: expr, right: this.logicAnd() };
    return expr;
  }
  logicAnd() {
    let expr = this.equality();
    while (this.match("KEYWORD", "and")) expr = { type: "BinaryOp", op: "and", left: expr, right: this.equality() };
    return expr;
  }
  equality() {
    let expr = this.comparison();
    while (this.check("SYMBOL") && ["==", "!="].includes(this.peek().value)) {
      const op = this.advance().value;
      expr = { type: "BinaryOp", op, left: expr, right: this.comparison() };
    }
    return expr;
  }
  comparison() {
    let expr = this.term();
    while (this.check("SYMBOL") && ["<", ">", "<=", ">="].includes(this.peek().value)) {
      const op = this.advance().value;
      expr = { type: "BinaryOp", op, left: expr, right: this.term() };
    }
    return expr;
  }
  term() {
    let expr = this.factor();
    while (this.check("SYMBOL") && ["+", "-"].includes(this.peek().value)) {
      const op = this.advance().value;
      expr = { type: "BinaryOp", op, left: expr, right: this.factor() };
    }
    return expr;
  }
  factor() {
    let expr = this.unary();
    while (this.check("SYMBOL") && ["*", "/", "%"].includes(this.peek().value)) {
      const op = this.advance().value;
      expr = { type: "BinaryOp", op, left: expr, right: this.unary() };
    }
    return expr;
  }
  unary() {
    if (this.match("KEYWORD", "not")) return { type: "UnaryOp", op: "not", operand: this.unary() };
    if (this.check("SYMBOL", "-")) { this.advance(); return { type: "UnaryOp", op: "-", operand: this.unary() }; }
    return this.call();
  }
  call() {
    let expr = this.primary();
    if (expr.type === "Identifier" && this.check("SYMBOL", "(")) {
      this.advance();
      const args = [];
      if (!this.check("SYMBOL", ")")) {
        args.push(this.expression());
        while (this.match("SYMBOL", ",")) args.push(this.expression());
      }
      this.expect("SYMBOL", ")");
      return { type: "Call", callee: expr.name, args };
    }
    return expr;
  }
  primary() {
    const t = this.peek();
    if (this.match("NUMBER")) return { type: "NumberLit", value: parseFloat(t.value) };
    if (this.match("STRING")) return { type: "StringLit", value: t.value };
    if (this.match("KEYWORD", "true")) return { type: "BoolLit", value: true };
    if (this.match("KEYWORD", "false")) return { type: "BoolLit", value: false };
    if (this.match("KEYWORD", "nil")) return { type: "NilLit" };
    if (this.check("IDENT")) { this.advance(); return { type: "Identifier", name: t.value }; }
    if (this.match("SYMBOL", "(")) { const e = this.expression(); this.expect("SYMBOL", ")"); return e; }
    throw new MiniLangError(`[line ${t.line}] Parse error: Unexpected token '${t.value}'`);
  }
}

/* ---------------- Interpreter ---------------- */
class ReturnSignal { constructor(value) { this.value = value; } }

class Environment {
  constructor(parent = null) { this.vars = new Map(); this.parent = parent; }
  define(name, value) { this.vars.set(name, value); }
  get(name) {
    if (this.vars.has(name)) return this.vars.get(name);
    if (this.parent) return this.parent.get(name);
    throw new MiniLangError(`Undefined variable '${name}'`);
  }
  assign(name, value) {
    if (this.vars.has(name)) { this.vars.set(name, value); return; }
    if (this.parent) { this.parent.assign(name, value); return; }
    throw new MiniLangError(`Cannot assign to undefined variable '${name}'`);
  }
}

class MiniFunction {
  constructor(decl, closure) { this.decl = decl; this.closure = closure; }
  call(interp, args) {
    if (args.length !== this.decl.params.length)
      throw new MiniLangError(`Function '${this.decl.name}' expects ${this.decl.params.length} argument(s), got ${args.length}`);
    const scope = new Environment(this.closure);
    this.decl.params.forEach((p, i) => scope.define(p, args[i]));
    try { interp.execBlock(this.decl.body, scope); } catch (r) { if (r instanceof ReturnSignal) return r.value; throw r; }
    return null;
  }
}

function truthy(v) { return !(v === null || v === false); }
function checkNumber(v, op) { if (typeof v !== "number") throw new MiniLangError(`Operator '${op}' requires a number, got ${stringify(v)}`); }
function stringify(v) {
  if (v === null || v === undefined) return "nil";
  if (v === true) return "true";
  if (v === false) return "false";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(v);
  return String(v);
}

class Interpreter {
  constructor(onPrint) {
    this.globals = new Environment();
    this.onPrint = onPrint || (() => {});
    this.globals.define("len", (args) => { if (args.length !== 1 || typeof args[0] !== "string") throw new MiniLangError("len() expects a single string argument"); return args[0].length; });
    this.globals.define("str", (args) => stringify(args[0]));
  }
  run(program) { this.execBlock(program, this.globals); }
  execBlock(block, scope) { for (const stmt of block.statements) this.execStmt(stmt, scope); }
  execStmt(stmt, scope) { this[`stmt_${stmt.type}`](stmt, scope); }

  stmt_LetStmt(s, scope) { scope.define(s.name, this.eval(s.value, scope)); }
  stmt_PrintStmt(s, scope) { this.onPrint(stringify(this.eval(s.value, scope))); }
  stmt_ExprStmt(s, scope) { this.eval(s.expr, scope); }
  stmt_Block(s, scope) { this.execBlock(s, new Environment(scope)); }
  stmt_IfStmt(s, scope) {
    if (truthy(this.eval(s.condition, scope))) this.execStmt(s.thenBranch, scope);
    else if (s.elseBranch) this.execStmt(s.elseBranch, scope);
  }
  stmt_WhileStmt(s, scope) {
    let guard = 0;
    while (truthy(this.eval(s.condition, scope))) {
      this.execStmt(s.body, scope);
      if (++guard > 200000) throw new MiniLangError("Loop exceeded 200000 iterations (safety limit)");
    }
  }
  stmt_FnDecl(s, scope) { scope.define(s.name, new MiniFunction(s, scope)); }
  stmt_ReturnStmt(s, scope) { throw new ReturnSignal(s.value !== null ? this.eval(s.value, scope) : null); }

  eval(node, scope) { return this[`eval_${node.type}`](node, scope); }
  eval_NumberLit(n) { return n.value; }
  eval_StringLit(n) { return n.value; }
  eval_BoolLit(n) { return n.value; }
  eval_NilLit() { return null; }
  eval_Identifier(n, scope) { return scope.get(n.name); }
  eval_Assign(n, scope) { const v = this.eval(n.value, scope); scope.assign(n.name, v); return v; }
  eval_UnaryOp(n, scope) {
    const v = this.eval(n.operand, scope);
    if (n.op === "-") { checkNumber(v, "-"); return -v; }
    if (n.op === "not") return !truthy(v);
    throw new MiniLangError(`Unknown unary operator '${n.op}'`);
  }
  eval_BinaryOp(n, scope) {
    if (n.op === "and") { const l = this.eval(n.left, scope); return truthy(l) ? this.eval(n.right, scope) : l; }
    if (n.op === "or") { const l = this.eval(n.left, scope); return truthy(l) ? l : this.eval(n.right, scope); }
    const l = this.eval(n.left, scope), r = this.eval(n.right, scope), op = n.op;
    switch (op) {
      case "+": if (typeof l === "string" || typeof r === "string") return stringify(l) + stringify(r);
                checkNumber(l, op); checkNumber(r, op); return l + r;
      case "-": checkNumber(l, op); checkNumber(r, op); return l - r;
      case "*": checkNumber(l, op); checkNumber(r, op); return l * r;
      case "/": checkNumber(l, op); checkNumber(r, op); if (r === 0) throw new MiniLangError("Division by zero"); return l / r;
      case "%": checkNumber(l, op); checkNumber(r, op); return l % r;
      case "==": return l === r;
      case "!=": return l !== r;
      case "<": return l < r;
      case ">": return l > r;
      case "<=": return l <= r;
      case ">=": return l >= r;
    }
    throw new MiniLangError(`Unknown binary operator '${op}'`);
  }
  eval_Call(n, scope) {
    const callee = scope.get(n.callee);
    const args = n.args.map(a => this.eval(a, scope));
    if (callee instanceof MiniFunction) return callee.call(this, args);
    if (typeof callee === "function") return callee(args);
    throw new MiniLangError(`'${n.callee}' is not callable`);
  }
}

/* Public API used by the playground UI */
function runMiniLang(source, onPrint) {
  const tokens = tokenize(source);
  const program = new Parser(tokens).parse();
  new Interpreter(onPrint).run(program);
  return tokens;
}
