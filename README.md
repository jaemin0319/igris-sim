# igris-sim

ROBROS IGRIS-C 시뮬레이션·텔레옵 연구 환경의 **재현용 골격**(스크립트·설정·문서). 외부 소스, 설치본, 캐시, 대용량 자산은 Git에 넣지 않고 `repos.lock`(커밋 고정)과 `assets.sha256`(체크섬)으로 복원·검증한다.

- 현재 상태·검증 여부: [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) — **실제 검증한 단계와 미검증 단계를 구분**해 기록한다.
- 버전·경로·상세 명령: [docs/SETUP.md](docs/SETUP.md)
- 작업 규칙(안전): [CLAUDE.md](CLAUDE.md) — 실물 명령 송신 금지, DDS/ROS는 루프백 기본값.

## 대상 환경(검증된 조합)

Ubuntu 24.04 x86_64 · NVIDIA 580 드라이버 · ROS 2 Jazzy · Isaac Sim 5.1.0(pip, Python 3.11) · micromamba 환경(`sdk` py3.12 / `gmr` py3.10 / `tools`).
이 저장소는 `~/igris_ws`에 클론하는 것을 전제로 한다(스크립트가 이 경로를 사용).

## 새 PC에서 복원

```bash
git clone https://github.com/<account>/igris-sim.git ~/igris_ws && cd ~/igris_ws
# 0) micromamba(사용자 공간) — docs/SETUP.md §3 참조. tools 환경(git, cmake, gh, redis) 생성
# 1) 외부 저장소를 고정 커밋으로 복원
bash scripts/01_clone_sources.sh
# 2) 시스템 패키지(1회, sudo): ROS 2 Jazzy + 빌드 도구 + XRoboToolkit deb. 드라이버/원격 패키지가 바뀌면 자동 중단
sudo bash scripts/00_sudo_install.sh
# 3) Python 환경(sdk/gmr) — docs/SETUP.md §3, docs/pip_freeze_*.txt
# 4) 자산 체크섬 검증
bash scripts/02_assets_manifest.sh verify
# 5) Isaac Sim 5.1.0 (별도 ext4 권장, 여유 ≥22GB). 공간 검사를 통과해야만 다운로드
ISAAC_ROOT=/mnt/isaac bash scripts/20_install_isaac.sh
# 6) IGRIS-C 1대 로딩 + 물리 (GUI) / headless
bash scripts/run_isaac_igris.sh --secs 5 --hold 60
bash scripts/run_isaac_igris.sh --headless --secs 5
```

## 구성

| 경로 | 내용 | Git |
| --- | --- | --- |
| `scripts/` | 설치·빌드·검증·실행 스크립트, `scripts/isaac/igris_min_scene.py` | 포함 |
| `config/` | 루프백 CycloneDDS XML, GMT 시험용 설정 사본 | 포함 |
| `docs/` | SETUP, CURRENT_STATE, pip freeze | 포함 |
| `repos.lock`, `assets.sha256` | 외부 저장소 커밋, 자산 SHA-256 | 포함 |
| `src/`, `envs/`, `opt/`, `downloads/`, `data/`, `logs/`, `ros2_ws/`, `build/` | 외부 소스·설치본·산출물 | **제외** |
| `/mnt/isaac` | Isaac Sim 설치본·pip 임시·Kit 캐시·장면 파일 | 저장소 밖 |

## 자산 출처·라이선스

- IGRIS-C USD/URDF/정책: `robrosinc/*_public` 저장소(각 저장소 LICENSE 준수, 재배포하지 않고 커밋으로 참조).
- LAFAN1 샘플 BVH: ubisoft-laforge-animation-dataset, CC BY-NC-ND 4.0(비상업 연구용, 재배포 안 함).
- XRoboToolkit PC Service: XR-Robotics 릴리스 v1.0.0 deb.
- 기존 시뮬 장면(`vla-repro`): 비공개 자산 — 접근 권한 확인 후 별도 보관, 복원 절차는 CURRENT_STATE 참조.
