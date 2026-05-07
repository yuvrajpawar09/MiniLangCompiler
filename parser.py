"""
parser.py
---------
Phase 2 — Recursive-descent syntax analyzer for MiniLang.

The parser consumes the token list produced by the lexer and validates
that the program follows the grammar below.  It also builds a small
abstract-syntax-tree (AST) consisting of plain dictionaries — one per
construct — which the intermediate-code generator then walks.

GRAMMAR
-------
program       -> stmt_list
stmt_list     -> stmt stmt_list | epsilon
stmt          -> declaration | assignment | if_stmt | while_stmt | print_stmt
declaration   -> INT id ;
assignment    -> id = expr ;
if_stmt       -> IF ( condition ) { stmt_list } [ ELSE { stmt_list } ]
while_stmt    -> WHILE ( condition ) { stmt_list }
print_stmt    -> PRINT ( expr ) ;
condition     -> expr relop expr
expr          -> term expr_prime
expr_prime    -> + term expr_prime | - term expr_prime | epsilon
term          -> factor term_prime
term_prime    -> * factor term_prime | / factor term_prime | epsilon
factor        -> id | number | ( expr )
"""

from symbol_table import SymbolTable


REL_OPS = {"<", ">", "<=", ">=", "==", "!="}


class SyntaxError_(Exception):
    """Internal parser error used for control flow only."""


