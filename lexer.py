"""
lexer.py
--------
Phase 1 — Lexical analyzer for the MiniLang language.

The Lexer reads raw source text and converts it into a stream of `Token`
objects.  Every token records its lexeme (text), its category, and the
line number on which it appeared so that meaningful error messages can
be produced in later phases.

Recognised token categories:
    KEYWORD     – INT, IF, ELSE, WHILE, PRINT
    IDENTIFIER  – user-defined names (start with letter / underscore)
    NUMBER      – integer constants
    OPERATOR    – + - * / = < > <= >= == !=
    DELIMITER   – ; ( ) { }
"""

from utils import is_identifier_start, is_identifier_part


# ---------- Reserved words and operator tables ---------- #
KEYWORDS = {"INT", "IF", "ELSE", "WHILE", "PRINT"}

# Two-character operators must be checked BEFORE single-character ones
TWO_CHAR_OPS = {"<=", ">=", "==", "!="}
ONE_CHAR_OPS = {"+", "-", "*", "/", "=", "<", ">"}
DELIMITERS = {";", "(", ")", "{", "}"}


class Token:
    """Lightweight token record used by the parser and code generator."""

    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_: str, value: str, line: int, col: int = 0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class LexicalError(Exception):
    """Raised when the lexer encounters input it cannot tokenise."""


class Lexer:
    """Convert MiniLang source text into a list of Token objects."""

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.errors = []

    # ----- helper utilities ----- #
    def _peek(self, offset: int = 0) -> str:
        """Return the character `offset` ahead of the cursor or '' at EOF."""
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return ""

    def _advance(self) -> str:
        """Consume and return one character, tracking line / column counters."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, type_: str, value: str, line: int, col: int):
        """Append a finished Token to the output list."""
        self.tokens.append(Token(type_, value, line, col))

    def _add_error(self, message: str, line: int):
        """Record a lexical error message but keep scanning."""
        self.errors.append(f"Line {line}: {message}")

    # ----- main scanning loop ----- #
    def tokenize(self):
        """Walk through the source and emit tokens until EOF is reached."""
        while self.pos < len(self.source):
            ch = self._peek()

            # 1. Skip whitespace -------------------------------------------
            if ch in " \t\r\n":
                self._advance()
                continue

            # 2. Single-line comment starting with '#' ---------------------
            if ch == "#":
                while self.pos < len(self.source) and self._peek() != "\n":
                    self._advance()
                continue

            line_start = self.line
            col_start = self.col

            # 3. Identifiers / keywords ------------------------------------
            if is_identifier_start(ch):
                lexeme = ""
                while self.pos < len(self.source) and is_identifier_part(self._peek()):
                    lexeme += self._advance()

                # Reject identifiers containing invalid combinations
                # (already enforced by is_identifier_part – kept for clarity)
                if lexeme in KEYWORDS:
                    self._add("KEYWORD", lexeme, line_start, col_start)
                else:
                    self._add("IDENTIFIER", lexeme, line_start, col_start)
                continue

            # 4. Numeric literals ------------------------------------------
            if ch.isdigit():
                lexeme = ""
                while self.pos < len(self.source) and self._peek().isdigit():
                    lexeme += self._advance()

                # If followed by an identifier-start, it is a malformed token
                if self.pos < len(self.source) and is_identifier_start(self._peek()):
                    bad = lexeme
                    while self.pos < len(self.source) and is_identifier_part(self._peek()):
                        bad += self._advance()
                    self._add_error(
                        f"Malformed token '{bad}' (numbers cannot be followed by letters)",
                        line_start,
                    )
                    continue

                self._add("NUMBER", lexeme, line_start, col_start)
                continue

            # 5. Two-character operators -----------------------------------
            two = self._peek() + self._peek(1)
            if two in TWO_CHAR_OPS:
                self._advance()
                self._advance()
                self._add("OPERATOR", two, line_start, col_start)
                continue

            # 6. Single-character operators --------------------------------
            if ch in ONE_CHAR_OPS:
                self._advance()
                self._add("OPERATOR", ch, line_start, col_start)
                continue

            # 7. Delimiters ------------------------------------------------
            if ch in DELIMITERS:
                self._advance()
                self._add("DELIMITER", ch, line_start, col_start)
                continue

            # 8. Anything else is an invalid character ---------------------
            self._advance()
            self._add_error(f"Invalid symbol '{ch}'", line_start)

        # End of input sentinel for the parser
        self._add("EOF", "EOF", self.line, self.col)
        return self.tokens, self.errors
