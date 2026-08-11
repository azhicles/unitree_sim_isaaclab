# Copyright (c) 2025. License: Apache License, Version 2.0
"""Small helpers for authoring plain USD prims (boxes, materials, lights) onto a
live stage.

These wrap the handful of ``pxr`` calls the procedural layers (:mod:`scene_props`,
:mod:`environments`) need, so those modules read as scene descriptions rather
than USD boilerplate. Everything here is import-safe only *after* Isaac Sim's
``SimulationApp`` has started (that is when ``pxr`` is importable).
"""

from __future__ import annotations

from typing import Sequence

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade


def make_xform(stage: Usd.Stage, path: str) -> UsdGeom.Xform:
    """Create (or fetch) an Xform scope at ``path``."""
    return UsdGeom.Xform.Define(stage, Sdf.Path(path))


def make_preview_material(
    stage: Usd.Stage,
    path: str,
    color: Sequence[float],
    *,
    roughness: float = 0.7,
    metallic: float = 0.0,
    opacity: float = 1.0,
) -> UsdShade.Material:
    """A UsdPreviewSurface material with a flat diffuse ``color``."""
    material = UsdShade.Material.Define(stage, Sdf.Path(path))
    shader = UsdShade.Shader.Define(stage, Sdf.Path(f"{path}/Shader"))
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    if opacity < 1.0:
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def bind_material(prim: Usd.Prim, material: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI(prim).Bind(material)


def make_box(
    stage: Usd.Stage,
    path: str,
    size: Sequence[float],
    center: Sequence[float],
    *,
    material: UsdShade.Material | None = None,
    rot_xyzw: Sequence[float] | None = None,
) -> UsdGeom.Cube:
    """An axis-aligned box of full extents ``size`` centred at ``center``.

    Implemented as a unit ``Cube`` (edge 2) scaled per-axis, so a single prim
    gives independent x/y/z dimensions without authoring mesh points.
    """
    cube = UsdGeom.Cube.Define(stage, Sdf.Path(path))
    cube.CreateSizeAttr(2.0)
    xf = UsdGeom.Xformable(cube)
    xf.AddTranslateOp().Set(Gf.Vec3d(*center))
    if rot_xyzw is not None:
        x, y, z, w = rot_xyzw
        xf.AddOrientOp().Set(Gf.Quatf(w, Gf.Vec3f(x, y, z)))
    xf.AddScaleOp().Set(Gf.Vec3f(size[0] / 2.0, size[1] / 2.0, size[2] / 2.0))
    if material is not None:
        bind_material(cube.GetPrim(), material)
    return cube


def make_ground(
    stage: Usd.Stage,
    path: str,
    *,
    size: float = 20.0,
    z: float = 0.0,
    material: UsdShade.Material | None = None,
) -> UsdGeom.Mesh:
    """A large flat quad at height ``z`` (a visible floor, distinct from any
    physics ground plane)."""
    mesh = UsdGeom.Mesh.Define(stage, Sdf.Path(path))
    h = size / 2.0
    mesh.CreatePointsAttr([(-h, -h, z), (h, -h, z), (h, h, z), (-h, h, z)])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateNormalsAttr([(0, 0, 1)] * 4)
    mesh.SetNormalsInterpolation("vertex")
    mesh.CreateExtentAttr([(-h, -h, z), (h, h, z)])
    if material is not None:
        bind_material(mesh.GetPrim(), material)
    return mesh


def make_rect_light(
    stage: Usd.Stage,
    path: str,
    *,
    center: Sequence[float],
    width: float,
    length: float,
    intensity: float,
    color: Sequence[float] = (1.0, 1.0, 1.0),
    orient_wxyz: Sequence[float] | None = None,
) -> UsdLux.RectLight:
    """A rectangular area light.

    A RectLight emits along its local -Z, so with no rotation it points straight
    down (ceiling panel). Pass ``orient_wxyz`` (w, x, y, z) to aim it elsewhere -
    e.g. a -90 deg rotation about Y turns local -Z toward world +X for a light
    that faces the rack front.
    """
    light = UsdLux.RectLight.Define(stage, Sdf.Path(path))
    light.CreateWidthAttr(width)
    # USD names the second in-plane dimension "height" (older builds: "length").
    light.CreateHeightAttr(length)
    light.CreateIntensityAttr(intensity)
    light.CreateColorAttr(Gf.Vec3f(*color))
    light.CreateNormalizeAttr(True)
    xf = UsdGeom.Xformable(light)
    xf.AddTranslateOp().Set(Gf.Vec3d(*center))
    if orient_wxyz is not None:
        w, x, y, z = orient_wxyz
        xf.AddOrientOp().Set(Gf.Quatf(w, Gf.Vec3f(x, y, z)))
    return light


def make_dome_light(
    stage: Usd.Stage,
    path: str,
    *,
    intensity: float,
    color: Sequence[float] = (1.0, 1.0, 1.0),
) -> UsdLux.DomeLight:
    light = UsdLux.DomeLight.Define(stage, Sdf.Path(path))
    light.CreateIntensityAttr(intensity)
    light.CreateColorAttr(Gf.Vec3f(*color))
    return light
