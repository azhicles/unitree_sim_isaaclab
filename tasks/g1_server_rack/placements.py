# Copyright (c) 2025. License: Apache License, Version 2.0
"""Asset paths and placements for the G1 / server-rack scene - the single source
of truth, deliberately free of any isaaclab/torch import.

Both the IsaacLab task core (:mod:`scene_cfg`) and the torch-free raw-USD
verifier (``tools/preview_scene_rawusd.py``) import these, so the geometry is
defined exactly once and stays consistent between them.

Every number here is derived from the frozen IsaacSIM_URDF dimensional ledgers,
not guessed:
    * server seat  -> rack_params.seated_r750_origin_mm()            = (0,0,945.6)
    * bay sockets  -> r750.urdf bay_slot{04,10}_socket_joint origins
    * half-insert  -> ssd_params.CARRIER_L_MM / 2                    = 63.25 mm

FRAME: +X rearward INTO the rack (drive insertion), +Y left-from-front, +Z up;
origin at the rack front-rail plane / centreline / floor. All three shipped
assets were authored on this one datum, so they seat by pure translation.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Asset locations. USD_VERIFY_DIR points at the sibling IsaacSIM_URDF project's
# usd_verify output; server/SSD/rack derive from it (override via env var).
# ---------------------------------------------------------------------------
USD_VERIFY_DIR = os.environ.get(
    "ISAAC_URDF_USD_VERIFY",
    "/home/admin/isaac-sim/IsaacSIM_URDF/models/usd_verify",
)
SERVER_USD = f"{USD_VERIFY_DIR}/r750/r750.usda"      # defaultPrim: dell_poweredge_r750
SSD_USD = f"{USD_VERIFY_DIR}/ssd/ssd.usda"           # defaultPrim: dell_dxd9h_carrier (6.0; static decor only)
RACK_USD = f"{USD_VERIFY_DIR}/rack/rack.usda"        # defaultPrim: netshelter_sx_42u

# 5.1-NATIVE articulated SSD (2 DOFs: handle_joint revolute + button_joint prismatic),
# produced by tools/reimport_ssd_articulated_51.py. This is the INTERACTIVE task
# object; the 6.0 SSD_USD above yields 0 PhysX DOFs on 5.1 (static decor only).
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SSD_ARTICULATED_USD = os.path.join(_REPO, "assets/objects/ssd_articulated/ssd_articulated.usd")

# Robot USD (Unitree G1, 29 DoF, Inspire hands, fixed base). Used as a plain
# reference by the raw-USD preview; the IsaacLab path uses the full articulation
# cfg (G129_CFG_WITH_INSPIRE_HAND) instead. Resolved against $PROJECT_ROOT.
ROBOT_USD_REL = "assets/robots/g1-29dof-brainco-base-fix-usd/g1_29dof_with_brainco_rev_1_0.usd"

# ---------------------------------------------------------------------------
# Placements (metres, world == asset native frame)
# ---------------------------------------------------------------------------
RACK_POS = (0.0, 0.0, 0.0)            # rack datum == world datum, by construction
SERVER_POS = (0.0, 0.0, 0.9456)      # R750 seated at U20 (2U), centred in its slot

SSD_BAY10_POS = (-0.022, 0.0272, 0.9890)     # bay 10 (right): fully inserted, flush
SSD_BAY04_POS = (-0.0853, 0.1338, 0.9890)    # bay 4  (left):  half inserted (~63 mm proud, -X)
SSD_BAY04_FULL_POS = (-0.022, 0.1338, 0.9890)  # bay 4 fully seated (task START pose)
SSD_IDENTITY_ROT = (1.0, 0.0, 0.0, 0.0)      # upright, as it sits in the bay

# The bay-4 SSD is the interactive task "object": an articulation whose two DOFs
# (from ssd.urdf) the robot operates. Initial state = seated + clasp closed.
#   handle_joint : revolute clasp/latch handle (urdf limits -0.5236..0.4014 rad)
#   button_joint : prismatic release button      (urdf limits 0..0.003 m)
# NOTE: which handle angle is "closed/locked" needs confirming live in 5.1;
# 0.0 (rest) is the starting assumption.
SSD_HANDLE_JOINT = "handle_joint"
SSD_BUTTON_JOINT = "button_joint"
SSD_OBJECT_JOINT_POS = {SSD_HANDLE_JOINT: 0.0, SSD_BUTTON_JOINT: 0.0}

SSD_TRAY_A_POS = (-0.10, -0.60, 0.9110)      # two spares laid flat on the tray
SSD_TRAY_B_POS = (-0.10, -0.49, 0.9110)
SSD_FLAT_ROT = (0.70710678, 0.70710678, 0.0, 0.0)   # +90 deg about X (lay on side)

ROBOT_POS = (-0.55, 0.0, 0.793)      # standing back from rack front, facing +X;
                                     # z set so the foot soles rest on the floor
                                     # (sole was -0.042 at z=0.75 -> feet clipped)
ROBOT_ROT = (1.0, 0.0, 0.0, 0.0)
