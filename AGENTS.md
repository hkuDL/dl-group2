# Project instructions

## User requirements
- Never modify third_party files or change the pinned submodule revision.
- Preserve the default GUI view: robot in the foreground, table behind it, viewed obliquely from behind the robot.
- scripts/pick_red_cube.py uses a FREE camera with lookat=[0.25,0,0.75], distance=2.8, azimuth=-155, elevation=-18. Do not replace this with a fixed/head/wrist camera or change these defaults unless the user explicitly asks.
- Resetting or switching task cases must not change the viewer camera.
- Dataset head/wrist cameras are independent of the GUI view.
