"""User recipes: components written as JSON, no code.

A recipe is::

    {"name": "pill_row", "description": "…",
     "props": {"items": {"type": "list", "description": "…", "required": true},
               "fill":  {"type": "color", "description": "…", "default": "accent"}},
     "height": "16",
     "ops": [
       {"each": "items", "as": "item", "ops": [
         {"op": "box", "x": "i * 70", "y": 0, "w": 64, "h": 16, "fill": "{fill}", "text": "{item}"}]},
       {"op": "text", "x": 0, "y": 20, "w": "w", "h": 12, "text": "{len(items)} pastilles"}]}

Two kinds of templating, both fed with the props plus ``w``, ``h`` and,
inside an ``each`` block, ``i``, ``n`` and the item:

- numeric keys (x, y, w, h, x1…, cx, cy, r, weight, size…) are *expressions*:
  ``"i * (64 + gap)"``, ``"w / 2"``, ``"len(items) * 26"`` — arithmetic,
  names from the context, ``min/max/round/abs/len``; nothing else;
- string keys are *templates*: ``"{item}"``, ``"{row.name} : {row.value}"``,
  ``"{len(items)} pastilles"`` — anything between braces is an expression.

Recipes live in ``~/.gslides-mcp/components/<name>.json`` and are picked up
by ``list_components`` / ``insert_component`` like built-ins. ``save``
dry-renders the recipe with sample props so a broken op is reported with its
index instead of failing on the first real insert.
"""

from __future__ import annotations

import ast
import json
import operator
import re
import sys
from pathlib import Path

from . import _REGISTRY, Component, Prop, register, unregister, validate

USER_COMPONENT_DIR = Path.home() / ".gslides-mcp" / "components"

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")
_NUMERIC_KEYS = {
    "x", "y", "w", "h", "x1", "y1", "x2", "y2", "cx", "cy", "r", "a0", "a1",
    "size", "weight", "thickness", "row_h", "spacing", "start", "value",
}
_FUNCS = {"min": min, "max": max, "round": round, "abs": abs, "len": len, "int": int, "float": float}
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}


class _Sample(dict):
    """Stand-in list item for dry runs: any field reads as '', str() is 'sample'."""

    def __missing__(self, key):
        return ""

    def __str__(self):
        return "sample"


# --- expression evaluation ---------------------------------------------------------

def _lookup(ctx: dict, dotted: str):
    cur = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict) and (part in cur or isinstance(cur, _Sample)):
            cur = cur[part]
        elif hasattr(cur, part) and not part.startswith("_"):
            cur = getattr(cur, part)
        else:
            raise ValueError(f"undefined name {dotted!r}")
    return cur


def _eval_node(node: ast.AST, ctx: dict, src: str):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ctx, src)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
        return node.value
    if isinstance(node, ast.Name):
        return _lookup(ctx, node.id)
    if isinstance(node, ast.Attribute):
        return _lookup(ctx, _dotted(node))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval_node(node.left, ctx, src), _eval_node(node.right, ctx, src))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval_node(node.operand, ctx, src))
    if isinstance(node, ast.Subscript):
        return _eval_node(node.value, ctx, src)[_eval_node(node.slice, ctx, src)]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in _FUNCS:
            raise ValueError(f"call to {node.func.id!r} not allowed in {src!r}")
        return _FUNCS[node.func.id](*[_eval_node(a, ctx, src) for a in node.args])
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval_node(e, ctx, src) for e in node.elts]
    raise ValueError(f"unsupported expression {src!r}")


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        raise ValueError("unsupported attribute access")
    parts.append(node.id)
    return ".".join(reversed(parts))


def evaluate(expr, ctx: dict):
    """Number as-is; string → arithmetic expression over the context."""
    if not isinstance(expr, str):
        return expr
    src = expr
    try:
        tree = ast.parse(src.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"bad expression {expr!r}: {exc.msg}") from None
    return _eval_node(tree, ctx, expr)


def _substitute(template: str, ctx: dict) -> str:
    """Replace every ``{expression}`` with its evaluated value."""
    return _PLACEHOLDER.sub(lambda m: _fmt(evaluate(m.group(1), ctx)), template)


