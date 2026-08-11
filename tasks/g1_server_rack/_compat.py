# Copyright (c) 2025. License: Apache License, Version 2.0
"""Best-effort compatibility shims for running this IsaacLab checkout (which
targets Isaac Sim 5.x) against the Isaac Sim 6.0 runtime installed here.

Isaac Sim 6.0 renamed a few kit modules. IsaacLab still imports the old paths, so
without a shim ``import isaaclab.assets`` fails at module load. :func:`apply`
aliases the known-renamed modules in ``sys.modules`` *after* the app has started
(the target modules only exist once kit has loaded their extensions) and *before*
isaaclab is imported. Each shim is guarded: it is a no-op when the old path
already resolves, so this is harmless on a matched 5.x stack.

This is a stop-gap, not a substitute for a version-matched stack. If it ends up
chasing many renames, that is the signal to instead run a 6.0-compatible
IsaacLab (or Isaac Sim 5.1, which the unitree repo targets).
"""

from __future__ import annotations

import importlib
import sys
import types


def _alias_submodule(old: str, new: str) -> bool:
    """Make ``old`` resolve to the module at ``new`` (and register it).

    Returns True if a shim was installed, False if unnecessary/unavailable.
    """
    if old in sys.modules:
        return False
    try:
        importlib.import_module(old)
        return False  # old path already works (matched stack)
    except ModuleNotFoundError:
        pass
    try:
        target = importlib.import_module(new)
    except ModuleNotFoundError:
        return False  # new path not present either; nothing we can do here
    sys.modules[old] = target
    return True


def apply() -> list[str]:
    """Install known Isaac Sim 6.0 -> 5.x module shims. Returns those applied."""
    applied: list[str] = []

    # omni.physics.tensors.impl(.api) -> omni.physics.tensors(.api)
    try:
        importlib.import_module("omni.physics.tensors.impl.api")
    except ModuleNotFoundError:
        try:
            api = importlib.import_module("omni.physics.tensors.api")
            impl = types.ModuleType("omni.physics.tensors.impl")
            impl.api = api  # type: ignore[attr-defined]
            sys.modules["omni.physics.tensors.impl"] = impl
            sys.modules["omni.physics.tensors.impl.api"] = api
            applied.append("omni.physics.tensors.impl.api -> omni.physics.tensors.api")

            # 6.0 also renamed the deformable view classes. isaaclab references
            # the old names at import time (type hints), so alias them onto the
            # api module. These are for deformable assets this scene doesn't use.
            renames = {
                "SoftBodyView": "DeformableBodyView",
                "SoftBodyMaterialView": "DeformableMaterialView",
            }
            for old_name, new_name in renames.items():
                if not hasattr(api, old_name) and hasattr(api, new_name):
                    setattr(api, old_name, getattr(api, new_name))
                    applied.append(f"api.{old_name} -> api.{new_name}")
        except ModuleNotFoundError:
            pass

    return applied
