# ROS 2 Jazzy(system Python 3.12) + colcon 워크스페이스 + onnxruntime C++. 사용: source ~/igris_ws/scripts/env_ros.sh
source "$HOME/igris_ws/scripts/env_common.sh"
[ -f /opt/ros/jazzy/setup.bash ] || { echo "ROS 2 Jazzy 미설치: sudo bash ~/igris_ws/scripts/00_sudo_install.sh"; return 1; }
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
export CMAKE_PREFIX_PATH="$IGRIS_WS/opt/onnxruntime:${CMAKE_PREFIX_PATH:-}"
export LD_LIBRARY_PATH="$IGRIS_WS/opt/onnxruntime/lib:${LD_LIBRARY_PATH:-}"
if [ -f "$IGRIS_WS/ros2_ws/install/setup.bash" ]; then source "$IGRIS_WS/ros2_ws/install/setup.bash"; fi
