#!/usr/bin/env bash
# 사용자 공간 Redis(127.0.0.1 전용, 비영속). 사용: redis_local.sh start|stop|ping
source "$HOME/igris_ws/scripts/env_common.sh"; R="$MAMBA_ROOT_PREFIX/envs/tools/bin"
case "${1:-start}" in
  start) "$R/redis-server" --bind 127.0.0.1 --port 6379 --protected-mode yes --save "" --appendonly no --daemonize yes --dir "$IGRIS_WS/logs" --logfile redis.log --pidfile "$IGRIS_WS/logs/redis.pid";;
  stop)  "$R/redis-cli" -h 127.0.0.1 shutdown nosave;;
  ping)  "$R/redis-cli" -h 127.0.0.1 ping;;
esac
