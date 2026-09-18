# GMR(Python 3.10, CPU torch) + xrobotoolkit_sdk. 사용: source ~/igris_ws/scripts/env_gmr.sh
source "$HOME/igris_ws/scripts/env_common.sh"
_igris_path_prepend "$MAMBA_ROOT_PREFIX/envs/tools/bin"; _igris_path_prepend "$MAMBA_ROOT_PREFIX/envs/gmr/bin"
export PYTHONPATH=
cd "$IGRIS_WS/src/GMR"
