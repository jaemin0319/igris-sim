#!/usr/bin/env bash
# 기존 G1 시뮬 장면 자산만 확보(전체 G1 복원 아님). vla-repro의 체크섬으로 검증, 원본 Release/복원 트리 무변경.
#   30_fetch_vla_scene.sh download   : Release 파트(22.8GB)+USD 보충본(276MB) 다운로드·SHA-256 검증  → $VLA_ROOT/parts
#   30_fetch_vla_scene.sh list       : 스트리밍 복호화로 tar 목록만 생성(평문 아카이브를 디스크에 쓰지 않음) → $VLA_ROOT/snapshot.filelist
#   30_fetch_vla_scene.sh supplement : (선택) USD 보충본 추출 → $VLA_ROOT/supplement. 끝나면 'forget'으로 암호 캐시 제거
#   30_fetch_vla_scene.sh extract    : 장면 관련 경로만 선택 추출                                       → $VLA_ROOT/extracted
# 암호는 pinentry(GUI 창)로만 입력한다. 인자·환경변수·로그에 남기지 않는다.
set -euo pipefail
source ~/igris_ws/scripts/env_common.sh; export PATH="$MAMBA_ROOT_PREFIX/envs/tools/bin:$PATH"
VLA_ROOT="${VLA_ROOT:-/mnt/isaac/vla-scene}"; PARTS="$VLA_ROOT/parts"; REPRO="$IGRIS_WS/src/vla-repro"; REL_REPO=jaemin0319/vla-recovery-private
SNAP_TAG=snapshot-g1-20260914-E0FK4Q; SUPP_TAG=usd-supplement-20260915; mkdir -p "$PARTS" "$VLA_ROOT/extracted"
GPG_HOME="$VLA_ROOT/.gnupg"
gpg_setup() { mkdir -p -m 700 "$GPG_HOME"; { command -v pinentry-gnome3 >/dev/null && printf 'pinentry-program %s\n' "$(command -v pinentry-gnome3)"; printf 'default-cache-ttl 5400\nmax-cache-ttl 5400\n'; } > "$GPG_HOME/gpg-agent.conf"; }
gpg_forget() { gpgconf --homedir "$GPG_HOME" --kill gpg-agent >/dev/null 2>&1 || true; }   # 에이전트 메모리의 암호 캐시 제거
gpg_stream() { DISPLAY="${DISPLAY:-:0}" gpg --no-options --homedir "$GPG_HOME" --pinentry-mode ask --quiet --decrypt; }   # 암호는 pinentry 창으로만
cat_parts() { while read -r p; do cat "$PARTS/$p"; done < "$REPRO/manifests/$SNAP_TAG.COMBINE_ORDER.txt"; }
# 장면 자산(USD·텍스처) + 장면/태스크/로봇 배치를 정의한 소형 .py 설정 + 실행 근거 문서. 제어기·conda·데이터셋·G1 로봇 USD는 제외.
PATTERNS=( '*/vla_ws/repos/unitree_sim_isaaclab/assets/objects/*' '*/vla_ws/repos/unitree_sim_isaaclab/assets/props/*'
           '*/vla_ws/repos/unitree_sim_isaaclab/tasks/*.py' '*/vla_ws/repos/unitree_sim_isaaclab/robots/*.py'
           '*/vla_ws/repos/unitree_sim_isaaclab/sim_main.py' '*/vla_ws/CLAUDE.md' '*/vla_ws/*.md' '*/metadata/roots.json' )
case "${1:-}" in
  download)
    need=26; free=$(df -BG --output=avail "$VLA_ROOT" | tail -n1 | tr -dc 0-9); [ "$free" -ge "$need" ] || { echo "BLOCKED: 여유 ${free}GB < ${need}GB"; exit 3; }
    gh release download "$SNAP_TAG" -R "$REL_REPO" -D "$PARTS" -p '*.part' --skip-existing
    gh release download "$SUPP_TAG" -R "$REL_REPO" -D "$PARTS" -p '*.gpg' --skip-existing
    ( cd "$PARTS" && LC_ALL=C sha256sum -c "$REPRO/manifests/$SNAP_TAG.SHA256SUMS" | grep -v ': OK$' || echo "snapshot parts: all OK" )
    want=$(python3 -c "import json;print(json.load(open('$REPRO/recovery-plan.json'))['usd_supplement']['cipher_sha256'])")
    [ "$(sha256sum "$PARTS"/g1-usd-supplement-20260915.tar.zst.gpg | cut -d' ' -f1)" = "$want" ] && echo "usd supplement: OK" || { echo "usd supplement: SHA MISMATCH"; exit 4; } ;;
  list)    gpg_setup; cat_parts | gpg_stream | zstd -dc | tar -tvf - > "$VLA_ROOT/snapshot.filelist"
           python3 "$IGRIS_WS/scripts/31_vla_select.py" "$VLA_ROOT" "${PATTERNS[@]}" ;;
  extract) gpg_setup; [ -s "$VLA_ROOT/selection.json" ] || { echo "먼저 list를 실행"; exit 1; }
           need=$(python3 -c "import json;d=json.load(open('$VLA_ROOT/selection.json'));print(int((d['selected_bytes']+d['supplement_bytes'])*1.1/2**30)+5)")
           free=$(df -BG --output=avail "$VLA_ROOT" | tail -n1 | tr -dc 0-9); [ "$free" -ge "$need" ] || { echo "BLOCKED: 추출에 ${need}GB 필요, 여유 ${free}GB"; exit 3; }
           cat_parts | gpg_stream | zstd -dc | tar -xf - -C "$VLA_ROOT/extracted" --wildcards "${PATTERNS[@]}" || echo "WARN: tar rc=$? (일부 패턴 무일치 가능)"
           du -sh "$VLA_ROOT/extracted"; echo "usd files: $(find "$VLA_ROOT/extracted" -name '*.usd*' | wc -l)" ;;
  supplement) # 공식 Isaac Sim 5.0 USD 보충본(별도 암호화). 기준 장면에는 불필요(required_for_current_fixed_base_baseline=false)
           gpg_setup; mkdir -p "$VLA_ROOT/supplement"; gpg_stream < "$PARTS/g1-usd-supplement-20260915.tar.zst.gpg" | zstd -dc | tar -xf - -C "$VLA_ROOT/supplement"; du -sh "$VLA_ROOT/supplement" ;;
  forget)  gpg_forget; echo "gpg-agent 종료(암호 캐시 제거)" ;;
  *) echo "usage: $0 download|list|extract|supplement|forget"; exit 1 ;;
esac
