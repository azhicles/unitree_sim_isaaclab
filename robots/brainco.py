# Copyright (c) 2025. License: Apache License, Version 2.0
"""Unitree G1 (29 DoF) with BrainCo Revo2 five-finger hands, fixed base.

A drop-in sibling of ``robots.unitree.G129_CFG_WITH_INSPIRE_HAND``: the G1 body
is identical, so this derives from that config and swaps in the merged
G1+Revo2 USD, the Revo2 finger joints, and a matching hand actuator group.

The Revo2 hand has 6 *driven* joints per hand (thumb metacarpal + thumb / index
/ middle / ring / pinky proximal); the 5 distal joints follow their proximals
via URDF mimic couplings that were preserved into the USD (so they are not
independently commanded). All 11 per-hand joint names are listed in the actuator
group regardless - IsaacLab covers whichever of them are real articulation DoFs
and ignores the rest, so this is correct whether the importer kept the distal
joints coupled or free.

Built from the merged URDF in IsaacSIM_URDF/models/g1_brainco/ (see that dir's
build_merged.py / convert_brainco.py).
"""

import copy
import os

from isaaclab.actuators import ImplicitActuatorCfg

from robots.unitree import G129_CFG_WITH_INSPIRE_HAND

_PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "")
_BRAINCO_USD = f"{_PROJECT_ROOT}/assets/robots/g1-29dof-brainco-base-fix-usd/g1_29dof_with_brainco_rev_1_0.usd"

# Every Revo2 hand joint (driven + coupled distal), both hands.
_FINGERS = (
    "thumb_metacarpal", "thumb_proximal", "thumb_distal",
    "index_proximal", "index_distal",
    "middle_proximal", "middle_distal",
    "ring_proximal", "ring_distal",
    "pinky_proximal", "pinky_distal",
)
BRAINCO_HAND_JOINTS = [f"{side}_{f}_joint" for side in ("left", "right") for f in _FINGERS]

# Driven joints only (what a controller actually commands) - handy for tasks.
BRAINCO_DRIVEN_JOINTS = [
    f"{side}_{f}_joint"
    for side in ("left", "right")
    for f in ("thumb_metacarpal", "thumb_proximal",
              "index_proximal", "middle_proximal", "ring_proximal", "pinky_proximal")
]

# Finger coupling: each distal joint follows its proximal (thumb 1:1, fingers
# 1.155:1), matching the Revo2 URDF mimic relations. Applied in the CONTROL layer
# (not as a PhysX constraint - see IsaacSIM_URDF/models/g1_brainco/convert_brainco.py
# for why physics mimic was rejected on 5.1). A controller/task commands the 6
# driven joints and mirrors the distal targets through this map.
_COUPLING_RATIO = {"thumb": 1.0, "index": 1.155, "middle": 1.155,
                   "ring": 1.155, "pinky": 1.155}
BRAINCO_COUPLING = {
    f"{side}_{finger}_distal_joint": (f"{side}_{finger}_proximal_joint", ratio)
    for side in ("left", "right")
    for finger, ratio in _COUPLING_RATIO.items()
}


def coupled_hand_targets(driven_targets: dict) -> dict:
    """Expand driven-joint targets into a full hand target dict, adding each
    distal joint = ratio * its proximal. ``driven_targets`` maps driven joint
    names (see BRAINCO_DRIVEN_JOINTS) to angles; returns driven + distal."""
    out = dict(driven_targets)
    for distal, (proximal, ratio) in BRAINCO_COUPLING.items():
        if proximal in driven_targets:
            out[distal] = ratio * driven_targets[proximal]
    return out


def _build_brainco_cfg():
    cfg = copy.deepcopy(G129_CFG_WITH_INSPIRE_HAND)
    cfg.spawn.usd_path = _BRAINCO_USD

    # Swap finger init poses: drop the Inspire fingers (L_*/R_* joints), add the
    # Revo2 joints, all at 0.0 (open hand). Body joints (legs/waist/arms) stay.
    jp = cfg.init_state.joint_pos
    for k in [k for k in jp if k.startswith(("L_", "R_"))]:
        jp.pop(k)
    for j in BRAINCO_HAND_JOINTS:
        jp[j] = 0.0

    # One hand actuator over ALL Revo2 finger joints (driven + distal), position
    # controlled. The distal joints are normal DoF; the proximal->distal coupling
    # is applied in the control layer via coupled_hand_targets()/BRAINCO_COUPLING
    # (physics mimic was rejected on 5.1 - see the build's convert_brainco.py).
    cfg.actuators["hands"] = ImplicitActuatorCfg(
        joint_names_expr=[f".*_{f}_joint" for f in _FINGERS],
        effort_limit=2.0,
        velocity_limit=5.0,
        stiffness=10.0,
        damping=1.0,
        armature=0.0,
    )
    return cfg


G129_CFG_WITH_BRAINCO_HAND = _build_brainco_cfg()
"""G1 29 DoF + BrainCo Revo2 hands, fixed base. Drop-in for the Inspire cfg."""
