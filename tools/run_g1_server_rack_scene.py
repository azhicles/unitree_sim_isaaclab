#!/usr/bin/env python
# Copyright (c) 2025. License: Apache License, Version 2.0
"""Standalone launcher / verifier for the "G1 services a server rack" scene.

Builds the full scene - G1 (Inspire, fixed base) + R750 server + 4 SSD carriers
+ 42U rack + a swappable backdrop - in Isaac Sim 6.0 and either opens it for
inspection or verifies it headless (screenshot + USD export).

RUN IT with the Isaac Sim python, with IsaacLab's source on PYTHONPATH so
`import isaaclab` resolves. From the unitree_sim_isaaclab repo root:

    ISAAC=/home/admin/isaac-sim/isaac-sim-standalone-6.0.1-linux-aarch64
    LAB=/home/admin/isaac-sim/IsaacLab/source
    # headless verification -> writes a screenshot and a composed USD
    PYTHONPATH=$LAB/isaaclab:$LAB/isaaclab_assets:$LAB/isaaclab_tasks \
      $ISAAC/python.sh tools/run_g1_server_rack_scene.py --headless \
      --screenshot /tmp/g1_rack.png --export-usd /tmp/g1_rack.usd

    # interactive (needs a display)
    PYTHONPATH=$LAB/isaaclab:$LAB/isaaclab_assets:$LAB/isaaclab_tasks \
      $ISAAC/python.sh tools/run_g1_server_rack_scene.py

Swap the backdrop with --env <name> (see tasks/g1_server_rack/environments.py).
"""

import argparse
import os
import sys

# --- repo wiring: robot cfgs reference $PROJECT_ROOT/assets, and the scene
#     package is imported as tasks.g1_server_rack, so the repo root must be
#     both on sys.path and in PROJECT_ROOT before anything else imports it.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PROJECT_ROOT", REPO_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# Import g1_server_rack as a top-level package (via the tasks dir), bypassing
# tasks/__init__.py so this launcher does not depend on the full task registry.
sys.path.insert(0, os.path.join(REPO_ROOT, "tasks"))

from isaaclab.app import AppLauncher  # noqa: E402

parser = argparse.ArgumentParser(description="Build/verify the G1 server-rack scene.")
parser.add_argument("--env", default="office", help="backdrop name (see environments.ENVIRONMENTS)")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--env_spacing", type=float, default=10.0)
parser.add_argument("--no-real-rack", action="store_true",
                    help="force the placeholder rack frame even if the USD exists")
parser.add_argument("--screenshot", type=str, default=None, help="write a viewport PNG here, then continue")
parser.add_argument("--export-usd", dest="export_usd", type=str, default=None,
                    help="export the composed stage to this .usd/.usda and continue")
parser.add_argument("--hold-seconds", type=float, default=0.0,
                    help="headless: keep stepping this long before exit (0 = brief settle only)")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

# Screenshots need the renderer active.
if args.screenshot:
    args.enable_cameras = True

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

# Shim Isaac Sim 6.0 module renames before importing isaaclab (this IsaacLab
# checkout targets 5.x). No-op on a matched stack. See g1_server_rack._compat.
from g1_server_rack import _compat  # noqa: E402
_shims = _compat.apply()
if _shims:
    print("[compat] applied 6.0 shims:", _shims)

# --- imports that require the running app (pxr, scene spawning) ---------------
import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.scene import InteractiveScene  # noqa: E402

from g1_server_rack.scene_cfg import G1ServerRackSceneCfg  # noqa: E402
from g1_server_rack import scene_props, environments  # noqa: E402


CAMERA_EYE = (-2.0, -1.7, 1.65)
CAMERA_TARGET = (0.05, 0.0, 1.02)


def _capture_screenshot(path: str) -> None:
    """Capture the active viewport to ``path`` (best-effort, headless-safe).

    ``capture_viewport_to_file`` schedules an ASYNC write, so we pump plenty of
    app.update()s afterwards to let it flush to disk before the app shuts down -
    and only report success once the file actually exists.
    """
    try:
        from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        # Warm up until a viewport exists, then let the frame converge.
        viewport = None
        for _ in range(120):
            simulation_app.update()
            viewport = get_active_viewport()
            if viewport is not None:
                break
        for _ in range(120):
            simulation_app.update()
        capture_viewport_to_file(viewport, path)
        # Flush the async write; stop early once the file lands.
        for _ in range(120):
            simulation_app.update()
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                break
        ok = os.path.isfile(path) and os.path.getsize(path) > 0
        print(f"[screenshot] {'wrote ' + path if ok else 'capture did not flush to ' + path}")
    except Exception as exc:  # noqa: BLE001 - verification aid, never fatal
        print(f"[screenshot] FAILED: {exc}")


def main() -> None:
    sim = sim_utils.SimulationContext(
        sim_utils.SimulationCfg(dt=1.0 / 120.0, device=args.device)
    )
    sim.set_camera_view(eye=CAMERA_EYE, target=CAMERA_TARGET)

    # 1) Interactive task core (robot + server + SSDs) via the reusable cfg.
    scene_cfg = G1ServerRackSceneCfg(num_envs=args.num_envs, env_spacing=args.env_spacing)
    scene = InteractiveScene(scene_cfg)
    stage = sim.stage

    # 2) Structural props: the 42U rack (real USD or placeholder) + the SSD tray.
    used_real_rack = scene_props.add_rack(stage, use_real_usd=not args.no_real_rack)
    scene_props.add_tray(stage)
    print(f"[rack] {'real USD' if used_real_rack else 'PLACEHOLDER frame'}")

    # 3) Swappable backdrop (room, lighting, office props).
    environments.build_environment(stage, name=args.env)
    print(f"[env] '{args.env}'")

    sim.reset()
    print("[scene] assembled OK; entities:", list(scene.keys()))

    if args.export_usd:
        os.makedirs(os.path.dirname(os.path.abspath(args.export_usd)), exist_ok=True)
        stage.Export(args.export_usd)
        print(f"[export] wrote {args.export_usd}")

    if app_launcher._headless:  # noqa: SLF001
        # Settle briefly (or for --hold-seconds) so physics is demonstrably stable.
        steps = max(int(args.hold_seconds * 120), 120)
        for _ in range(steps):
            scene.write_data_to_sim()
            sim.step()
            scene.update(sim.get_physics_dt())
        # Capture LAST, after physics has settled and with no further sim.step()s
        # to truncate the async write before the app closes.
        if args.screenshot:
            _capture_screenshot(args.screenshot)
        print("[headless] settle complete; exiting")
    else:
        if args.screenshot:
            _capture_screenshot(args.screenshot)
        print("[interactive] close the window to exit")
        while simulation_app.is_running():
            scene.write_data_to_sim()
            sim.step()
            scene.update(sim.get_physics_dt())


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
