"""
optimizer.py
------------
Phase 4 — Optimisation passes for the 3AC produced by `TACGenerator`.

Three classic optimisations are implemented, each in its own pass so
that students can see the effect of every individual transformation:

1. **Constant Folding**         – replace pure-constant expressions with
                                   their pre-computed value.
2. **Common Subexpression
   Elimination (CSE)**          – when the same expression `a op b` is
                                   computed twice in a basic block, reuse
                                   the first result.
3. **Dead Code Elimination
   (DCE)**                      – remove assignments whose target is
                                   never read again (and that have no
                                   externally visible side-effects).

The optimiser purposely operates on *one* basic block at a time when
that simplifies analysis (CSE), and on the whole list when a global
view is required (DCE).
"""

from utils import safe_int


# Operations that can be safely constant-folded
_FOLDABLE = {"+", "-", "*", "/"}

# Operations that must never be removed — they have side effects
_SIDE_EFFECTING_OPS = {"print", "label", "goto", "ifnot", "if", "decl"}


# --------------------------------------------------------------------- #
# 1. Constant folding
# --------------------------------------------------------------------- #
def constant_folding(code):
    """Fold compile-time constant arithmetic expressions.

    Walks the code linearly.  When it encounters an arithmetic
    instruction whose operands are both numeric literals, it replaces
    the instruction with a direct assignment.  It also propagates
    constants forward so that something like::

        t1 = 2 + 3
        t2 = t1 * 4

    becomes::

        t1 = 5
        t2 = 20
    """
    optimised = []
    constants = {}                     # name → numeric value (string)

    def resolve(arg):
        """Return the numeric form of `arg` if it is a known constant."""
        if arg is None:
            return None
        if arg in constants:
            return constants[arg]
        return arg

    for ins in code:
        op = ins["op"]
        new = dict(ins)                # shallow copy so we don't mutate input

        if op in _FOLDABLE:
            a = resolve(ins.get("arg1"))
            b = resolve(ins.get("arg2"))
            ai = safe_int(a)
            bi = safe_int(b)
            if ai is not None and bi is not None:
                # Both operands are constants — compute the value
                try:
                    if op == "+": value = ai + bi
                    elif op == "-": value = ai - bi
                    elif op == "*": value = ai * bi
                    elif op == "/":
                        # integer division, guard against /0
                        value = ai // bi if bi != 0 else None
                    if value is not None:
                        new = {"op": "=", "arg1": str(value),
                               "result": ins["result"]}
                        constants[ins["result"]] = str(value)
                        optimised.append(new)
                        continue
                except Exception:
                    pass
            # If only one operand was foldable, still update the args
            new["arg1"] = a
            new["arg2"] = b
            # Result is no longer a known constant
            constants.pop(ins["result"], None)

        elif op == "=":
            src = resolve(ins["arg1"])
            new["arg1"] = src
            if safe_int(src) is not None:
                constants[ins["result"]] = src
            else:
                constants.pop(ins["result"], None)

        elif op == "print":
            new["arg1"] = resolve(ins["arg1"])

        elif op in {"if", "ifnot"}:
            new["arg1"] = resolve(ins.get("arg1"))
            new["arg2"] = resolve(ins.get("arg2"))

        elif op == "label":
            # Crossing a label invalidates constant tracking — be safe
            constants.clear()

        optimised.append(new)
    return optimised


