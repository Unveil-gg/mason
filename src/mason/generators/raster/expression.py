"""Sandboxed raster expressions: formula -> PNG, then role:image."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
from PIL import Image

from mason.core.assets import LayeredRasterSpec, RasterLayer
from mason.core.jobs import AssetJob
from mason.core.styles import StyleProfile, hex_rgba
from mason.errors import MasonError

_BIN = {
    ast.Add: np.add,
    ast.Sub: np.subtract,
    ast.Mult: np.multiply,
    ast.Div: np.divide,
    ast.Pow: np.power,
    ast.Mod: np.mod,
}
_UNARY = {ast.UAdd: np.positive, ast.USub: np.negative}
_FUNCS = {
    "sin": np.sin,
    "cos": np.cos,
    "abs": np.abs,
    "min": np.minimum,
    "max": np.maximum,
    "sqrt": np.sqrt,
    "pow": np.power,
    "clamp": np.clip,
    "lerp": lambda a, b, t: np.add(
        np.multiply(a, np.subtract(1.0, t)),
        np.multiply(b, t),
    ),
    "noise": None,
}


def materialize_expressions(
    spec: LayeredRasterSpec,
    style: StyleProfile,
    job: AssetJob,
) -> LayeredRasterSpec:
    """Bake expression layers to PNGs. Returns a copy for the script."""
    layers: list[RasterLayer] = []
    out_dir = job.dir / "expressions"
    for layer in spec.layers:
        if layer.expression is None:
            layers.append(layer)
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{layer.name}.png"
        render_expression(layer, style, dest)
        layers.append(layer.model_copy(update={
            "image": str(dest),
            "expression": None,
        }))
    return spec.model_copy(update={"layers": layers})


def render_expression(
    layer: RasterLayer,
    style: StyleProfile,
    dest: Path,
) -> Path:
    """Evaluate layer.expression over its rect and write an RGBA PNG."""
    assert layer.expression is not None
    assert layer.rect is not None
    width = layer.rect.width
    height = layer.rect.height
    seed = float(layer.expression.seed)
    yy, xx = np.mgrid[0:height, 0:width]
    ctx = {
        "x": xx.astype(np.float32),
        "y": yy.astype(np.float32),
        "u": (xx / max(width - 1, 1)).astype(np.float32),
        "v": (yy / max(height - 1, 1)).astype(np.float32),
        "w": np.float32(width),
        "h": np.float32(height),
        "seed": np.float32(seed),
    }
    value = np.clip(
        _eval_formula(layer.expression.formula, ctx), 0.0, 1.0,
    )
    rgba = _to_rgba(layer, style, value)
    Image.fromarray(rgba, mode="RGBA").save(dest)
    return dest


def _to_rgba(
    layer: RasterLayer,
    style: StyleProfile,
    value: np.ndarray,
) -> np.ndarray:
    assert layer.fill is not None
    assert layer.expression is not None
    src = np.array(hex_rgba(style.color(layer.fill)), dtype=np.float32)
    opacity = float(layer.opacity)
    if layer.expression.mode == "color":
        if not layer.expression.to:
            raise MasonError(
                "expression color mode needs 'to'.",
                code="expression_to",
            )
        dst = np.array(
            hex_rgba(style.color(layer.expression.to)),
            dtype=np.float32,
        )
        mix = value[..., None]
        rgb = src[:3] * (1.0 - mix) + dst[:3] * mix
        alpha = np.full(value.shape, src[3] * opacity, dtype=np.float32)
    else:
        rgb = np.broadcast_to(src[:3], value.shape + (3,))
        alpha = value * src[3] * opacity
    out = np.empty(value.shape + (4,), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return out


def _eval_formula(formula: str, ctx: dict) -> np.ndarray:
    """Evaluate a tiny AST. No names, attrs, or calls outside the
    allowlist. Returns a float32 array shaped like x/y."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise MasonError(
            f"Invalid expression: {exc}",
            code="expression_syntax",
        ) from exc
    result = _eval(tree.body, ctx)
    return np.asarray(result, dtype=np.float32)


def _eval(node: ast.AST, ctx: dict):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return np.float32(node.value)
    if isinstance(node, ast.Name):
        if node.id not in ctx:
            raise MasonError(
                f"Unknown expression name '{node.id}'.",
                code="expression_name",
                hint="Use x y u v w h seed, or sin/cos/abs/min/max/"
                     "sqrt/pow/clamp/lerp/noise.",
            )
        return ctx[node.id]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand, ctx))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](
            _eval(node.left, ctx), _eval(node.right, ctx),
        )
    if isinstance(node, ast.Call):
        return _call(node, ctx)
    raise MasonError(
        "Unsupported expression node.",
        code="expression_node",
    )


def _call(node: ast.Call, ctx: dict):
    if not isinstance(node.func, ast.Name) or node.keywords:
        raise MasonError(
            "Expression calls must be bare allowlisted names.",
            code="expression_call",
        )
    name = node.func.id
    if name not in _FUNCS:
        raise MasonError(
            f"Unknown expression function '{name}'.",
            code="expression_func",
        )
    args = [_eval(arg, ctx) for arg in node.args]
    if name == "noise":
        if len(args) < 2:
            raise MasonError(
                "noise(u, v[, seed]) needs two coordinates.",
                code="expression_noise",
            )
        seed = args[2] if len(args) > 2 else ctx["seed"]
        return _noise(args[0], args[1], seed)
    if name == "clamp" and len(args) != 3:
        raise MasonError(
            "clamp(v, lo, hi) needs three arguments.",
            code="expression_clamp",
        )
    return _FUNCS[name](*args)


def _noise(u, v, seed) -> np.ndarray:
    """Value noise in [0, 1]."""
    u = np.asarray(u, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    s = float(np.asarray(seed).reshape(-1)[0])
    i0 = np.floor(u)
    j0 = np.floor(v)
    fu = u - i0
    fv = v - j0
    su = fu * fu * (3.0 - 2.0 * fu)
    sv = fv * fv * (3.0 - 2.0 * fv)

    def _hash(a, b):
        n = np.sin((a * 127.1 + b * 311.7 + s * 74.7) * math.pi / 180.0)
        return n - np.floor(n)

    n00 = _hash(i0, j0)
    n10 = _hash(i0 + 1.0, j0)
    n01 = _hash(i0, j0 + 1.0)
    n11 = _hash(i0 + 1.0, j0 + 1.0)
    nx0 = n00 * (1.0 - su) + n10 * su
    nx1 = n01 * (1.0 - su) + n11 * su
    return (nx0 * (1.0 - sv) + nx1 * sv).astype(np.float32)
