# Copyright (c) 2025. License: Apache License, Version 2.0
"""Interactive-core scene configuration for the "G1 services a server rack" task.

This module defines ONLY the interactive / task-relevant entities as an
``InteractiveSceneCfg`` (following the conventions in ``tasks/common_scene``):

    * the Unitree G1 (29 DoF, Inspire hands, fixed base) robot,
    * the Dell PowerEdge R750 server (static, seated in the rack),
    * four Dell DXD9H SSD carriers - two staged in the server's drive bays and
      two resting on a tray beside the rack.

The *background* (room, lighting, office props) is deliberately NOT defined here.
It lives in :mod:`environments`, is authored procedurally onto the USD stage, and
is fully swappable - this is the first of many environments that reuse the exact
same robot + rack + server + SSD core with a different backdrop. Keeping the two
layers separate is the whole point: to make a new environment you write a new
``Environment`` subclass and change one flag; you never touch this file.

The rack itself is structural rather than interactive, so it is authored in
:mod:`scene_props` (real 42U USD when present, an open wireframe placeholder when
not) together with the SSD tray/stand.

FRAME (shared by every asset here - see IsaacSIM_URDF/models/*_params.py):
    +X points rearward, INTO the rack (the insertion direction of the drives).
    +Y points left as viewed from the front.  +Z is up.  Origin: rack front
    rail flange plane / width centreline / floor.  Because the R750, the rack
    and the SSD carriers were all authored on this one datum, seating them is a
    pure translation - no rotations, no per-asset offsets to reconcile.  The
    robot therefore stands at negative X and looks toward +X, at the rack front.
"""

from __future__ import annotations

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.utils import configclass

from robots.unitree import G129_CFG_WITH_INSPIRE_HAND

# Asset paths and all placements live in the torch-free `placements` module, so
# the raw-USD verifier can share this exact geometry without importing isaaclab.
from .placements import (
    RACK_USD,
    SERVER_USD,
    SSD_USD,
    RACK_POS,          # noqa: F401 - re-exported for callers/back-compat
    SERVER_POS,
    SSD_BAY10_POS,
    SSD_BAY04_POS,
    SSD_IDENTITY_ROT,
    SSD_TRAY_A_POS,
    SSD_TRAY_B_POS,
    SSD_FLAT_ROT,
    ROBOT_POS,
    ROBOT_ROT,
)


def _server_spawn() -> sim_utils.UsdFileCfg:
    """The R750 as a static collider (it was imported without RigidBodyAPI)."""
    return sim_utils.UsdFileCfg(usd_path=SERVER_USD)


def _ssd_spawn() -> sim_utils.UsdFileCfg:
    """A single SSD carrier.

    Spawned static for now (v1 is a staged scene). To make the tray carriers
    graspable for the manipulation task, promote those two to ``RigidObjectCfg``
    - the carrier already carries RigidBodyAPI + a handle/button articulation in
    the source USD, so this is a config change, not a re-import.
    """
    return sim_utils.UsdFileCfg(usd_path=SSD_USD)


@configclass
class G1ServerRackSceneCfg(InteractiveSceneCfg):
    """Robot + server + SSDs. Background and rack/tray are added separately.

    See the module docstring: the room, lights and props come from an
    :class:`environments.Environment`, and the rack/tray from
    :mod:`scene_props`, both authored onto the stage by the runner. This keeps
    the swappable backdrop out of the reusable task core.
    """

    # --- the robot: G1 29 DoF, Inspire hands, fixed base ---------------------
    robot = G129_CFG_WITH_INSPIRE_HAND.replace(
        prim_path="/World/envs/env_.*/Robot",
    )

    # --- the Dell PowerEdge R750, seated in the rack -------------------------
    server = AssetBaseCfg(
        prim_path="/World/envs/env_.*/Server",
        init_state=AssetBaseCfg.InitialStateCfg(pos=SERVER_POS, rot=SSD_IDENTITY_ROT),
        spawn=_server_spawn(),
    )

    # --- SSD #1: staged fully inserted in bay 10 (right) ---------------------
    ssd_bay10 = AssetBaseCfg(
        prim_path="/World/envs/env_.*/SSD_bay10",
        init_state=AssetBaseCfg.InitialStateCfg(pos=SSD_BAY10_POS, rot=SSD_IDENTITY_ROT),
        spawn=_ssd_spawn(),
    )

    # --- SSD #2: staged half inserted in bay 4 (left) ------------------------
    ssd_bay04 = AssetBaseCfg(
        prim_path="/World/envs/env_.*/SSD_bay04",
        init_state=AssetBaseCfg.InitialStateCfg(pos=SSD_BAY04_POS, rot=SSD_IDENTITY_ROT),
        spawn=_ssd_spawn(),
    )

    # --- SSD #3 & #4: spares on the tray beside the rack ---------------------
    ssd_tray_a = AssetBaseCfg(
        prim_path="/World/envs/env_.*/SSD_tray_a",
        init_state=AssetBaseCfg.InitialStateCfg(pos=SSD_TRAY_A_POS, rot=SSD_FLAT_ROT),
        spawn=_ssd_spawn(),
    )
    ssd_tray_b = AssetBaseCfg(
        prim_path="/World/envs/env_.*/SSD_tray_b",
        init_state=AssetBaseCfg.InitialStateCfg(pos=SSD_TRAY_B_POS, rot=SSD_FLAT_ROT),
        spawn=_ssd_spawn(),
    )

    def __post_init__(self):
        # Stand the robot back from the rack, facing +X toward the drive bays.
        self.robot.init_state.pos = ROBOT_POS
        self.robot.init_state.rot = ROBOT_ROT
