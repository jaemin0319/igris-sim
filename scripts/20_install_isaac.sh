#!/usr/bin/env bash
# [보류] Isaac Sim 5.1.0 설치. sudo 불필요. 공간 검사를 통과해야만 다운로드를 시작한다.
#   MODE=sim (기본): Isaac Sim만. 목표 = 최소 장면 + IGRIS USD 1대 + 화면 표시 + 기본 물리. Isaac Lab/torch 미설치.
#   MODE=lab       : + torch 2.7.0+cu128 + Isaac Lab 2.3.2(f4aa17f) + robros_lab (공식 정책 예제용)
# 다른 ext4 위치 사용: ISAAC_ROOT=/mnt/isaac bash 20_install_isaac.sh  → env·pip 임시파일·Kit 캐시를 모두 그 아래에 둔다(NTFS 직접 설치 비권장).
set -euo pipefail
source ~/igris_ws/scripts/env_common.sh
MODE="${MODE:-sim}"; ISAAC_ROOT="${ISAAC_ROOT:-$(mountpoint -q /mnt/isaac && echo /mnt/isaac || echo "$IGRIS_WS/envs/isaac")}"; PREFIX="$ISAAC_ROOT/env"
NEED_GB="${NEED_GB:-$([ "$MODE" = lab ] && echo 32 || echo 22)}"   # 산정 근거: docs/SETUP.md §5
mkdir -p "$ISAAC_ROOT"; FREE=$(df -BG --output=avail "$ISAAC_ROOT" | tail -n1 | tr -dc 0-9)
[ "$FREE" -ge "$NEED_GB" ] || { echo "BLOCKED: $ISAAC_ROOT 여유 ${FREE}GB < 필요 ${NEED_GB}GB (MODE=$MODE). 다운로드하지 않음."; exit 3; }
LOG="$IGRIS_WS/logs/50_isaac_install.log"; REPO="$IGRIS_WS/src/igris_c_isaacsim_public"
export PATH="$MAMBA_ROOT_PREFIX/envs/tools/bin:$PATH" OMNI_KIT_ACCEPT_EULA=YES PIP_NO_CACHE_DIR=1 TMPDIR="$ISAAC_ROOT/tmp" CONDA_PKGS_DIRS="$ISAAC_ROOT/pkgs" XDG_CACHE_HOME="$ISAAC_ROOT/cache"; mkdir -p "$TMPDIR" "$CONDA_PKGS_DIRS" "$XDG_CACHE_HOME"
{
  [ -x "$PREFIX/bin/python" ] || "$HOME/.local/bin/micromamba" create -y -q -p "$PREFIX" -c conda-forge python=3.11 pip
  export PATH="$PREFIX/bin:$PATH" CONDA_PREFIX="$PREFIX"
  pip install "isaacsim[all,extscache]==5.1.0" --extra-index-url https://pypi.nvidia.com
  if [ "$MODE" = lab ]; then
    pip install -U torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128
    ( cd "$REPO/third_party/IsaacLab" && ./isaaclab.sh --install none )
    pip install -e "$REPO/source/robros_lab"
  fi
} 2>&1 | tee "$LOG"
rm -rf "$TMPDIR"; echo "$ISAAC_ROOT" > "$IGRIS_WS/envs/isaac_root.txt"; echo "DONE (MODE=$MODE). 다음: source ~/igris_ws/scripts/env_isaac.sh"
