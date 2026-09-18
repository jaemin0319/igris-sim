"""Isaac Sim 5.1.0 최소 장면: 지면 + 조명 + 공식 IGRIS-C USD 1대(reference, 원본 무수정) + 수 초 물리.
Isaac Lab 불필요. 실행: bash ~/igris_ws/scripts/run_isaac_igris.sh [--headless] [--secs 5] [--hold 30] [--pd official|usd]
- 모델 로딩(관절 수·DOF 이름)과 균형 유지(베이스 높이·기울기)를 구분해 JSON으로 기록한다.
- --pd official: robros_lab/assets/robots/robros.py의 공식 stiffness/damping을 PhysX 위치 드라이브로 적용하고 공식 초기자세를 목표로 유지
  (Lab의 DelayedPD·마찰·armature 모델은 아님. 균형 제어기 없음 → 넘어질 수 있음).  --pd usd: USD에 저장된 드라이브 값 그대로."""
import argparse, json, os, re, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument("--headless", action="store_true"); ap.add_argument("--secs", type=float, default=5.0); ap.add_argument("--hold", type=float, default=0.0)
ap.add_argument("--variant", default="extras/wrist_hand_independent", help='공식 ArticulationCfg가 쓰는 변형. 기본 USD는 ""')
ap.add_argument("--pd", choices=["official", "usd"], default="official"); ap.add_argument("--out", default=os.path.expanduser("~/igris_ws/data/isaac"))
ap.add_argument("--tag", default="run"); a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
USD_DIR = os.path.expanduser("~/igris_ws/src/igris_c_isaacsim_public/source/robros_lab/robros_lab/assets/robots/robros/igris_c/from_urdf/usd")
USD = os.path.join(USD_DIR, a.variant, "igris_c.usd"); assert os.path.isfile(USD), USD
def vram():
    o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip().split(","); return int(o[0]), int(o[1])
res = {"usd": USD, "variant": a.variant, "pd": a.pd, "headless": a.headless, "vram_before_mib": vram()[0], "stages": {}}; t_start = time.time()
from isaacsim import SimulationApp
app = SimulationApp({"headless": a.headless, "width": 1280, "height": 720, "renderer": "RaytracedLighting"}); res["stages"]["app_start_s"] = round(time.time() - t_start, 1)
import numpy as np, omni.usd
from isaacsim.core.api import World
from isaacsim.core.api.objects import GroundPlane
from isaacsim.core.prims import SingleArticulation
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.core.utils.viewports import set_camera_view
from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics
world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 200.0, rendering_dt=1.0 / 50.0); stage = omni.usd.get_context().get_stage()
GroundPlane(prim_path="/World/Ground", size=20.0, color=np.array([0.45, 0.45, 0.45]))          # 로컬 생성(에셋 서버 다운로드 없음)
UsdLux.DomeLight.Define(stage, Sdf.Path("/World/DomeLight")).CreateIntensityAttr(800.0)
sun = UsdLux.DistantLight.Define(stage, Sdf.Path("/World/Sun")); sun.CreateIntensityAttr(2500.0); UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-50.0, 20.0, 0.0))
robot_prim = add_reference_to_stage(usd_path=USD, prim_path="/World/IGRIS_C")                    # 원본 USD는 reference만(읽기 전용)
xf = UsdGeom.Xformable(robot_prim); ops = {o.GetOpName(): o for o in xf.GetOrderedXformOps()}
(ops.get("xformOp:translate") or xf.AddTranslateOp()).Set(Gf.Vec3d(0.0, 0.0, 0.961))           # 공식 init_state pos
roots = [p.GetPath().pathString for p in stage.Traverse() if p.GetPath().pathString.startswith("/World/IGRIS_C") and p.HasAPI(UsdPhysics.ArticulationRootAPI)]
joints = [p for p in stage.Traverse() if p.GetPath().pathString.startswith("/World/IGRIS_C") and p.IsA(UsdPhysics.Joint)]
res["load"] = {"default_prim_ok": robot_prim.IsValid(), "articulation_roots": roots, "usd_joint_prims": len(joints), "mesh_prims": sum(1 for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))}
assert roots, "ArticulationRootAPI prim not found under /World/IGRIS_C"
scene_usd = os.path.join(os.environ.get("ISAAC_ROOT", a.out), "scenes", "igris_min_scene.usd"); os.makedirs(os.path.dirname(scene_usd), exist_ok=True)
stage.GetRootLayer().Export(scene_usd); res["scene_usd"] = scene_usd                              # 새 장면 파일(원본을 reference)
art = SingleArticulation(prim_path=roots[0], name="igris_c"); world.scene.add(art); world.reset(); res["stages"]["scene_ready_s"] = round(time.time() - t_start, 1)
names = list(art.dof_names); res["load"].update({"num_dof": int(art.num_dof), "dof_names_head": names[:8], "fixed_base": bool(getattr(art, "is_fixed_base", lambda: None)() if callable(getattr(art, "is_fixed_base", None)) else False)})
INIT = [(r".*_Hip_Pitch_.*", -0.2), (r".*_Knee_Pitch_.*", 0.3), (r".*_Ankle_Pitch_.*", -0.15), (r".*_Shoulder_Pitch_(Left|Right)", 0.13), (r".*_Shoulder_Roll_Left", 0.13), (r".*_Shoulder_Roll_Right", -0.13), (r".*_Elbow_Pitch_(Left|Right)", -0.3)]
GAINS = [(r".*Hip_Pitch.*|.*Knee.*", 118.435253, 15.079645), (r".*Hip_Roll.*", 122.136354, 10.367256), (r".*Hip_Yaw.*|.*Waist_Yaw.*|.*_Shoulder_.*|.*_Elbow_.*", 121.514570, 6.077864),
         (r".*Waist_Roll.*", 660.634418, 34.67), (r".*Waist_Pitch.*", 230.579719, 12.10), (r".*Ankle_Pitch.*", 93.373568, 14.863025), (r".*Ankle_Roll.*", 77.634366, 12.355893)]
