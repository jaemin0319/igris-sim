#!/usr/bin/env bash
# Isaac Sim 최소 장면 + IGRIS-C 1대. 예: run_isaac_igris.sh --secs 5 --hold 60   |  --headless
source ~/igris_ws/scripts/env_isaac.sh || exit 1
export ISAAC_ROOT DISPLAY="${DISPLAY:-:0}"
exec python "$IGRIS_WS/scripts/isaac/igris_min_scene.py" "$@"
