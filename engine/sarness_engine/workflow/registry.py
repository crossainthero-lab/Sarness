"""Node type registry. Node modules register themselves on import."""

from __future__ import annotations

from typing import Any, Callable

from .types import NodeSpec, Param, Socket

_REGISTRY: dict[str, NodeSpec] = {}
_LOADED = False


def node(type: str, *, title: str, category: str, description: str = "",
         inputs: list[Socket] | None = None, outputs: list[Socket] | None = None,
         params: list[Param] | None = None, output_node: bool = False, gpu: bool = False,
         cacheable: bool = True, passthrough: bool = False, tags: list[str] | None = None) -> Callable:
    def deco(fn: Callable[..., dict[str, Any]]):
        if type in _REGISTRY:
            raise ValueError(f"duplicate node type {type}")
        _REGISTRY[type] = NodeSpec(
            type=type, title=title, category=category, description=description or (fn.__doc__ or "").strip(),
            run=fn, inputs=inputs or [], outputs=outputs or [], params=params or [],
            output_node=output_node, gpu=gpu, cacheable=cacheable, passthrough=passthrough, tags=tags or [],
        )
        return fn

    return deco


def load_builtin_nodes() -> None:
    global _LOADED
    if _LOADED:
        return
    from .nodes import core, diffusion, image, output, upscale, video  # noqa: F401

    _LOADED = True


def get(type: str) -> NodeSpec | None:
    load_builtin_nodes()
    return _REGISTRY.get(type)


def all_specs() -> list[NodeSpec]:
    load_builtin_nodes()
    return sorted(_REGISTRY.values(), key=lambda s: (s.category, s.title))


CATEGORY_ORDER = [
    "Loaders", "Prompt", "Latent", "Sampling", "Schedulers", "VAE", "Conditioning", "Control",
    "Image", "Mask", "Transform", "Video", "Upscale", "Output", "Values", "Utility",
]
