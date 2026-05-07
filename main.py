"""
main.py
-------
Entry point for the MiniLang compiler.

Run with:

    python main.py

This boots the Tkinter GUI defined in `gui.py`, which orchestrates the
four compiler phases (lexical analysis, syntax analysis, three-address
code generation and optimisation).
"""

import sys

from gui import launch


def main():
    try:
        launch()
    except Exception as exc:                  # pragma: no cover
        # Last-resort guard so the program exits cleanly even if Tk is
        # unavailable on the host machine.
        print(f"[FATAL] MiniLang Compiler could not start: {exc}",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
