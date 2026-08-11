# Copyright (c) 2025. License: Apache License, Version 2.0
"""Reward for the G1 server-rack task.

This is a teleoperation / data-collection task with operator-judged success
(timeout-only episodes), so there is no shaped reward: ``compute_reward`` returns
zeros. It still publishes to the RewardsDDS channel so the framework's DDS
plumbing (which sim_main creates and reads) sees a well-formed value each step,
mirroring tasks/common_rewards/base_reward_pickplace_redblock.py.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv

_rewards_dds = None
_dds_initialized = False


def _get_rewards_dds_instance():
    """Lazily fetch the RewardsDDS instance registered by sim_main (if any)."""
    global _rewards_dds, _dds_initialized
    if not _dds_initialized or _rewards_dds is None:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "dds"))
            from dds.dds_master import dds_manager

            _rewards_dds = dds_manager.get_object("rewards")
        except Exception as e:  # noqa: BLE001
            print(f"[reward:server_rack] no RewardsDDS instance yet: {e}")
            _rewards_dds = None
        _dds_initialized = True
    return _rewards_dds


def compute_reward(env: "ManagerBasedRLEnv") -> torch.Tensor:
    """Zero reward for every env (success is operator-judged; timeout-only)."""
    reward = torch.zeros(env.num_envs, device=env.device, dtype=torch.float)
    rewards_dds = _get_rewards_dds_instance()
    if rewards_dds:
        rewards_dds.write_rewards_data(reward)
    return reward
