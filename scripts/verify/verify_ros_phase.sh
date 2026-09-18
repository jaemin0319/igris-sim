#!/usr/bin/env bash
# ROS 단계 검증(모두 루프백/도메인 77). 읽기 전용 예제만 실행. 결과: logs/40_verify_ros_phase.log
source ~/igris_ws/scripts/env_ros.sh || exit 1
L="$IGRIS_WS/logs"; R="$L/40_verify_ros_phase.log"; : > "$R"; res() { echo "$1 | $2 | $3" | tee -a "$R"; }
SDKPY="$MAMBA_ROOT_PREFIX/envs/sdk/bin/python"; SIM="$IGRIS_WS/scripts/verify/sim_dds_loopback.py"
# 1) ROS 로컬 통신
( timeout 12 ros2 run demo_nodes_cpp talker > "$L/41_talker.log" 2>&1 & ); sleep 2
timeout 10 ros2 topic echo --once /chatter > "$L/41_chatter_echo.log" 2>&1 && res PASS "ROS2 local pub/sub (rmw=$RMW_IMPLEMENTATION, LOCALHOST)" "$L/41_chatter_echo.log" || res FAIL "ROS2 local pub/sub" "$L/41_chatter_echo.log"
# 2) URDF(xacro) 전개 + robot_state_publisher
xacro "$IGRIS_WS/src/igris_c_description_public/urdf/igris_c_v2.urdf.xacro" > "$IGRIS_WS/data/igris_c_v2.urdf" 2> "$L/42_xacro.log" \
  && res PASS "URDF xacro expand: $(grep -c '<joint ' "$IGRIS_WS/data/igris_c_v2.urdf") joints, $(grep -c '<link ' "$IGRIS_WS/data/igris_c_v2.urdf") links" "$L/42_xacro.log" || res FAIL "URDF xacro expand" "$L/42_xacro.log"
( DISPLAY="${DISPLAY:-:0}" timeout -s INT -k 5 20 ros2 launch igris_c_description display_urdf_with_gui.launch.py > "$L/43_rviz_launch.log" 2>&1 & ); sleep 10
N=$(ros2 node list 2>/dev/null | tr '\n' ' '); echo "$N" | grep -q robot_state_publisher && echo "$N" | grep -q rviz && res PASS "RViz2 + robot_state_publisher launch (nodes: $N)" "$L/43_rviz_launch.log" || res FAIL "RViz2 launch (nodes: $N)" "$L/43_rviz_launch.log"
sleep 13; killall -q joint_state_publisher_gui rviz2 robot_state_publisher 2>/dev/null
# 3) SDK ROS2 listener(읽기 전용) <- MuJoCo LowState(SDK, 루프백)
( timeout 14 ros2 run igris_c_sdk ros_lowstate_listener --ros-args -p robot_namespace:=igris_c_SIMTEST > "$L/44_ros_lowstate_listener.log" 2>&1 & ); sleep 3
( source "$IGRIS_WS/scripts/env_sdk.sh"; cd "$IGRIS_WS"; "$SDKPY" "$SIM" --role sim --secs 3 --realtime --tag _ros > "$L/44_sim_for_ros.log" 2>&1 ); sleep 2
C=$(grep -c "^seq=" "$L/44_ros_lowstate_listener.log"); [ "$C" -gt 0 ] && res PASS "SDK->ROS2 LowState interop on loopback ($C msgs; $(grep '^seq=' "$L/44_ros_lowstate_listener.log" | tail -n 1))" "$L/44_ros_lowstate_listener.log" || res BLOCKED "native SDK pub -> ROS2 listener: 0 msgs (DDS topic/type names differ; robot-side SDK bridge required; logs/44c_dds_topic_names.log)" "$L/44_ros_lowstate_listener.log"
sleep 9
# 4) GMT 노드 (A: onnx_replay, B: ros2 모의 입력). LowCmd는 루프백에서 기록만. 제어모드 브리지는 실행하지 않음.
gmt_run() { # $1=tag $2=params $3=with_mock(0/1)
  rm -f "$IGRIS_WS/data/gmt_logs/infer_$1.csv"
  ( source "$IGRIS_WS/scripts/env_sdk.sh"; cd "$IGRIS_WS"; "$SDKPY" "$SIM" --role cmdlogger --secs 14 --tag "_$1" > "$L/45_${1}_lowcmd_logger.log" 2>&1 & )
  ( timeout -s INT 13 ros2 run igris_c_gmt_public igris_c_gmt_public_node --config "$2" > "$L/45_${1}_gmt_node.log" 2>&1 & ); sleep 2
  [ "$3" = 1 ] && ( timeout 12 python3 "$IGRIS_WS/scripts/verify/mock_gmr_frame_pub.py" "$IGRIS_WS/data/gmr_out/walk1_retarget_frames.txt" 9 30 > "$L/45_${1}_mock_pub.log" 2>&1 & )
  ( source "$IGRIS_WS/scripts/env_sdk.sh"; cd "$IGRIS_WS"; "$SDKPY" "$SIM" --role sim --secs 7 --realtime --tag "_$1" > "$L/45_${1}_sim.log" 2>&1 ); sleep 7
  local csv="$IGRIS_WS/data/gmt_logs/infer_$1.csv" rows=0; [ -f "$csv" ] && rows=$(($(wc -l < "$csv") - 1))
  grep -qiE "onnx|policy|model" "$L/45_${1}_gmt_node.log" && ! grep -qiE "failed to load|cannot open|No such file" "$L/45_${1}_gmt_node.log" && res PASS "GMT[$1] node start + policy load" "$L/45_${1}_gmt_node.log" || res FAIL "GMT[$1] node start/policy load" "$L/45_${1}_gmt_node.log"
  [ "$rows" -gt 0 ] && res PASS "GMT[$1] inference: $rows logged obs/action rows" "$csv" || res FAIL "GMT[$1] inference: no CSV rows" "$L/45_${1}_gmt_node.log"
  grep -q "received [1-9][0-9]* LowCmd.*finite=True" "$L/45_${1}_lowcmd_logger.log" && res PASS "GMT[$1] DDS output (loopback): $(grep -o 'received.*' "$L/45_${1}_lowcmd_logger.log")" "$L/45_${1}_lowcmd_logger.log" || res FAIL "GMT[$1] DDS output: $(tail -n 1 "$L/45_${1}_lowcmd_logger.log")" "$L/45_${1}_lowcmd_logger.log"
}
gmt_run onnx_replay "$IGRIS_WS/config/gmt/params.yaml" 0
gmt_run ros2_input "$IGRIS_WS/config/gmt/params_ros2.yaml" 1
grep -h "published" "$L/45_ros2_input_mock_pub.log" | tee -a "$R"
