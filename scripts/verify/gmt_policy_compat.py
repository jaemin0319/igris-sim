"""student_126.onnx <-> GMT(C++) 호환성 점검. (A) 정적 계약 대조, (B) C++ 노드 CSV 로그를 독립 재구성과 비교.
실행: source scripts/env_sdk.sh && python scripts/verify/gmt_policy_compat.py  (verify_ros_phase.sh 이후)"""
import ast, re, numpy as np, onnx, onnxruntime as ort, yaml
from pathlib import Path
WS = Path.home() / "igris_ws"; G = WS / "src/igris_c_gmt_public"; R = []
def rec(ok, name, detail=""): R.append(ok); print(f"{'PASS' if ok is True else 'FAIL' if ok is False else ok} | {name} | {detail}")
m = onnx.load(str(G / "models/wbc_teleop/student_126.onnx")); md = {p.key: p.value for p in m.metadata_props}
jn = md["joint_names"].split(","); dq = np.array(md["default_joint_pos"].split(","), float)
ab = lambda n: ("L" if n.endswith("Left") else "R" if n.endswith("Right") else "") + "".join(w[0] for w in n.replace("Joint_", "").replace("_Left", "").replace("_Right", "").split("_"))
order = "LSP RSP WY LSR RSR WR LSY RSY WP LEP REP LHP RHP LHR RHR LHY RHY LKP RKP LAP RAP LAR RAR".split()
# ---- (A) static
rec([ab(n) for n in jn] == order, "A1 joint order: ONNX joint_names == GMT policy order", ",".join(ab(n) for n in jn[:6]) + ",...")
obs = yaml.safe_load(open(G / "config/obs.yaml"))["igris_c_gmt_public_observation"]; act = yaml.safe_load(open(G / "config/action.yaml"))["igris_c_gmt_public_action"]
terms = obs["groups"][0]["terms"]; alias = {"joint_pos_rel": "joint_pos", "last_actions": "actions", "motion_anchor_height": "motion_anchor_pos_z", "motion_root_state": "motion_anchor_ori_b", "motion_body_pos": "motion_body_pos_b"}
rec([alias.get(t["function"], t["function"]) for t in terms] == md["observation_names"].split(","), "A2 observation term order == ONNX observation_names")
rec([float(t["history"]) for t in terms] == [float(x) for x in md["observation_history_lengths"].split(",")], "A3 history lengths (20x5, 1x7)")
rec(np.allclose(obs["q_default"], dq, atol=1e-3) and np.allclose(act["q_default"], dq, atol=1e-3), "A4 default pose: obs.yaml & action.yaml q_default == ONNX default_joint_pos")
rec(np.allclose(act["action_scale"], float(md["action_scale"])) and act["use_motion_residual_action"] is False, "A5 action scale 0.25, non-residual (q_default + a*scale)")
hdr = (G / "include/utils/obs_functions.h").read_text(); bodies = re.findall(r'"([^"]+)"', hdr[hdr.index("kMotionBodyNames = {"):hdr.index("};", hdr.index("kMotionBodyNames = {"))])
rec(bodies == md["resolved_body_names"].split(","), "A6 tracked bodies (14) order == ONNX resolved_body_names", f"anchor={md['anchor_body_name']}")
ops = [n.op_type for n in m.graph.node[:2]]; rec(ops == ["Sub", "Div"], "A7 normalization embedded in ONNX (Sub mean, Div std); GMT applies none", "GMT only clamps raw action to +-100")
sysidx = dict(WY=0, WR=1, WP=2, LHP=3, LHR=4, LHY=5, LKP=6, LAP=7, LAR=8, RHP=9, RHR=10, RHY=11, RKP=12, RAP=13, RAR=14, LSP=15, LSR=16, LSY=17, LEP=18, RSP=22, RSR=23, RSY=24, REP=25)
gl = (WS / "logs/12_gmr_offline.log").read_text(); gm = dict(re.findall(r"Motor ID (\d+): (\S+)", gl)); bad = [o for o in order if ab(gm[str(sysidx[o])]) != o]
rec(not bad, "A8 GMT system index enum == GMR/SDK motor id order (31 dof)", f"mismatch={bad}")
iso = {"X12-150(HipPitch,Knee)": (118.435253, 15.079645, ["LHP", "LKP"]), "HipRoll": (122.136354, 10.367256, ["LHR"]), "X6-60(HipYaw,WaistYaw,Shoulder,Elbow)": (121.514570, 6.077864, ["LHY", "WY", "LSP", "LEP"]),
       "WaistRoll": (660.634418, 34.67, ["WR"]), "WaistPitch": (230.579719, 12.10, ["WP"]), "AnklePitch": (93.373568, 14.863025, ["LAP"]), "AnkleRoll": (77.634366, 12.355893, ["LAR"])}
