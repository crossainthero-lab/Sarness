"""Typed node graph primitives shared by the API process and the GPU worker.

This module must stay import-light (no torch) so the API can validate graphs
and publish the node library without touching the GPU.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Socket types
# ---------------------------------------------------------------------------
MODEL = "MODEL"                    # image diffusion pipeline handle
VIDEO_MODEL = "VIDEO_MODEL"        # video diffusion pipeline handle
CONDITIONING = "CONDITIONING"      # encoded image prompt
VIDEO_CONDITIONING = "VIDEO_CONDITIONING"
LATENT = "LATENT"
IMAGE = "IMAGE"                    # batch of RGB images
MASK = "MASK"                      # single-channel mask
VIDEO = "VIDEO"                    # frames + fps
SCHEDULER = "SCHEDULER"
UPSCALE_MODEL = "UPSCALE_MODEL"
CONTROL = "CONTROL"                # controlnet + hint image + strength
CONTROLNET = "CONTROLNET"          # loaded controlnet model
VAE = "VAE"
INT = "INT"
FLOAT = "FLOAT"
STRING = "STRING"
BOOLEAN = "BOOLEAN"
ANY = "ANY"

SOCKET_TYPES = [
    MODEL, VIDEO_MODEL, CONDITIONING, VIDEO_CONDITIONING, LATENT, IMAGE, MASK, VIDEO,
    SCHEDULER, UPSCALE_MODEL, CONTROL, CONTROLNET, VAE, INT, FLOAT, STRING, BOOLEAN, ANY,
]

# Display colours for the editor (Sarness Obsidian palette, no pink).
SOCKET_COLORS = {
    MODEL: "#a78bfa", VIDEO_MODEL: "#8b5cf6", CONDITIONING: "#fbbf24", VIDEO_CONDITIONING: "#f59e0b",
    LATENT: "#fb923c", IMAGE: "#60a5fa", MASK: "#94a3b8", VIDEO: "#38bdf8",
    SCHEDULER: "#34d399", UPSCALE_MODEL: "#2dd4bf", CONTROL: "#c4b5fd",
    CONTROLNET: "#818cf8", VAE: "#f87171", INT: "#a3e635", FLOAT: "#86efac", STRING: "#e5e7eb",
    BOOLEAN: "#fde68a", ANY: "#d4d4d8",
}

# Implicit coercions allowed when connecting sockets.
_COERCE = {(INT, FLOAT)}


def compatible(src: str, dst: str) -> bool:
    if src == dst or ANY in (src, dst):
        return True
    return (src, dst) in _COERCE


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------
@dataclass
class Socket:
    name: str
    type: str
    label: str | None = None
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "label": self.label or self.name.replace("_", " ").title(),
                "optional": self.optional}


@dataclass
class Param:
    """A widget value on a node. ``socket=True`` lets an edge override it."""

    name: str
    kind: str  # int|float|string|text|bool|enum|seed|model|file|color
    default: Any = None
    label: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[Any] | None = None
    model_category: str | None = None   # for kind == "model"
    model_family: list[str] | None = None
    file_accept: str | None = None      # for kind == "file": "image" | "video"
    socket: bool = False
    advanced: bool = False
    description: str | None = None
    optional: bool = False

    @property
    def socket_type(self) -> str:
        return {"int": INT, "seed": INT, "float": FLOAT, "bool": BOOLEAN}.get(self.kind, STRING)

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items() if v is not None}
        d["label"] = self.label or self.name.replace("_", " ").title()
        if self.socket:
            d["socket_type"] = self.socket_type
        return d

    def validate(self, value: Any) -> str | None:
        if value is None:
            return None if (self.optional or self.default is None) else f"'{self.name}' is required"
        k = self.kind
        if k in ("int", "seed"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
                return f"'{self.name}' must be an integer"
            if k == "seed" and value < 0:
                return None  # resolved to random before execution
        elif k == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return f"'{self.name}' must be a number"
        elif k == "bool":
            if not isinstance(value, bool):
                return f"'{self.name}' must be true/false"
        elif k in ("string", "text", "model", "file", "color"):
            if not isinstance(value, str):
                return f"'{self.name}' must be text"
            if k in ("model", "file") and not value and not self.optional:
                return f"'{self.name}' is required"
        elif k == "enum":
            if self.options and value not in [o["value"] if isinstance(o, dict) else o for o in self.options]:
                return f"'{self.name}' must be one of the listed options"
        if k in ("int", "float", "seed") and isinstance(value, (int, float)):
            if self.min is not None and value < self.min:
                return f"'{self.name}' must be ≥ {self.min}"
            if self.max is not None and value > self.max:
                return f"'{self.name}' must be ≤ {self.max}"
        return None


@dataclass
class NodeSpec:
    type: str
    title: str
    category: str
    description: str
    run: Callable[..., dict[str, Any]]
    inputs: list[Socket] = field(default_factory=list)
    outputs: list[Socket] = field(default_factory=list)
    params: list[Param] = field(default_factory=list)
    output_node: bool = False
    gpu: bool = False
    cacheable: bool = True
    # Passthrough nodes (reroute) adopt the type of what is connected to them.
    passthrough: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type, "title": self.title, "category": self.category,
            "description": self.description,
            "inputs": [s.to_dict() for s in self.inputs],
            "outputs": [s.to_dict() for s in self.outputs],
            "params": [p.to_dict() for p in self.params],
            "output_node": self.output_node, "gpu": self.gpu, "passthrough": self.passthrough,
            "tags": self.tags,
        }

    def input(self, name: str) -> Socket | None:
        return next((s for s in self.inputs if s.name == name), None)

    def output(self, name: str) -> Socket | None:
        return next((s for s in self.outputs if s.name == name), None)

    def param(self, name: str) -> Param | None:
        return next((p for p in self.params if p.name == name), None)


class WorkflowError(Exception):
    """Raised for a failure attributable to a specific node."""

    def __init__(self, message: str, node_id: str | None = None, *, oom: bool = False, hint: str | None = None):
        super().__init__(message)
        self.node_id = node_id
        self.oom = oom
        self.hint = hint


class Cancelled(Exception):
    pass


WORKFLOW_FORMAT = "sarness.workflow"
WORKFLOW_VERSION = 1
