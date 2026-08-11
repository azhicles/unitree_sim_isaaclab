# Source this before running sim_main.py:  source tools/teleop_env.sh
# Sets the env the Isaac Sim 5.1 stack needs (conda env python, libgomp
# LD_PRELOAD, CycloneDDS, IsaacLab on PYTHONPATH). Safe to source repeatedly.
_ENVDIR=/home/admin/miniforge3/envs/unitree_sim_env
_LAB=/home/admin/isaac-sim/IsaacLab/source
_CDDS=/home/admin/isaac-sim/cyclonedds/install
_GOMP="$_ENVDIR/lib/python3.11/site-packages/torch.libs/libgomp-58a43326.so.1.0.0"

export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$_LAB/isaaclab${PYTHONPATH:+:$PYTHONPATH}"
export CYCLONEDDS_HOME="$_CDDS"
export LD_LIBRARY_PATH="$_CDDS/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_PRELOAD="/lib/aarch64-linux-gnu/libgomp.so.1:$_GOMP"
# The sim's DDS runs on domain 1 - the teleop client must match (ChannelFactoryInitialize(1)).

echo "[teleop_env] ready. python: $_ENVDIR/bin/python  (use --device cpu)"
