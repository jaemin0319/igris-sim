# SETUP — IGRIS-C · PICO 연구 환경 (jammin-MS-7E34)

작성 2026-09-18. 호스트: Ubuntu 24.04.5 x86_64, Core Ultra 7 265K, RAM 64GB, RTX 4060 8GB (driver 580.178.04), `/` 48GB.

## 1. 공식 코드로 확인한 실제 파이프라인

```
PICO ─(Wi-Fi/USB, tcp 63901)→ XRoboToolkit PC Service ─(gRPC 127.0.0.1:60061)→ xrobotoolkit_sdk(py3.10)
  → GMR scripts/xrobot_teleop_to_robot_w_hand.py ─→ Redis(127.0.0.1:6379)
  → GMR scripts/redis_to_ros2_bridge.py (ROS py3.12, raw socket) ─→ /gmr/teleop/retarget_frame (std_msgs/String)
  → igris_c_gmt_public_node (ONNX 정책, obs 1601 → 23 actions) ─→ CycloneDDS rt/lowcmd (LowCmd, 31 모터) → 로봇
```

- `igris_c_isaacsim_public`에는 **DDS/ROS 브리지가 없다**. Isaac Lab에서 NPZ 모션/명령을 재생하는 독립 추론 환경(Student 1601→23, HugWBC 700→13)이다. "GMT→DDS→Isaac" 연결은 공식 코드에 없음.
- GMT 노드는 모드 전환을 하지 않는다. `gmr_control_mode_dds_bridge`는 PICO 버튼으로 **로봇 제어모드 요청을 송신**하므로 실물 없이/격리 없이 실행 금지.
- GMT `config/params.yaml`은 `student_130.onnx`를 가리키지만 저장소에는 `student_126.onnx`만 있음 → `config/gmt/params.yaml`(사본)에서 수정.

## 2. 고정 버전(커밋)

| 구성 | 커밋/버전 | 위치 |
| --- | --- | --- |
| igris_c_sdk_public | d13565b (2026-08-08), wheel 2.1.0.post2 | src/igris_c_sdk_public |
| igris_c_description_public | 784616e (2026-07-16) | src/igris_c_description_public |
| igris_c_isaacsim_public | b53e424 (2026-09-17) | src/igris_c_isaacsim_public |
| └ IsaacLab 서브모듈 | f4aa17f = **Isaac Lab 2.3.2** (shallow) | third_party/IsaacLab |
| └ IsaacSim 서브모듈 | aa503a9 (미수신; pip 설치 경로에선 불필요) | — |
| igris_c_gmt_public | 990cdad (2026-09-10) | src/igris_c_gmt_public |
| robrosinc/GMR | d6e049d (2026-09-10) | src/GMR |
| XRoboToolkit-PC-Service | 85bac4d, 릴리스 v1.0.0 ubuntu_24.04 deb | src/…, downloads/, opt/xrobotoolkit |
| XRoboToolkit-PC-Service-Pybind (YanjieZe) | 75cb113 → xrobotoolkit_sdk 1.0.2 | src/… |
| onnxruntime C++ | 1.30.0 (linux-x64 tgz) | opt/onnxruntime |
| Isaac Sim | **5.1.0 (pip, Python 3.11, MODE=sim)** 설치본 17GB; torch 2.7.0은 의존성으로 설치됨. Isaac Lab 미설치 | /mnt/isaac/env |
| 기존 환경 출처 | vla-repro@ca375db → Release snapshot-g1-20260914-E0FK4Q (22파트 22.78GB, SHA-256 전부 OK) | src/vla-repro, /mnt/isaac/vla-scene |
| GitHub CLI | gh 2.101.0 (tools env), 계정 jaemin0319 | envs/mamba/envs/tools |

## 3. 환경 분리 (시스템 Python 무변경, sudo pip 없음)

micromamba 2.9.0 (`~/.local/bin/micromamba`, root `~/igris_ws/envs/mamba`).

