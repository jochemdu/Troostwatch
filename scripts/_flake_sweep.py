# Conservative flake8 sweep script
# - For each .py in scripts/, replace print(f"...") with print("...")
#   only when the f-string contains no '{' or '}' characters.
# - Strip trailing whitespace from all lines.
# - Creates a .bak copy before editing.

import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

PRINT_F_RE = re.compile(r"print\(f(\"|')(.*?)(\1)\)", re.DOTALL)

for p in SCRIPTS_DIR.glob("*.py"):
    if p.name == "_flake_sweep.py":
        continue
    txt = p.read_text(encoding="utf-8")
    orig = txt
    # Replace print(f"...") only if no braces inside

    def repl(m):
        inner = m.group(2)
        if "{" in inner or "}" in inner:
            return m.group(0)
        # return print("inner") preserving same quote type
        quote = m.group(1)
        return f"print({quote}{inner}{quote})"

    txt = PRINT_F_RE.sub(repl, txt)
    # Strip trailing whitespace from lines
    lines = [ln.rstrip() for ln in txt.splitlines()]
    txt = "\n".join(lines) + ("\n" if txt.endswith("\n") else "")

    if txt != orig:
        bak = p.with_suffix(p.suffix + ".bak")
        bak.write_text(orig, encoding="utf-8")
        p.write_text(txt, encoding="utf-8")
        print(f"Updated {p.name} (backup: {bak.name})")

print("Sweep complete")
