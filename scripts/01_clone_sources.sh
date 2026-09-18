#!/usr/bin/env bash
# repos.lock에 고정된 커밋으로 외부 저장소를 src/ 아래에 복원한다(이미 있으면 커밋만 검증).
set -euo pipefail; WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; mkdir -p "$WS/src"
grep -vE '^\s*(#|$)' "$WS/repos.lock" | while read -r dir url commit; do
  dst="$WS/src/$dir"
  if [ -d "$dst/.git" ] || [ -f "$dst/.git" ]; then have=$(git -C "$dst" rev-parse HEAD); [ "$have" = "$commit" ] && echo "OK   $dir $commit" || echo "DIFF $dir have=$have want=$commit"; continue; fi
  case "$dir" in */third_party/*) git -C "$WS/src/${dir%%/*}" submodule update --init --filter=blob:none --depth 1 "${dir#*/}";; *) GIT_LFS_SKIP_SMUDGE=1 git clone -q --filter=blob:none "$url" "$dst" && git -C "$dst" checkout -q "$commit";; esac
  echo "NEW  $dir $(git -C "$dst" rev-parse HEAD)"
done