| 환경 | Python | 용도 | 활성화 |
| --- | --- | --- | --- |
| tools | — | git, git-lfs, cmake, ninja, redis-server | (다른 env 스크립트가 PATH에 추가) |
| sdk | 3.12 | igris_c_sdk wheel, **mujoco==3.2.7**, onnxruntime 1.30.0, xacro | `source scripts/env_sdk.sh` |
| gmr | 3.10 | GMR(-e), torch 2.14 **CPU**, mujoco 3.13, mink, xrobotoolkit_sdk | `source scripts/env_gmr.sh` |
| ROS | system 3.12 | ROS 2 Jazzy + ros2_ws(colcon) | `source scripts/env_ros.sh` |
| isaac (`/mnt/isaac/env`) | 3.11 | Isaac Sim 5.1.0. 캐시는 `/mnt/isaac/{cache,data}`(XDG 재지정) | `source scripts/env_isaac.sh` |

- `env_common.sh`가 **안전 기본값**을 건다: `CYCLONEDDS_URI=config/cyclonedds_loopback.xml`(lo 전용), `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, `ROS_DOMAIN_ID=77`. 시험용 네임스페이스는 `igris_c_SIMTEST`.
- MuJoCo ≥3.3은 공식 `igris_c_v2.xml.xacro`(`kv`+`dampratio` 동시 정의)를 거부 → sdk 환경은 3.2.7 고정. GMR은 자체 asset을 쓰므로 3.13 유지.
- 전체 패키지 목록: `docs/pip_freeze_{sdk,gmr}.txt`.

## 4. 재실행 명령

```bash
# (1회, sudo) ROS 2 Jazzy(ros-base+rviz2+dev tools), 빌드 도구, XRoboToolkit deb. 드라이버/원격 패키지 변경 시 자동 중단
sudo bash ~/igris_ws/scripts/00_sudo_install.sh
# colcon(igris_c_sdk, igris_c_description, igris_c_gmt_public) + SDK C++ 예제 빌드
bash ~/igris_ws/scripts/10_build_ros_ws.sh
# ROS 단계 검증(루프백, 읽기 전용 예제 + GMT 노드 LowCmd 기록)
bash ~/igris_ws/scripts/verify/verify_ros_phase.sh
# MuJoCo(공식 모델) → SDK LowState 루프백 발행/구독 + mp4·npz 기록
bash ~/igris_ws/scripts/verify/run_sim_dds_loopback.sh
# GMR 오프라인(LAFAN1 BVH → IGRIS-C, mp4+pkl)
source ~/igris_ws/scripts/env_gmr.sh && python scripts/bvh_to_robot.py --robot robros_igris_c_v2 --format lafan1 \
  --bvh_file ~/igris_ws/data/lafan1/walk1_subject1_300f.bvh --record_video \
  --video_path ~/igris_ws/data/gmr_out/walk1_igris_c.mp4 --save_path ~/igris_ws/data/gmr_out/walk1_igris_c.pkl
