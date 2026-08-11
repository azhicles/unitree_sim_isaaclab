# Copyright (c) 2025. License: Apache License, Version 2.0
"""Structural, non-interactive props authored procedurally onto the stage:

    * the 42U rack - the real NetShelter USD when it is available, otherwise an
      open wireframe placeholder that does NOT hide the server inside it, and
    * the tray/stand beside the rack that the two spare SSD carriers rest on.

These are static and shared across environments (they belong to the task, not to
the backdrop), so they live here rather than in :mod:`environments`. The rack is
authored rather than declared in :class:`scene_cfg.G1ServerRackSceneCfg` purely
so the real-USD / placeholder fallback can be a runtime decision.
"""

from __future__ import annotations

import os

from pxr import Usd

from . import placements as C
from . import _authoring as A

RACK_ROOT = "/World/Rack"
TRAY_ROOT = "/World/Tray"


def add_rack(stage: Usd.Stage, *, use_real_usd: bool = True) -> bool:
    """Add the 42U rack at the world datum.

    Returns True if the real rack USD was referenced, False if the placeholder
    frame was drawn instead (real USD missing or ``use_real_usd`` False). The
    rack's native frame is origin-aligned with the server, so it references in
    at the world origin with no transform.
    """
    if use_real_usd and os.path.isfile(C.RACK_USD):
        # Reference the finished rack. add_reference_to_stage brings in the
        # layer's defaultPrim (netshelter_sx_42u) under RACK_ROOT.
        from isaacsim.core.utils.stage import add_reference_to_stage

        add_reference_to_stage(usd_path=C.RACK_USD, prim_path=RACK_ROOT)
        return True

    _draw_rack_placeholder(stage)
    return False


def _draw_rack_placeholder(stage: Usd.Stage) -> None:
    """An open box frame standing in for the 42U enclosure.

    Envelope from rack_params: 0.60 m wide (Y) x 1.07 m deep (X) x 1.991 m tall
    (Z), front rail flange plane at X=0, extending rearward to +X. Drawn as four
    corner posts + a top and bottom ring so the seated server stays fully
    visible through the open front - a solid box would defeat the purpose.
    """
    W, D, H = 0.60, 1.07, 1.991          # rack_params WIDTH/DEPTH/HEIGHT (m)
    x0, x1 = 0.0, D                       # front rail plane -> rear
    y0, y1 = -W / 2.0, W / 2.0
    post = 0.04                           # square section of the frame members

    A.make_xform(stage, RACK_ROOT)
    mat = A.make_preview_material(
        stage, f"{RACK_ROOT}/Mat", color=(0.32, 0.33, 0.36), roughness=0.6, opacity=0.55
    )

    # Four vertical corner posts.
    for i, (px, py) in enumerate([(x0, y0), (x0, y1), (x1, y0), (x1, y1)]):
        A.make_box(stage, f"{RACK_ROOT}/post_{i}", (post, post, H), (px, py, H / 2.0),
                   material=mat)

    # Top and bottom horizontal rails (front, rear, left, right) at both heights.
    for z in (post / 2.0, H - post / 2.0):
        A.make_box(stage, f"{RACK_ROOT}/rail_front_{z:.2f}", (post, W, post), (x0, 0.0, z), material=mat)
        A.make_box(stage, f"{RACK_ROOT}/rail_rear_{z:.2f}", (post, W, post), (x1, 0.0, z), material=mat)
        A.make_box(stage, f"{RACK_ROOT}/rail_left_{z:.2f}", (D, post, post), (D / 2.0, y0, z), material=mat)
        A.make_box(stage, f"{RACK_ROOT}/rail_right_{z:.2f}", (D, post, post), (D / 2.0, y1, z), material=mat)


def add_tray(stage: Usd.Stage, root: str = TRAY_ROOT) -> None:
    """A simple stand + tray beside the rack that the spare SSDs rest on.

    Sized and placed so its top sits just under the tray-SSD positions in
    placements (~0.90 m), within the standing robot's right-hand reach. ``root``
    lets the tray be authored under a different prim (e.g. when baking it into a
    single environment USD).
    """
    # Tray top surface, centred on the two spare-SSD positions.
    cx = (C.SSD_TRAY_A_POS[0] + C.SSD_TRAY_B_POS[0]) / 2.0
    cy = (C.SSD_TRAY_A_POS[1] + C.SSD_TRAY_B_POS[1]) / 2.0
    top_z = 0.90
    top_thick = 0.03
    tw, td = 0.45, 0.35                   # tray top extents (Y, X)

    A.make_xform(stage, root)
    top_mat = A.make_preview_material(stage, f"{root}/TopMat", color=(0.55, 0.42, 0.30), roughness=0.5)
    leg_mat = A.make_preview_material(stage, f"{root}/LegMat", color=(0.20, 0.20, 0.22), roughness=0.6)

    A.make_box(stage, f"{root}/top", (td, tw, top_thick), (cx, cy, top_z - top_thick / 2.0),
               material=top_mat)

    # Four legs down to the floor.
    leg = 0.04
    lz = (top_z - top_thick)
    for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
        lx = cx + sx * (td / 2.0 - leg)
        ly = cy + sy * (tw / 2.0 - leg)
        A.make_box(stage, f"{root}/leg_{i}", (leg, leg, lz), (lx, ly, lz / 2.0), material=leg_mat)
