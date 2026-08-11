# Copyright (c) 2025. License: Apache License, Version 2.0
"""Base scene for the "G1 services a 42U server rack" task family.

Mirrors the conventions of the other tasks/common_scene bases (room + object +
world_camera as cfg entities; the robot and egocentric cameras are added by the
env_cfg). It is the reusable, background-swappable core: every future
environment reuses this scene and only changes the baked ``room`` USD.

Entities:
    room       - the swappable backdrop (office room + props + lights + tray +
                 spare SSDs), BAKED to one USD by tools/bake_environment_usd.py.
    rack       - the real 42U NetShelter USD.
    server     - the Dell PowerEdge R750, seated in the rack.
    ssd_bay10  - a static SSD carrier fully inserted in bay 10 (decor).
    object     - the INTERACTIVE bay-4 SSD carrier (an articulation with the
                 clasp/handle + release-button DOFs). Named "object" so it plugs
                 into the framework's DDS reset + recorder machinery unchanged.
    world_camera - a fixed 3rd-person camera framing the robot + rack.

Placements come from the frozen dimensional ledgers via
tasks.g1_server_rack.placements (see that module for provenance).
"""

import os

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.utils import configclass

from tasks.common_config import CameraBaseCfg
from tasks.g1_server_rack import placements as P

project_root = os.environ.get("PROJECT_ROOT")

# Baked backdrop USD produced by tools/bake_environment_usd.py --env office.
BAKED_ENV_USD = f"{project_root}/assets/environments/office_server_rack.usd"


@configclass
class G1ServerRackSceneCfg(InteractiveSceneCfg):
    """Room + rack + server + SSDs (+ fixed world cam). Robot/egocentric cams
    are added by the env_cfg subclass."""

    # --- swappable backdrop (baked): office room + props + lights + tray -----
    room = AssetBaseCfg(
        prim_path="/World/envs/env_.*/Room",
        init_state=AssetBaseCfg.InitialStateCfg(pos=[0.0, 0.0, 0.0], rot=[1.0, 0.0, 0.0, 0.0]),
        spawn=UsdFileCfg(usd_path=BAKED_ENV_USD),
    )

    # --- the 42U rack (real USD), origin-aligned with the server -------------
    rack = AssetBaseCfg(
        prim_path="/World/envs/env_.*/Rack",
        init_state=AssetBaseCfg.InitialStateCfg(pos=list(P.RACK_POS), rot=[1.0, 0.0, 0.0, 0.0]),
        spawn=UsdFileCfg(usd_path=P.RACK_USD),
    )

    # --- the Dell PowerEdge R750, seated at U20 ------------------------------
    server = AssetBaseCfg(
        prim_path="/World/envs/env_.*/Server",
        init_state=AssetBaseCfg.InitialStateCfg(pos=list(P.SERVER_POS), rot=list(P.SSD_IDENTITY_ROT)),
        spawn=UsdFileCfg(usd_path=P.SERVER_USD),
    )

    # --- static decor SSD, fully inserted in bay 10 --------------------------
    ssd_bay10 = AssetBaseCfg(
        prim_path="/World/envs/env_.*/SSD_bay10",
        init_state=AssetBaseCfg.InitialStateCfg(pos=list(P.SSD_BAY10_POS), rot=list(P.SSD_IDENTITY_ROT)),
        spawn=UsdFileCfg(usd_path=P.SSD_USD),
    )

    # --- the INTERACTIVE bay-4 SSD: the task "object" ------------------------
    # The 5.1-native articulated DXD9H carrier (2 DOFs: handle_joint revolute
    # clasp + button_joint prismatic release), seated fully in bay 4 with the
    # clasp closed. Floating base so the robot draws it out and reseats it;
    # joints are passive (stiffness 0) so they are back-drivable by contact.
    # Named "object" so it plugs into the framework reset/recorder machinery.
    #
    # NOTE: uses SSD_ARTICULATED_USD (re-imported on 5.1 by
    # tools/reimport_ssd_articulated_51.py) — the shipped 6.0 SSD_USD yields 0
    # PhysX DOFs on 5.1 and is used only for the static decor SSDs. Joint
    # stiffness/damping, seated retention and grasp friction are live-tuning
    # knobs (start values below).
    object = ArticulationCfg(
        prim_path="/World/envs/env_.*/object",
        spawn=UsdFileCfg(
            usd_path=P.SSD_ARTICULATED_USD,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=False, max_depenetration_velocity=1.0,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=False, fix_root_link=False,
                solver_position_iteration_count=12, solver_velocity_iteration_count=4,
            ),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            pos=P.SSD_BAY04_FULL_POS, rot=P.SSD_IDENTITY_ROT,
            joint_pos=dict(P.SSD_OBJECT_JOINT_POS), joint_vel={".*": 0.0},
        ),
        actuators={
            "mechanism": ImplicitActuatorCfg(
                joint_names_expr=[".*"], stiffness=0.0, damping=0.2,
                effort_limit=5.0, velocity_limit=10.0,
            ),
        },
    )

    # --- fixed 3rd-person world camera (4th view) ----------------------------
    # Frames the robot (-X) and the rack front. rot_offset is a look-at estimate
    # (ros convention) toward the drive bays; verify/tune the framing on 5.1.
    world_camera = CameraBaseCfg.get_camera_config(
        prim_path="/World/PerspectiveCamera",
        pos_offset=(-2.0, -1.7, 1.65),
        rot_offset=(0.5590, -0.7118, 0.3344, -0.2627),
        focal_length=12.0,
        horizontal_aperture=27.0,
    )
