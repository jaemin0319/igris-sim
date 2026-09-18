# CURRENT STATE — 2026-09-18 (2차 갱신, 범위 축소 후)

판정: PASS / FAIL / BLOCKED / NOT TESTED. 로그: `~/igris_ws/logs/`.

## 현재 목표(축소)

**Isaac Sim 최소 장면에 IGRIS-C 1대를 불러와 화면 표시 + 기본 물리 실행 확인**까지.
추가 GMR/GMT·PICO·DDS 검증, 보행, 데이터 수집은 **보류**. Isaac DDS 브리지 신규 구현은 범위 밖.

## 안전 마무리 상태 (전환 시점)

- apt/dpkg: 진행 중 작업 없음, `dpkg --audit` 이상 없음(`unattended-upgr`는 시스템 상주 데몬, 미접촉). 잠금 파일 미접촉.
- 빌드: 실행 중 없음(3종 모두 완료). 직접 띄운 ROS 노드·시뮬·Redis·XRoboToolkit 서비스·ros2 daemon: 모두 종료 확인.
- Tailscale·NoMachine 동작 유지. ssh 서비스는 원래 비활성(변경 없음). NVIDIA 580.178.04 유지.
- 기존 설치물(envs, src, opt, ros2_ws, /opt/ros, /opt/apps/roboticsservice) 모두 보존. 삭제한 것 없음.

## 완료

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| sudo 설치(ROS 2 Jazzy ros-base+rviz2+dev tools, 빌드 도구, XRoboToolkit deb) | PASS | logs/00_sudo_install.log (RESULT: OK) |
| colcon: igris_c_sdk(ROS msgs/nodes), igris_c_description, igris_c_gmt_public | PASS | logs/30_colcon_sdk_desc.log, 31_colcon_gmt.log |
| SDK C++ 예제 8종 빌드(`cyclonedds_sensor_viewer`는 OpenCV 없음으로 공식 CMake가 제외) | PASS | logs/32_sdk_cpp_examples.log |
| ROS 2 로컬 pub/sub (rmw_cyclonedds, LOCALHOST, 도메인 77) | PASS | logs/41_chatter_echo.log |
| URDF xacro 전개(34 joints/35 links) + RViz2·robot_state_publisher 기동 | PASS | logs/42_xacro.log, 43_rviz_launch.log |
| GMT 노드 — 정책 로딩(student_126.onnx, C++ ORT 1.30) | PASS | logs/45_*_gmt_node.log |
| GMT 노드 — 추론(50Hz, 347행 obs/action CSV, onnx ≈0.1–0.3ms) | PASS | data/gmt_logs/infer_{onnx_replay,ros2_input}.csv |
| GMT 노드 — ROS 입력 수신(모의 GMR payload 267프레임 → `motion_mode=live`) | PASS(수신·모드 전환) / 내용 대조는 미완(아래) | logs/45_ros2_input_gmt_node.log, 45_ros2_input_mock_pub.log |
| GMT 노드 — DDS 출력(LowCmd 347개, finite, **루프백 lo·도메인 77·ns SIMTEST에서 기록만**) | PASS | logs/45_*_lowcmd_logger.log |
| student_126 ↔ GMT 정적 계약(A1–A8): 관절 순서 23, obs 항목 순서 12, 히스토리 20×5+1×7(=1601), 기준자세, action scale 0.25·비잔차, 추적 바디 14개 순서, 정규화는 ONNX 내장(Sub/Div)·GMT 미적용, 시스템 인덱스↔GMR/SDK 모터 순서 | PASS | logs/46_gmt_policy_compat.log |
| 공개 Isaac 자산 대비 PD 게인(A9) | **MISMATCH**: HipPitch/Knee/HipRoll 일치. X6-60군(HipYaw·WaistYaw·Shoulder·Elbow) GMT kp 60.76 = Isaac 121.51의 1/2, Waist Roll/Pitch·Ankle Pitch/Roll 상이(병렬기구 PJS 공간 차이 가능). student_126 학습 자산은 비공개(ROBROS_LAB)라 판정 불가 | logs/46_gmt_policy_compat.log |
| 1차 세션 항목(SDK import, MuJoCo 모델, GMR 오프라인, XRoboToolkit 등) | PASS(변동 없음) | 1차 로그 10–24 |

## 진행 중이던 것(중단·보류)

- `scripts/verify/gmt_policy_compat.py` **B부(동적 대조)**: 스크립트 버그(ONNX 배치 차원 1 고정인데 347행 일괄 입력)로 B1에서 중단. 미실행: C++↔Python 추론 일치, 히스토리 순서·last_action, joint_pos_rel 매핑, 모션 항목(anchor z·yaw-free 6D·body_pos_b) 재구성 대조, ROS payload 내용 대조(B6), LowCmd q/kp 매핑(B7–B8). → **차원·메타데이터 일치만 확인된 상태이며 호환성 검증 완료가 아님.** 입력 CSV/npz는 보존됨(재실행 시 노드 재구동 불필요).

