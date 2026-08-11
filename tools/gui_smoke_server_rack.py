#!/usr/bin/env python
# Copyright (c) 2025. License: Apache License, Version 2.0
"""Open the G1 server-rack task in the Isaac Sim GUI and gently wave the arm, so
you can watch the scene live (no XR teleop client needed). Needs a display.

Easiest: run the wrapper that sets the env for you:

    bash tools/run_server_rack_gui.sh            # gentle arm wave
    bash tools/run_server_rack_gui.sh --still    # hold the start pose

Or drive this directly (see run_server_rack_gui.sh for the required env vars).
Flags: --still (hold), --device cpu|cuda:0, --wave-joint <name>.
"""

import argparse
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PROJECT_ROOT", REPO)
sys.path.insert(0, REPO)

from isaaclab.app import AppLauncher  # noqa: E402

parser = argparse.ArgumentParser(description="GUI smoke for the server-rack task.")
parser.add_argument("--still", action="store_true", help="hold the start pose instead of waving")
parser.add_argument("--wave-joint", default="right_elbow_joint", help="joint to wave")
parser.add_argument("--amplitude", type=float, default=0.5, help="wave amplitude (rad)")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
args.headless = False           # GUI
args.enable_cameras = True       # the task's observations include camera images

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

import tasks  # noqa: E402,F401  (registers all tasks)
from tasks.g1_tasks.server_rack_g1_29dof_inspire.server_rack_g1_29dof_inspire_joint_env_cfg import (  # noqa: E402
    ServerRackG129InspireHandBaseFixEnvCfg,
)

TASK = "Isaac-ServerRack-G129-Inspire-Joint"


def main():
    cfg = ServerRackG129InspireHandBaseFixEnvCfg()
    cfg.scene.num_envs = 1
    cfg.sim.device = args.device
    env = gym.make(TASK, cfg=cfg)
    u = env.unwrapped
    env.reset()

    # Frame the robot + rack.
    u.sim.set_camera_view(eye=(-2.0, -1.7, 1.65), target=(0.05, 0.0, 1.02))

    ad = u.action_manager.total_action_dim
    widx = u.scene["robot"].find_joints([args.wave_joint])[0][0]
    print(f"[gui] {TASK} up. device={args.device}. "
          f"{'holding start pose' if args.still else f'waving {args.wave_joint}'}. "
          f"Close the window to exit.")

    i = 0
    while simulation_app.is_running():
        # Zero action = the robot's default pose (use_default_offset=True); add a
        # small delta on one joint so you can see the control loop is live.
        act = torch.zeros((1, ad), device=args.device)
        if not args.still:
            act[0, widx] = args.amplitude * math.sin(i * 0.02)
        env.step(act)
        i += 1

    env.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
