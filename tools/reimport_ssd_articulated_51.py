#!/usr/bin/env python
# Copyright (c) 2025. License: Apache License, Version 2.0
"""Re-import the DXD9H SSD carrier as a NATIVE Isaac Sim 5.1 PhysX articulation.

The shipped ssd.usda (converted on Isaac Sim 6.0, NewtonArticulationRootAPI)
yields ZERO PhysX DOFs on 5.1, so it can't be the interactive task "object".
This rebuilds it with IsaacLab's version-matched UrdfConverter so the two DOFs
(handle_joint revolute + button_joint prismatic) actually exist on 5.1.

The URDF's visual meshes are .glb (which the importer drops); .obj siblings
already exist next to them, so we rewrite a temp URDF to reference the .obj and
absolute paths, keep the 7 box colliders as-is, and convert with a floating base
and free (undriven) joints so the robot back-drives them by contact.

Run in the unitree_sim_env conda env (see the task README for the LD_PRELOAD /
PYTHONPATH / CYCLONEDDS env). Output:
    assets/objects/ssd_articulated/ssd_articulated.usd
"""

import argparse
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSD_URDF = "/home/admin/isaac-sim/IsaacSIM_URDF/models/ssd.urdf"

parser = argparse.ArgumentParser()
parser.add_argument("--urdf", default=SSD_URDF)
parser.add_argument("--out-dir", default=os.path.join(REPO, "assets", "objects", "ssd_articulated"))
parser.add_argument("--name", default="ssd_articulated.usd")
args = parser.parse_args()

from isaaclab.app import AppLauncher  # noqa: E402

app = AppLauncher(headless=True).app

from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg  # noqa: E402


def _rewrite_urdf(src: str) -> str:
    """Rewrite visual .glb mesh refs -> absolute .obj; return a temp URDF path."""
    tree = ET.parse(src)
    base = os.path.dirname(os.path.abspath(src))
    n = 0
    for mesh in tree.iter("mesh"):
        fn = mesh.get("filename")
        if not fn:
            continue
        abspath = os.path.join(base, fn)
        if abspath.lower().endswith(".glb"):
            obj = abspath[:-4] + ".obj"
            if not os.path.isfile(obj):
                raise SystemExit(f"FAIL: no .obj sibling for {fn} ({obj})")
            abspath = obj
        mesh.set("filename", abspath)
        n += 1
    tmp = os.path.join(tempfile.mkdtemp(prefix="ssd_urdf_"), "ssd_obj.urdf")
    tree.write(tmp, xml_declaration=True, encoding="unicode")
    print(f"[reimport] rewrote {n} mesh ref(s) -> {tmp}")
    return tmp


def main():
    os.makedirs(args.out_dir, exist_ok=True)
    urdf = _rewrite_urdf(args.urdf)

    cfg = UrdfConverterCfg(
        asset_path=urdf,
        usd_dir=args.out_dir,
        usd_file_name=args.name,
        force_usd_conversion=True,
        make_instanceable=False,
        # Floating base: the robot draws the whole carrier out and reseats it.
        fix_base=False,
        # Preserve the exact link/joint tree (no fixed joints to merge anyway).
        merge_fixed_joints=False,
        # Free, undriven DOFs — the robot back-drives handle/button by contact;
        # resistance/spring is tuned via ImplicitActuatorCfg in the scene cfg.
        joint_drive=None,
        collider_type="convex_hull",
    )
    conv = UrdfConverter(cfg)
    print(f"[reimport] wrote {conv.usd_path}")


if __name__ == "__main__":
    try:
        main()
    finally:
        app.close()
