# Isaac Sim 5.1.0 (Python 3.11). 사용: source ~/igris_ws/scripts/env_isaac.sh
source "$HOME/igris_ws/scripts/env_common.sh"
ISAAC_ROOT="$(cat "$IGRIS_WS/envs/isaac_root.txt" 2>/dev/null || echo /mnt/isaac)"
[ -x "$ISAAC_ROOT/env/bin/python" ] || { echo "Isaac 환경 없음(보류 상태): bash ~/igris_ws/scripts/20_install_isaac.sh"; return 1; }
_igris_path_prepend "$ISAAC_ROOT/env/bin"; export CONDA_PREFIX="$ISAAC_ROOT/env" OMNI_KIT_ACCEPT_EULA=YES PYTHONPATH=
# Kit 캐시/데이터를 ISAAC_ROOT 아래로(기본 위치: ~/.cache/ov, ~/.local/share/ov, ~/.nvidia-omniverse)
export XDG_CACHE_HOME="$ISAAC_ROOT/cache" XDG_DATA_HOME="$ISAAC_ROOT/data"; mkdir -p "$XDG_CACHE_HOME" "$XDG_DATA_HOME"
export IGRIS_USD="$IGRIS_WS/src/igris_c_isaacsim_public/source/robros_lab/robros_lab/assets/robots/robros/igris_c/from_urdf/usd/igris_c.usd"
