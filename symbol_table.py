"""
symbol_table.py
---------------
Maintains a simple symbol table for the MiniLang compiler.

Each entry stores:
    - variable name
    - data type
    - current value (None until assigned)
    - memory reference (a synthetic offset like @0, @4, @8…)
    - line of declaration
"""


class SymbolTable:
    """Flat (single-scope) symbol table sufficient for MiniLang."""

    def __init__(self):
        # Use an ordinary dict so insertion order is preserved (Py 3.7+)
        self.symbols = {}
        self._next_offset = 0  # synthetic memory offset counter

    # ----- mutation API ----- #
    def declare(self, name: str, dtype: str, line: int) -> bool:
        """Declare a new symbol. Return False if it already exists."""
        if name in self.symbols:
            return False
        self.symbols[name] = {
            "name":   name,
            "type":   dtype,
            "value":  None,
            "memory": f"@{self._next_offset}",
            "line":   line,
        }
        self._next_offset += 4  # assume 4-byte INT slots
        return True

    def assign(self, name: str, value):
        """Update the value column for an existing symbol."""
        if name in self.symbols:
            self.symbols[name]["value"] = value

    # ----- query API ----- #
    def exists(self, name: str) -> bool:
        return name in self.symbols

    def get(self, name: str):
        return self.symbols.get(name)

    def all_entries(self):
        """Return a list of dicts (one per declared variable)."""
        return list(self.symbols.values())

    def reset(self):
        """Clear the table — used when the user recompiles."""
        self.symbols.clear()
        self._next_offset = 0