class Parser:
    """Recursive-descent parser that emits a list of statement-AST nodes."""

    def __init__(self, tokens, symbol_table: SymbolTable):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.symtab = symbol_table

    # ---------------- helpers ---------------- #
    def _peek(self, offset: int = 0):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF sentinel

    def _advance(self):
        tok = self.tokens[self.pos]
        if tok.type != "EOF":
            self.pos += 1
        return tok

    def _expect(self, type_: str, value: str = None):
        """Consume the next token if it matches, otherwise raise an error."""
        tok = self._peek()
        if tok.type == type_ and (value is None or tok.value == value):
            return self._advance()
        expected = value if value else type_
        raise SyntaxError_(
            f"Line {tok.line}: Expected '{expected}' but found '{tok.value}'"
        )

    def _error(self, message: str):
        self.errors.append(message)

    def _synchronize(self):
        """Skip tokens until we reach a likely statement boundary."""
        while self._peek().type != "EOF":
            tok = self._peek()
            if tok.type == "DELIMITER" and tok.value in (";", "}"):
                self._advance()
                return
            if tok.type == "KEYWORD" and tok.value in ("INT", "IF", "WHILE", "PRINT"):
                return
            self._advance()

    # ---------------- entry point ---------------- #
    def parse(self):
        """Parse the entire token stream and return (ast_list, errors)."""
        program = []
        while self._peek().type != "EOF":
            try:
                stmt = self._stmt()
                if stmt is not None:
                    program.append(stmt)
            except SyntaxError_ as e:
                self._error(str(e))
                self._synchronize()
        return program, self.errors

    # ---------------- statements ---------------- #
    def _stmt(self):
        tok = self._peek()
        if tok.type == "KEYWORD":
            if tok.value == "INT":
                return self._declaration()
            if tok.value == "IF":
                return self._if_stmt()
            if tok.value == "WHILE":
                return self._while_stmt()
            if tok.value == "PRINT":
                return self._print_stmt()
        if tok.type == "IDENTIFIER":
            return self._assignment()

        raise SyntaxError_(
            f"Line {tok.line}: Unexpected token '{tok.value}' — statement expected"
        )

    def _declaration(self):
        kw = self._expect("KEYWORD", "INT")
        ident = self._expect("IDENTIFIER")
        self._expect("DELIMITER", ";")

        # Semantic action: register variable in the symbol table
        if not self.symtab.declare(ident.value, "INT", kw.line):
            self._error(
                f"Line {kw.line}: Variable '{ident.value}' already declared"
            )
        return {"node": "decl", "name": ident.value, "line": kw.line}

    def _assignment(self):
        ident = self._expect("IDENTIFIER")
        # Semantic check: variable must be declared before use
        if not self.symtab.exists(ident.value):
            self._error(
                f"Line {ident.line}: Variable '{ident.value}' used before declaration"
            )
        self._expect("OPERATOR", "=")
        expr = self._expr()
        self._expect("DELIMITER", ";")
        return {
            "node": "assign",
            "target": ident.value,
            "expr": expr,
            "line": ident.line,
        }

    def _if_stmt(self):
        kw = self._expect("KEYWORD", "IF")
        self._expect("DELIMITER", "(")
        cond = self._condition()
        self._expect("DELIMITER", ")")
        self._expect("DELIMITER", "{")
        body = self._block()
        self._expect("DELIMITER", "}")

        else_body = None
        if self._peek().type == "KEYWORD" and self._peek().value == "ELSE":
            self._advance()
            self._expect("DELIMITER", "{")
            else_body = self._block()
            self._expect("DELIMITER", "}")

        return {
            "node": "if",
            "cond": cond,
            "then": body,
            "else": else_body,
            "line": kw.line,
        }

    def _while_stmt(self):
        kw = self._expect("KEYWORD", "WHILE")
        self._expect("DELIMITER", "(")
        cond = self._condition()
        self._expect("DELIMITER", ")")
        self._expect("DELIMITER", "{")
        body = self._block()
        self._expect("DELIMITER", "}")
        return {
            "node": "while",
            "cond": cond,
            "body": body,
            "line": kw.line,
        }

    def _print_stmt(self):
        kw = self._expect("KEYWORD", "PRINT")
        self._expect("DELIMITER", "(")
        expr = self._expr()
        self._expect("DELIMITER", ")")
        self._expect("DELIMITER", ";")
        return {"node": "print", "expr": expr, "line": kw.line}

    def _block(self):
        """Parse a brace-delimited block of statements."""
        statements = []
        while not (
            self._peek().type == "DELIMITER" and self._peek().value == "}"
        ) and self._peek().type != "EOF":
            try:
                s = self._stmt()
                if s is not None:
                    statements.append(s)
            except SyntaxError_ as e:
                self._error(str(e))
                self._synchronize()
                # If we synchronised onto the closing brace, stop the block
                if self._peek().type == "DELIMITER" and self._peek().value == "}":
                    break
        return statements

    # ---------------- expressions ---------------- #
    def _condition(self):
        left = self._expr()
        op = self._peek()
        if op.type == "OPERATOR" and op.value in REL_OPS:
            self._advance()
            right = self._expr()
            return {"node": "cond", "op": op.value, "left": left, "right": right}
        raise SyntaxError_(
            f"Line {op.line}: Expected relational operator, found '{op.value}'"
        )

    def _expr(self):
        node = self._term()
        while (
            self._peek().type == "OPERATOR"
            and self._peek().value in ("+", "-")
        ):
            op = self._advance().value
            right = self._term()
            node = {"node": "binop", "op": op, "left": node, "right": right}
        return node

    def _term(self):
        node = self._factor()
        while (
            self._peek().type == "OPERATOR"
            and self._peek().value in ("*", "/")
        ):
            op = self._advance().value
            right = self._factor()
            node = {"node": "binop", "op": op, "left": node, "right": right}
        return node

    def _factor(self):
        tok = self._peek()
        if tok.type == "NUMBER":
            self._advance()
            return {"node": "num", "value": int(tok.value)}
        if tok.type == "IDENTIFIER":
            self._advance()
            if not self.symtab.exists(tok.value):
                self._error(
                    f"Line {tok.line}: Variable '{tok.value}' used before declaration"
                )
            return {"node": "var", "name": tok.value}
        if tok.type == "DELIMITER" and tok.value == "(":
            self._advance()
            inner = self._expr()
            self._expect("DELIMITER", ")")
            return inner
        raise SyntaxError_(
            f"Line {tok.line}: Unexpected token '{tok.value}' in expression"
        )
