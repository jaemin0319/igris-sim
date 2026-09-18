"""MuJoCo(IGRIS-C 공식 모델, 고정 베이스) -> SDK LowState 발행(루프백 DDS) / 구독 로거.
LowCmd·서비스 요청은 일절 발행하지 않는다. 사용: --role logger | sim | cmdlogger"""
import argparse, os, sys, time
from pathlib import Path
import numpy as np
WS = Path.home() / "igris_ws"
uri = os.environ.get("CYCLONEDDS_URI", "")
assert "cyclonedds_loopback.xml" in uri, "CYCLONEDDS_URI가 루프백 설정이 아님 - 중단"
import igris_c_sdk as igc
ap = argparse.ArgumentParser(); ap.add_argument("--role", required=True); ap.add_argument("--domain", type=int, default=77)
ap.add_argument("--ns", default="igris_c_SIMTEST"); ap.add_argument("--secs", type=float, default=3.0); ap.add_argument("--realtime", action="store_true"); ap.add_argument("--tag", default=""); ap.add_argument("--out", default=str(WS / "data/sim_logs"))
a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
ch = igc.ChannelFactory.Instance(); ch.Init(a.domain, a.ns); assert ch.IsInitialized()
N = 31
if a.role == "logger":
    rows = []
    def cb(msg):
        ms = msg.motor_state(); rows.append([time.time()] + [ms[i].q() for i in range(N)] + [ms[i].dq() for i in range(N)])
    sub = igc.LowStateSubscriber("rt/lowstate", igc.QosProfile.SensorData()); assert sub.init(cb)
    t0 = time.time()
    while time.time() - t0 < a.secs + 4.0: time.sleep(0.05)
    sub.stop(); arr = np.asarray(rows); np.savez(out / "lowstate_received.npz", data=arr)
    print(f"[logger] received {len(rows)} LowState msgs -> {out/'lowstate_received.npz'}"); sys.exit(0 if len(rows) else 1)
if a.role == "cmdlogger":  # GMT 노드가 루프백에 발행하는 LowCmd를 기록만 한다(재발행 없음)
    rows = []
    def cb(msg):
        mo = msg.motors(); rows.append([time.time()] + [mo[i].q() for i in range(N)] + [mo[i].kp() for i in range(N)])
    sub = igc.LowCmdSubscriber("rt/lowcmd", igc.QosProfile.SensorData()); assert sub.init(cb)
    t0 = time.time()
    while time.time() - t0 < a.secs: time.sleep(0.05)
    sub.stop(); arr = np.asarray(rows); np.savez(out / f"lowcmd_received{a.tag}.npz", data=arr)
    print(f"[cmdlogger] received {len(rows)} LowCmd msgs; finite={bool(np.isfinite(arr).all()) if len(rows) else None}; |q|max={np.abs(arr[:,1:N+1]).max() if len(rows) else None}")
    sys.exit(0)
os.environ.setdefault("MUJOCO_GL", "egl")
import mujoco, imageio.v2 as iio
sys.path.insert(0, str(WS / "scripts/verify")); from igris_mj_loader import load
m = load(parallel="false", fixed="true"); d = mujoco.MjData(m)
acts = [i for i in range(m.nu) if m.actuator(i).name.endswith("_Pos")][:N]
jids = [m.actuator(i).trnid[0] for i in acts]; qadr = [m.jnt_qposadr[j] for j in jids]; vadr = [m.jnt_dofadr[j] for j in jids]
names = [m.joint(j).name for j in jids]; print(f"[sim] {len(acts)} position actuators; e.g. {names[:4]}")
pub = igc.LowStatePublisher("rt/lowstate", igc.QosProfile.SensorData()); assert pub.init()
time.sleep(1.5)  # discovery
ren = mujoco.Renderer(m, 360, 480); cam = mujoco.MjvCamera(); cam.lookat[:] = [0, 0, 1.15]; cam.distance = 3.2; cam.azimuth = 140; cam.elevation = -15
from OpenGL import GL; print('[sim] GL_RENDERER:', GL.glGetString(GL.GL_RENDERER).decode())
vw = iio.get_writer(out / f"igris_mujoco{a.tag}.mp4", fps=50); sent = []; steps = int(a.secs / m.opt.timestep); pub_every = max(1, round(0.01 / m.opt.timestep)); vid_every = max(1, round(0.02 / m.opt.timestep))
arm = [k for k, n in enumerate(names) if "shoulder_pitch" in n or "elbow" in n]
t_wall = time.time()
for s in range(steps):
    for k in arm: d.ctrl[acts[k]] = 0.4 * np.sin(2 * np.pi * 0.5 * d.time)
    mujoco.mj_step(m, d)
    if s % pub_every == 0:
        msg = igc.LowState(); ms = msg.motor_state()
        for i in range(N): ms[i].q(float(d.qpos[qadr[i]])); ms[i].dq(float(d.qvel[vadr[i]]))
        msg.motor_state(ms); imu = msg.imu_state(); imu.quaternion([1.0, 0.0, 0.0, 0.0]); msg.imu_state(imu)
        h = msg.header(); h.seq(len(sent) + 1); msg.header(h); pub.write(msg); sent.append([d.time] + [d.qpos[q] for q in qadr] + [d.qvel[v] for v in vadr])
        time.sleep(max(0.002, (t_wall + d.time) - time.time()) if a.realtime else 0.002)
    if s % vid_every == 0: ren.update_scene(d, cam); vw.append_data(ren.render())
vw.close(); ren.close(); np.savez(out / f"lowstate_sent{a.tag}.npz", data=np.asarray(sent), joint_names=np.array(names))
print(f"[sim] {steps} steps ({a.secs}s sim) in {time.time()-t_wall:.1f}s wall; sent {len(sent)} LowState; video+npz -> {out}")