q0 = np.zeros(len(names), dtype=np.float32)
for i, n in enumerate(names):
    for pat, v in INIT:
        if re.fullmatch(pat, n): q0[i] = v
art.set_joint_positions(q0); art.set_joint_velocities(np.zeros_like(q0))
kp_usd, kd_usd = art.get_articulation_controller().get_gains(); kp, kd = np.array(kp_usd, dtype=np.float32).copy(), np.array(kd_usd, dtype=np.float32).copy(); matched = 0
if a.pd == "official":
    for i, n in enumerate(names):
        for pat, p, d in GAINS:
            if re.fullmatch(pat, n): kp[i], kd[i] = p, d; matched += 1; break
    art.get_articulation_controller().set_gains(kps=kp, kds=kd)
res["pd"] = {"mode": a.pd, "official_gain_joints": matched, "usd_kp_minmax": [float(np.min(kp_usd)), float(np.max(kp_usd))], "applied_kp_minmax": [float(kp.min()), float(kp.max())]}
from isaacsim.core.utils.types import ArticulationAction
art.apply_action(ArticulationAction(joint_positions=q0)); set_camera_view(eye=[2.6, 2.0, 1.4], target=[0.0, 0.0, 0.85])
def tilt_deg(quat_wxyz):
    w, x, y, z = [float(v) for v in quat_wxyz]; return float(np.degrees(np.arccos(np.clip(1 - 2 * (x * x + y * y), -1, 1))))
p0, _ = art.get_world_pose(); series = []; steps = int(a.secs * 50); peak = 0; t_sim0 = time.time(); shot = None
for k in range(steps):
    world.step(render=True)
    if k % 25 == 0 or k == steps - 1:
        p, q = art.get_world_pose(); qd = art.get_joint_velocities(); peak = max(peak, vram()[0])
        series.append({"t": round((k + 1) / 50.0, 2), "base_z": round(float(p[2]), 4), "tilt_deg": round(tilt_deg(q), 2), "max_abs_qd": round(float(np.abs(qd).max()), 3), "finite": bool(np.isfinite(qd).all() and np.isfinite(p).all())})
    if k == min(steps - 1, 60) and shot is None:
        try:
            from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file
            shot = os.path.join(a.out, f"igris_min_scene_{a.tag}.png"); capture_viewport_to_file(get_active_viewport(), shot)
        except Exception as e: shot = f"capture failed: {e}"
wall = time.time() - t_sim0; end = series[-1]
res["physics"] = {"sim_secs": a.secs, "wall_secs": round(wall, 2), "realtime_factor": round(a.secs / wall, 2), "physics_dt": 1 / 200, "all_finite": all(s["finite"] for s in series), "series": series}
res["balance"] = {"base_z_start": round(float(p0[2]), 4), "base_z_end": end["base_z"], "tilt_end_deg": end["tilt_deg"], "upright_at_end": bool(end["base_z"] > 0.8 * float(p0[2]) and end["tilt_deg"] < 20.0),
                  "note": "균형 제어기 없음: 초기자세 PD 유지뿐. upright는 지정 시간 동안 서 있었는지의 관찰값"}
res["vram_mib"] = {"peak_during_run": peak, "total": vram()[1]}; res["screenshot"] = shot
t_hold = time.time()
while a.hold > 0 and time.time() - t_hold < a.hold and app.is_running(): world.step(render=True)
js = os.path.join(a.out, f"igris_min_scene_{a.tag}.json"); json.dump(res, open(js, "w"), indent=1); print("RESULT_JSON", js); app.close()
