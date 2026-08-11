# Copyright (c) 2025. License: Apache License, Version 2.0
"""Registers the G1 (Inspire, fixed base) server-rack task."""

import gymnasium as gym

from . import server_rack_g1_29dof_inspire_joint_env_cfg

gym.register(
    id="Isaac-ServerRack-G129-Inspire-Joint",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point":
            server_rack_g1_29dof_inspire_joint_env_cfg.ServerRackG129InspireHandBaseFixEnvCfg,
    },
    disable_env_checker=True,
)