# --------------------------------------------------------------------- #
# 2. Common Subexpression Elimination
# --------------------------------------------------------------------- #
def common_subexpression_elimination(code):
    """Remove redundant recomputation of identical expressions.

    The analysis is per basic block — a label, jump, or assignment that
    overwrites an operand resets the local table.
    """
    optimised = []
    expr_table = {}    # ("op", "arg1", "arg2") → temp/var holding value
    alias_map = {}     # old temp name → replacement name

    def resolve(arg):
        return alias_map.get(arg, arg)

    def reset_block():
        expr_table.clear()
        alias_map.clear()

    for ins in code:
        op = ins["op"]
        new = dict(ins)

        if op in _FOLDABLE:
            a = resolve(ins.get("arg1"))
            b = resolve(ins.get("arg2"))
            new["arg1"], new["arg2"] = a, b

            key = (op, a, b)
            # Commutative ops — also try the swapped key
            commutative_key = (op, b, a) if op in {"+", "*"} else None

            if key in expr_table:
                replacement = expr_table[key]
                alias_map[ins["result"]] = replacement
                # Replace with a simple copy so the SSA chain remains valid
                new = {"op": "=", "arg1": replacement,
                       "result": ins["result"]}
            elif commutative_key and commutative_key in expr_table:
                replacement = expr_table[commutative_key]
                alias_map[ins["result"]] = replacement
                new = {"op": "=", "arg1": replacement,
                       "result": ins["result"]}
            else:
                expr_table[key] = ins["result"]

        elif op == "=":
            src = resolve(ins["arg1"])
            new["arg1"] = src
            # Any cached expression that referenced the overwritten name is
            # no longer trustworthy — drop those entries.
            target = ins["result"]
            stale = [k for k in expr_table if target in k or expr_table[k] == target]
            for k in stale:
                expr_table.pop(k, None)

        elif op == "print":
            new["arg1"] = resolve(ins["arg1"])

        elif op in {"if", "ifnot"}:
            new["arg1"] = resolve(ins.get("arg1"))
            new["arg2"] = resolve(ins.get("arg2"))
            reset_block()        # control-flow boundary

        elif op in {"label", "goto"}:
            reset_block()

        optimised.append(new)
    return optimised


# --------------------------------------------------------------------- #
# 3. Dead Code Elimination
# --------------------------------------------------------------------- #
def dead_code_elimination(code):
    """Remove assignments whose result is never used afterwards.

    A backwards walk over the code maintains a `live` set of names whose
    values are still required.  An instruction whose `result` is not
    live (and that has no side effects) is dropped.

    Side-effecting instructions (`print`, jumps, labels, etc.) are
    always retained, and their operands are added to the live set.
    """
    live = set()
    keep = [True] * len(code)

    # Pass 1: backwards liveness analysis
    for i in range(len(code) - 1, -1, -1):
        ins = code[i]
        op = ins["op"]

        if op in _SIDE_EFFECTING_OPS:
            # Operands of side-effecting ops become live
            for k in ("arg1", "arg2"):
                v = ins.get(k)
                if v and not _is_constant(v):
                    live.add(v)
            continue

        target = ins.get("result")
        if target is None:
            continue

        if target in live:
            # Used downstream → operands become live, result becomes dead
            live.discard(target)
            for k in ("arg1", "arg2"):
                v = ins.get(k)
                if v and not _is_constant(v):
                    live.add(v)
        else:
            # Result never read again — drop the instruction
            keep[i] = False

    # Pass 2: keep only surviving instructions
    return [ins for ins, k in zip(code, keep) if k]


# --------------------------------------------------------------------- #
# Helper utilities
# --------------------------------------------------------------------- #
def _is_constant(value: str) -> bool:
    """Return True if `value` is a numeric literal rather than a name."""
    if value is None:
        return True
    return safe_int(value) is not None


# --------------------------------------------------------------------- #
# Convenience: run all passes in sequence
# --------------------------------------------------------------------- #
def optimize(code):
    """Apply all three optimisations in a sensible order.

    Several iterations are performed because, e.g., constant folding can
    expose new dead code and CSE can make further folding possible.
    """
    optimised = list(code)
    for _ in range(3):
        before = optimised
        optimised = constant_folding(optimised)
        optimised = common_subexpression_elimination(optimised)
        optimised = dead_code_elimination(optimised)
        if optimised == before:
            break
    return optimised