for k, (kp, kd, js) in iso.items():
    g = [(act["kp"][order.index(j)], act["kd"][order.index(j)]) for j in js]; ok = all(abs(a - kp) < 1e-3 and abs(b - kd) < 1e-3 for a, b in g)
    rec(True if ok else "MISMATCH", f"A9 PD gains vs public Isaac asset [{k}]", f"isaac kp/kd={kp}/{kd} gmt={g[0][0]}/{g[0][1]}")
# ---- (B) dynamic: C++ node CSV vs independent reconstruction
S = dict(jp=(0, 460), jv=(460, 920), g=(920, 980), w=(980, 1040), la=(1040, 1500), mjp=(1500, 1523), mjv=(1523, 1546), z=(1546, 1547), ori=(1547, 1553), bp=(1553, 1595), lv=(1595, 1598), av=(1598, 1601))
def load(tag):
    a = np.genfromtxt(WS / f"data/gmt_logs/infer_{tag}.csv", delimiter=",", skip_header=1, usecols=range(3, 1628)); return a[:, 0].astype(int), a[:, 1:1602], a[:, 1602:]
sess = ort.InferenceSession(str(G / "models/wbc_teleop/student_126.onnx"), providers=["CPUExecutionProvider"])
for tag in ("onnx_replay", "ros2_input"):
    step, O, A = load(tag); n = len(O)
    py = sess.run(None, {"obs": O.astype(np.float32)})[0]; rec(np.abs(py - A).max() < 1e-3, f"B1[{tag}] C++ ORT raw action == Python ORT on logged obs", f"rows={n} max|d|={np.abs(py-A).max():.2e}")
    rec(np.allclose(O[:, slice(*S['g'])].reshape(n, 20, 3), [0, 0, -1], atol=1e-6), f"B2[{tag}] projected_gravity == (0,0,-1) x20 for identity IMU")
    la = O[:, slice(*S["la"])].reshape(n, 20, 23); cl = np.clip(A, -100, 100)
    rec(np.abs(la[1:, -1] - cl[:-1]).max() < 1e-5 and np.abs(la[2:, -2] - cl[:-2]).max() < 1e-5, f"B3[{tag}] history is oldest->newest; last_actions[t] == raw_action[t-1]")
    sent = np.load(WS / f"data/sim_logs/lowstate_sent_{tag}.npz")["data"][:, 1:32]; pol = sent[:, [sysidx[o] for o in order]] - dq
    jp = O[:, slice(*S["jp"])].reshape(n, 20, 23)[:, -1]; d = np.abs(jp[:, None, :] - pol[None, :, :]).max(-1).min(1)
    rec(d.max() < 2e-3, f"B4[{tag}] joint_pos_rel(newest) == sim q[system->policy map] - q_default", f"max nearest-sample err={d.max():.1e}")
ms = ort.InferenceSession(str(G / "data/onnx/recorded_walk_4.onnx"), providers=["CPUExecutionProvider"]); mm = ms.get_modelmeta().custom_metadata_map; bn = mm["body_names"].split(","); on = [o.name for o in ms.get_outputs()]
step, O, A = load("onnx_replay"); e = dict(mjp=0, z=0, bp=0, ori=0)
def yawfree6(q):  # wxyz -> inv(yaw(q))*q -> first two columns, row-major (IsaacLab motion_anchor_ori_b; robot anchor = identity)
    w, x, y, z = q; yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)); cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
    iw, iz = cy, -sy; w2, x2, y2, z2 = iw * w - iz * z, iw * x - iz * y, iw * y + iz * x, iw * z + iz * w
    Rm = np.array([[1 - 2 * (y2 * y2 + z2 * z2), 2 * (x2 * y2 - z2 * w2)], [2 * (x2 * y2 + z2 * w2), 1 - 2 * (x2 * x2 + z2 * z2)], [2 * (x2 * z2 - y2 * w2), 2 * (y2 * z2 + x2 * w2)]]); return Rm.reshape(-1)
