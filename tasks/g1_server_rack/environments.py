# Copyright (c) 2025. License: Apache License, Version 2.0
"""Swappable BACKGROUND environments for the G1 / server-rack scene.

This is the extensibility seam of the whole task. The robot, rack, server and
SSDs never change; only the backdrop does. To add a new environment (warehouse,
data-centre, lab, outdoor ...) you subclass :class:`Environment`, implement
:meth:`build`, and register it in :data:`ENVIRONMENTS`. The runner selects one by
name (``--env office``) and nothing in the task core is touched.

An ``Environment`` authors purely static, non-physics backdrop prims (room
shell, lighting, decorative props) under a single root prim, so a whole
environment can be swapped or cleared as a unit.

The first environment, :class:`OfficeEnvironment`, is a plain procedural office:
neutral room shell, bright even white lighting so the whole scene reads clearly,
and a few deliberately unobtrusive props off to the side.
"""

from __future__ import annotations

from typing import Dict, Type

from pxr import Usd

from . import _authoring as A

ENV_ROOT = "/World/Environment"


class Environment:
    """Base class for a swappable backdrop.

    Subclasses implement :meth:`build`, authoring everything under ``self.root``
    (default ``/World/Environment``) so the backdrop is isolated from the task
    core and can be replaced wholesale.
    """

    name: str = "base"

    def __init__(self, root: str = ENV_ROOT):
        self.root = root

    def build(self, stage: Usd.Stage) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class OfficeEnvironment(Environment):
    """A simple, brightly and evenly lit procedural office room.

    Geometry is intentionally cheap and dependency-free (built from primitives,
    no external USD to fetch) so the scene always loads. Lighting is the point:
    a soft dome fill plus overhead white panels give clean, shadow-light
    visibility across the robot and the rack.
    """

    name = "office"

    # Room interior extents. The main scene sits near the world origin; the room
    # is centred a little behind the rack so the robot has open floor in front.
    ROOM_W = 8.0          # along Y
    ROOM_D = 8.0          # along X
    ROOM_H = 3.0          # ceiling height
    CENTER = (1.0, 0.0)   # (x, y) of the room centre

    def build(self, stage: Usd.Stage) -> None:
        A.make_xform(stage, self.root)
        self._build_shell(stage)
        self._build_lighting(stage)
        self._build_props(stage)

    # -- room shell ----------------------------------------------------------
    def _build_shell(self, stage: Usd.Stage) -> None:
        cx, cy = self.CENTER
        w, d, h = self.ROOM_W, self.ROOM_D, self.ROOM_H
        wall_t = 0.1

        floor_mat = A.make_preview_material(stage, f"{self.root}/FloorMat",
                                            color=(0.62, 0.62, 0.64), roughness=0.4)
        wall_mat = A.make_preview_material(stage, f"{self.root}/WallMat",
                                           color=(0.88, 0.88, 0.90), roughness=0.8)
        ceil_mat = A.make_preview_material(stage, f"{self.root}/CeilMat",
                                           color=(0.95, 0.95, 0.96), roughness=0.9)

        A.make_ground(stage, f"{self.root}/Floor", size=max(w, d) + 4.0, z=0.001, material=floor_mat)
        A.make_box(stage, f"{self.root}/Ceiling", (d, w, wall_t), (cx, cy, h), material=ceil_mat)

        x0, x1 = cx - d / 2.0, cx + d / 2.0
        y0, y1 = cy - w / 2.0, cy + w / 2.0
        A.make_box(stage, f"{self.root}/Wall_front", (wall_t, w, h), (x0, cy, h / 2.0), material=wall_mat)
        A.make_box(stage, f"{self.root}/Wall_rear", (wall_t, w, h), (x1, cy, h / 2.0), material=wall_mat)
        A.make_box(stage, f"{self.root}/Wall_left", (d, wall_t, h), (cx, y0, h / 2.0), material=wall_mat)
        A.make_box(stage, f"{self.root}/Wall_right", (d, wall_t, h), (cx, y1, h / 2.0), material=wall_mat)

    # -- lighting ------------------------------------------------------------
    def _build_lighting(self, stage: Usd.Stage) -> None:
        cx, cy = self.CENTER
        white = (1.0, 1.0, 1.0)
        # Soft white ambient fill.
        A.make_dome_light(stage, f"{self.root}/DomeLight", intensity=600.0, color=white)
        # Overhead white panels just below the ceiling for even, bright key light.
        z = self.ROOM_H - 0.05
        for i, (dx, dy) in enumerate([(-1.6, -1.6), (-1.6, 1.6), (1.6, -1.6), (1.6, 1.6), (0.0, 0.0)]):
            A.make_rect_light(stage, f"{self.root}/Panel_{i}", center=(cx + dx, cy + dy, z),
                              width=1.8, length=1.8, intensity=9000.0, color=white)
        # Front fill: overhead panels light the TOP of the rack/server, but the
        # drive bays face -X (toward the robot) and stay dark. A tall panel in
        # front of the rack, aimed at +X (local -Z rotated -90 deg about Y),
        # washes the server front and the robot's workspace with even white light.
        face_plus_x = (0.70710678, 0.0, -0.70710678, 0.0)   # -90 deg about Y
        A.make_rect_light(stage, f"{self.root}/FrontFill", center=(-1.6, 0.0, 1.45),
                          width=2.6, length=2.4, intensity=11000.0, color=white,
                          orient_wxyz=face_plus_x)

    # -- unobtrusive office props -------------------------------------------
    def _build_props(self, stage: Usd.Stage) -> None:
        """A desk with a monitor against the rear wall, and a couple of boxes.

        Kept small, muted and pushed to the room's edges so they read as
        "an office" without competing with the robot-and-rack focal point.
        """
        root = f"{self.root}/Props"
        A.make_xform(stage, root)
        desk_mat = A.make_preview_material(stage, f"{root}/DeskMat", color=(0.75, 0.72, 0.66), roughness=0.5)
        dark_mat = A.make_preview_material(stage, f"{root}/DarkMat", color=(0.12, 0.12, 0.13), roughness=0.4)
        box_mat = A.make_preview_material(stage, f"{root}/BoxMat", color=(0.70, 0.55, 0.38), roughness=0.7)

        # Desk against the rear wall (+X side), off to the left (+Y).
        dx, dy = self.CENTER[0] + self.ROOM_D / 2.0 - 0.6, self.CENTER[1] + 2.4
        A.make_box(stage, f"{root}/desk_top", (0.7, 1.4, 0.04), (dx, dy, 0.75), material=desk_mat)
        for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
            A.make_box(stage, f"{root}/desk_leg_{i}", (0.05, 0.05, 0.73),
                       (dx + sx * 0.30, dy + sy * 0.65, 0.365), material=dark_mat)
        # Monitor on the desk.
        A.make_box(stage, f"{root}/monitor", (0.05, 0.55, 0.33), (dx + 0.15, dy, 0.95), material=dark_mat)
        A.make_box(stage, f"{root}/monitor_stand", (0.15, 0.06, 0.12), (dx + 0.1, dy, 0.83), material=dark_mat)

        # A small stack of storage boxes in the far corner (-Y, +X).
        bx, by = self.CENTER[0] + self.ROOM_D / 2.0 - 0.5, self.CENTER[1] - 2.9
        A.make_box(stage, f"{root}/box_0", (0.4, 0.4, 0.35), (bx, by, 0.175), material=box_mat)
        A.make_box(stage, f"{root}/box_1", (0.38, 0.38, 0.32), (bx, by, 0.51), material=box_mat)


# Registry: extend this to add environments. `--env <key>` selects one.
ENVIRONMENTS: Dict[str, Type[Environment]] = {
    "office": OfficeEnvironment,
}


def build_environment(stage: Usd.Stage, name: str = "office", root: str = ENV_ROOT) -> Environment:
    """Instantiate and build the named environment. Raises on unknown names."""
    try:
        env_cls = ENVIRONMENTS[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown environment '{name}'; registered: {sorted(ENVIRONMENTS)}"
        ) from exc
    env = env_cls(root=root)
    env.build(stage)
    return env