def _fmt(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _render_value(key: str, value, ctx: dict):
    if isinstance(value, str):
        return evaluate(value, ctx) if key in _NUMERIC_KEYS else _substitute(value, ctx)
    if isinstance(value, list):
        return [_render_value(key, v, ctx) for v in value]
    if isinstance(value, dict):
        return {k: _render_value(k, v, ctx) for k, v in value.items()}
    return value


def expand(ops: list[dict], ctx: dict) -> list[dict]:
    """Resolve templates/expressions and unroll ``each`` blocks."""
    out: list[dict] = []
    for op in ops:
        if "each" in op:
            items = _lookup(ctx, op["each"])
            alias = op.get("as", "item")
            n = len(items)
            for i, item in enumerate(items):
                out.extend(expand(op.get("ops", []), {**ctx, alias: item, "i": i, "n": n}))
        else:
            out.append({k: _render_value(k, v, ctx) for k, v in op.items()})
    return out


# --- recipe → component ---------------------------------------------------------------

_SAMPLE_BY_TYPE = {"list": [_Sample()], "number": 1, "bool": False, "color": "accent", "dict": _Sample()}


def _prop(name: str, spec: dict) -> Prop:
    return Prop(name=name, type=spec.get("type", "str"), description=spec.get("description", ""),
                default=spec.get("default"), required=bool(spec.get("required", False)), choices=spec.get("choices"))


def _height(recipe: dict, ops: list[dict], ctx: dict) -> float:
    if recipe.get("height") is not None:
        return float(evaluate(recipe["height"], ctx))
    bottoms = [float(o.get("y", 0)) + float(o.get("h", 0)) for o in ops if "y" in o]
    return max(bottoms) if bottoms else 0.0


def parse(recipe: dict) -> Component:
    """Validate a recipe (schema + dry render) and build its Component."""
    from .. import draw, themes

    name = recipe.get("name")
    if not name or not _NAME_RE.match(str(name)):
        raise ValueError("recipe needs a 'name': lowercase letters, digits, underscores, 2–40 chars")
    if name in _REGISTRY and _REGISTRY[name].source == "builtin":
        raise ValueError(f"{name!r} is a built-in component; pick another name")
    if not isinstance(recipe.get("ops"), list):
        raise ValueError(f"recipe {name!r} needs an 'ops' list")
    props = [_prop(k, v or {}) for k, v in (recipe.get("props") or {}).items()]

    def render(p: dict, theme, w: float, h: float | None) -> tuple[list[dict], float]:
        ctx = {**p, "w": w, "h": h}
        ops: list[dict] = []
        for idx, op in enumerate(recipe["ops"]):
            try:
                expanded = expand([op], ctx)
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise ValueError(f"recipe {name!r}: ops[{idx}] {exc}") from None
            for o in expanded:
                if o.get("op") not in draw._OPS:
                    raise ValueError(f"recipe {name!r}: ops[{idx}] unknown draw op {o.get('op')!r}")
            ops.extend(expanded)
        return ops, (h if h is not None else _height(recipe, ops, {**ctx, "n": len(ops)}))

    component = Component(
        name=name, description=str(recipe.get("description", "")), props=props, render=render,
        example=dict(recipe.get("example") or {p.name: p.default for p in props if p.default is not None}),
        source="recipe", tags=list(recipe.get("tags") or []), use=str(recipe.get("use", "")),
    )
    # dry run with sample props: a broken op fails here, with its index
    sample = {p.name: (p.default if p.default is not None else _SAMPLE_BY_TYPE.get(p.type, "sample"))
              for p in props}
    ops, _ = render(validate(component, sample), themes.load("default"), 300, None)
    try:
        draw.ops_to_requests("dry", ops, themes.load("default"), prefix="dry")
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"recipe {name!r}: {exc}") from None
    return component


def save(recipe: dict) -> Path:
    component = parse(recipe)
    USER_COMPONENT_DIR.mkdir(parents=True, exist_ok=True)
    path = USER_COMPONENT_DIR / f"{component.name}.json"
    path.write_text(json.dumps(recipe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    register(component)
    return path


def delete(name: str) -> None:
    if not _NAME_RE.match(str(name)):  # the name becomes a file path
        raise ValueError(f"invalid component name {name!r}")
    if name in _REGISTRY and _REGISTRY[name].source == "builtin":
        raise ValueError(f"{name!r} is a built-in component and can't be deleted")
    path = USER_COMPONENT_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
    unregister(name)


def load_user_recipes() -> None:
    """Register every recipe found in the user directory (idempotent)."""
    if not USER_COMPONENT_DIR.is_dir():
        return
    for path in sorted(USER_COMPONENT_DIR.glob("*.json")):
        if path.stem in _REGISTRY:
            continue
        try:
            register(parse(json.loads(path.read_text(encoding="utf-8"))))
        except Exception as exc:  # a broken recipe must not take the catalogue down
            print(f"gslides-mcp: skipping recipe {path.name}: {exc}", file=sys.stderr)
