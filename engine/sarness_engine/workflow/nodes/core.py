"""Value, utility and routing nodes."""

from __future__ import annotations

import math

from ..registry import node
from ..types import ANY, BOOLEAN, FLOAT, INT, STRING, Param, Socket


@node("util.reroute", title="Reroute", category="Utility", passthrough=True,
      description="Passes a connection through unchanged; use it to tidy wiring.",
      inputs=[Socket("in", ANY, "In")], outputs=[Socket("out", ANY, "Out")])
def reroute(ctx, inputs, params):
    return {"out": inputs.get("in")}


@node("value.int", title="Integer", category="Values",
      outputs=[Socket("value", INT)], params=[Param("value", "int", 0)])
def value_int(ctx, inputs, params):
    return {"value": int(params["value"])}


@node("value.float", title="Float", category="Values",
      outputs=[Socket("value", FLOAT)], params=[Param("value", "float", 1.0, step=0.01)])
def value_float(ctx, inputs, params):
    return {"value": float(params["value"])}


@node("value.string", title="Text", category="Values",
      outputs=[Socket("value", STRING)], params=[Param("value", "text", "")])
def value_string(ctx, inputs, params):
    return {"value": str(params["value"])}


@node("value.bool", title="Boolean", category="Values",
      outputs=[Socket("value", BOOLEAN)], params=[Param("value", "bool", True)])
def value_bool(ctx, inputs, params):
    return {"value": bool(params["value"])}


@node("value.seed", title="Seed", category="Values", description="A seed; −1 picks a random one per run.",
      outputs=[Socket("seed", INT)], params=[Param("seed", "seed", -1, min=-1, max=2**32 - 1)])
def value_seed(ctx, inputs, params):
    return {"seed": int(params["seed"])}


_OPS = {
    "add": lambda a, b: a + b, "subtract": lambda a, b: a - b, "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b if b else math.nan, "min": min, "max": max,
    "power": lambda a, b: a ** b, "modulo": lambda a, b: a % b if b else math.nan,
}


@node("util.math", title="Math", category="Utility",
      inputs=[Socket("a", FLOAT, optional=True), Socket("b", FLOAT, optional=True)],
      outputs=[Socket("float", FLOAT), Socket("int", INT)],
      params=[Param("op", "enum", "add", options=list(_OPS)),
              Param("a_value", "float", 0.0, label="A (if unconnected)"),
              Param("b_value", "float", 0.0, label="B (if unconnected)")])
def util_math(ctx, inputs, params):
    a = inputs.get("a", params["a_value"])
    b = inputs.get("b", params["b_value"])
    r = _OPS[params["op"]](float(a), float(b))
    return {"float": r, "int": int(r) if math.isfinite(r) else 0}


@node("util.text_join", title="Join Text", category="Prompt",
      description="Concatenate text fragments, e.g. a style suffix onto a prompt.",
      inputs=[Socket("a", STRING, optional=True), Socket("b", STRING, optional=True)],
      outputs=[Socket("text", STRING)],
      params=[Param("a_text", "text", "", label="A (if unconnected)"),
              Param("b_text", "text", "", label="B (if unconnected)"),
              Param("separator", "string", ", ")])
def text_join(ctx, inputs, params):
    parts = [inputs.get("a", params["a_text"]), inputs.get("b", params["b_text"])]
    return {"text": params["separator"].join(p for p in parts if p)}


@node("util.switch", title="Switch", category="Utility",
      description="Selects one of two inputs based on a boolean.",
      inputs=[Socket("on_true", ANY, "If true"), Socket("on_false", ANY, "If false")],
      outputs=[Socket("out", ANY)],
      params=[Param("condition", "bool", True, socket=True)])
def switch(ctx, inputs, params):
    return {"out": inputs["on_true"] if params["condition"] else inputs["on_false"]}
