#!/usr/bin/env bash
# 기존 시뮬 환경 + IGRIS-C 1대. 예: run_igris_vla_scene.sh --secs 5 --hold 60  |  --headless  |  --compose-only
source ~/igris_ws/scripts/env_isaac.sh || exit 1
export ISAAC_ROOT DISPLAY="${DISPLAY:-:0}" VLA_ROOT="${VLA_ROOT:-/mnt/isaac/vla-scene}"
exec python "$IGRIS_WS/scripts/isaac/igris_in_vla_scene.py" "$@"
