#!/usr/bin/env python
# Copyright (c) 2025. License: Apache License, Version 2.0
"""Torch-free preview / verifier for the G1 server-rack scene.

IsaacLab needs PyTorch, which is not installed in the bare Isaac Sim 6.0 python.
This script builds the SAME scene - same placements, same rack/tray props, same
swappable backdrop - using only raw Isaac Sim + USD (no isaaclab, no torch), so
the scene can be rendered and eyeballed on this machine right now. The robot is
brought in as a plain USD reference in its default pose (no articulation); the
full articulated robot comes from the IsaacLab path once torch is available.

    ISAAC=/home/admin/isaac-sim/isaac-sim-standalone-6.0.1-linux-aarch64
    $ISAAC/python.sh tools/preview_scene_rawusd.py \
        --screenshot /tmp/g1_rack.png --export-usd /tmp/g1_rack.usd

    # placeholder rack instead of the real USD:
    $ISAAC/python.sh tools/preview_scene_rawusd.py --no-real-rack --screenshot /tmp/ph.png
"""

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PROJECT_ROOT", REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# Import g1_server_rack as a TOP-LEVEL package (via the tasks dir) so the heavy
# tasks/__init__.py (gymnasium/torch) never runs - this path is deliberately
# torch-free.
sys.path.insert(0, os.path.join(REPO_ROOT, "tasks"))

parser = argparse.ArgumentParser(description="Raw-USD preview of the G1 server-rack scene.")
parser.add_argument("--env", default="office")
parser.add_argument("--no-real-rack", action="store_true", help="force the placeholder rack frame")
parser.add_argument("--no-robot", action="store_true", help="omit the robot (useful for asset detail shots)")
parser.add_argument("--screenshot", type=str, default=None)
parser.add_argument("--export-usd", dest="export_usd", type=str, default=None)
parser.add_argument("--cam-eye", type=float, nargs=3, default=None, metavar=("X", "Y", "Z"),
                    help="camera eye position (default: a 3/4 establishing view)")
parser.add_argument("--cam-target", type=float, nargs=3, default=None, metavar=("X", "Y", "Z"),
                    help="camera look-at target")
args = parser.parse_args()

from isaacsim import SimulationApp  # noqa: E402

simulation_app = SimulationApp({"headless": True})

import omni.usd  # noqa: E402
from isaacsim.core.utils.stage import add_reference_to_stage  # noqa: E402
from isaacsim.core.utils.viewports import set_camera_view  # noqa: E402
from pxr import Gf, Sdf, UsdGeom  # noqa: E402

from g1_server_rack import placements as P  # noqa: E402
from g1_server_rack import scene_props, environments  # noqa: E402

CAMERA_EYE = (-2.0, -1.7, 1.65)
CAMERA_TARGET = (0.05, 0.0, 1.02)


def _reference_at(stage, prim_path, usd_path, pos, rot_wxyz):
    """Pose a fresh wrapper Xform and reference ``usd_path`` as its child.

    Posing a wrapper (rather than the referenced prim itself) sidesteps xformOp
    precision clashes: some source USDs - the robot articulation, for one - ship
    a double-precision ``orient`` op on their root, which a float op authored on
    the same prim would conflict with. rot is (w, x, y, z).
    """
    xform = UsdGeom.Xform.Define(stage, Sdf.Path(prim_path))
    add_reference_to_stage(usd_path=usd_path, prim_path=f"{prim_path}/Model")
    xf = UsdGeom.Xformable(xform)
    xf.AddTranslateOp().Set(Gf.Vec3d(*pos))
    w, x, y, z = rot_wxyz
    xf.AddOrientOp().Set(Gf.Quatf(w, Gf.Vec3f(x, y, z)))
    return xform


def _capture(path):
    try:
        from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        # Warm up until the viewport exists (light scenes reach this point before
        # the renderer has created one), then let the frame converge.
        vp = None
        for _ in range(60):
            simulation_app.update()
            vp = get_active_viewport()
            if vp is not None:
                break
        for _ in range(120):
            simulation_app.update()
        capture_viewport_to_file(vp, path)
        for _ in range(30):
            simulation_app.update()
        print(f"[screenshot] wrote {path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[screenshot] FAILED: {exc}")


def main():
    stage = omni.usd.get_context().get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.Xform.Define(stage, Sdf.Path("/World"))

    # --- interactive core assets (as plain references) ---
    _reference_at(stage, "/World/Server", P.SERVER_USD, P.SERVER_POS, P.SSD_IDENTITY_ROT)
    _reference_at(stage, "/World/SSD_bay10", P.SSD_USD, P.SSD_BAY10_POS, P.SSD_IDENTITY_ROT)
    _reference_at(stage, "/World/SSD_bay04", P.SSD_USD, P.SSD_BAY04_POS, P.SSD_IDENTITY_ROT)
    _reference_at(stage, "/World/SSD_tray_a", P.SSD_USD, P.SSD_TRAY_A_POS, P.SSD_FLAT_ROT)
    _reference_at(stage, "/World/SSD_tray_b", P.SSD_USD, P.SSD_TRAY_B_POS, P.SSD_FLAT_ROT)

    robot_usd = os.path.join(REPO_ROOT, P.ROBOT_USD_REL)
    if args.no_robot:
        print("[robot] omitted (--no-robot)")
    elif os.path.isfile(robot_usd):
        _reference_at(stage, "/World/Robot", robot_usd, P.ROBOT_POS, P.ROBOT_ROT)
        print("[robot] referenced")
    else:
        print(f"[robot] SKIPPED - USD not found: {robot_usd}")

    # --- structural props + swappable backdrop (shared torch-free modules) ---
    used_real = scene_props.add_rack(stage, use_real_usd=not args.no_real_rack)
    scene_props.add_tray(stage)
    environments.build_environment(stage, name=args.env)
    print(f"[rack] {'real USD' if used_real else 'PLACEHOLDER frame'}   [env] '{args.env}'")

    eye = tuple(args.cam_eye) if args.cam_eye else CAMERA_EYE
    target = tuple(args.cam_target) if args.cam_target else CAMERA_TARGET
    set_camera_view(eye=eye, target=target)
    for _ in range(20):
        simulation_app.update()

    prim_count = len(list(stage.Traverse()))
    print(f"[scene] assembled OK; {prim_count} prims on stage")

    if args.export_usd:
        os.makedirs(os.path.dirname(os.path.abspath(args.export_usd)), exist_ok=True)
        stage.Export(args.export_usd)
        print(f"[export] wrote {args.export_usd}")
    if args.screenshot:
        _capture(args.screenshot)


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
