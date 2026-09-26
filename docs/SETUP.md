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
bash ~/igris_ws/scripts/run_igris_vla_scene.sh --secs 12 --hold 3600      # 기본: 몸통(base_link) 고정 + 팔 접은 자세 + 고개 30° 아래 + 임시 외형 + RGB 카메라 4개 + 하단 모니터. 동작 시험은 --arm-test
#   하단 실시간 모니터 [HEAD STEREO (L|R)] [LEFT HAND] [RIGHT HAND] 기본 표시(scripts/isaac/igris_monitor.py) · 끄기: --no-monitor
#   카메라 옵션: --no-cameras · --viewport-camera head_left|head_right|hand_left|hand_right|scene (hold 중 GUI 뷰포트) · 캡처: data/isaac/cameras/<tag>_{static,moving,end}_*.png
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

루트 장면 레이어의 subLayer로 아래 파일을 실행 시 생성한다(`/mnt/isaac/scenes/`). 설정 원본은 Git의 YAML.

| 레이어 | 설정 | 내용 | 끄기 |
| --- | --- | --- | --- |
| `igris_fix_base.usda` | `config/vla_scene.yaml` → `igris.fix {enabled, link, hold_tolerance}` (**기본 `link: root`**) | 현재 자세의 월드 포즈에 world→링크 FixedJoint 1개. **기본 `root` = `base_link`(몸통)** 을 Isaac Lab `fix_root_link` 방식(루트 API를 부모로 이동)으로 고정. `auto` = 골반(`Link_Waist_Pitch`, 양쪽 Joint_Hip_Pitch의 부모) world 구속 — 5–7차 방식, 몸통 흔들림으로 기본에서 제외 | `--no-fix` 또는 `enabled: false` |
| `igris_head_pose.usda` | `igris.head_pitch_deg` (기본 30) | FixedJoint `Joint_Neck_Pitch`의 관절 프레임+링크 xform 회전 override(URDF 한계 ±30°) | `head_pitch_deg: 0`(레이어 미생성) · 실행 1회만 `--head-pitch` |
| `igris_appearance.usda` | `config/igris_appearance.yaml` | 링크 `visuals` 스코프에 UsdPreviewSurface를 strongerThanDescendants로 바인딩(렌더링 전용) | `--no-appearance` 또는 `enabled: false` |
| `igris_cameras.usda` | `config/igris_cameras.yaml` | 링크 자식 Camera prim(§10) | `--no-cameras` 또는 `enabled: false` |

- 고정은 **지지 상태**(균형 제어 아님). 현재 기본(몸통 고정) 검증(8차): 12초, 위치 0.00 mm·방향 0.00°. 과거 골반 고정 때 보고한 '방향 ≤0.50°'는 앵커 쿼터니언 반올림이 만든 가짜 오차였다(8차에서 수정). 허용치 `hold_tolerance` 1.0°.
- 외형은 **공식 스킨이 아닌 임시 근사 재질**(공식 사진 육안 참고, 출처는 YAML 머리말). 공식 외형·재질 파일 제공 여부 확인 전까지 수정·확정 보류.
- 구현 메모: 레이어 mute/unmute·RigidPrim 뷰 추가는 PhysX 텐서 뷰를 무효화하므로, 전후 스크린샷 뒤 `world.reset()`으로 재초기화하고 고정 링크 포즈는 USD 변환에서 읽는다. 최종 배치·레이어 작성은 `world.stop()` 상태에서 한다(관절 프레임 불일치 경고 방지).

## 10. RGB 카메라 4개 (config/igris_cameras.yaml → 레이어 igris_cameras.usda, scripts/isaac/igris_cameras.py)

출발점: ROBROS 공식 `robot_cfg.py`/`camera_cfg.py`(igris_c_isaacsim_public b53e424). 실행 중인 USD 변형 = `extras/wrist_hand_independent/igris_c.usd`. **공식 USD에는 Camera prim이 없다**(from_urdf 변형 전부; 공식 Isaac Lab cfg가 실행 시 spawn). 이 프로젝트에서도 실행 시 별도 레이어에 생성하며 기존 `/World/SceneCamera`(관찰용)만 있었다. D435 RGB·깊이는 이번 4개에 포함하지 않음.