nf = int(mm["motion_num_frames"])
for r in range(0, len(O), 7):
    out = dict(zip(on, ms.run(None, {"time_step": np.array([[step[r] % nf]], np.int64)}))); sel = [bn.index(b) for b in bodies]
    e["mjp"] = max(e["mjp"], np.abs(out["joint_pos"][0] - O[r, slice(*S["mjp"])]).max()); e["z"] = max(e["z"], abs(out["body_pos_w"][0, bn.index("base_link"), 2] - O[r, 1546]))
    e["bp"] = max(e["bp"], np.abs(out["body_pos_b"][0, sel].reshape(-1) - O[r, slice(*S["bp"])]).max()); e["ori"] = max(e["ori"], np.abs(yawfree6(out["body_quat_w"][0, bn.index("base_link")]) - O[r, slice(*S["ori"])]).max())
for k, nm in (("mjp", "motion_joint_pos == motion ONNX joint_pos[step]"), ("z", "motion_anchor_pos_z == base_link z"), ("bp", "motion_body_pos_b == body_pos_b[14 bodies by name]"), ("ori", "motion_anchor_ori_b == yaw-free 6D (IsaacLab def.)")):
    rec(e[k] < 2e-3, f"B5[onnx_replay] {nm}", f"max err={e[k]:.1e}")
step, O, A = load("ros2_input"); fr = [ast.literal_eval(l) for l in open(WS / "data/gmr_out/walk1_retarget_frames.txt")]
dof = np.array([f["dof_pos"][0] for f in fr])[:, [sysidx[o] for o in order]]; d = np.abs(O[:, None, slice(*S["mjp"])] - dof[None]).max(-1).min(1)
rec(d.max() < 1e-4, "B6[ros2_input] motion_joint_pos == mock GMR payload dof_pos[31->23 map] (ROS input actually consumed)", f"max err={d.max():.1e}, distinct frames={len(set(np.abs(O[:, None, slice(*S['mjp'])] - dof[None]).max(-1).argmin(1)))}")
for tag in ("onnx_replay", "ros2_input"):
    step, O, A = load(tag); C = np.load(WS / f"data/sim_logs/lowcmd_received_{tag}.npz")["data"]; q, kp = C[:, 1:32], C[:, 32:63]; k = min(len(q), len(A))
    want = dq + 0.25 * np.clip(A[-k:], -100, 100); got = q[-k:, [sysidx[o] for o in order]]; lo, hi = np.array(act["joint_position_min"]), np.array(act["joint_position_max"]); inside = (want > lo + 0.25) & (want < hi - 0.25)
    rec(np.abs(want - got)[inside].max() < 1e-4, f"B7[{tag}] LowCmd.q[system idx] == q_default + 0.25*action (where away from soft limits)", f"n={k}, inside-limit frac={inside.mean():.2f}, max err={np.abs(want-got)[inside].max():.1e}")
    rec(np.allclose(kp[-1, [sysidx[o] for o in order]], act["kp"], atol=1e-3), f"B8[{tag}] LowCmd.kp mapped per action.yaml", f"non-policy motors kp={sorted(set(np.round(np.delete(kp[-1], [sysidx[o] for o in order]), 2)))}")
    a = np.abs(0.25 * A); print(f"INFO | [{tag}] |a*scale| mean={a.mean():.3f} rad, p99={np.percentile(a, 99):.3f}, max={a.max():.3f} (open-loop, fixed-base mock state: magnitude not a tracking metric)")
print(f"SUMMARY pass={sum(r is True for r in R)} fail={sum(r is False for r in R)} mismatch={sum(r == 'MISMATCH' for r in R)}")
