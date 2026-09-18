#!/usr/bin/env bash
# 자산 체크섬 기록/검증. 사용: 02_assets_manifest.sh write|verify   (대상 목록: 아래 LIST, 결과: assets.sha256)
set -euo pipefail; WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$WS"
U=src/igris_c_isaacsim_public/source/robros_lab/robros_lab/assets/robots/robros/igris_c/from_urdf/usd
LIST=$( { find "$U" -type f -name "*.usd"; ls src/igris_c_gmt_public/models/wbc_teleop/*.onnx src/igris_c_isaacsim_public/logs/rsl_rl/*/*.pt 2>/dev/null; \
          ls downloads/*.deb data/lafan1/walk1_subject1.bvh 2>/dev/null; if [ -f assets.extra.list ]; then grep -vE "^\s*(#|$)" assets.extra.list; fi; } 2>/dev/null | sort )
case "${1:-verify}" in
  write)  sha256sum $LIST > assets.sha256; echo "wrote $(wc -l < assets.sha256) entries";;
  verify) LC_ALL=C sha256sum -c assets.sha256 | grep -v ': OK$' || echo "all $(wc -l < assets.sha256) assets OK";;
esac
