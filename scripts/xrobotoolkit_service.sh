#!/usr/bin/env bash
# XRoboToolkit PC Service 실행 도우미. 사용: xrobotoolkit_service.sh start|stop|status
# 시스템 설치(/opt/apps/roboticsservice)가 있으면 우선, 없으면 사용자 공간 추출본 사용.
A=/opt/apps/roboticsservice; [ -x "$A/RoboticsServiceProcess" ] || A="$HOME/igris_ws/opt/xrobotoolkit/opt/apps/roboticsservice"
case "${1:-status}" in
  start) ( cd "$A" && exec env LD_LIBRARY_PATH="$A:$A/lib:$A/SDK/x64" QT_PLUGIN_PATH="$A/plugins/" QT_QML_PATH="$A/qml/" DISPLAY="${DISPLAY:-:0}" \
           setsid ./RoboticsServiceProcess > "$HOME/igris_ws/logs/xrobotoolkit_service.out" 2>&1 < /dev/null ) & sleep 3; "$0" status;;
  stop)  killall -q RoboticsServiceProcess; sleep 1; "$0" status;;
  status) P=$(pidof RoboticsServiceProcess) && { echo "RUNNING pid=$P ($A)"; ss -ltnup 2>/dev/null | grep "pid=${P%% *}," | awk '{print $1,$5}' | sort -u; } || echo "STOPPED";;
esac
