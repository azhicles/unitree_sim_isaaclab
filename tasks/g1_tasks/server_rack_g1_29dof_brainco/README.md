# Isaac-ServerRack-G129-Brainco-Joint

A registered IsaacLab task: a Unitree G1 (29 DoF, **BrainCo** hands, fixed base)
services a 42U rack holding a Dell R750. Built to mirror
`pick_place_redblock_g1_29dof_inspire` 1:1 so the framework's **teleoperation /
replay / data-generation** paths pick it up unchanged.

> **BrainCo hand teleop is wired.** Run with `--enable_brainco_dds`: the arm
> teleops over `rt/lowcmd` and the Revo2 fingers over `rt/brainco/cmd` (12 driven
> motors; distal joints follow via coupling). See the DDS contract at the top of
> `dds/brainco_dds.py`. The only remaining piece is the teleop client
> (`xr_teleoperate`) publishing to `rt/brainco/cmd` — until then the arm
> teleoperates and the fingers hold their open pose.

**Task** (operator-judged, timeout-only): the bay-4 SSD starts fully seated with
its clasp closed; the operator drives the G1 to press the release button, draw
the drive out partway, reinsert it fully, and re-lock the clasp.

## Files

| File | Role |
|---|---|
| `__init__.py` | `gym.register(id="Isaac-ServerRack-G129-Brainco-Joint", ...)` |
| `server_rack_g1_29dof_brainco_joint_env_cfg.py` | The `ManagerBasedRLEnvCfg`: scene + actions + observations + (empty) terminations/events + reward + DDS reset events |
| `mdp/` | Re-exports of shared `common_observations` / `common_rewards` |
| `../../common_scene/base_scene_g1_server_rack.py` | Scene base (room + rack + server + SSDs + object + world cam) |
| `../../common_rewards/base_reward_server_rack.py` | Zero reward (timeout-only task) |

Scene assets & placements come from `tasks/g1_server_rack/` (the backdrop is
baked by `tools/bake_environment_usd.py`; see that package's README).

## Cameras (4)

`front_camera` (head D435) + `left_wrist_camera` + `right_wrist_camera` — the 3
egocentric views the data recorder saves as `color_0/1/2` — plus a fixed
`world_camera` (3rd-person). The wrist cams use `CameraPresets.*_brainco_wrist_camera`
mounted on `*_wrist_yaw_link` (BrainCo has no hand-camera link); their pos/rot are
a starting estimate — tune the framing live. The world cam's framing is likewise
a look-at estimate — tune in `base_scene_g1_server_rack.py`.

## Prerequisites (this machine)

Runs in the `unitree_sim_env` conda env (Isaac Sim 5.1 + torch, python 3.11).

Installed (done):
- **IsaacLab 2.3.2** — used via `PYTHONPATH=$LAB/isaaclab`; leaf deps
  (`h5py prettytable toml flatdict einops junitparser trimesh warp-lang hidapi
  gymnasium`) pip-installed.
- **Unitree DDS stack** — `cyclonedds==0.10.2` (bindings built against the
  prebuilt C lib at `/home/admin/isaac-sim/cyclonedds/install`) + editable
  `unitree_sdk2_python`. NB: the SDK pulls numpy>=2 / opencv 5 — both were pinned
  back (`numpy==1.26.0`, `opencv-python==4.10.0.84`) to keep Isaac Sim happy.

- **`pin` + `pin-pink`** (`pinocchio`) — 8 sibling cylinder/wholebody tasks
  `import pink`, and the task registry imports **all** tasks and fails hard on any
  missing dep, so this is required for `--task` discovery at all (not specific to
  this task).
- **BrainCo hand DDS** — built in-repo (`dds/brainco_dds.py`, `--enable_brainco_dds`).

Runtime env every invocation needs: `LD_PRELOAD` for `libgomp`,
`CYCLONEDDS_HOME` + its `lib` on `LD_LIBRARY_PATH`, `PYTHONPATH=$LAB/isaaclab`,
`--device cpu` (CPU torch). See the `g1_server_rack` README / repo memory for the
exact lines.

## Run

```bash
conda activate unitree_sim_env          # or use its python directly
# teleoperation (drive from the XR teleop client over DDS)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-ServerRack-G129-Brainco-Joint --enable_brainco_dds --robot_type g129

# data replay
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-ServerRack-G129-Brainco-Joint --enable_brainco_dds --robot_type g129 \
  --replay --file_path <recorded_dir>

# data generation (records head+wrist images + joint/action states)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-ServerRack-G129-Brainco-Joint --enable_brainco_dds --robot_type g129 \
  --replay --file_path <recorded_dir> --generate_data --generate_data_dir ./data_serverrack
```

## Verified on Isaac Sim 5.1

The full scene builds, resets and steps cleanly: all assets spawn (room / rack /
server / SSDs / robot / object), the **BrainCo robot articulation is live (51
DoF)**, the fixed base is stable, and the **interactive SSD object has its 2 DOFs
(`button_joint`, `handle_joint`) and stays seated in bay 4** (dz≈0). Also verified
end-to-end via `gym.make` (discovery → env build → reset with observations → step;
all 4 cameras, 51 DoF) and the BrainCo DDS command→action mapping (including the
finger coupling). The full `sim_main` teleop run additionally needs the
`xr_teleoperate` client publishing to `rt/brainco/cmd`.

## The interactive SSD "object" (resolved)

The shipped `ssd.usda` was converted on **Isaac Sim 6.0** and yields **0 PhysX
DOFs on 5.1** (and is multi-body, so not a single RigidObject) — it is used only
for the static decor SSDs. The task object uses a **5.1-native re-import**,
`assets/objects/ssd_articulated/ssd_articulated.usd`, produced by
[`tools/reimport_ssd_articulated_51.py`](../../../tools/reimport_ssd_articulated_51.py)
(IsaacLab `UrdfConverter`, floating base, free joints). It exposes the real
`handle_joint` (clasp) + `button_joint` (release) DOFs; joint stiffness/damping,
seated retention and grasp friction are start values in
`base_scene_g1_server_rack.py` to **tune live** during teleop.
