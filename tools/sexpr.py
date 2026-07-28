"""Minimal KiCad s-expression parser/serializer.

Atoms are kept as raw token strings (quoted strings keep their quotes), so
round-tripping stock library content is lossless enough for KiCad to accept.
Nodes are plain Python lists whose first element is normally an atom tag.
"""

from __future__ import annotations


def tokenize(text: str):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c in "()":
            yield c
            i += 1
            continue
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            yield text[i : j + 1]
            i = j + 1
            continue
        j = i
        while j < n and text[j] not in ' \t\r\n()"':
            j += 1
        yield text[i:j]
        i = j


def loads(text: str):
    """Parse text, returning the single top-level node."""
    stack = [[]]
    for tok in tokenize(text):
        if tok == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif tok == ")":
            stack.pop()
        else:
            stack[-1].append(tok)
    top = stack[0]
    if len(top) != 1:
        raise ValueError(f"expected 1 top-level node, got {len(top)}")
    return top[0]


def q(s: str) -> str:
    """Quote a python string as a kicad quoted-string atom."""
    esc = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def uq(atom: str) -> str:
    """Unquote a quoted atom (no-op for bare atoms)."""
    if isinstance(atom, str) and len(atom) >= 2 and atom[0] == '"' and atom[-1] == '"':
        return atom[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return atom


def dumps(node, indent: int = 0) -> str:
    """Serialize with light pretty-printing (KiCad is whitespace-agnostic)."""
    if not isinstance(node, list):
        return str(node)
    pad = "  " * indent
    # Small nodes with no child lists go on one line.
    if all(not isinstance(x, list) for x in node) or _flat_len(node) < 100:
        inner = " ".join(dumps(x, 0) for x in node)
        return f"({inner})"
    parts = [f"({node[0]}"] if node and not isinstance(node[0], list) else ["("]
    rest = node[1:] if parts[0] != "(" else node
    line = parts[0]
    out = []
    for x in rest:
        if isinstance(x, list):
            if line is not None:
                out.append(line)
                line = None
            out.append(pad + "  " + dumps(x, indent + 1))
        else:
            piece = str(x)
            if line is None:
                out.append(pad + "  " + piece)
            else:
                line += " " + piece
    if line is not None:
        out.append(line)
    out.append(pad + ")")
    return "\n".join(out)


def _flat_len(node) -> int:
    if not isinstance(node, list):
        return len(str(node)) + 1
    return 2 + sum(_flat_len(x) for x in node)


def tag(node) -> str | None:
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return None


def find_all(node, name: str):
    return [x for x in node if isinstance(x, list) and tag(x) == name]


def find(node, name: str):
    hits = find_all(node, name)
    return hits[0] if hits else None


def sym_name(sym_node) -> str:
    return uq(sym_node[1])


def load_symbol(lib_path: str, name: str):
    """Load a symbol by name from a .kicad_sym library, flattening `extends`."""
    with open(lib_path) as f:
        lib = loads(f.read())
    by_name = {sym_name(s): s for s in find_all(lib, "symbol")}
    if name not in by_name:
        raise KeyError(f"{name} not in {lib_path}")

    def flatten(n):
        node = by_name[n]
        ext = find(node, "extends")
        if not ext:
            return node
        parent = flatten(uq(ext[1]))
        # child properties override parent's; graphics/pins come from parent
        merged = [x for x in parent if tag(x) != "symbol" or True]
        merged = [list(x) if isinstance(x, list) else x for x in parent]
        child_props = {uq(p[1]): p for p in find_all(node, "property")}
        out = ["symbol", parent[1]]
        for x in merged[2:]:
            if tag(x) == "property" and uq(x[1]) in child_props:
                out.append(child_props.pop(uq(x[1])))
            else:
                out.append(x)
        for p in child_props.values():
            out.append(p)
        # rename: the flattened copy carries the child's name everywhere
        return rename_symbol(out, sym_name(node), old=sym_name(parent))

    return flatten(name)


def rename_symbol(sym_node, new_name: str, old: str | None = None):
    old = old or sym_name(sym_node)
    node = _deep_copy(sym_node)
    node[1] = q(new_name)
    for child in find_all(node, "symbol"):
        cn = sym_name(child)
        if cn.startswith(old):
            child[1] = q(new_name + cn[len(old) :])
    return node


def _deep_copy(node):
    if isinstance(node, list):
        return [_deep_copy(x) for x in node]
    return node


def pin_table(sym_node):
    """Return [(unit_suffix, number, name, electrical_type)] for a symbol."""
    rows = []
    base = sym_name(sym_node)
    for unit in find_all(sym_node, "symbol"):
        suffix = sym_name(unit)[len(base) :]
        for pin in find_all(unit, "pin"):
            num = name = ""
            for x in pin:
                if tag(x) == "number":
                    num = uq(x[1])
                elif tag(x) == "name":
                    name = uq(x[1])
            rows.append((suffix, num, name, pin[1]))
    return rows
