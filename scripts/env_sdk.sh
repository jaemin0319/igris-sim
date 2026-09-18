# ROBROS SDK(Python 3.12 wheel) + MuJoCo 3.2.7 + onnxruntime. 사용: source ~/igris_ws/scripts/env_sdk.sh
source "$HOME/igris_ws/scripts/env_common.sh"
_igris_path_prepend "$MAMBA_ROOT_PREFIX/envs/tools/bin"; _igris_path_prepend "$MAMBA_ROOT_PREFIX/envs/sdk/bin"
export PYTHONPATH=   # SDK README(pixi.toml)와 동일하게 ROS/system PYTHONPATH 차단
