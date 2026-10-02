"""List every TreeMap read in Load context that is not guarded by ``_read``.

``TreeMap.__getitem__`` raises ``KeyError`` for an unwritten key — measured, not
assumed — so an unguarded read is a write-before-read bug waiting for the state
that does not write that key. Used to drive the M4 hardening pass.
"""
import ast
import pathlib
import sys


def main() -> int:
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "contracts/contest_receipt.py")
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ContestReceipt")

    treemaps = set()
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if "TreeMap" in ast.dump(node.annotation):
                treemaps.add(node.target.id)

    reads = []
    for node in ast.walk(cls):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
            and node.value.attr in treemaps
            and isinstance(node.ctx, ast.Load)
        ):
            reads.append((node.lineno, node.value.attr))

    print(f"{len(treemaps)} TreeMaps declared; {len(reads)} unguarded reads")
    for line, name in sorted(reads):
        print(f"  {line}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
