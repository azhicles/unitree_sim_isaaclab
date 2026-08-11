#!/usr/bin/env bash
# Launch the G1 server-rack task in the Isaac Sim GUI (gentle arm wave).
# Needs a display. Sets every env var the 5.1 stack requires, then runs
# tools/gui_smoke_server_rack.py. Pass through flags, e.g.:
#   bash tools/run_server_rack_gui.sh --still
set -euo pipefail

ENVDIR=/home/admin/miniforge3/envs/unitree_sim_env
PY="$ENVDIR/bin/python"
LAB=/home/admin/isaac-sim/IsaacLab/source
CDDS=/home/admin/isaac-sim/cyclonedds/install
GOMP="$ENVDIR/lib/python3.11/site-packages/torch.libs/libgomp-58a43326.so.1.0.0"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO"
export PROJECT_ROOT="$REPO"
export PYTHONPATH="$LAB/isaaclab${PYTHONPATH:+:$PYTHONPATH}"
export CYCLONEDDS_HOME="$CDDS"
export LD_LIBRARY_PATH="$CDDS/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_PRELOAD="/lib/aarch64-linux-gnu/libgomp.so.1:$GOMP"

# CPU torch in this env -> device cpu (the GPU still renders the viewport).
exec "$PY" tools/gui_smoke_server_rack.py --device cpu "$@"
