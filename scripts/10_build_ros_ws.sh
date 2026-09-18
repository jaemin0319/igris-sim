#!/usr/bin/env bash
# colcon 빌드(ROS msgs/nodes, description, GMT) + SDK C++ 예제 빌드. sudo 불필요. 로그: ~/igris_ws/logs/30_*.log
source ~/igris_ws/scripts/env_ros.sh || exit 1
SDK_CMAKE="$IGRIS_WS/src/igris_c_sdk_public/cyclonedds/lib/cmake/igris_c_sdk"
mkdir -p "$IGRIS_WS/ros2_ws/src"; cd "$IGRIS_WS/ros2_ws"
ln -sfn ../../src/igris_c_sdk_public/ros2/src/igris_c_sdk_public src/igris_c_sdk; ln -sfn ../../src/igris_c_description_public src/igris_c_description; ln -sfn ../../src/igris_c_gmt_public src/igris_c_gmt_public
colcon build --symlink-install --packages-select igris_c_sdk igris_c_description > "$IGRIS_WS/logs/30_colcon_sdk_desc.log" 2>&1; echo "colcon sdk+description rc=$?"
source install/setup.bash
# GMT는 네이티브 C++ SDK(igris_c_sdk::igris_c_sdk, 동명 ROS 패키지 아님)에 링크 -> igris_c_sdk_DIR 고정
colcon build --packages-select igris_c_gmt_public --cmake-args "-Digris_c_sdk_DIR=$SDK_CMAKE" -DCMAKE_BUILD_TYPE=Release > "$IGRIS_WS/logs/31_colcon_gmt.log" 2>&1; echo "colcon gmt rc=$?"
cmake -S "$IGRIS_WS/src/igris_c_sdk_public/cyclonedds" -B "$IGRIS_WS/build/sdk_cpp_examples" -DCMAKE_BUILD_TYPE=Release > "$IGRIS_WS/logs/32_sdk_cpp_examples.log" 2>&1 \
  && cmake --build "$IGRIS_WS/build/sdk_cpp_examples" -j"$(nproc)" >> "$IGRIS_WS/logs/32_sdk_cpp_examples.log" 2>&1; echo "sdk cpp examples rc=$?"
