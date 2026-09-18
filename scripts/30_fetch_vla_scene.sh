#!/usr/bin/env bash
# 기존 G1 시뮬 장면 자산만 확보(전체 G1 복원 아님). vla-repro의 체크섬으로 검증, 원본 Release/복원 트리 무변경.
#   30_fetch_vla_scene.sh download   : Release 파트(22.8GB)+USD 보충본(276MB) 다운로드·SHA-256 검증  → $VLA_ROOT/parts
#   30_fetch_vla_scene.sh list       : 스트리밍 복호화로 tar 목록만 생성(평문 아카이브를 디스크에 쓰지 않음) → $VLA_ROOT/snapshot.filelist
#   30_fetch_vla_scene.sh extract    : 장면 관련 경로만 선택 추출                                       → $VLA_ROOT/extracted
# 암호는 pinentry(GUI 창)로만 입력한다. 인자·환경변수·로그에 남기지 않는다.
set -euo pipefail
source ~/igris_ws/scripts/env_common.sh; export PATH="$MAMBA_ROOT_PREFIX/envs/tools/bin:$PATH"
VLA_ROOT="${VLA_ROOT:-/mnt/isaac/vla-scene}"; PARTS="$VLA_ROOT/parts"; REPRO="$IGRIS_WS/src/vla-repro"; REL_REPO=jaemin0319/vla-recovery-private
SNAP_TAG=snapshot-g1-20260914-E0FK4Q; SUPP_TAG=usd-supplement-20260915; mkdir -p "$PARTS" "$VLA_ROOT/extracted"
gpg_stream() { # 복호화 스트림을 stdout으로. 전용 GNUPGHOME + pinentry-gnome3(없으면 기본 pinentry)
  local home="$VLA_ROOT/.gnupg"; mkdir -p -m 700 "$home"
  command -v pinentry-gnome3 >/dev/null && printf 'pinentry-program %s\n' "$(command -v pinentry-gnome3)" > "$home/gpg-agent.conf"
  gpgconf --homedir "$home" --kill gpg-agent >/dev/null 2>&1 || true
  DISPLAY="${DISPLAY:-:0}" gpg --no-options --homedir "$home" --pinentry-mode ask --quiet --decrypt
}
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
  list)    cat_parts | gpg_stream | zstd -dc | tar -tf - > "$VLA_ROOT/snapshot.filelist"; echo "entries: $(wc -l < "$VLA_ROOT/snapshot.filelist")" ;;
  extract) cat_parts | gpg_stream | zstd -dc | tar -xf - -C "$VLA_ROOT/extracted" --wildcards --no-anchored "${PATTERNS[@]}" || true
           gpg_stream < "$PARTS/g1-usd-supplement-20260915.tar.zst.gpg" | zstd -dc | tar -xf - -C "$VLA_ROOT/extracted"
           du -sh "$VLA_ROOT/extracted"; find "$VLA_ROOT/extracted" -name "*.usd*" | wc -l ;;
  *) echo "usage: $0 download|list|extract"; exit 1 ;;
esac
