"""Component registry: named, prop-validated recipes rendered as draw ops.

A component is a function ``render(props, theme, w, h) -> (ops, height)``
that draws at origin (0, 0) inside a box ``w`` points wide; the caller
offsets the ops to the target position. Components only name theme roles
and text styles, never raw colors or sizes, so a brand change is a theme
change. Two sources: built-ins (Python, ``builtin.py``) and user recipes
(JSON, ``recipes.py``), both listed by ``catalogue()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..themes import Theme

Render = Callable[[dict, Theme, float, "float | None"], tuple[list[dict], float]]

_TYPES = ("str", "markdown", "number", "bool", "list", "choice", "color", "dict", "image")


@dataclass
class Prop:
    name: str
    type: str
    description: str
    default: object = None
    required: bool = False
    choices: list[str] | None = None

    def schema(self) -> dict:
        out: dict = {"name": self.name, "type": self.type, "description": self.description}
        if self.default is not None:
            out["default"] = self.default
        if self.required:
            out["required"] = True
        if self.choices:
            out["choices"] = list(self.choices)
        return out


@dataclass
class Component:
    name: str
    description: str          # what it draws
    props: list[Prop]
    render: Render
    example: dict
    source: str = "builtin"
    tags: list[str] = field(default_factory=list)
    use: str = ""             # when to use it, and the close alternatives
    variants: list[dict] = field(default_factory=list)  # [{title, when, props, native?}]: other typical settings, shown in the catalogue
    intents: list[str] = field(default_factory=list)  # a recipe's own intentions; built-ins are in intents.INTENTS

    def schema(self) -> dict:
        from .intents import of

        out = {
            "name": self.name,
            "description": self.description,
            "use": self.use,
            "intents": of(self.name, self.intents),
            "source": self.source,
            "tags": list(self.tags),
            "props": [p.schema() for p in self.props],
            "example": {"props": self.example},
        }
        variants = self.variants or self.auto_variants()
        if variants:
            out["variants"] = [{"title": v["title"], "when": v.get("when", ""), "props": v["props"], **({"native": v["native"]} if v.get("native") else {})}
                               for v in variants]
        return out

    def auto_variants(self) -> list[dict]:
        """One variant per value of each ``choice`` prop the example does not use.

        A component without an entry in ``variants.VARIANTS`` still shows its modes
        in the catalogue: ``when`` is the prop's description, ``props`` the example
        with that value. Declare explicit variants when the modes worth showing are
        combinations of props or need a real *when*.
        """
        out = []
        for prop in self.props:
            if not prop.choices:
                continue
            current = self.example.get(prop.name, prop.default)
            for choice in prop.choices:
                if choice == current:
                    continue
                out.append({"title": f"{prop.name} = {choice}", "when": f"{prop.description} Réglage `{prop.name}: {choice!r}`.",
                            "props": {**self.example, prop.name: choice}})
        return out


_REGISTRY: dict[str, Component] = {}


def register(component: Component) -> Component:
    _REGISTRY[component.name] = component
    return component


def unregister(name: str) -> None:
    _REGISTRY.pop(name, None)


def names() -> list[str]:
    return sorted(_REGISTRY)


def get(name: str) -> Component:
    from . import recipes  # user recipes are picked up lazily

    recipes.load_user_recipes()
    if name not in _REGISTRY:
        raise ValueError(f"unknown component {name!r}; available: {', '.join(names())}")
    return _REGISTRY[name]


def catalogue() -> list[dict]:
    from . import recipes

    recipes.load_user_recipes()
    return [_REGISTRY[n].schema() for n in names()]


def validate(component: Component, props: dict | None) -> dict:
    """Fill defaults, reject unknown/missing/invalid props with precise messages."""
    props = dict(props or {})
    known = {p.name: p for p in component.props}
    unknown = [k for k in props if k not in known]
    if unknown:
        raise ValueError(
            f"unknown prop {unknown[0]!r} for {component.name}; props: {', '.join(known)}"
        )
    out: dict = {}
    for p in component.props:
        if p.name in props and props[p.name] is not None:
            value = props[p.name]
            if p.choices and value not in p.choices:
                raise ValueError(
                    f"prop {p.name!r} of {component.name} must be one of "
                    f"{', '.join(p.choices)}; got {value!r}"
                )
            out[p.name] = value
        elif p.required:
            raise ValueError(f"required prop {p.name!r} missing for {component.name}")
        else:
            out[p.name] = p.default
    return out


def render(name: str, props: dict | None, theme: Theme, w: float, h: float | None = None) -> tuple[list[dict], float]:
    """Render ``name`` with validated props; returns (ops at origin, height used)."""
    component = get(name)
    return component.render(validate(component, props), theme, w, h)


def shift(ops: list[dict], dx: float, dy: float) -> list[dict]:
    """Copy of ``ops`` translated by (dx, dy)."""
    out = []
    for op in ops:
        o = dict(op)
        for kx, ky in (("x", "y"), ("x1", "y1"), ("x2", "y2"), ("cx", "cy")):
            if kx in o:
                o[kx] = o[kx] + dx
                o[ky] = o[ky] + dy
        if "points" in o:
            o["points"] = [[x + dx, y + dy] for x, y in o["points"]]
        out.append(o)
    return out


from . import axes, blocks, brand, builtin, charts2, charts3, diagrams, flow, lists, mockups, people, reporting, schemes, training, workshop  # noqa: E402,F401  — registers the built-in components
from .uses import USES  # noqa: E402
from .variants import VARIANTS  # noqa: E402

for _name, _use in USES.items():
    _REGISTRY[_name].use = _use
for _name, _variants in VARIANTS.items():
    _REGISTRY[_name].variants = _variants
del _name, _use, _variants
