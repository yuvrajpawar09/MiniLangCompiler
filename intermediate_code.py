"""
intermediate_code.py
--------------------
Phase 3 — Three Address Code (3AC) generator.

Walks the AST produced by `parser.Parser` and emits a list of 3AC
quadruples represented as dictionaries.  Each instruction has one of
the following shapes:

    {"op": "=",      "arg1": "<src>",          "result": "<dst>"}
    {"op": "+",      "arg1": "x", "arg2": "y", "result": "t1"}
    {"op": "label",  "result": "L1"}
    {"op": "goto",   "result": "L2"}
    {"op": "if",     "arg1": "x", "arg2": "y", "rel": "<", "result": "L3"}   # jump if true
    {"op": "ifnot",  "arg1": "x", "arg2": "y", "rel": "<", "result": "L4"}   # jump if false
    {"op": "print",  "arg1": "t5"}

The companion `format_tac` helper converts these quadruples back into
the conventional textual form (`t1 = b + c`, `goto L2`, …) for display.
"""


class TACGenerator:
    """Translate a MiniLang AST into a list of 3AC instructions."""

    def __init__(self):
        self.code = []
        self._temp_counter = 0
        self._label_counter = 0

    # ---------------- helpers ---------------- #
    def _new_temp(self) -> str:
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def _new_label(self) -> str:
        self._label_counter += 1
        return f"L{self._label_counter}"

    def _emit(self, instr: dict):
        self.code.append(instr)

    # ---------------- public entry point ---------------- #
    def generate(self, program):
        """Generate 3AC for a list of statement nodes."""
        for stmt in program:
            self._gen_stmt(stmt)
        return self.code

    # ---------------- statement dispatch ---------------- #
    def _gen_stmt(self, stmt):
        kind = stmt["node"]
        if kind == "decl":
            # Declarations don't produce 3AC on their own, but we record a
            # marker so the optimiser knows about declared names.
            self._emit({"op": "decl", "result": stmt["name"]})
        elif kind == "assign":
            self._gen_assign(stmt)
        elif kind == "if":
            self._gen_if(stmt)
        elif kind == "while":
            self._gen_while(stmt)
        elif kind == "print":
            self._gen_print(stmt)

    # ---------------- specific generators ---------------- #
    def _gen_assign(self, stmt):
        value = self._gen_expr(stmt["expr"])
        self._emit({"op": "=", "arg1": value, "result": stmt["target"]})

    def _gen_print(self, stmt):
        value = self._gen_expr(stmt["expr"])
        self._emit({"op": "print", "arg1": value})

    def _gen_if(self, stmt):
        cond = stmt["cond"]
        left = self._gen_expr(cond["left"])
        right = self._gen_expr(cond["right"])

        else_label = self._new_label()
        end_label = self._new_label() if stmt["else"] else else_label

        # Jump to the else/end target when the condition is FALSE
        self._emit({
            "op": "ifnot",
            "arg1": left,
            "arg2": right,
            "rel": cond["op"],
            "result": else_label,
        })

        # then-branch
        for s in stmt["then"]:
            self._gen_stmt(s)

        if stmt["else"]:
            self._emit({"op": "goto", "result": end_label})
            self._emit({"op": "label", "result": else_label})
            for s in stmt["else"]:
                self._gen_stmt(s)
            self._emit({"op": "label", "result": end_label})
        else:
            self._emit({"op": "label", "result": else_label})

    def _gen_while(self, stmt):
        start_label = self._new_label()
        end_label = self._new_label()

        self._emit({"op": "label", "result": start_label})
        cond = stmt["cond"]
        left = self._gen_expr(cond["left"])
        right = self._gen_expr(cond["right"])
        self._emit({
            "op": "ifnot",
            "arg1": left,
            "arg2": right,
            "rel": cond["op"],
            "result": end_label,
        })
        for s in stmt["body"]:
            self._gen_stmt(s)
        self._emit({"op": "goto", "result": start_label})
        self._emit({"op": "label", "result": end_label})

    # ---------------- expression generation ---------------- #
    def _gen_expr(self, node) -> str:
        kind = node["node"]
        if kind == "num":
            return str(node["value"])
        if kind == "var":
            return node["name"]
        if kind == "binop":
            left = self._gen_expr(node["left"])
            right = self._gen_expr(node["right"])
            temp = self._new_temp()
            self._emit({
                "op": node["op"],
                "arg1": left,
                "arg2": right,
                "result": temp,
            })
            return temp
        # Should never reach here — fall back to a placeholder
        return "?"


# ---------------- pretty-printer ---------------- #
def format_tac(code):
    """Convert a list of 3AC dicts into human-readable text lines."""
    lines = []
    for idx, ins in enumerate(code, start=1):
        op = ins["op"]
        if op == "decl":
            lines.append(f"{idx:>3}: decl {ins['result']}")
        elif op == "=":
            lines.append(f"{idx:>3}: {ins['result']} = {ins['arg1']}")
        elif op in {"+", "-", "*", "/"}:
            lines.append(
                f"{idx:>3}: {ins['result']} = {ins['arg1']} {op} {ins['arg2']}"
            )
        elif op == "label":
            lines.append(f"{idx:>3}: {ins['result']}:")
        elif op == "goto":
            lines.append(f"{idx:>3}: goto {ins['result']}")
        elif op == "ifnot":
            lines.append(
                f"{idx:>3}: ifFalse {ins['arg1']} {ins['rel']} {ins['arg2']} "
                f"goto {ins['result']}"
            )
        elif op == "if":
            lines.append(
                f"{idx:>3}: if {ins['arg1']} {ins['rel']} {ins['arg2']} "
                f"goto {ins['result']}"
            )
        elif op == "print":
            lines.append(f"{idx:>3}: print {ins['arg1']}")
        else:
            lines.append(f"{idx:>3}: {ins}")
    return "\n".join(lines)
