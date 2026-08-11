# Copyright (c) 2025. License: Apache License, Version 2.0
"""Env cfg: G1 (29 DoF, Inspire hands, fixed base) services a 42U server rack.

Task (teleop / data-gen, operator-judged): the bay-4 SSD starts fully seated
with its clasp closed; the operator drives the G1 to press the release button,
draw the drive out partway, reinsert it fully, and re-lock the clasp.

Structure mirrors tasks/g1_tasks/pick_place_redblock_g1_29dof_inspire 1:1 so the
framework's teleop / replay / data-gen paths pick it up unchanged. Differences:
our scene base, 4 cameras (adds a fixed world cam), timeout-only terminations,
and a zero reward.
"""

import torch

import isaaclab.envs.mdp as base_mdp
from isaaclab.assets import ArticulationCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import configclass

from . import mdp
from tasks.common_config import CameraPresets  # isort: skip
from tasks.common_event.event_manager import SimpleEvent, SimpleEventManager
from tasks.common_scene.base_scene_g1_server_rack import G1ServerRackSceneCfg
from tasks.g1_server_rack import placements as P
from robots.brainco import G129_CFG_WITH_BRAINCO_HAND  # canonical BrainCo cfg (Revo2 coupling)


##
# Scene: reuse the server-rack base, add the robot + the 3 egocentric cameras.
##
@configclass
class ServerRackSceneCfg(G1ServerRackSceneCfg):
    """G1 server-rack scene + BrainCo-hand robot + head/wrist cameras."""

    robot: ArticulationCfg = G129_CFG_WITH_BRAINCO_HAND.replace(
        prim_path="/World/envs/env_.*/Robot",
        init_state=G129_CFG_WITH_BRAINCO_HAND.init_state.replace(
            pos=P.ROBOT_POS, rot=P.ROBOT_ROT,
        ),
    )

    # BrainCo nests d435_link under torso_link (Inspire has it directly under
    # /Robot), so retarget the head-camera prim path.
    front_camera = CameraPresets.g1_front_camera().replace(
        prim_path="/World/envs/env_.*/Robot/torso_link/d435_link/front_cam",
    )
    left_wrist_camera = CameraPresets.left_brainco_wrist_camera()
    right_wrist_camera = CameraPresets.right_brainco_wrist_camera()


##
# MDP
##
@configclass
class ActionsCfg:
    """Direct joint-position control of all robot joints."""

    joint_pos = mdp.JointPositionActionCfg(
        asset_name="robot", joint_names=[".*"], scale=1.0, use_default_offset=True
    )


@configclass
class ObservationsCfg:
    """Body joints + Inspire-hand joints + camera images (the data-gen record)."""

    @configclass
    class PolicyCfg(ObsGroup):
        robot_joint_state = ObsTerm(func=mdp.get_robot_boy_joint_states)
        robot_brainco_state = ObsTerm(func=mdp.get_robot_brainco_joint_states)
        camera_image = ObsTerm(func=mdp.get_camera_image)

        def __post_init__(self):
            self.enable_corruption = False
            self.concatenate_terms = False

    policy: PolicyCfg = PolicyCfg()


@configclass
class TerminationsCfg:
    """Timeout-only: episodes end on episode_length_s; success is operator-judged."""

    pass


@configclass
class RewardsCfg:
    """No shaped reward (see base_reward_server_rack); keeps the RewardsDDS contract."""

    reward = RewTerm(func=mdp.compute_reward, weight=1.0)


@configclass
class EventCfg:
    """No IsaacLab-managed events; runtime resets are DDS-driven (see __post_init__)."""

    pass


@configclass
class ServerRackG129BrainCoHandBaseFixEnvCfg(ManagerBasedRLEnvCfg):
    """Unitree G1 (Inspire, fixed base) server-rack environment."""

    scene: ServerRackSceneCfg = ServerRackSceneCfg(
        num_envs=1, env_spacing=2.5, replicate_physics=True
    )
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    terminations: TerminationsCfg = TerminationsCfg()
    events = EventCfg()
    commands = None
    rewards: RewardsCfg = RewardsCfg()
    curriculum = None

    def __post_init__(self):
        """Post initialization (values copied from the Inspire pick-place task)."""
        self.decimation = 2
        self.episode_length_s = 20.0
        self.sim.dt = 0.005
        self.sim.render_interval = self.decimation
        self.sim.physx.bounce_threshold_velocity = 0.01
        self.sim.physx.gpu_found_lost_aggregate_pairs_capacity = 1024 * 1024 * 4
        self.sim.physx.gpu_total_aggregate_pairs_capacity = 32 * 1024
        self.sim.physx.friction_correlation_distance = 0.003
        self.sim.physx.enable_ccd = True
        self.sim.physx.gpu_constraint_solver_heavy_spring_enabled = True
        self.sim.physx.num_substeps = 2
        self.sim.physx.contact_offset = 0.015
        self.sim.physx.rest_offset = 0.001
        self.sim.physx.num_position_iterations = 12
        self.sim.physx.num_velocity_iterations = 4

        # Out-of-band event system that sim_main triggers from the reset-pose DDS
        # command: category '1' -> reset just the object, '2' -> reset the scene.
        self.event_manager = SimpleEventManager()
        self.event_manager.register("reset_object_self", SimpleEvent(
            func=lambda env: base_mdp.reset_root_state_uniform(
                env,
                torch.arange(env.num_envs, device=env.device),
                pose_range={"x": [0.0, 0.0], "y": [0.0, 0.0]},
                velocity_range={},
                asset_cfg=SceneEntityCfg("object"),
            )
        ))
        self.event_manager.register("reset_all_self", SimpleEvent(
            func=lambda env: base_mdp.reset_scene_to_default(
                env,
                torch.arange(env.num_envs, device=env.device),
            )
        ))