## 미검증 / BLOCKED

| 항목 | 판정 | 비고 |
| --- | --- | --- |
| 네이티브 SDK 발행 → ROS 2 `ros_lowstate_listener` | BLOCKED(구조상) | DDS 토픽·타입 이름이 다름(`igris_c_SIMTEST/rt/lowstate`·`igris_c::msg::dds::LowState` vs `rt/…`·`igris_c_sdk::msg::dds_::LowState_`). ROS 2 예제는 로봇 측 SDK bridge 필요. logs/44c_dds_topic_names.log |
| **폐루프 제어**(LowCmd→PD 토크→물리→LowState) | NOT TESTED | 지금까지의 MuJoCo 시험은 **상태 발행 전용**(고정 베이스, LowCmd 미반영, 개루프). GMT 출력 크기는 추종 성능 지표 아님 |
| 정책 추종 성능·학습 시 의미 일치(게인 포함) | NOT TESTED | Isaac(Lab) 폐루프 또는 실기 필요 |
| PICO 실기기 스트림, Redis→ROS 브리지 실데이터 | BLOCKED(장비) / 보류 | |
| Isaac Sim 설치·최소 장면·IGRIS 로딩 | BLOCKED(디스크 15GB < 22GB) | 아래 |
| CUDA 연산(torch.cuda) | NOT TESTED | MODE=lab에서만 해당 |

## Isaac 최소 목표 — 공간 산정과 확보안

- 공식 IGRIS-C는 완성 USD(9.8MB, `…/assets/robots/robros/igris_c/from_urdf/usd/igris_c.usd`)로 제공 → **Isaac Lab·torch 불필요**(`MODE=sim`). Lab은 공식 정책 예제(`isaaclab.sh -p …`)에만 필요.
- 실측(HEAD 요청, logs/60_isaacsim_wheel_sizes.log): `isaacsim[all,extscache]==5.1.0` 휠 합계 ≈4.8GB 압축(extscache-kit 3.0 + kit-sdk 1.35 + 기타 0.45).
- 필요 공간(MODE=sim): 설치 ≈11–13GB(추정, 압축 해제) + Kit 셰이더/확장/데이터 캐시 ≈3–5GB + 설치 중 임시 ≈4GB → **여유 22GB 이상 권장**. MODE=lab은 +torch cu128 ≈7GB + Lab deps ≈2GB → 32GB.
- 경로: env `$ISAAC_ROOT/env`, pip 임시 `$ISAAC_ROOT/tmp`, 캐시 `$ISAAC_ROOT/{cache,data}`(XDG 재지정; 기본은 `~/.cache/ov`, `~/.local/share/ov`, `~/.nvidia-omniverse`). 기본 `ISAAC_ROOT=~/igris_ws/envs/isaac`.
- 현재 `/` 여유 15GB → 부족. 확보안(사용자 결정, 임의 수행 안 함):
  1. **(권장)** Windows 디스크 관리에서 NTFS(882GB) 60–100GB 축소 → Ubuntu에서 새 ext4 파티션 생성·`/mnt/isaac` 마운트 → `ISAAC_ROOT=/mnt/isaac`. 루트 파티션 확장은 복구 파티션(p4)이 사이에 있어 이동이 필요하므로 비권장.
  2. 별도 SSD/외장 ext4 → 동일하게 `ISAAC_ROOT` 지정.
  3. NTFS 위 ext4 루프 이미지(파티션 무변경, Windows 빠른 시작 해제 필요, 느림) — 시험용.
  - 참고: `/` 안에서 회수 가능한 내 설치물은 중복 XRoboToolkit 추출본·deb(≈0.55GB)뿐이라 22GB 도달 불가.
- 요구사항: VRAM 8GB < 공식 최소 16GB(**미충족**, 실행 시험 NOT TESTED). Vulkan은 RTX 4060 인식(logs/61_vulkan_summary.log), 현재 VRAM 사용 0.7GB.

## 다음 작업

1. 공간 확보안 결정·수행(사용자) → `ISAAC_ROOT=<경로> bash scripts/20_install_isaac.sh` (MODE=sim).
2. 최소 장면 스크립트 작성·실행(미작성): SimulationApp → 지면+조명 → `igris_c.usd` reference 1대 → GUI 표시 → 수 초 물리 step, 관절 수·베이스 높이·VRAM 기록.
3. (보류 해제 시) compat B부 수정·재실행, 폐루프 시험, PICO 연결.
