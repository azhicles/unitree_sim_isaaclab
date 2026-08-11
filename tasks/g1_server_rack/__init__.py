# Copyright (c) 2025. License: Apache License, Version 2.0
"""G1 services a server rack - scene package.

Layers (see the individual module docstrings):
    scene_cfg     - the interactive task core (robot + server + SSDs) as an
                    InteractiveSceneCfg. Reused unchanged by every environment.
    scene_props   - the 42U rack (real USD or open placeholder) and the SSD tray.
    environments  - swappable backdrops (office now; add more here). The seam
                    for "same task, different background".

Build it standalone with tools/run_g1_server_rack_scene.py (IsaacLab) or, without
torch, tools/preview_scene_rawusd.py.

NOTE: this __init__ intentionally does NOT import scene_cfg. scene_cfg pulls in
isaaclab (hence torch); importing it here would make even the torch-free modules
(placements / environments / scene_props / _authoring) unimportable in the bare
Isaac Sim python. Import G1ServerRackSceneCfg explicitly from .scene_cfg when you
have IsaacLab available.
"""

