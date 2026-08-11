#!/usr/bin/env python
# Copyright (c) 2025. License: Apache License, Version 2.0
"""Bake a swappable BACKGROUND (office room + props + lighting + tray + spare
SSDs) into a single self-contained USD that the registered IsaacLab task
references as one ``AssetBaseCfg`` (mirroring how the repo references
``small_warehouse_digital_twin.usd``).

Why bake: the registered ManagerBasedRLEnv builds its scene purely from cfg
(``UsdFileCfg`` etc.); it has no hook for the procedural stage-authoring the
standalone preview uses. Baking turns the procedural environment into a cfg-
referable asset while keeping the interactive objects (rack, server, the bay-4
SSD "object") as separate addressable cfg entities.

Torch-free (raw Isaac Sim + USD). Run:

    ISAAC=/home/admin/isaac-sim/isaac-sim-standalone-6.0.1-linux-aarch64
    $ISAAC/python.sh tools/bake_environment_usd.py --env office

Add a new backdrop by registering an Environment in
tasks/g1_server_rack/environments.py, then bake it with --env <name>.
"""

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PROJECT_ROOT", REPO_ROOT)
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "tasks"))  # import g1_server_rack top-level

parser = argparse.ArgumentParser(description="Bake a background environment to USD.")
parser.add_argument("--env", default="office")
parser.add_argument("--out", default=None,
                    help="output .usd path (default: assets/environments/<env>_server_rack.usd)")
args = parser.parse_args()

from isaacsim import SimulationApp  # noqa: E402

simulation_app = SimulationApp({"headless": True})

from pxr import Gf, Sdf, Usd, UsdGeom  # noqa: E402

from g1_server_rack import environments, scene_props  # noqa: E402
from g1_server_rack import placements as P  # noqa: E402

ROOT = "/Environment"


def _reference_child(stage, prim_path, usd_path, pos, rot_wxyz):
    """Reference ``usd_path`` under a fresh, posed wrapper Xform.

    Posing the wrapper (not the referenced prim) avoids xformOp precision
    clashes with source USDs that ship a double-precision orient op.
    """
    xform = UsdGeom.Xform.Define(stage, Sdf.Path(prim_path))
    child = stage.DefinePrim(Sdf.Path(f"{prim_path}/Model"))
    child.GetReferences().AddReference(usd_path)
    xf = UsdGeom.Xformable(xform)
    xf.AddTranslateOp().Set(Gf.Vec3d(*pos))
    w, x, y, z = rot_wxyz
    xf.AddOrientOp().Set(Gf.Quatf(w, Gf.Vec3f(x, y, z)))


def main():
    out = args.out or os.path.join(
        REPO_ROOT, "assets", "environments", f"{args.env}_server_rack.usd")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)

    stage = Usd.Stage.CreateNew(out)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, Sdf.Path(ROOT))
    stage.SetDefaultPrim(root.GetPrim())

    # Backdrop: room shell + white lighting + subtle office props.
    environments.build_environment(stage, name=args.env, root=f"{ROOT}/{args.env.capitalize()}")

    # Static task-adjacent decor that belongs to the backdrop: the tray and the
    # two spare SSD carriers resting on it (not manipulated by the bay-4 task).
    scene_props.add_tray(stage, root=f"{ROOT}/Tray")
    _reference_child(stage, f"{ROOT}/SpareSSD_a", P.SSD_USD, P.SSD_TRAY_A_POS, P.SSD_FLAT_ROT)
    _reference_child(stage, f"{ROOT}/SpareSSD_b", P.SSD_USD, P.SSD_TRAY_B_POS, P.SSD_FLAT_ROT)

    stage.GetRootLayer().Save()
    n = len(list(stage.Traverse()))
    print(f"[bake] env='{args.env}' prims={n} -> {out}")


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
