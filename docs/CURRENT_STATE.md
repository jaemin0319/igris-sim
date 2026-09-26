# CURRENT STATE — 2026-09-26 (7차 갱신: GUI 하단 카메라 모니터)

판정: PASS / FAIL / BLOCKED / NOT TESTED. 로그: `~/igris_ws/logs/`, 결과: `~/igris_ws/data/isaac/`(Git 제외), 요약본: `docs/results/`, 미리보기: `docs/img/`.

## 7차 — Isaac Sim 한 창 안 하단 실시간 모니터 [HEAD STEREO (L|R)] [LEFT HAND] [RIGHT HAND]

실행(기본 표시): `bash ~/igris_ws/scripts/run_igris_vla_scene.sh --secs 12 --hold 3600` · 끄기: `--no-monitor` (헤드리스에서는 자동 비활성)

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| 구현: `scripts/isaac/igris_monitor.py` — 기존 카메라 센서 4개의 RGBA를 `omni.ui.DynamicTextureProvider`로 그리는 `ui.Window` 3개를 메인 뷰포트 아래에 도킹(머리 BOTTOM 30% → 왼손 RIGHT → 오른손 RIGHT). G1 `sim_main.py`의 '3-camera bottom monitor' 도킹 방식을 따르되, 머리 좌\|우 결합 때문에 뷰포트 창 대신 이미지 창 사용. 카메라·뷰포트 추가 생성 없음, 포즈·화각 불변 | PASS | docs/results/igris_monitor.json `docked` |
| 셀 이름·종횡비: 라벨 "HEAD STEREO (L \| R) 1280x480", "LEFT HAND 320x200", "RIGHT HAND 320x200"; `IWP_PRESERVE_ASPECT_FIT` | PASS | docs/img/igris_monitor_window.jpg |
| 전체 창 스크린샷(스왑체인 캡처) | PASS | data/isaac/monitor/monitor_window.png |
| 일시정지 유지: 30프레임 평균 절대차 head 0.75 / left 1.7 / right 1.6 (RTX 누적 노이즈 수준, 임계 4.0) | PASS | 〃 `paused_hold_diff_30f` |
| 재생 시 갱신: 팔·손목 사인파 1.5초 재생 후 차이 head 45.7 / left 58.4 / right 63.5 (임계 8.0) | PASS | 〃 `play_diff_vs_paused` |
| 다시 일시정지: 수렴 후 30프레임 차이 0.4 / 1.8 / 2.1 → 마지막 프레임 유지 | PASS | 〃 `pause_again_diff_30f` |
| 검은 화면 없음(dark_frac 0.00 / 0.07 / 0.08), 좌\|우 순서: 좌안 영상이 왼쪽 절반(좌안이 좌측 벽을 더 봄) | PASS | data/isaac/monitor/monitor_cell_head_after_play.png |
| 성능: 모니터 포함 VRAM 최대 3.9 GB; 셀 갱신은 CPU 복사(1280×480×4 매 프레임) | 관찰 | 〃 |

메모: `ByteImageProvider.set_bytes_data_from_gpu`(torch 포인터)와 `set_raw_bytes_data`(capsule) 경로는 이 환경에서 화면에 그려지지 않아 `DynamicTextureProvider.set_data_array`로 확정(`data/isaac/monitor/ui_provider_test*.png`). 창 생성 전에 자리표시 텍스처를 넣어야 셀이 표시된다.

### 미검증
- 사용자가 GUI에서 Play/Pause 버튼을 눌렀을 때의 동작(스크립트 내 `world.play()/pause()`로만 검증). 창 크기 변경 시 레이아웃 유지.

---

(이하 6차 갱신 기록)

## 6차 — 머리 좌/우 눈 + 좌/우 손바닥 RGB 카메라 (GUI 실행·실제 렌더 검증 완료)

