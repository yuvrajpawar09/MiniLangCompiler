# MiniLang Compiler

A Python-based mini compiler with a Tkinter GUI, built for the
**Systems Programming and Compiler Construction (SPCC)** university
course. The project demonstrates the four classical phases of compiler
construction on a small custom language called **MiniLang**:

1. Lexical Analysis
2. Syntax Analysis (recursive-descent parser)
3. Intermediate Code Generation (Three Address Code)
4. Code Optimisation (Constant Folding, Dead Code Elimination, Common
   Subexpression Elimination)

---

## Features

- Clean, modular Python source — one file per compiler phase.
- Custom MiniLang grammar with declarations, assignments, IF / ELSE,
  WHILE loops and PRINT statements.
- Recursive-descent parser with synchronisation-based error recovery.
- 3AC generator using temporary variables (`t1`, `t2`, …) and labels
  (`L1`, `L2`, …).
- Three independent optimisation passes that can be inspected
  side-by-side with the original 3AC.
- Polished dark-theme Tkinter GUI with line numbers, syntax
  highlighting, scrollbars, status bar, error console and tabbed output
  panels.
- Open / Save source files, save full compilation report, export only
  the generated TAC, reset the compiler state.
- Friendly, beginner-readable code with comments explaining every
  phase — perfect for viva preparation.

---

## Project structure

```
MiniLangCompiler/
├── main.py                 # Entry point (boots the GUI)
├── lexer.py                # Phase 1 — Lexical analyser
├── parser.py               # Phase 2 — Syntax analyser
├── intermediate_code.py    # Phase 3 — Three Address Code generator
├── optimizer.py            # Phase 4 — Optimisation passes
├── symbol_table.py         # Symbol table data structure
├── gui.py                  # Tkinter GUI front-end
├── utils.py                # Shared constants and helpers
├── sample_inputs/
│   ├── valid_program.txt
│   └── invalid_program.txt
├── requirements.txt
└── README.md
```

---

## Setup & running

The project relies only on the Python standard library (Tkinter).

### Windows / macOS

```
python --version          # must be 3.10 or newer
cd MiniLangCompiler
python main.py
```

### Linux

If your distribution does not bundle Tkinter, install it first:

```
sudo apt install python3-tk
python3 main.py
```

No `pip install` step is required.

---

## MiniLang language reference

### Keywords

`INT`, `IF`, `ELSE`, `WHILE`, `PRINT`

### Operators

Arithmetic: `+ - * /`
Assignment: `=`
Relational: `< > <= >= == !=`

### Delimiters

`;` `(` `)` `{` `}`

### Statement examples

```
INT a;                    # declaration
a = b + 5;                # assignment
IF(a < b){                # conditional
    c = a + b;
}
WHILE(a < 10){            # loop
    a = a + 1;
}
PRINT(a);                 # output
```

Comments begin with `#` and run to the end of the line.

### Grammar (BNF)

```
program     -> stmt_list
stmt_list   -> stmt stmt_list | epsilon
stmt        -> declaration | assignment | if_stmt | while_stmt | print_stmt
declaration -> INT id ;
assignment  -> id = expr ;
if_stmt     -> IF ( condition ) { stmt_list } [ELSE { stmt_list }]
while_stmt  -> WHILE ( condition ) { stmt_list }
print_stmt  -> PRINT ( expr ) ;
condition   -> expr relop expr
expr        -> term expr_prime
expr_prime  -> + term expr_prime | - term expr_prime | epsilon
term        -> factor term_prime
term_prime  -> * factor term_prime | / factor term_prime | epsilon
factor      -> id | number | ( expr )
```

---

## Example input / output

### Input

```
INT a;
INT b;
INT x;
INT y;

a = 5 + 3;
b = 10;
x = a + b;
y = a + b;
PRINT(y);
```

### Original Three-Address Code

```
  1: decl a
  2: decl b
  3: decl x
  4: decl y
  5: t1 = 5 + 3
  6: a = t1
  7: b = 10
  8: t2 = a + b
  9: x = t2
 10: t3 = a + b
 11: y = t3
 12: print y
```

### Optimised Three-Address Code

```
  1: decl a
  2: decl b
  3: decl x
  4: decl y
  5: a = 8                # constant folding
  6: b = 10
  7: t2 = a + b
  8: x = t2
  9: t3 = t2              # common subexpression elimination
 10: y = t3
 11: print y
```

(Indices may vary slightly because dead-code elimination renumbers the
output.)

---

## Optimisation techniques in detail

### 1. Constant Folding

If both operands of an arithmetic instruction are integer literals, the
optimiser pre-computes the value and rewrites the instruction as a
direct assignment. Constants are also propagated forward so chained
expressions collapse on subsequent passes.

### 2. Dead Code Elimination

A backwards liveness analysis builds a `live` set of variables whose
values are still needed. Any plain assignment whose target is not in
`live` is dropped. Side-effecting instructions (`print`, jumps, labels,
declarations) are always preserved.

### 3. Common Subexpression Elimination

Inside a basic block (terminated by labels or jumps) the optimiser
remembers every `(op, arg1, arg2)` triple it has seen. If the same
expression is computed again, the second instruction is replaced by a
copy from the first temporary. Commutative operators (`+`, `*`) are
matched in either argument order.

---

## Error handling

Every phase reports problems with a line number prefix:

```
Line 4: Invalid symbol '@'
Line 6: Expected ';' but found 'PRINT'
Line 7: Variable 'c' used before declaration
```

Lexical errors are caught while scanning, syntax errors during parsing,
and simple semantic errors (use-before-declare, redeclaration) during
parsing as well. The parser uses statement-level synchronisation so a
single mistake does not cascade into a flood of follow-on errors.

---

## Sample programs

Open either of the files inside `sample_inputs/` from the GUI:

- `valid_program.txt` — exercises every supported construct and shows
  all three optimisation techniques at work.
- `invalid_program.txt` — intentionally contains lexical, syntax and
  semantic errors so you can see the error console in action.

---

## Viva explanation notes

- **Why a symbol table?** It centralises information about every
  declared name (type, value, memory offset, declaration line) and lets
  the parser detect use-before-declaration errors.
- **Why recursive descent?** The MiniLang grammar is LL(1), which maps
  one-to-one onto a hand-written recursive descent parser — simple to
  write, easy to extend, and excellent for teaching.
- **Why generate 3AC?** Three-Address Code is a flat, low-level
  representation that decouples the front-end from any particular
  target machine. It is also the natural input format for classical
  optimisation algorithms.
- **Why optimise on 3AC instead of the AST?** Many optimisations (CSE,
  liveness, copy propagation) are easiest to express in terms of
  individual quadruples and basic blocks.
- **Why iterate the optimiser?** Folding can expose new dead code; CSE
  can enable further folding. The optimiser therefore runs the three
  passes up to three times or until a fixed point is reached.

---

## Screenshots

(Add screenshots of the GUI showing the source editor, tokens, symbol
table, original 3AC, optimised 3AC, and error console here.)

```
docs/
├── 01-editor.png
├── 02-tokens.png
├── 03-symbol-table.png
├── 04-original-tac.png
├── 05-optimised-tac.png
└── 06-errors.png
```

---

## Author

Built as a Systems Programming and Compiler Construction (SPCC) mini
project. Contributions, suggestions and bug reports are welcome.
