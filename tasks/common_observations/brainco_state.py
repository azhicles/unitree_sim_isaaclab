# Copyright (c) 2025. License: Apache License, Version 2.0
"""BrainCo hand joint-state observation.

Mirrors tasks/common_observations/inspire_state.py, but for the BrainCo hand
(11 finger joints per hand) and resolving joint indices by NAME (via the
articulation) rather than the Inspire version's hardcoded index list — so it is
robust to joint-ordering changes.

DDS: publishes to a "brainco" DDS object IF one is registered (there is no
BrainCo DDS channel in this framework yet, so by default this is a no-op and the
function simply returns the observed hand-joint positions for recording).
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


def get_robot_brainco_joint_names() -> list[str]:
    """The 12 DRIVEN BrainCo joints, LEFT hand then RIGHT — the DDS motor order.

    Must stay in lock-step with dds/brainco_dds.py and the action provider's
    brainco_hand_joint_mapping (indices 0-11). The 5 distal joints per hand are
    NOT published; they are derived from their proximal via BRAINCO_COUPLING.
    """
    order = ["thumb_metacarpal", "thumb_proximal", "index_proximal",
             "middle_proximal", "ring_proximal", "pinky_proximal"]
    return [f"{side}_{f}_joint" for side in ("left", "right") for f in order]


_cache = {"device": None, "idx": None}
_brainco_dds = None
_dds_initialized = False


def _get_brainco_dds_instance():
    """Fetch a registered 'brainco' DDS object if present (else None)."""
    global _brainco_dds, _dds_initialized
    if not _dds_initialized or _brainco_dds is None:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "dds"))
            from dds.dds_master import dds_manager

            _brainco_dds = dds_manager.get_object("brainco")
        except Exception:  # noqa: BLE001
            _brainco_dds = None
        _dds_initialized = True
    return _brainco_dds


def get_robot_brainco_joint_states(
    env: "ManagerBasedRLEnv",
    enable_dds: bool = True,
) -> torch.Tensor:
    """Return the BrainCo hand joint positions (batch, 22); publish to DDS if any."""
    robot = env.scene["robot"]
    joint_pos = robot.data.joint_pos
    device = joint_pos.device

    if _cache["device"] != device or _cache["idx"] is None:
        names = get_robot_brainco_joint_names()
        idx, _ = robot.find_joints(names, preserve_order=True)
        _cache["idx"] = torch.tensor(idx, dtype=torch.long, device=device)
        _cache["device"] = device

    idx = _cache["idx"]
    pos = joint_pos[:, idx]

    if enable_dds and pos.shape[0] > 0:
        dds = _get_brainco_dds_instance()
        if dds is not None:
            try:
                vel = robot.data.joint_vel[:, idx]
                torque = robot.data.applied_torque[:, idx]
                dds.write_brainco_state(
                    pos[0].contiguous().cpu().numpy(),
                    vel[0].contiguous().cpu().numpy(),
                    torque[0].contiguous().cpu().numpy(),
                )
            except Exception as e:  # noqa: BLE001
                print(f"[brainco_state] DDS write failed: {e}")

    return pos
