# 공통: 작업공간 경로 + 안전 기본값(DDS/ROS 모두 루프백 한정). source 전용.
export IGRIS_WS="$HOME/igris_ws"
export MAMBA_ROOT_PREFIX="$IGRIS_WS/envs/mamba"
export CYCLONEDDS_URI="file://$IGRIS_WS/config/cyclonedds_loopback.xml"   # 실물 연결 시에만 명시적으로 교체
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"
_igris_path_prepend() { case ":$PATH:" in *":$1:"*) ;; *) export PATH="$1:$PATH";; esac; }
