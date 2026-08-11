# Isaac-ServerRack-G129-Inspire-Joint

A registered IsaacLab task: a Unitree G1 (29 DoF, **BrainCo** hands, fixed base)
services a 42U rack holding a Dell R750. Built to mirror
`pick_place_redblock_g1_29dof_inspire` 1:1 so the framework's **teleoperation /
replay / data-generation** paths pick it up unchanged.

> **Naming:** the task id / folder still say `Inspire` (from the original build)
> but the robot is now **BrainCo** (`G129_CFG_WITH_BRAINCO_HAND`, 22 finger DOFs
> vs Inspire's 24). Rename to a `-Brainco-` id/folder if you want the name to
> match — say the word and I'll do it (it's a mechanical rename of the package +
> gym id).

> **BrainCo hand teleop needs a BrainCo DDS.** The arm teleops over `rt/lowcmd`
> as usual, but there is no BrainCo hand DDS channel in this framework (Inspire/
> Dex1/Dex3 only). So live finger teleop won't drive the BrainCo hand until a
> `brainco` DDS object is added (matching the real hand's interface); the hand
> observation (`get_robot_brainco_joint_states`) already publishes to it if
> present. Scripted / replay hand control and data recording work today.

**Task** (operator-judged, timeout-only): the bay-4 SSD starts fully seated with
its clasp closed; the operator drives the G1 to press the release button, draw
the drive out partway, reinsert it fully, and re-lock the clasp.

## Files

| File | Role |
|---|---|
| `__init__.py` | `gym.register(id="Isaac-ServerRack-G129-Inspire-Joint", ...)` |
| `server_rack_g1_29dof_inspire_joint_env_cfg.py` | The `ManagerBasedRLEnvCfg`: scene + actions + observations + (empty) terminations/events + reward + DDS reset events |
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

Still needed before `sim_main.py --task` works — **`pink` + `pinocchio`**: 8
sibling cylinder/wholebody tasks `import pink`, and the task registry
(`tasks/__init__` → `import_packages`) imports **all** tasks and **fails hard**
on the first missing dep. So discovery is blocked for *every* task, ours
included, until `pinocchio` (+ `pin-pink`) is installed. (Not specific to this
task.)

Runtime env every invocation needs: `LD_PRELOAD` for `libgomp`,
`CYCLONEDDS_HOME` + its `lib` on `LD_LIBRARY_PATH`, `PYTHONPATH=$LAB/isaaclab`,
`--device cpu` (CPU torch). See the `g1_server_rack` README / repo memory for the
exact lines.

## Run (once the DDS stack is installed)

```bash
conda activate unitree_sim_env          # or use its python directly
# teleoperation (drive from the XR teleop client over DDS)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-ServerRack-G129-Inspire-Joint --enable_inspire_dds --robot_type g129

# data replay
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-ServerRack-G129-Inspire-Joint --enable_inspire_dds --robot_type g129 \
  --replay --file_path <recorded_dir>

# data generation (records head+wrist images + joint/action states)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-ServerRack-G129-Inspire-Joint --enable_inspire_dds --robot_type g129 \
  --replay --file_path <recorded_dir> --generate_data --generate_data_dir ./data_serverrack
```

## Verified on Isaac Sim 5.1

The full scene builds, resets and steps cleanly: all assets spawn (room / rack /
server / SSDs / robot / object), the **Inspire robot articulation is live (53
DoF)**, the fixed base is stable, and the **interactive SSD object has its 2 DOFs
(`button_joint`, `handle_joint`) and stays seated in bay 4** (dz≈0). Verified via
a DDS-free InteractiveScene build (`tools/` verify scripts); the gym-registration
+ observation + DDS layer is structurally identical to the verified Inspire
pick-place task, and its end-to-end `sim_main` run is gated only on the
`pink`/`pinocchio` install noted above.

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