| 역할 | prim(부모 링크 자식) | 해상도 | fx, fy, cx, cy | 왜곡(k1 k2 p1 p2 k3) | 위치(링크, m) | 회전 | near/far |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 머리 좌안 | `…/IGRIS_C/Link_Neck_Pitch/LeftRgbCamera` | 640×480 | 433.3, 433.3, 320, 240 | 없음 | (0.095516, 0.026076, 0.121) 공식 그대로 | ROS 규약 (0.5,−0.5,0.5,−0.5)에 링크 z축 +14° | 0.05 / 100 |
| 머리 우안 | `…/Link_Neck_Pitch/RightRgbCamera` | 640×480 | 433.3, 433.3, 320, 240 | 없음 | (0.095516, −0.026076, 0.121) 공식 그대로 | 〃 −14° | 0.05 / 100 |
| 왼손바닥 | `…/Left_Hand/l_hand_camera_link` | 320×200 | 115.6696, 115.5467, 159.6695, 96.9483 (LEFT_WRIST_INTRINSIC) | 0.047115, −0.056155, 0, 0, 0.012162 | 공식 (−0.024420, 0.010317, 0.034793) → **적용 (−0.019605, 0.017160, 0.040269)** (광축 +10 mm) | world 규약 (0.281491, −0.813343, −0.479715, −0.170613) 공식 **+ 카메라 z축 −20°**(11차 `tilt_yaw_deg`) | **0.02** / 4 (공식 0.001) |
| 오른손바닥 | `…/Right_Hand/r_hand_camera_link` | 320×200 | 115.4599, 115.4226, 157.1594, 91.9294 (RIGHT_WRIST_INTRINSIC) | 0.044201, −0.057607, −0.000818, 0.000326, 0.012698 | 공식 (−0.024420, −0.010317, 0.034793) → **적용 (−0.019605, −0.017177, 0.040247)** | world 규약 (0.280192, 0.813790, −0.479987, 0.169854) 공식 그대로 | **0.02** / 4 |

- 손 위치를 옮긴 근거: 공식 STL 시각 메시에는 눈·손바닥 구멍이 없고 공식 광학 중심 4개가 닫힌 셸 내부에 있다(`scripts/isaac/tools/camera_geometry_probe.py`, `data/isaac/camera_probe/`). 머리는 앞 셸까지 17.6–25.9 mm라 공식 near 0.05 m가 셸을 통과시키므로 무수정. 손은 5.7–8.1 mm(공식 near 0.001)라 셸 내부가 보여, 광축 방향 +10 mm(셸 표면 +2 mm)로 옮기고 near 0.02 m로 셸 가장자리(2 cm 이내)를 제거. 남는 자기 메시(2–3 cm, 손바닥 가장자리)는 화면 테두리 7–8%(`self_occlusion_frac`), +20 mm로 두면 1–2%로 줄지만 공식 extrinsic에서 더 멀어짐(YAML `axial_offset_m`).
- 1차 튜닝(11차): 왼손 `tilt_yaw_deg: -20`(카메라 z축, 공식 대비 20°). 오른손·거리 미변경. 스윕 옵션 `--cam-variants/--cam-override/--xy-offset/--pose-file/--head-pitch`는 실행 전용.
- 내부 파라미터 → USD: focalLength 24, horizontalAperture = 24·W/fx, verticalAperture = 24·H/fy; 손은 `Camera.set_opencv_pinhole_properties(cx, cy, fx, fy, [k1..k3])`(OmniLensDistortionOpenCvPinholeAPI, 공식 camera_cfg.py와 같은 스키마)로 주점·왜곡 적용. 회전은 공식 규약(ros/world)을 USD 카메라(−z 전방, +y 상)로 변환(`igris_cameras.conv_to_usd`).
- 출력: 공식 4개 + `cam_head` 1280×480(좌|우 hstack; `lerobot_robot_igris` view=left가 `frame[:, :640]`이므로 좌안이 왼쪽) + 손 학습용 `train_extend` 640×480(`l_hand_camera_link_train`, `r_…_train` prim; fx,fy,cx,cy ×2, cy+40; 수평 FOV 108.3° 동일, 수직 81.7°→92.2°, 상하 40 px는 보정 범위 밖 외삽). `letterbox`(640×400 렌더+상하 검은 띠)와 `none`은 YAML `train_output.mode`.
- 검증 지표(결과 JSON `cameras.verdict`): rendered(std>2), not_black(어두운 화소<50%), updates_between_poses(정지↔동작 평균 절대차>1), self_occlusion_frac(<3 cm 화소)<15%. 랜드마크(손가락 끝·머그·작업대) 화소 투영 `landmark_pixels`로 방향 확인.

## 11. 기본 자세·몸통 고정·고개 (8차, config/vla_scene.yaml `igris`)

- 고정: `fix.link: root` → `base_link`(몸통, articulation root) 고정 베이스(레이어 `igris_fix_base.usda`). `auto`는 골반 구속(흔들림 있음). 둘 중 하나만 생성.
- 팔: `init_joint_pos` 어깨 pitch −0.35 / roll ±0.15(바깥) / yaw 0, 팔꿈치 −1.30, 손목 0 (축·한계: 공식 URDF `igris_c_v2_wrist_hand_isaac.urdf`).
- 고개: `head_pitch_deg: 30` → 레이어 `igris_head_pose.usda`(Joint_Neck_Pitch는 FixedJoint라 관절 목표 불가; 관절 프레임+링크 xform 회전 override). 0이면 레이어 미생성.
- `arm_test.enabled: false` 기본. `--arm-test`로 사인파 동작·모니터 갱신 검증.
- 모니터 손 셀은 표시만 회전(왼손 CW 90°, 오른손 CCW 90°; `igris_monitor.DISPLAY_ROT`). 원본 캡처·카메라 설정은 회전하지 않는다. 고개는 URDF 한계 ±30° 안에서만(45° 요청 시에도 30° 유지).
