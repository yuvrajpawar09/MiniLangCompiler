"""
gui.py
------
Tkinter GUI front-end for the MiniLang compiler.

The interface is divided into a left-hand source-code editor (with line
numbers, syntax highlighting, scrollbars, and standard text shortcuts)
and a right-hand notebook of analysis panels: tokens, symbol table,
three-address code, optimised code and an error console.

A toolbar exposes the four required actions — Compile, Clear, Open File
and Save Output — and a status bar at the bottom reports the result of
the last compilation.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from lexer import Lexer, KEYWORDS
from parser import Parser
from intermediate_code import TACGenerator, format_tac
from optimizer import optimize
from symbol_table import SymbolTable
from utils import (
    THEME, FONT_MONO, FONT_MONO_SMALL,
    FONT_UI, FONT_UI_BOLD, FONT_TITLE,
)


# --------------------------------------------------------------------- #
# Editor with line numbers
# --------------------------------------------------------------------- #
class LineNumberCanvas(tk.Canvas):
    """A thin canvas that mirrors the line numbers of an attached Text widget."""

    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.configure(width=42, highlightthickness=0,
                       bg=THEME["panel"], bd=0)

    def redraw(self, *_):
        """Redraw line numbers, called whenever the text changes/scrolls."""
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_no = str(i).split(".")[0]
            self.create_text(
                36, y,
                anchor="ne", text=line_no,
                fill=THEME["comment"], font=FONT_MONO_SMALL,
            )
            i = self.text_widget.index(f"{i}+1line")


class CodeEditor(tk.Frame):
    """Source code editor: line numbers + Text widget + scrollbar + highlighter."""

    def __init__(self, master, **kw):
        super().__init__(master, bg=THEME["panel"], **kw)

        self.text = tk.Text(
            self, wrap="none", undo=True,
            bg=THEME["panel"], fg=THEME["fg"],
            insertbackground=THEME["fg"],
            selectbackground=THEME["select"],
            font=FONT_MONO, relief="flat", borderwidth=0,
            padx=6, pady=4, tabs=("4c"),
        )
        self.linenums = LineNumberCanvas(self, self.text)
        self.vbar = ttk.Scrollbar(self, orient="vertical",
                                  command=self._on_yview)
        self.hbar = ttk.Scrollbar(self, orient="horizontal",
                                  command=self.text.xview)
        self.text.configure(yscrollcommand=self._on_yscroll,
                            xscrollcommand=self.hbar.set)

        # Layout
        self.linenums.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.vbar.grid(row=0, column=2, sticky="ns")
        self.hbar.grid(row=1, column=1, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Configure highlight tags
        self.text.tag_configure("kw", foreground=THEME["keyword"])
        self.text.tag_configure("num", foreground=THEME["number"])
        self.text.tag_configure("op", foreground=THEME["operator"])
        self.text.tag_configure("comment", foreground=THEME["comment"],
                                font=("Consolas", 11, "italic"))

        # Re-highlight / re-paint line numbers on edits
        self.text.bind("<KeyRelease>", self._on_change)
        self.text.bind("<MouseWheel>", lambda e: self.after(1, self.linenums.redraw))
        self.text.bind("<Button-1>", lambda e: self.after(1, self.linenums.redraw))
        self.text.bind("<<Modified>>", self._on_modified)
        self.after(120, self.linenums.redraw)

    # ----- proxied scroll handling so line numbers stay in sync ----- #
    def _on_yview(self, *args):
        self.text.yview(*args)
        self.linenums.redraw()

    def _on_yscroll(self, *args):
        self.vbar.set(*args)
        self.linenums.redraw()

    def _on_modified(self, _):
        self.text.edit_modified(False)
        self._highlight()
        self.linenums.redraw()

    def _on_change(self, _):
        self._highlight()
        self.linenums.redraw()

    # ----- public helpers ----- #
    def get(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set(self, content: str):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._highlight()
        self.linenums.redraw()

    def clear(self):
        self.text.delete("1.0", "end")
        self.linenums.redraw()

    # ----- naive syntax highlighter ----- #
    def _highlight(self):
        """Apply colour tags to keywords / numbers / operators / comments."""
        for tag in ("kw", "num", "op", "comment"):
            self.text.tag_remove(tag, "1.0", "end")

        content = self.text.get("1.0", "end-1c")
        for line_idx, line in enumerate(content.split("\n"), start=1):
            # Comments
            if "#" in line:
                col = line.index("#")
                self.text.tag_add(
                    "comment",
                    f"{line_idx}.{col}",
                    f"{line_idx}.{len(line)}",
                )
                line = line[:col]   # don't process tokens inside comments

            i = 0
            while i < len(line):
                ch = line[i]
                # Identifier / keyword
                if ch.isalpha() or ch == "_":
                    j = i
                    while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                        j += 1
                    word = line[i:j]
                    if word in KEYWORDS:
                        self.text.tag_add(
                            "kw",
                            f"{line_idx}.{i}",
                            f"{line_idx}.{j}",
                        )
                    i = j
                # Number
                elif ch.isdigit():
                    j = i
                    while j < len(line) and line[j].isdigit():
                        j += 1
                    self.text.tag_add(
                        "num",
                        f"{line_idx}.{i}",
                        f"{line_idx}.{j}",
                    )
                    i = j
                # Operators
                elif ch in "+-*/=<>!":
                    j = i + 1
                    if j < len(line) and line[j] == "=" and ch in "<>=!":
                        j += 1
                    self.text.tag_add(
                        "op",
                        f"{line_idx}.{i}",
                        f"{line_idx}.{j}",
                    )
                    i = j
                else:
                    i += 1


# --------------------------------------------------------------------- #
# Main application window
# --------------------------------------------------------------------- #
class CompilerGUI(tk.Tk):
    """Top-level Tk window — wires the editor and analysis panels together."""

    DEFAULT_SAMPLE = (
        "# MiniLang sample program\n"
        "INT a;\n"
        "INT b;\n"
        "INT c;\n"
        "INT d;\n"
        "INT x;\n"
        "INT y;\n"
        "\n"
        "a = 5 + 3;       # constant folding -> a = 8\n"
        "b = 10;\n"
        "b = 20;          # dead-code: first assignment removed\n"
        "x = a + b;\n"
        "y = a + b;       # CSE: reuses x's computation\n"
        "\n"
        "IF(x < 100){\n"
        "    c = x * 2;\n"
        "}\n"
        "\n"
        "WHILE(b < 25){\n"
        "    b = b + 1;\n"
        "}\n"
        "\n"
        "PRINT(b);\n"
        "PRINT(y);\n"
    )

    def __init__(self):
        super().__init__()
        self.title("MiniLang Compiler — SPCC Mini Project")
        self.geometry("1280x780")
        self.minsize(1024, 640)
        self.configure(bg=THEME["bg"])

        self._configure_styles()
        self._build_layout()
        self.editor.set(self.DEFAULT_SAMPLE)
        self._set_status("Ready", "info")

    # ------------------------------------------------------------ #
    # Theming
    # ------------------------------------------------------------ #
    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Notebook
        style.configure("TNotebook",
                        background=THEME["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=THEME["panel"], foreground=THEME["fg"],
                        padding=(14, 6), font=FONT_UI_BOLD, borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", THEME["panel_alt"])],
                  foreground=[("selected", THEME["accent"])])

        # Frames
        style.configure("TFrame", background=THEME["bg"])
        style.configure("Panel.TFrame", background=THEME["panel"])

        # Labels
        style.configure("TLabel",
                        background=THEME["bg"], foreground=THEME["fg"],
                        font=FONT_UI)
        style.configure("Title.TLabel",
                        background=THEME["bg"], foreground=THEME["accent"],
                        font=FONT_TITLE)
        style.configure("Status.TLabel",
                        background=THEME["panel"], foreground=THEME["fg"],
                        font=FONT_UI, padding=6)

        # Buttons
        style.configure("TButton",
                        background=THEME["accent"], foreground="#1a1a2e",
                        font=FONT_UI_BOLD, padding=(14, 6), borderwidth=0)
        style.map("TButton",
                  background=[("active", THEME["accent_alt"])])

        style.configure("Secondary.TButton",
                        background=THEME["panel_alt"], foreground=THEME["fg"],
                        font=FONT_UI_BOLD, padding=(14, 6), borderwidth=0)
        style.map("Secondary.TButton",
                  background=[("active", THEME["select"])])

        # Treeview
        style.configure("Treeview",
                        background=THEME["panel"], foreground=THEME["fg"],
                        fieldbackground=THEME["panel"],
                        font=FONT_MONO_SMALL, rowheight=22, borderwidth=0)
        style.configure("Treeview.Heading",
                        background=THEME["panel_alt"], foreground=THEME["accent"],
                        font=FONT_UI_BOLD, padding=4, borderwidth=0)
        style.map("Treeview",
                  background=[("selected", THEME["select"])],
                  foreground=[("selected", THEME["accent"])])

        # Scrollbars
        style.configure("Vertical.TScrollbar",
                        background=THEME["panel"], troughcolor=THEME["bg"],
                        bordercolor=THEME["bg"], arrowcolor=THEME["fg"])
        style.configure("Horizontal.TScrollbar",
                        background=THEME["panel"], troughcolor=THEME["bg"],
                        bordercolor=THEME["bg"], arrowcolor=THEME["fg"])

    # ------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------ #
    def _build_layout(self):
        # ----- Header ----- #
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=14, pady=(12, 6))
        ttk.Label(header,
                  text="MiniLang Compiler",
                  style="Title.TLabel").pack(side="left")
        ttk.Label(header,
                  text="  Lexical · Syntax · 3AC · Optimisation",
                  style="TLabel").pack(side="left", padx=10)

        # ----- Toolbar ----- #
        toolbar = ttk.Frame(self, style="TFrame")
        toolbar.pack(fill="x", padx=14, pady=(0, 8))

        ttk.Button(toolbar, text="▶  Compile", command=self.compile_source)\
            .pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Clear",
                   style="Secondary.TButton",
                   command=self.clear_all).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Open File",
                   style="Secondary.TButton",
                   command=self.open_file).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Save Output",
                   style="Secondary.TButton",
                   command=self.save_output).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Export TAC",
                   style="Secondary.TButton",
                   command=self.export_tac).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Reset",
                   style="Secondary.TButton",
                   command=self.reset_state).pack(side="left", padx=6)

        # ----- Main paned window ----- #
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=14, pady=4)

        # Left side: editor
        left = ttk.Frame(body, style="Panel.TFrame")
        body.add(left, weight=1)

        ttk.Label(left, text="  Source Code",
                  style="TLabel",
                  background=THEME["panel"],
                  foreground=THEME["accent"],
                  font=FONT_UI_BOLD).pack(fill="x")
        self.editor = CodeEditor(left)
        self.editor.pack(fill="both", expand=True, padx=4, pady=4)

        # Right side: notebook of analysis panels
        right = ttk.Frame(body, style="TFrame")
        body.add(right, weight=2)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)

        self._build_tokens_tab()
        self._build_symtab_tab()
        self._build_tac_tab()
        self._build_opt_tab()
        self._build_errors_tab()

        # ----- Status bar ----- #
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var,
                           style="Status.TLabel", anchor="w")
        status.pack(fill="x", side="bottom")
        self.status_label = status

    # ----- helper to build a Text-based output panel ----- #
    def _build_text_panel(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        text = tk.Text(frame,
                       wrap="none",
                       bg=THEME["panel"], fg=THEME["fg"],
                       insertbackground=THEME["fg"],
                       selectbackground=THEME["select"],
                       font=FONT_MONO_SMALL, relief="flat",
                       borderwidth=0, padx=8, pady=6)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        text.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return frame, text

    # ----- Tabs ----- #
    def _build_tokens_tab(self):
        frame = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(frame, text="Tokens")

        cols = ("token", "type", "line")
        self.tok_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c, w in zip(cols, (200, 140, 80)):
            self.tok_tree.heading(c, text=c.upper())
            self.tok_tree.column(c, width=w, anchor="w")
        vbar = ttk.Scrollbar(frame, orient="vertical",
                             command=self.tok_tree.yview)
        self.tok_tree.configure(yscrollcommand=vbar.set)
        self.tok_tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def _build_symtab_tab(self):
        frame = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(frame, text="Symbol Table")

        cols = ("name", "type", "value", "memory", "line")
        self.sym_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c, w in zip(cols, (160, 90, 110, 110, 80)):
            self.sym_tree.heading(c, text=c.upper())
            self.sym_tree.column(c, width=w, anchor="w")
        vbar = ttk.Scrollbar(frame, orient="vertical",
                             command=self.sym_tree.yview)
        self.sym_tree.configure(yscrollcommand=vbar.set)
        self.sym_tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def _build_tac_tab(self):
        frame, txt = self._build_text_panel(self.notebook)
        self.notebook.add(frame, text="3-Address Code")
        self.tac_text = txt

    def _build_opt_tab(self):
        frame, txt = self._build_text_panel(self.notebook)
        self.notebook.add(frame, text="Optimised Code")
        self.opt_text = txt

    def _build_errors_tab(self):
        frame, txt = self._build_text_panel(self.notebook)
        self.notebook.add(frame, text="Errors")
        txt.tag_configure("err", foreground=THEME["error"])
        txt.tag_configure("ok",  foreground=THEME["success"])
        self.err_text = txt

    # ------------------------------------------------------------ #
    # Compilation pipeline
    # ------------------------------------------------------------ #
    def compile_source(self):
        """Run all four phases on the editor's contents and update the UI."""
        source = self.editor.get()
        self._reset_panels()

        if not source.strip():
            self._set_status("Nothing to compile — editor is empty.", "warn")
            return

        symtab = SymbolTable()

        # ---- Phase 1: lexical analysis ---- #
        try:
            lexer = Lexer(source)
            tokens, lex_errors = lexer.tokenize()
        except Exception as e:    # pragma: no cover
            self._append_error(f"Internal lexer error: {e}", error=True)
            self._set_status("Compilation failed (lexer crash)", "error")
            return

        self._populate_tokens(tokens)

        # ---- Phase 2: syntax analysis ---- #
        try:
            parser = Parser(tokens, symtab)
            program, parse_errors = parser.parse()
        except Exception as e:    # pragma: no cover
            self._append_error(f"Internal parser error: {e}", error=True)
            self._set_status("Compilation failed (parser crash)", "error")
            return

        self._populate_symtab(symtab)

        all_errors = list(lex_errors) + list(parse_errors)

        # ---- Phase 3: 3AC generation ---- #
        # Only generate code if the program parsed cleanly enough to be useful.
        if program and not parse_errors and not lex_errors:
            try:
                tac_gen = TACGenerator()
                tac = tac_gen.generate(program)
                self.tac_text.delete("1.0", "end")
                self.tac_text.insert("1.0", format_tac(tac))

                # ---- Phase 4: optimisation ---- #
                optimised = optimize(tac)
                self.opt_text.delete("1.0", "end")
                self.opt_text.insert("1.0", format_tac(optimised))
            except Exception as e:    # pragma: no cover
                self._append_error(f"Internal codegen error: {e}", error=True)
        else:
            note = "(skipped — fix the errors above to see 3AC)"
            self.tac_text.insert("1.0", note)
            self.opt_text.insert("1.0", note)

        # ---- Errors panel ---- #
        if all_errors:
            for err in all_errors:
                self._append_error(err, error=True)
            self._set_status(
                f"Compilation finished with {len(all_errors)} error(s).",
                "error",
            )
            self.notebook.select(4)   # focus errors tab
        else:
            self._append_error("Compilation successful — no errors found.",
                               error=False)
            self._set_status("✓ Compilation successful", "success")
            self.notebook.select(2)   # focus 3AC tab

    # ------------------------------------------------------------ #
    # Toolbar actions
    # ------------------------------------------------------------ #
    def clear_all(self):
        self.editor.clear()
        self._reset_panels()
        self._set_status("Cleared.", "info")

    def reset_state(self):
        self.editor.set(self.DEFAULT_SAMPLE)
        self._reset_panels()
        self._set_status("Reset to default sample.", "info")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open MiniLang source",
            filetypes=[("MiniLang files", "*.txt *.minilang *.ml"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.set(f.read())
            self._set_status(f"Opened {os.path.basename(path)}", "info")
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def save_output(self):
        """Save a combined report of every output panel to a file."""
        path = filedialog.asksaveasfilename(
            title="Save compilation report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(" MiniLang Compilation Report\n")
                f.write("=" * 60 + "\n\n")

                f.write("[ SOURCE CODE ]\n")
                f.write(self.editor.get() + "\n\n")

                f.write("[ TOKENS ]\n")
                for child in self.tok_tree.get_children():
                    f.write(" | ".join(self.tok_tree.item(child)["values"].__iter__()
                                       if False else
                                       map(str, self.tok_tree.item(child)["values"]))
                            + "\n")
                f.write("\n")

                f.write("[ SYMBOL TABLE ]\n")
                for child in self.sym_tree.get_children():
                    f.write(" | ".join(map(str,
                            self.sym_tree.item(child)["values"])) + "\n")
                f.write("\n")

                f.write("[ THREE ADDRESS CODE ]\n")
                f.write(self.tac_text.get("1.0", "end-1c") + "\n\n")

                f.write("[ OPTIMISED CODE ]\n")
                f.write(self.opt_text.get("1.0", "end-1c") + "\n\n")

                f.write("[ ERRORS / MESSAGES ]\n")
                f.write(self.err_text.get("1.0", "end-1c") + "\n")
            self._set_status(f"Report saved to {os.path.basename(path)}",
                             "success")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def export_tac(self):
        """Write only the optimised 3AC to a file (handy for grading)."""
        path = filedialog.asksaveasfilename(
            title="Export Three Address Code",
            defaultextension=".tac",
            filetypes=[("TAC files", "*.tac *.txt"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Original 3AC\n")
                f.write(self.tac_text.get("1.0", "end-1c") + "\n\n")
                f.write("# Optimised 3AC\n")
                f.write(self.opt_text.get("1.0", "end-1c") + "\n")
            self._set_status(f"TAC exported to {os.path.basename(path)}",
                             "success")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    # ------------------------------------------------------------ #
    # Helpers for populating analysis panels
    # ------------------------------------------------------------ #
    def _reset_panels(self):
        for tree in (self.tok_tree, self.sym_tree):
            for c in tree.get_children():
                tree.delete(c)
        for txt in (self.tac_text, self.opt_text, self.err_text):
            txt.delete("1.0", "end")

    def _populate_tokens(self, tokens):
        for tok in tokens:
            if tok.type == "EOF":
                continue
            self.tok_tree.insert(
                "", "end", values=(tok.value, tok.type, tok.line)
            )

    def _populate_symtab(self, symtab: SymbolTable):
        for entry in symtab.all_entries():
            value = "—" if entry["value"] is None else entry["value"]
            self.sym_tree.insert(
                "", "end",
                values=(entry["name"], entry["type"],
                        value, entry["memory"], entry["line"]),
            )

    def _append_error(self, message: str, error: bool = True):
        tag = "err" if error else "ok"
        self.err_text.insert("end", message + "\n", tag)

    def _set_status(self, message: str, level: str = "info"):
        colour = {
            "info":    THEME["fg"],
            "success": THEME["success"],
            "warn":    THEME["warn"],
            "error":   THEME["error"],
        }.get(level, THEME["fg"])
        self.status_var.set(message)
        try:
            self.status_label.configure(foreground=colour)
        except tk.TclError:
            pass


def launch():
    """Entry point used by main.py."""
    app = CompilerGUI()
    app.mainloop()


if __name__ == "__main__":
    launch()
