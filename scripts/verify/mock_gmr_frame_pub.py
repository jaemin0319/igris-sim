#!/usr/bin/env python3
"""모의 GMR 입력: GMR 오프라인 결과(pkl→payload 줄)를 /gmr/teleop/retarget_frame(std_msgs/String)로 발행.
redis_to_ros2_bridge.py와 같은 repr(dict) 형식·BEST_EFFORT QoS. ROS 토픽만 발행(로봇 DDS 명령 없음)."""
import sys, time, rclpy
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String
lines = open(sys.argv[1]).read().splitlines(); secs = float(sys.argv[2]); hz = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
rclpy.init(); node = rclpy.create_node("mock_gmr_frame_pub"); pub = node.create_publisher(String, "/gmr/teleop/retarget_frame", qos_profile_sensor_data)
t0 = time.time(); i = 0
while time.time() - t0 < secs:
    m = String(); m.data = lines[i % len(lines)]; pub.publish(m); i += 1; time.sleep(1.0 / hz)
print(f"[mock_gmr] published {i} frames"); node.destroy_node(); rclpy.shutdown()
