#!/usr/bin/env python
# Copyright (c) 2025. License: Apache License, Version 2.0
"""Render a still image of a USD scene, headless, via Replicator.

A reliable alternative to viewport screenshotting on headless kit builds where
``capture_viewport_to_file`` does not flush. Opens a USD, points a camera at it,
and writes a PNG. Handy for turning an exported scene (e.g. the composed USD from
run_g1_server_rack_scene.py --export-usd) into a shareable image.

    PY=/home/admin/miniforge3/envs/unitree_sim_env/bin/python
    $PY tools/render_usd_shot.py --usd /path/scene.usd --out /path/shot.png \
        --eye -2.0 -1.7 1.65 --target 0.05 0.0 1.02
"""

import argparse
import os
import sys

parser = argparse.ArgumentParser(description="Headless still render of a USD via Replicator.")
parser.add_argument("--usd", required=True, help="USD stage to open")
parser.add_argument("--out", required=True, help="output PNG path")
parser.add_argument("--eye", type=float, nargs=3, default=[-2.0, -1.7, 1.65], metavar=("X", "Y", "Z"))
parser.add_argument("--target", type=float, nargs=3, default=[0.05, 0.0, 1.02], metavar=("X", "Y", "Z"))
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=720)
parser.add_argument("--subframes", type=int, default=48, help="RTX accumulation subframes (higher = cleaner)")
parser.add_argument("--hide", nargs="*", default=[], metavar="PRIM_PATH",
                    help="prim paths to make invisible before rendering (e.g. the robot)")
parser.add_argument("--add-dome", type=float, default=None, metavar="INTENSITY",
                    help="add a white dome light at this intensity (for USDs that ship no lights)")
args = parser.parse_args()

from isaacsim import SimulationApp  # noqa: E402

simulation_app = SimulationApp({"headless": True})

import omni.usd  # noqa: E402
import omni.replicator.core as rep  # noqa: E402


def main() -> int:
    omni.usd.get_context().open_stage(args.usd)
    for _ in range(60):  # let the stage + assets load
        simulation_app.update()

    if args.hide:
        from pxr import UsdGeom

        stage = omni.usd.get_context().get_stage()
        for path in args.hide:
            prim = stage.GetPrimAtPath(path)
            if prim and prim.IsValid():
                UsdGeom.Imageable(prim).MakeInvisible()
                print(f"[render] hid {path}")
            else:
                print(f"[render] hide skipped (not found): {path}")

    if args.add_dome is not None:
        from pxr import Gf, Sdf, UsdLux

        stage = omni.usd.get_context().get_stage()
        dome = UsdLux.DomeLight.Define(stage, Sdf.Path("/RenderDome"))
        dome.CreateIntensityAttr(args.add_dome)
        dome.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))
        for _ in range(10):
            simulation_app.update()

    cam = rep.create.camera(position=tuple(args.eye), look_at=tuple(args.target))
    rp = rep.create.render_product(cam, (args.width, args.height))

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir=out_dir, rgb=True)
    writer.attach([rp])

    # Render a few frames so RTX accumulates a clean image, then step the writer.
    rep.orchestrator.step(rt_subframes=args.subframes)
    for _ in range(30):
        simulation_app.update()

    # BasicWriter names files rgb_<frame>.png; rename the newest to --out.
    pngs = sorted(
        [f for f in os.listdir(out_dir) if f.startswith("rgb_") and f.endswith(".png")],
        key=lambda f: os.path.getmtime(os.path.join(out_dir, f)),
    )
    if not pngs:
        print("[render] FAILED: no rgb_*.png produced")
        return 1
    src = os.path.join(out_dir, pngs[-1])
    os.replace(src, args.out)
    print(f"[render] wrote {args.out} ({os.path.getsize(args.out)} bytes)")
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        simulation_app.close()
    sys.exit(rc)
