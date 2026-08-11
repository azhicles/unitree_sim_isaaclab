# Copyright (c) 2025. License: Apache License, Version 2.0
"""BrainCo Revo2 hand DDS communication class.

Mirrors dds/inspire_dds.py but for the BrainCo Revo2 hand. Publishes hand state
on ``rt/brainco/state`` and receives hand commands on ``rt/brainco/cmd`` using
the generic ``MotorStates_`` / ``MotorCmds_`` messages, with **12 driven motors**
(6 per hand).

CONTRACT (this is the "spec" the teleop client must match; there is no external
BrainCo DDS convention yet, so we define a clean one here):

  * 12 motors, order = the driven joints from robots/brainco.py BRAINCO_DRIVEN_JOINTS,
    LEFT hand first then RIGHT:
        0 left_thumb_metacarpal   6 right_thumb_metacarpal
        1 left_thumb_proximal     7 right_thumb_proximal
        2 left_index_proximal     8 right_index_proximal
        3 left_middle_proximal    9 right_middle_proximal
        4 left_ring_proximal     10 right_ring_proximal
        5 left_pinky_proximal    11 right_pinky_proximal
  * ``q`` is the target/observed joint angle in RADIANS (raw pass-through - no
    normalization, unlike the Inspire channel).
  * The 5 distal joints per hand are NOT sent; they are derived in the sim's
    action provider from their proximal via BRAINCO_COUPLING (thumb 1.0, fingers
    1.155). The client only commands the 6 driven joints per hand.
"""

import threading
from typing import Any, Dict, Optional

import numpy as np

from dds.dds_base import DDSObject
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_go_msg_dds__MotorState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorCmds_, MotorStates_

_N_MOTORS = 12  # 6 driven joints per hand


class BrainCoDDS(DDSObject):
    """BrainCo Revo2 hand DDS node (12 driven motors, raw-radian contract)."""

    def __init__(self, node_name: str = "brainco"):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self.node_name = node_name

        self.brainco_hand_state = MotorStates_()
        self.brainco_hand_state.states = [unitree_go_msg_dds__MotorState_() for _ in range(_N_MOTORS)]

        self._initialized = True
        self.setup_shared_memory(
            input_shm_name="isaac_brainco_state",   # Isaac writes hand state here
            input_size=1024,
            output_shm_name="isaac_brainco_cmd",     # received cmd goes here (read by action provider)
            output_size=1024,
        )
        print(f"[{self.node_name}] BrainCo Hand DDS node initialized ({_N_MOTORS} motors)")

    def setup_publisher(self) -> bool:
        try:
            self.publisher = ChannelPublisher("rt/brainco/state", MotorStates_)
            self.publisher.Init()
            print(f"[{self.node_name}] BrainCo Hand state publisher initialized")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"brainco_dds [{self.node_name}] state publisher init failed: {e}")
            return False

    def setup_subscriber(self) -> bool:
        try:
            self.subscriber = ChannelSubscriber("rt/brainco/cmd", MotorCmds_)
            self.subscriber.Init(lambda msg: self.dds_subscriber(msg, ""), 32)
            print(f"[{self.node_name}] BrainCo Hand command subscriber initialized")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"brainco_dds [{self.node_name}] command subscriber init failed: {e}")
            return False

    def dds_publisher(self) -> Any:
        """Read Isaac hand state from input_shm and publish it (raw radians)."""
        try:
            data = self.input_shm.read_data()
            if data is None:
                return
            if not all(k in data for k in ("positions", "velocities", "torques")):
                return
            positions = data["positions"]
            velocities = data["velocities"]
            torques = data["torques"]
            for i in range(min(_N_MOTORS, len(positions))):
                self.brainco_hand_state.states[i].q = float(positions[i])
                if i < len(velocities):
                    self.brainco_hand_state.states[i].dq = float(velocities[i])
                if i < len(torques):
                    self.brainco_hand_state.states[i].tau_est = float(torques[i])
            self.publisher.Write(self.brainco_hand_state)
        except Exception as e:  # noqa: BLE001
            print(f"brainco_dds [{self.node_name}] publish error: {e}")
            return None

    def dds_subscriber(self, msg: MotorCmds_, datatype: str = None) -> Dict[str, Any]:
        """Receive a hand command (raw radians) and stash it for the action provider."""
        try:
            cmd = {"positions": [], "velocities": [], "torques": [], "kp": [], "kd": []}
            for i in range(min(_N_MOTORS, len(msg.cmds))):
                cmd["positions"].append(float(msg.cmds[i].q))     # raw radians
                cmd["velocities"].append(float(msg.cmds[i].dq))
                cmd["torques"].append(float(msg.cmds[i].tau))
                cmd["kp"].append(float(msg.cmds[i].kp))
                cmd["kd"].append(float(msg.cmds[i].kd))
            self.output_shm.write_data(cmd)
        except Exception as e:  # noqa: BLE001
            print(f"brainco_dds [{self.node_name}] subscribe error: {e}")
            return None

    def get_brainco_hand_command(self) -> Optional[Dict[str, Any]]:
        """Return the latest received hand command (or None)."""
        if self.output_shm:
            return self.output_shm.read_data()
        return None

    def write_brainco_state(self, positions, velocities, torques):
        """Push the current hand state (12 driven joints, radians) for publishing."""
        try:
            state = {
                "positions": positions.tolist() if hasattr(positions, "tolist") else list(positions),
                "velocities": velocities.tolist() if hasattr(velocities, "tolist") else list(velocities),
                "torques": torques.tolist() if hasattr(torques, "tolist") else list(torques),
            }
            if self.input_shm:
                self.input_shm.write_data(state)
        except Exception as e:  # noqa: BLE001
            print(f"brainco_dds [{self.node_name}] Error writing state: {e}")