# 텔레옵 체인(PICO 연결 시): 서비스 → Redis → GMR → (ROS 터미널) 브리지
~/igris_ws/scripts/xrobotoolkit_service.sh start ; ~/igris_ws/scripts/redis_local.sh start
source ~/igris_ws/scripts/env_gmr.sh && bash scripts/retarget_teleop.sh
source ~/igris_ws/scripts/env_ros.sh && cd ~/igris_ws/src/GMR && bash scripts/run_ros2_redis_bridge.sh
# GMT 정책 호환성 점검(A: 정적 계약 완료, B: 동적 대조는 스크립트 수정 필요 — CURRENT_STATE 참조)
source ~/igris_ws/scripts/env_sdk.sh && python ~/igris_ws/scripts/verify/gmt_policy_compat.py
# Isaac Sim만(MODE=sim, 여유 ≥22GB) / 정책 예제까지(MODE=lab, ≥32GB). 공간 검사 통과 시에만 다운로드
ISAAC_ROOT=/mnt/isaac bash ~/igris_ws/scripts/20_install_isaac.sh          # verify/verify_isaac.sh는 MODE=lab 전용
# 기존 환경 자산(암호는 pinentry 창에만): download → list → extract → forget
bash ~/igris_ws/scripts/30_fetch_vla_scene.sh download|list|extract|forget
# ★ 기존 환경 + IGRIS-C 1대(GUI 유지)
bash ~/igris_ws/scripts/run_igris_vla_scene.sh --secs 12 --hold 3600      # 기본: 골반 고정 on + 임시 외형 on + 팔 동작 시험
#   옵션: --no-fix(고정 해제, 제어기 없어 넘어짐) · --fix-link root(상체 base_link를 고정 베이스로) · --no-appearance(공식 USD의 흰색 그대로) · --headless
```

## 5. 디스크 (실측, 3차 갱신)

`/` 48GB: 여유 14GB(Isaac 관련 사용 없음). `/mnt/isaac`(nvme0n1p6, ext4, 98GB, UUID 05b3e26d-…, fstab `defaults,nofail`): 사용 ≈41GB.
| 항목 | 크기 |
| --- | --- |
| Isaac Sim 설치본 `env` | 17GB |
| 암호화 파트+보충본 `vla-scene/parts` | 23.1GB (장면 검증 후 삭제 가능, 재다운로드 가능) |
| 복호화 중간파일 | 0 (스트리밍; 평문 62.4GiB는 디스크에 쓰지 않음) |
| 선택 추출 `vla-scene/extracted` | 1.2GB (720개 항목; 실제 사용은 PackingTable 153MB + 머그 9MB + 설정 .py) |
| Kit/GL 캐시·pkgs·장면 | ≈1–5GB |
최대 동시 사용 ≈45GB(설치 중 임시 8GB 포함 시 51GB) → 100GB 내.

## 6. 안전 메모

- SDK 예제 중 읽기 전용은 `ros_lowstate_listener`, `cyclonedds_sensor_viewer`, `cyclonedds_metaquest`뿐(`logs/23_example_command_audit.log`). 나머지는 LowCmd/서비스/Twist/Hand 명령을 송신한다.
- CycloneDDS는 수신 소켓을 0.0.0.0에 바인드한다(송신·로케이터는 lo 한정, `logs/19_dds_isolation.log`). 이 PC는 공인 IP(163.180.x) 망에 있으므로 실물 연결 전 방화벽/전용 NIC 구성 권장.
- XRoboToolkit 서비스는 tcp `*:63901`을 연다(PICO 접속용). 사용하지 않을 때는 `xrobotoolkit_service.sh stop`.
- LAFAN1 샘플은 CC BY-NC-ND 4.0(비상업 연구용).

## 7. GMT ↔ student_126.onnx 계약 (ONNX 메타데이터 기준)

- 입력 `obs[1,1601]`(배치 1 고정) = 히스토리 20: joint_pos_rel·joint_vel(23)·projected_gravity·base_ang_vel(3)·last_actions(23) + 히스토리 1: motion_joint_pos·vel(23)·anchor z(1)·yaw-free 6D(6)·body_pos_b(14×3)·anchor lin/ang vel_b(3). 정규화는 ONNX 내장, GMT는 미적용.
- 출력 `actions[1,23]` → `q_des = q_default + 0.25·a`(비잔차) → 시스템 인덱스 매핑(WY0…RAR14, LSP15…LEP18, RSP22…REP25) → LowCmd(31). 손목·목은 정책 외.
- GMT는 로봇 모드와 무관하게 LowState+모션이 들어오면 **즉시 LowCmd를 발행**한다 → 루프백 설정(`config/gmt/*.yaml`, `env_common.sh`) 밖에서 실행 금지.
- ROS 2 예제 노드는 로봇 측 SDK bridge의 `rt/…` 토픽·`igris_c_sdk::msg::dds_` 타입을 쓰므로 네이티브 SDK 발행과 직접 연결되지 않는다.
- MuJoCo 시험(`sim_dds_loopback.py`)은 **상태 발행 전용 개루프**다. 폐루프(LowCmd 반영)는 미구현·미검증.

## 8. 기존 환경 + IGRIS-C 장면 (config/vla_scene.yaml → scripts/isaac/igris_in_vla_scene.py)

- 출처: 사용자 최종 설정 `tasks/common_scene/base_scene_pickplace_cylindercfg.py`·`…/pickplace_cylinder_g1_29dof_dex1_joint_env_cfg.py`·`tasks/common_config/robot_configs.py`(sha256은 YAML `provenance`). Isaac Lab 장면 cfg를 실행하지 않고 값만 옮겨 USD 레이어로 구성(Isaac Lab·G1 환경 불필요).
- 구성: Grid 바닥 10×10(tint 0.04, 기본 조명 제거) · PackingTable (0,0.55,−0.2) kinematic + 흰색 0.9/roughness 0.65 재질 override · YCB 025 머그 (−0.20,0.27,0.8657) · 회색 배경판 4장(시각 전용) · DomeLight 3000/0.75. Room(warehouse)·추가 작업대는 최종 설정에서 비활성 → 미포함(USD 보충본 불필요).
- G1 자리 `/World/envs/env_0/Robot` = (−0.15, 0, 0.76), yaw 90° → **비활성 prim으로만 기록**. IGRIS-C는 `/World/envs/env_0/IGRIS_C`에 공식 `extras/wrist_hand_independent/igris_c.usd`를 reference. x,y,yaw는 G1 기준, **z = 바닥 raycast(0.0) + 공식 기립 높이 0.961 + 0.01 = 0.971**.
- 원본 보존: 자산은 전부 reference, 재질·kinematic·배치는 새 레이어(`/mnt/isaac/scenes/igris_in_vla_scene.usda`)의 override. 로봇 USD에 Bake/Flatten 없음.
- 장면 카메라 `/World/SceneCamera`(eye (−0.1,3.6,1.6) = 부모 cfg의 world_camera 위치). G1 탑재 카메라·손·브래킷·제어 스크립트는 미이식.
- 결과물: `data/isaac/igris_vla_scene_<tag>.json`(자산 누락·겹침·발 높이·물리 시계열·VRAM) + `…_init_{front,diag,side}.png`, `…_after_physics.png`.

## 9. IGRIS override 레이어 (원본 USD 무수정, Bake/Flatten 없음)

루트 장면 레이어의 subLayer로 두 파일을 실행 시 생성한다(`/mnt/isaac/scenes/`). 설정 원본은 Git의 YAML.

| 레이어 | 설정 | 내용 | 끄기 |
| --- | --- | --- | --- |
| `igris_fix_pelvis.usda` | `config/vla_scene.yaml` → `igris.fix {enabled, link, hold_tolerance}` | 현재 자세의 월드 포즈에 world→링크 FixedJoint. `link: auto` = 양쪽 Joint_Hip_Pitch의 부모(`Link_Waist_Pitch`, 실제 골반; articulation 밖 구속). `root` = `base_link`(상체)를 Isaac Lab `fix_root_link` 방식(루트 API를 부모로 이동)으로 고정 | `--no-fix` 또는 `enabled: false` |
| `igris_appearance.usda` | `config/igris_appearance.yaml` | 링크 `visuals` 스코프에 UsdPreviewSurface를 strongerThanDescendants로 바인딩(렌더링 전용) | `--no-appearance` 또는 `enabled: false` |

- 골반 고정은 **지지 상태**(균형 제어 아님). 검증: 12초, 위치 0.00mm·방향 ≤0.50°(허용치 1.0°), 팔 4관절 사인파 추종 확인(`igris.arm_test`).
- 외형은 **공식 스킨이 아닌 임시 근사 재질**(공식 사진 육안 참고, 출처는 YAML 머리말). 공식 외형·재질 파일 제공 여부 확인 전까지 수정·확정 보류.
- 구현 메모: 레이어 mute/unmute·RigidPrim 뷰 추가는 PhysX 텐서 뷰를 무효화하므로, 전후 스크린샷 뒤 `world.reset()`으로 재초기화하고 고정 링크 포즈는 USD 변환에서 읽는다. 최종 배치·레이어 작성은 `world.stop()` 상태에서 한다(관절 프레임 불일치 경고 방지).
