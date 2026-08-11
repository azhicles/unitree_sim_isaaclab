# G1 services a server rack — scene

A Unitree G1 (29 DoF, Inspire hands, fixed base) standing at a 42U rack that
holds a Dell PowerEdge R750, with SSD carriers staged in the drive bays and on a
tray beside the rack. This is the **first of many environments** that reuse the
same robot + rack + server + SSD core against different backdrops.

## Layers (each in its own module)

| Module | Role | Change it when… |
|---|---|---|
| `scene_cfg.py` | Interactive task core: robot + server + 4 SSDs, as an `InteractiveSceneCfg`. All placements derived from the frozen IsaacSIM_URDF dimensional ledgers. | The task itself changes (assets, poses, making SSDs graspable). |
| `scene_props.py` | The 42U rack (real USD, else an open wireframe placeholder) + the SSD tray/stand. | Rack asset or tray changes. |
| `environments.py` | **Swappable backdrop** — room, lighting, props. `OfficeEnvironment` today. | You want a new background. |
| `_authoring.py` | Thin USD-authoring helpers (boxes, materials, lights). | Rarely. |
| `../../tools/run_g1_server_rack_scene.py` | Launcher / headless verifier. | Rarely. |

The split is deliberate: **a new environment = a new `Environment` subclass +
one line in `ENVIRONMENTS`**, and nothing in the task core is touched.

## Frame

All assets share one datum (see `IsaacSIM_URDF/models/*_params.py`): **+X points
rearward into the rack** (drive insertion direction), **+Y left-from-front**,
**+Z up**, origin at the rack front-rail plane / centreline / floor. The robot
stands at −X and faces +X. Because the R750, rack and SSDs were authored on this
one datum, they seat by pure translation.

## Run

### A. Torch-free raw-USD preview (verified working)

The bare Isaac Sim 6.0 python on this machine has **no PyTorch**, which IsaacLab
requires. So the primary local verifier is torch-free: it builds the *same*
scene (same placements, rack/tray props, backdrop) with raw USD. The robot comes
in as a plain reference in its default pose (no articulation).

```bash
ISAAC=/home/admin/isaac-sim/isaac-sim-standalone-6.0.1-linux-aarch64
$ISAAC/python.sh tools/preview_scene_rawusd.py \
    --screenshot /tmp/g1_rack.png --export-usd /tmp/g1_rack.usd
```

Flags: `--env <name>` (backdrop), `--no-real-rack` (placeholder frame),
`--no-robot`, `--cam-eye X Y Z --cam-target X Y Z`. Sample renders live in
`preview/`.

### B. Full IsaacLab scene — VERIFIED in Isaac Sim 5.1

`scene_cfg.py` + `tools/run_g1_server_rack_scene.py` build the fully articulated
robot via IsaacLab. This runs in the `unitree_sim_env` conda env (Isaac Sim 5.1
+ torch, pip-installed). IsaacLab 2.3.2 source is used via `PYTHONPATH`; its
runtime deps (`warp-lang flatdict prettytable gymnasium hidapi`) must be present
in the env. Isaac Sim 5.1's pip build also needs an `LD_PRELOAD` for `libgomp`
(it prints the exact line if missing):

```bash
PY=/home/admin/miniforge3/envs/unitree_sim_env/bin/python
LAB=/home/admin/isaac-sim/IsaacLab/source
GOMP=/home/admin/miniforge3/envs/unitree_sim_env/lib/python3.11/site-packages/torch.libs/libgomp-58a43326.so.1.0.0
PROJECT_ROOT=$PWD PYTHONPATH=$LAB/isaaclab \
  LD_PRELOAD="/lib/aarch64-linux-gnu/libgomp.so.1:$GOMP" \
  $PY tools/run_g1_server_rack_scene.py --headless --device cpu \
  --export-usd /tmp/g1_rack.usd
# drop --headless for interactive (needs a display)
```

`--device cpu` because torch in that env is a CPU build (rendering still uses the
GPU). The scene assembles, resets and steps physics cleanly on the real
articulated G1. `_compat.py` no-ops on 5.1 (its shims are only needed on 6.0).

> **Screenshots:** viewport capture does not flush on this headless kit build.
> Use `--export-usd` and then render the composed USD with
> `tools/render_usd_shot.py` (Replicator-based, reliable headless):
> ```bash
> $PY tools/render_usd_shot.py --usd /tmp/g1_rack.usd --out /tmp/shot.png \
>   --eye -2.0 -1.7 1.65 --target 0.05 0 1.02
> # detail shots: --hide /World/envs/env_0/Robot, --add-dome 1500
> ```
> The `preview/isaacsim51_*.png` renders come from this path.

> **On Isaac Sim 6.0:** the machine also had a 6.0.1 standalone (now removed).
> IsaacLab 2.3.2 is 5.x-era and hits 6.0 API renames; `_compat.py` shims the
> import-time ones but 6.0 removed `pxr.PhysxSchema.PhysxDeformableBodyAPI` too,
> so path B needs a version-matched stack. Path A (raw USD) runs on either.

## Asset paths

`scene_cfg.USD_VERIFY_DIR` (env-overridable via `ISAAC_URDF_USD_VERIFY`) points at
the IsaacSIM_URDF `usd_verify` output; server / SSD / rack are derived from it.

## Known follow-ups

- **R750 textures** are being regenerated (OBJ textures) in a parallel effort;
  when the R750 USD is re-pointed, only `scene_cfg.SERVER_USD` may need a look —
  no code change if the path is stable.
- **Graspable SSDs**: the two tray carriers are static in v1. Promote them to
  `RigidObjectCfg` in `scene_cfg.py` for the manipulation task (the source USD
  already has RigidBodyAPI + handle/button joints).
- **Registered task**: `G1ServerRackSceneCfg` is ready to drop into a
  `ManagerBasedRLEnvCfg` for teleop/data-gen alongside the other g1 tasks.
