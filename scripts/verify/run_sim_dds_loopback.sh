#!/usr/bin/env bash
# 루프백 DDS(도메인 77, ns igris_c_SIMTEST)에서 MuJoCo LowState 발행 + 구독 로깅. 명령(LowCmd) 송신 없음.
source ~/igris_ws/scripts/env_sdk.sh
cd ~/igris_ws && python scripts/verify/sim_dds_loopback.py --role logger & LP=$!
sleep 1; python scripts/verify/sim_dds_loopback.py --role sim; wait $LP