실행: `bash ~/igris_ws/scripts/run_igris_vla_scene.sh --secs 12 --hold 3600` (카메라 기본 on; `--no-cameras`, `--viewport-camera hand_left` 등)

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| 현황: 실행 USD = `extras/wrist_hand_independent/igris_c.usd`; 머리 `Link_Neck_Pitch`, 손 `Left_Hand`/`Right_Hand` 링크 확인. **공식 USD에 Camera prim 없음**, 프로젝트에는 관찰용 `/World/SceneCamera`뿐(중복 생성 없음). 이 저장소에 AGENTS.md는 없고 규칙 파일은 CLAUDE.md | PASS(조사) | logs/80, data/isaac/inspect_igris_usd.json |
| 메시 기하: 공식 STL에 눈 구멍·손바닥 구멍 없음. 공식 광학 중심 4개 모두 닫힌 셸 내부(머리 앞 셸 17.6–25.9 mm, 손 5.7–8.1 mm) | PASS(조사) | docs/results/igris_cameras.json `probe`, data/isaac/camera_probe/*_depthmap.png |
| 장착: 별도 레이어 `igris_cameras.usda`, 링크 자식 Camera prim 4개(+학습용 손 2개) → 링크를 따라 움직임(동작 프레임에서 손 카메라 영상 변화 평균 58–87/255) | PASS | docs/results/igris_cameras.json `verdict.updates_between_poses` |
| 머리 광학: 640×480, fx=fy=433.3, cx=320, cy=240, ±14° 설치, 공식 위치 그대로, near 0.05 | PASS | 〃 `specs` |
| 손 광학: 320×200, LEFT/RIGHT_WRIST_INTRINSIC·왜곡·회전 공식 그대로. **위치만 광축 +10 mm**(수정 전/후 값 SETUP §10), near 0.001→0.02 | PASS(수정 기록) | 〃 |
| 렌더 검증(GUI, 정지·동작·종료 3회 캡처): 4개 모두 렌더됨·검지 않음·자세 간 갱신. 머리 자기 메시 0%, 손 7–8%(화면 테두리 손바닥 셸 2–3 cm; 빨강 표시 depth PNG) | PASS | data/isaac/cameras/cams_*.png, docs/img/igris_cameras_*.jpg |
| 방향: 머리 영상 정립(바닥 아래·벽 위), 좌안이 좌측을 더 봄(±14°). 손: 정지 자세(팔 내림)에서 자기 허벅지·엄지가 좌측 테두리, 검지는 하단 밖 → **손가락은 영상 하단 방향**(공식 회전 그대로). 동작 자세에서 바닥·작업대 다리·머그 방향이 시야에 들어옴 | PASS(관찰) | 〃 `landmark_pixels` |
| **작업 대상 시야**: 로봇이 작업대 바로 앞(머그가 얼굴 전방 0.17 m·아래 0.58 m)이라 목 중립 자세의 머리 카메라 시야(수직 58°)에 작업대·머그가 **들어오지 않음**(약 70° 아래). 목 pitch를 숙여야 함(이번 범위 밖) | 관찰 | 〃 |
| 데이터셋 연결: `cam_head` 1280×480 = 좌\|우 결합 출력 제공. 손은 공식 320×200 + 학습용 640×480 `train_extend`(같은 렌즈 모델 ×2, 세로 80 px 외삽; H-FOV 108.3° 동일, V-FOV 81.7→92.2°) | PASS(구현) | 〃 `specs[output=train_extend]` |
| 성능: 4+2 카메라 렌더 시 RTF 0.21, VRAM 최대 3.8 GB | 관찰 | 〃 |

### 데이터셋(igris_c_trainer sample_dataset)과 남는 차이
- 실기 카메라의 내부 파라미터·왜곡이 데이터셋에 없음(cam_head 1280×480, cam_left/right 640×480, 20 fps만 확인). 시뮬 머리는 공식 fx 433.3(왜곡 없음), 손은 공식 320×200 보정값 기반 → 640×480 `train_extend`는 **실기 640×480 카메라와 동일하다고 볼 수 없음**(종횡비 1.6→1.333을 세로 외삽으로 맞춘 근사).
- 시뮬 프레임률은 물리 50 Hz 스텝마다 렌더(캡처는 정지/동작/종료 3회). 20 fps 스트림·동영상 인코딩(mp4)은 미구현.
- D435 RGB/깊이(공식 head_camera/head_depth_camera)는 미장착.

### 미검증
- 실기 카메라와의 화각·색·노출 비교, 왜곡 계수의 렌더 반영 정밀도(Isaac OpenCV pinhole 모델 적용 여부는 prim 속성으로만 확인).
- `--viewport-camera` 로 GUI 뷰포트를 카메라로 전환하는 기능(코드만, 실행 확인 안 함).
- 목 pitch 조정 후 작업대가 머리 시야에 들어오는지.

---

(이하 5차 갱신 기록)

## 5차 — 골반 고정·외형 레이어 (사용자 화면 확인 후 확정)

실행: `bash ~/igris_ws/scripts/run_igris_vla_scene.sh --secs 12 --hold 3600` · 끄기: `--no-fix`, `--no-appearance` · 고정 링크 변경: `--fix-link root|<링크명>`

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| 루트/골반 식별: articulation root `base_link`는 **상체(torso)**(자식: 목·양어깨·허리 요우). 실제 골반 = 양쪽 `Joint_Hip_Pitch`의 부모 **`Link_Waist_Pitch`** | PASS | docs/results/igris_vla_scene_fix_appearance.json `root_body` |
| 골반 고정: 별도 레이어 `igris_fix_pelvis.usda`에 world→`Link_Waist_Pitch` FixedJoint(`excludeFromArticulation`). 로봇 kinematic화·관절 잠금 없음, 51 DOF articulation 유지 | PASS | 〃 `pelvis_fix` |
| 12초 유지: 위치 오차 0.00mm, **방향 오차 최대 0.50°**(팔 동작 중; 사용자 허용, 허용치 `hold_tolerance` 1.0°로 설정). 해당 실행 JSON의 `held=false`는 변경 전 임계 0.5° 기준 | PASS(허용) | 〃 `hold_check` |
| 팔 관절 움직임: 어깨 pitch·팔꿈치 pitch 좌우 4관절, 목표 ±0.4rad@0.3Hz → 관측 범위 0.39–0.46rad | PASS | 〃 `arm_test` |
| **균형 제어** | **해당 없음 — 월드에 골반을 고정한 지지 상태다. 균형 제어 성공이 아니다.** `--no-fix`에서는 1–2초 내 넘어진다(4차 결과) | — |
| 흰색 원인: 공식 USD가 STL 메시+흰색 OmniPBR 기본재질(diffuse 1,1,1, 텍스처 없음)만 포함. 공식 URDF/MJCF·GMR 자산도 공통 placeholder(`random` rgba 0.0706, α0.7)뿐 → 경로/바인딩 문제 아님, **완성된 공식 재질 없음** | PASS(조사) | logs/80, data/isaac/inspect_igris_usd.json |
| 외형: 별도 레이어 `igris_appearance.usda`, 56링크를 5개 재질군으로 바인딩(렌더링 전용; 충돌·질량·관성·관절·마찰 무변경). 같은 시점·조명 전후 스크린샷 | PASS(적용) | docs/img/igris_{before,after}_appearance_diag.jpg |
| **외형의 지위** | **공식 스킨 아님 — ROBROS 공식 제품 사진(robros.co.kr/en/igrisc)을 육안 참고한 임시 근사 재질.** 로고·통풍구·LED·바이저·배선 등 메시에 없는 형상은 미구현 | config/igris_appearance.yaml |
| 자산 누락 0, 링크 단위 초기 겹침 0, 발바닥−바닥 +9.8mm, VRAM 최대 3.1GB | PASS | docs/results/… |

### 보류
- **외형 작업의 추가 수정·최종 확정은 보류**: ROBROS의 공식 외형·재질 파일(텍스처/컬러 메시/USD 재질) 제공 여부를 확인한 뒤 진행. 그 전까지 `config/igris_appearance.yaml`은 임시값.
- 방향 오차 축소(솔버 반복 수 상향, 또는 `--fix-link root`로 상체 루트를 고정 베이스로) 비교는 미실시 — 현재 허용.

### 자산 보관
- 참고 사진 사본: `/mnt/isaac/reference/robros_igrisc/`(SOURCE.txt, DOWNLOADED_AT.txt). ROBROS 저작물이므로 Git에 넣지 않고 URL만 기록.
- 생성 레이어: `/mnt/isaac/scenes/{igris_in_vla_scene,igris_fix_pelvis,igris_appearance}.usda` — 실행 때마다 YAML에서 재생성되므로 보관 불필요(원본은 `config/*.yaml`).

---

(이하 4차 갱신 기록)

## 이번 목표 결과 — 기존 G1 시뮬 환경에 공식 IGRIS-C 1대

실행 명령(하나): `bash ~/igris_ws/scripts/run_igris_vla_scene.sh --secs 5 --hold 3600`

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| Isaac Sim 5.1.0 설치(`/mnt/isaac/env`, 17GB, 루트 영향 없음) | PASS | logs/50_isaac_install.log |
| 설치 확인용 빈 장면: IGRIS 로딩(51 DOF)·5초 물리·GUI 창 | PASS (최종 산출물 아님) | logs/70·71, data/isaac/igris_min_scene_*.json |
| 스냅샷 22파트+보충본 다운로드, SHA-256 | PASS (23/23) | logs/63_vla_scene_download.log |
| 스트리밍 복호화·목록(431,334 항목 = 매니페스트 일치, 평문 62.4GiB 미저장) | PASS | logs/64, /mnt/isaac/vla-scene/selection.json |
| 선택 추출(720항목 1.16GiB: 장면 자산+배치 설정) · 암호 캐시 제거 | PASS | logs/66_vla_scene_extract.log |
| USD 보충본 복호화 | FAIL(`Bad session key`) → **불필요로 판정**: 최종 장면은 Room/warehouse 비활성, 매니페스트도 `required_for_current_fixed_base_baseline=false` | logs/64 |
| 최종 사용 장면 식별: `Isaac-PickPlace-Cylinder-G129-Dex1-Joint`의 사용자 수정 cfg(작업대 1·머그·바닥·배경판 4·돔 조명; Room·추가 작업대·world_camera 비활성) | PASS(파일 확인) | config/vla_scene.yaml `provenance` |
| 장면 구성: 환경 USD reference + 재질/kinematic override, G1 자리 비활성 prim, IGRIS reference | PASS | /mnt/isaac/scenes/igris_in_vla_scene.usda |
| 자산 누락: 의존성 9 레이어/29 자산, **unresolved 0, 누락 reference 0** | PASS | data/isaac/igris_vla_scene_gui2.json |
| 로봇 위치·방향: G1 자리 (−0.15, 0), yaw 90°(작업대 방향) | PASS | 〃 `placement` |
| 발 높이: 바닥 raycast z=0.0 → base z=0.971, **발바닥−바닥 = +7.5mm**(박힘 없음) | PASS | 〃 `initial_check` |
| 초기 겹침: 로봇 전체 AABB는 작업대 AABB와 y 2.7cm 겹치나, **링크(56)×작업대 메시(24) 단위 겹침 0건**, 머그와 겹침 없음, 첫 스텝 관절속도 0(밀어내기 반발 없음) | PASS | 〃 `initial_check_link_level` |
| GUI 표시·스크린샷(정면/대각/측면/물리 후) | PASS | data/isaac/igris_vla_scene_gui2_*.png, logs/73 |
| 기본 물리 5초: 전 구간 유한값, 기립 중 바닥 관통 없음, 베이스 침강 지속 없음, 작업대(kinematic) 불변, 머그는 작업대 위에 안착(2.4cm 내려앉음), RTF 1.84 | PASS | 〃 `physics` |
| **균형 유지** | **유지 안 됨(성공 기준 아님)**: 제어기 없이 초기자세 PD만 → 약 1–2초에 넘어져 바닥에 정지 | 〃 `balance_observation` |
| VRAM 최대 2.9–3.4GB / 8GB | 관찰값(공식 최소 16GB는 미충족) | 〃 `vram_mib` |

관찰 메모: 넘어진 뒤 `Link_Waist_Pitch`의 시각 메시 AABB가 바닥 아래 3cm까지 내려간 채 정지(충돌 형상이 단순화된 영향으로 보임, 침강 아님). IGRIS USD는 재질 색이 없어 흰색으로 표시됨(공식 자산 그대로).

### 미검증 / 범위 밖
- 균형 제어·보행·teleop·PICO 연결·DDS 연동, G1 탑재 카메라/손/브래킷 이식, Isaac Lab 기반 실행(설치 안 함).
- Isaac Lab이 같은 cfg로 만든 원래 화면과의 픽셀 단위 동일성(이 PC에서 원본 G1 장면을 실행한 적 없음). 구성값은 cfg에서 옮겼으나 Lab의 GroundPlane 물리 재질 등 세부 기본값은 대조하지 않음.
- 새 PC에서 README 절차 전체의 일괄 재현(각 단계는 이 PC에서 개별 실행·확인).

### 남은 결정
- `/mnt/isaac/vla-scene/parts`(23.1GB)는 재다운로드 가능 — 삭제 여부는 사용자 결정(현재 보존).
- `extracted`(1.2GB) 중 실제 사용은 PackingTable·025_mug·설정 3개(체크섬 기록). 나머지 추출분(small_warehouse 등)도 보존 중.

---

## 3차 갱신(2026-09-18) — 목표 재정의: 기존 시뮬 환경 + IGRIS-C

**목표**: 기존 G1 시뮬레이션의 *환경만* 가져와 G1 자리에 공식 IGRIS-C 1대를 reference로 배치하고, 화면 표시·자산 누락·충돌/기본 물리 실행을 확인. 제어기 없는 균형 유지는 성공 기준이 아님. 빈 장면은 설치 확인용일 뿐 최종 산출물이 아님.
범위 밖: G1 Python 환경·IK·BrainCo·Unitree DDS·Vision Pro 복원, 로봇 탑재 카메라, teleop, 학습, DDS 신규 구현.

### 과거 작업 이력 (사용자 제공 — 이 PC에서 **미검증**)
- Unitree G1 29DoF + BrainCo Revo2 손을 Isaac Sim에서 사용. Vision Pro → xr_teleoperate → 좌표 변환 → G1 팔 IK·손가락 retargeting → Unitree DDS → 시뮬레이터.
- 양팔·양손 teleop, 키보드 locomotion 동작(현재 백업에서의 재현 여부는 재확인 필요).
- 머리·양 손목 카메라, 브래킷, 로봇 외형, 주변 물체 표시·색상 수정.
- 교훈: 로봇 USD를 fixed-base로 Bake/Flatten하다 물리 구조가 손상돼 침강 → 정상 Wholebody USD 물리를 유지하고 외형만 별도 레이어로 해결. **이번에도 로봇 물리를 훼손하는 일괄 변환 금지**(IGRIS는 공식 USD를 reference로만 사용).
- 향후 입력 장치: PICO 4 Ultra + 트래커(모델·개수·부착 위치 미확정 — 가정 금지). PICO/XRoboToolkit → GMR/GMT → IGRIS 제어·기록은 추후.

### 확인한 사실 (이 PC에서 직접 확인)
- GitHub 로그인 계정 `jaemin0319`(API 확인, gh 2.101.0 keyring). 새 비공개 저장소 https://github.com/jaemin0319/igris-sim 생성·첫 push(`ccac999`).
- `jaemin0319/vla-repro`@`ca375db`(비공개, 복구 지침·체크섬 전용, 76KB)를 `src/vla-repro`에 클론. AGENTS.md 규칙: G1 복원 트리 무변경, 암호는 로컬 pinentry로만, IGRIS는 별도 작업 루트.
- 기존 장면의 실체: `unitree_sim_isaaclab` 태스크 `Isaac-PickPlace-Cylinder-G129-Dex1-Joint`(recovery-plan.json `runtime.baseline_task`). 단일 USD 스테이지가 아니라 **Python 장면 설정이 방(warehouse)·PackingTable·소품 USD를 조합**하는 구조(상류 공개 코드 `tasks/common_scene/base_scene_pickplace_cylindercfg.py`로 구조 확인; 사용자 수정본은 스냅샷 안).
- 자산 위치: 비공개 Release `vla-recovery-private`의 `snapshot-g1-20260914-E0FK4Q`(GPG 대칭 AES256, 22파트 22.78GB 단일 tar.zst) 안 `vla_ws/repos/unitree_sim_isaaclab/assets/objects/…`, 그리고 공식 Isaac Sim 5.0 USD 보충본 `usd-supplement-20260915`(276MB). 전체 G1 복원은 150GB 요구 → 수행하지 않음.
- 확보 방식: `scripts/30_fetch_vla_scene.sh`(download → SHA-256 검증 → 스트리밍 복호화로 장면 경로만 선택 추출, 평문 아카이브 미저장, 작업 루트 `/mnt/isaac/vla-scene`).

---
(이하 2차 갱신 기록)

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
| Isaac Sim 설치·최소 장면·IGRIS 로딩 | (2차 시점 BLOCKED → 4차에서 PASS, 상단 표 참조) | |
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
