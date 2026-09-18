#!/usr/bin/env bash
# VRAM 8GB(<공식 최소 16GB): 최소 장면 -> IGRIS HugWBC 200스텝 headless 순으로만 시험. 로그: logs/51_*, 52_*
source ~/igris_ws/scripts/env_isaac.sh || exit 1; L="$IGRIS_WS/logs"
python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0))" 2>&1 | tee "$L/51_isaac_torch_cuda.log"
timeout 900 ./third_party/IsaacLab/isaaclab.sh -p third_party/IsaacLab/scripts/tutorials/00_sim/create_empty.py --headless > "$L/52_isaac_min_scene.log" 2>&1; echo "min scene rc=$? (timeout 124 = 정상 기동 후 시간 종료)"
timeout 1500 ./third_party/IsaacLab/isaaclab.sh -p scripts/hugwbc/igris_c_hugwbc.py --motion_file motion/hugwbc_forward_arm_motion.npz --num_envs 1 --headless --max_steps 200 > "$L/53_isaac_igris_hugwbc.log" 2>&1; echo "igris hugwbc rc=$?"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | tee -a "$L/53_isaac_igris_hugwbc.log"
