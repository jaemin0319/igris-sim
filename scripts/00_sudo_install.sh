#!/usr/bin/env bash
# IGRIS/PICO 연구 환경 - 시스템(apt) 설치. 실행: sudo bash ~/igris_ws/scripts/00_sudo_install.sh
# - apt upgrade / 드라이버 변경 / 재부팅 없음. nvidia·nomachine·tailscale·커널 패키지가 바뀌면 중단.
# - Gazebo, CUDA Toolkit, 학습 패키지 미포함.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "sudo로 실행하세요"; exit 1; }
RUSER="${SUDO_USER:-jammin}"
WS="/home/${RUSER}/igris_ws"
LOG="${WS}/logs/00_sudo_install.log"
mkdir -p "${WS}/logs"; exec > >(tee "${LOG}") 2>&1
export DEBIAN_FRONTEND=noninteractive
echo "== $(date -Is) start; free: $(df -h / | awk 'NR==2{print $4}')"

BASE_PKGS="git git-lfs curl ca-certificates gnupg lsb-release build-essential cmake ninja-build pkg-config \
python3-pip python3-venv python3-dev libssl-dev libglfw3-dev libgl1-mesa-dev libegl1 libeigen3-dev libyaml-cpp-dev \
ffmpeg vulkan-tools xdg-utils"
ROS_PKGS="ros-jazzy-ros-base ros-jazzy-rviz2 ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher-gui \
ros-jazzy-xacro ros-jazzy-tf2-ros ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py ros-dev-tools"
GUARD='^(Remv|Inst) (nvidia|libnvidia|xserver-xorg-video-nvidia|nomachine|tailscale|linux-image|linux-modules|linux-headers)'

guard() { # $@ = packages
  local sim; sim="$(apt-get -s install --no-install-recommends "$@")"
  if echo "${sim}" | grep -E "${GUARD}"; then echo "ABORT: 보호 대상 패키지 변경이 감지됨(위 목록). 설치하지 않음."; exit 2; fi
  echo "${sim}" | grep -E "^Remv" && { echo "ABORT: 패키지 제거가 포함됨."; exit 2; } || true
}

echo "== [1/5] base tools"
apt-get update -qq
guard ${BASE_PKGS}
apt-get install -y -qq --no-install-recommends ${BASE_PKGS}

echo "== [2/5] ROS 2 apt source (official ros2-apt-source)"
if ! dpkg -s ros2-apt-source >/dev/null 2>&1; then
  VER="$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F tag_name | awk -F'"' '{print $4}')"
  CODENAME="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME}}")"
  curl -fsSL -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${VER}/ros2-apt-source_${VER}.${CODENAME}_all.deb"
  dpkg -i /tmp/ros2-apt-source.deb
fi
add-apt-repository -y universe >/dev/null 2>&1 || true
apt-get update -qq

echo "== [3/5] ROS 2 Jazzy (ros-base + rviz2 + dev tools)"
guard ${ROS_PKGS}
apt-get install -y -qq --no-install-recommends ${ROS_PKGS}
[ -f /etc/ros/rosdep/sources.list.d/20-default.list ] || rosdep init

echo "== [4/5] XRoboToolkit PC Service (official ubuntu 24.04 deb)"
DEB="${WS}/downloads/XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb"
if [ -f "${DEB}" ]; then guard "${DEB}"; apt-get install -y -qq --no-install-recommends "${DEB}"; else echo "SKIP: ${DEB} 없음"; fi

echo "== [5/5] apt 캐시 정리(다운로드된 .deb 캐시만 삭제)"
apt-get clean
chown -R "${RUSER}:${RUSER}" "${WS}/logs"
echo "== $(date -Is) done; free: $(df -h / | awk 'NR==2{print $4}')"
echo "RESULT: OK"
