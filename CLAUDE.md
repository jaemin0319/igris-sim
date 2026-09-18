# igris_ws 작업 규칙

- 먼저 `docs/CURRENT_STATE.md`(진행/막힌 점) → `docs/SETUP.md`(버전·경로·명령)를 읽는다. 변경 후 두 문서를 갱신한다.
- **실물 명령 송신 금지.** DDS/ROS 시험은 `scripts/env_*.sh`의 기본값(루프백 XML, 도메인 77, ns `igris_c_SIMTEST`, LOCALHOST)으로만. `gmr_control_mode_dds_bridge`와 읽기 전용이 아닌 SDK 예제(`logs/23_example_command_audit.log`)는 실행하지 않는다.
- 시스템 Python 교체·`sudo pip` 금지. 환경은 micromamba(`envs/mamba`: tools/sdk/gmr/isaac_env) + ROS는 system Python. sdk 환경의 `mujoco==3.2.7` 고정 유지.
- 드라이버 교체·재부팅·파티션/NTFS 변경·원격(Tailscale, NoMachine) 설정 변경은 사용자 확인 없이는 하지 않는다. sudo는 `scripts/00_sudo_install.sh`처럼 스크립트로 묶어 사용자에게 실행을 요청한다.
- `src/` 공식 저장소는 수정하지 않는다(설정 사본은 `config/`, 산출물은 `data/`, 로그는 `logs/`). 버전은 SETUP.md의 커밋에 고정.
- 디스크가 작다(`/` 48GB): 설치 전 `df -h /` 확인, pip은 `--no-cache-dir`, Isaac은 `scripts/20_install_isaac.sh`의 공간 검사 통과 시에만.
- 결과는 PASS/FAIL/BLOCKED/NOT TESTED + 로그 경로로 기록. 전체 로그를 채팅에 출력하지 않는다. 비밀정보 기록 금지.
