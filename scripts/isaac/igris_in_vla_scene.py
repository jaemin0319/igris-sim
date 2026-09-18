"""기존 G1 시뮬 환경(바닥·작업대·소품·배경·조명·재질) + 공식 IGRIS-C 1대. Isaac Lab 불필요.
장면 정의: config/vla_scene.yaml (사용자 최종 장면 설정 .py의 값을 옮겨 적고 sha256으로 출처 고정).
  1) 새 장면 레이어에 환경 USD를 reference로 배치(원본 자산·백업 무수정, 재질/kinematic은 이 레이어의 override),
  2) G1 자리는 비활성(active=false) prim으로만 기록,
  3) 공식 IGRIS-C USD를 reference로 추가(Bake/Flatten 등 로봇 물리를 건드리는 변환 없음),
  4) x,y,yaw는 G1 자리 기준, z = 바닥 raycast 높이 + IGRIS 공식 기립 높이(+여유) 로 재계산,
  5) 자산 누락·초기 겹침·발 높이 점검 → 수 초 물리 → 관통/유한성/VRAM 기록 → 다중 시점 스크린샷.
실행: bash ~/igris_ws/scripts/run_igris_vla_scene.sh [--headless] [--secs 5] [--hold 600]
제어기 없이 서 있는 것은 성공 기준이 아니다(넘어짐은 정상 범주, 바닥 관통·NaN·자산 누락이 실패)."""
import argparse, json, math, os, re, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument("--headless", action="store_true"); ap.add_argument("--secs", type=float, default=5.0); ap.add_argument("--hold", type=float, default=0.0)
ap.add_argument("--config", default=os.path.expanduser("~/igris_ws/config/vla_scene.yaml")); ap.add_argument("--tag", default="run")
ap.add_argument("--out", default=os.path.expanduser("~/igris_ws/data/isaac")); ap.add_argument("--freeze", action="store_true", help="물리를 돌리지 않고 초기 배치만 표시")
a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
import yaml
cfg = yaml.safe_load(open(a.config))
def expand(v):  # ${VAR:-default}, ${VAR}, ~
    v = re.sub(r"\$\{(\w+):-([^}]*)\}", lambda m: os.environ.get(m.group(1)) or m.group(2), v); return os.path.expanduser(os.path.expandvars(v))
ROOTS = {k: expand(v) for k, v in cfg["roots"].items()}
def rp(p): return re.sub(r"\$\{(\w+)\}", lambda m: ROOTS[m.group(1)], p)
def vram():
    o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip().split(","); return int(o[0]), int(o[1])
res = {"config": a.config, "roots": ROOTS, "vram_before_mib": vram()[0]}; t0 = time.time()
from isaacsim import SimulationApp
app = SimulationApp({"headless": a.headless, "width": 1280, "height": 720, "renderer": "RaytracedLighting"})
import numpy as np, omni.usd, omni.physx
from isaacsim.core.api import World
from isaacsim.core.prims import SingleArticulation
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.core.utils.viewports import set_camera_view
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, UsdUtils
world = World(stage_units_in_meters=1.0, physics_dt=1.0 / 200.0, rendering_dt=1.0 / 50.0); stage = omni.usd.get_context().get_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
def place(prim, pos, rot_wxyz=(1, 0, 0, 0), scale=None):
    xf = UsdGeom.Xformable(prim); xf.ClearXformOpOrder()
    xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*[float(v) for v in pos]))
    w, x, y, z = [float(v) for v in rot_wxyz]; xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(w, x, y, z))
    if scale: xf.AddScaleOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*[float(v) for v in scale]))
def bind_preview(prim, m, name):  # Isaac Lab visual_material=PreviewSurfaceCfg 와 동일 효과: 새 레이어의 재질을 strongerThanDescendants로 바인딩
    mat = UsdShade.Material.Define(stage, Sdf.Path(f"/World/Looks/{name}")); sh = UsdShade.Shader.Define(stage, Sdf.Path(f"/World/Looks/{name}/Shader")); sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*[float(c) for c in m["diffuse"]])); sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(m.get("metallic", 0.0)))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(m.get("roughness", 0.5))); mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
# ---- 바닥
g = cfg["ground"]; ground_mode = "plane"
if g.get("mode") == "lab_grid":
    try:
        from isaacsim.storage.native import get_assets_root_path
        root = get_assets_root_path()
        if root:
            gp = stage.DefinePrim(g["prim"], "Xform"); gp.GetReferences().AddReference(f"{root}/Isaac/Environments/Grid/default_environment.usd"); ground_mode = "lab_grid"
            for _ in range(20): app.update()
            res["ground_children"] = [c.GetName() for c in gp.GetChildren()]
            env = stage.GetPrimAtPath(f'{g["prim"]}/Environment')                                  # Isaac Lab spawn_ground_plane 과 동일: 100m 기본 환경을 size/100 로 스케일
            if env.IsValid():
                try: UsdGeom.XformCommonAPI(env).SetScale(Gf.Vec3f(g["size"][0] / 100.0, g["size"][1] / 100.0, 1.0)); res["ground_scaled"] = True
                except Exception as ex: res["ground_scale_error"] = str(ex)
            shd = stage.GetPrimAtPath(f'{g["prim"]}/Looks/theGrid/Shader')
            if shd.IsValid(): shd.CreateAttribute("inputs:diffuse_tint", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*[float(c) for c in g["color"]])); res["ground_tinted"] = True
            sl = stage.GetPrimAtPath(f'{g["prim"]}/SphereLight')
            if sl.IsValid(): sl.SetActive(False); res["ground_default_light_removed"] = True      # Isaac Lab도 기본 환경의 조명은 제거한다
            res["ground_asset_root"] = root
    except Exception as ex: res["ground_error"] = str(ex)
if ground_mode == "plane":
    from isaacsim.core.api.objects import GroundPlane
    GroundPlane(prim_path=g["prim"], size=float(max(g["size"])), color=np.array(g["color"], dtype=float))
res["ground_mode"] = ground_mode
# ---- 환경 USD(기존 배치 그대로)
missing_files = []
for i, e in enumerate(cfg["environment"]):
    path = rp(e["usd"]); prim = stage.DefinePrim(e["prim"], "Xform")
    if not os.path.isfile(path): missing_files.append({"prim": e["prim"], "usd": path}); continue
    prim.GetReferences().AddReference(path); place(prim, e.get("pos", (0, 0, 0)), e.get("rot", (1, 0, 0, 0)), e.get("scale"))
    if e.get("visual_material"): bind_preview(prim, e["visual_material"], f"EnvMat_{i}")
for i, p in enumerate(cfg.get("primitives", [])):
    t = p["type"]; prim = stage.DefinePrim(p["prim"], {"cylinder": "Cylinder", "cuboid": "Cube", "sphere": "Sphere"}[t])
    if t == "cylinder": c = UsdGeom.Cylinder(prim); c.CreateRadiusAttr(float(p["radius"])); c.CreateHeightAttr(float(p["height"])); c.CreateAxisAttr(p.get("axis", "Z"))
    if t == "cuboid": UsdGeom.Cube(prim).CreateSizeAttr(1.0)
    if t == "sphere": UsdGeom.Sphere(prim).CreateRadiusAttr(float(p["radius"]))
    place(prim, p["pos"], p.get("rot", (1, 0, 0, 0)), p.get("size") if t == "cuboid" else None)
    if p.get("visual_material"): bind_preview(prim, p["visual_material"], f"PrimMat_{i}")
    if p.get("collision", True): UsdPhysics.CollisionAPI.Apply(prim)
    if p.get("rigid", True): UsdPhysics.RigidBodyAPI.Apply(prim); UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(float(p.get("mass", 0.1)))
for l in cfg.get("lights", []):
    L = {"dome": UsdLux.DomeLight, "distant": UsdLux.DistantLight, "sphere": UsdLux.SphereLight}[l["type"]].Define(stage, Sdf.Path(l["prim"])); L.CreateIntensityAttr(float(l["intensity"]))
    if "color" in l: L.CreateColorAttr(Gf.Vec3f(*[float(c) for c in l["color"]]))
    if "pos" in l or "rot" in l: place(L.GetPrim(), l.get("pos", (0, 0, 0)), l.get("rot", (1, 0, 0, 0)))
for _ in range(20): app.update()
for e in cfg["environment"]:
    if e.get("kinematic"):                                                                        # RigidBodyPropertiesCfg(kinematic_enabled=True) 에 해당
        n = 0
        for prim in Usd.PrimRange(stage.GetPrimAtPath(e["prim"])):
            if prim.HasAPI(UsdPhysics.RigidBodyAPI): UsdPhysics.RigidBodyAPI(prim).CreateKinematicEnabledAttr(True); n += 1
        res.setdefault("kinematic_overrides", {})[e["prim"]] = n
# ---- G1 자리(비활성 기록) + IGRIS reference
g1 = cfg["g1_slot"]; slot = stage.DefinePrim(g1["prim"], "Xform"); place(slot, g1["pos"], g1["rot"])
slot.SetCustomDataByKey("igris_sim:note", "original G1 instance slot; deactivated in this layer, asset not loaded"); slot.SetCustomDataByKey("igris_sim:original_usd", g1.get("usd", "")); slot.SetActive(False)
ig = cfg["igris"]; IGRIS_USD = rp(ig["usd"]); assert os.path.isfile(IGRIS_USD), IGRIS_USD
robot = stage.DefinePrim(ig["prim"], "Xform"); robot.GetReferences().AddReference(IGRIS_USD)
w, x, y, z = [float(v) for v in g1["rot"]]; yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) + math.radians(float(ig.get("yaw_offset_deg", 0.0))); qyaw = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
gx, gy = float(g1["pos"][0]) + float(ig["xy_offset"][0]), float(g1["pos"][1]) + float(ig["xy_offset"][1])
place(robot, (gx, gy, 50.0), qyaw)                                                                 # 바닥 측정 전까지 raycast 경로 밖에 둔다
cam = cfg["scene_camera"]; camera = UsdGeom.Camera.Define(stage, Sdf.Path(cam["prim"])); camera.CreateFocalLengthAttr(float(cam.get("focal_length", 18.0)))
for _ in range(10): app.update()
# ---- 자산 누락 점검
try:
    layers, assets, unres = UsdUtils.ComputeAllDependencies(stage.GetRootLayer().identifier); unresolved = sorted(set(str(u) for u in unres))
    res["dependencies"] = {"layers": len(layers), "assets": len(assets), "unresolved": len(unresolved), "unresolved_list": unresolved[:40]}
except Exception as ex: res["dependencies"] = {"error": str(ex)}
res["missing_reference_files"] = missing_files
# ---- 바닥 높이(raycast) → IGRIS 높이 확정
world.reset(); sq = omni.physx.get_physx_scene_query_interface(); z_from = float(g1["pos"][2]) + float(ig.get("raycast_from_above", 0.3))
hit = sq.raycast_closest((gx, gy, z_from), (0.0, 0.0, -1.0), 10.0); floor_z = float(hit["position"][2]) if hit.get("hit") else 0.0
res["floor"] = {"raycast_from": [gx, gy, z_from], "hit": bool(hit.get("hit")), "collider": str(hit.get("collision", "")), "floor_z": round(floor_z, 4)}
stand = float(ig["standing_base_height"]); base_z = floor_z + stand + float(ig.get("clearance", 0.01)); place(robot, (gx, gy, base_z), qyaw)
res["placement"] = {"g1_slot_pos": g1["pos"], "g1_slot_rot_wxyz": g1["rot"], "igris_base_pos": [gx, gy, round(base_z, 4)], "igris_yaw_deg": round(math.degrees(yaw), 2),
                    "rule": "x,y,yaw from G1 slot (+xy_offset); z = floor_z(raycast) + standing_base_height + clearance (G1 z not copied)"}
scene_dir = os.path.join(ROOTS.get("isaac_root", a.out), "scenes"); os.makedirs(scene_dir, exist_ok=True); scene_usda = os.path.join(scene_dir, "igris_in_vla_scene.usda")
stage.GetRootLayer().Export(scene_usda); res["scene_layer"] = scene_usda
roots = [p.GetPath().pathString for p in Usd.PrimRange(robot) if p.HasAPI(UsdPhysics.ArticulationRootAPI)]; assert roots, "IGRIS articulation root not found"
art = SingleArticulation(prim_path=roots[0], name="igris_c"); world.scene.add(art); world.reset()
names = list(art.dof_names); q0 = np.zeros(len(names), dtype=np.float32)
for i, n in enumerate(names):
    for pat, v in ig.get("init_joint_pos", {}).items():
        if re.fullmatch(pat, n): q0[i] = float(v)
def reset_pose():
    art.set_world_pose(position=np.array([gx, gy, base_z]), orientation=np.array(qyaw)); art.set_joint_positions(q0); art.set_joint_velocities(np.zeros_like(q0))
    art.set_linear_velocity(np.zeros(3)); art.set_angular_velocity(np.zeros(3))
ctrl = art.get_articulation_controller(); kp, kd = [np.array(v, dtype=np.float32).copy() for v in ctrl.get_gains()]; matched = 0
for i, n in enumerate(names):
    for pat, (p_, d_) in ig.get("pd_gains", {}).items():
        if re.fullmatch(pat, n): kp[i], kd[i] = float(p_), float(d_); matched += 1; break
ctrl.set_gains(kps=kp, kds=kd); reset_pose(); art.apply_action(ArticulationAction(joint_positions=q0))
res["load"] = {"igris_usd": IGRIS_USD, "articulation_root": roots[0], "num_dof": int(art.num_dof), "pd_gain_joints": matched,
               "env_prims": {e["prim"]: sum(1 for _ in Usd.PrimRange(stage.GetPrimAtPath(e["prim"]), Usd.TraverseInstanceProxies())) for e in cfg["environment"]},
               "mesh_prims_total": sum(1 for p in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh))}
# ---- 초기 겹침·발 높이(물리 시작 전 자세 기준 AABB)
timeline = omni.timeline.get_timeline_interface() if hasattr(omni, "timeline") else None
world.step(render=True); reset_pose(); world.pause()
for _ in range(3): app.update()
def aabb(prim):
    bc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy]); r = bc.ComputeWorldBound(prim).ComputeAlignedRange(); return [list(r.GetMin()), list(r.GetMax())]
rb = aabb(robot); overlaps = {}
for e in cfg["environment"]:
    eb = aabb(stage.GetPrimAtPath(e["prim"])); gap = [max(eb[0][k] - rb[1][k], rb[0][k] - eb[1][k]) for k in range(3)]
    overlaps[e["prim"]] = {"aabb_min": [round(v, 3) for v in eb[0]], "aabb_max": [round(v, 3) for v in eb[1]], "axis_gaps_xyz": [round(v, 3) for v in gap], "aabb_overlap": bool(max(gap) < 0)}
links = [p for p in Usd.PrimRange(robot) if p.HasAPI(UsdPhysics.RigidBodyAPI)]; table = stage.GetPrimAtPath(cfg["environment"][0]["prim"]); fine = []
parts = [p for p in Usd.PrimRange(table, Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh)]; part_boxes = [(p.GetPath().pathString, aabb(p)) for p in parts]
for lk in links:
    lb = aabb(lk)
    if any(lb[0][k] > overlaps[cfg["environment"][0]["prim"]]["aabb_max"][k] or lb[1][k] < overlaps[cfg["environment"][0]["prim"]]["aabb_min"][k] for k in range(3)): continue
    for name, pb in part_boxes:
        depth = [min(lb[1][k], pb[1][k]) - max(lb[0][k], pb[0][k]) for k in range(3)]
        if min(depth) > 0: fine.append({"link": lk.GetName(), "table_part": name.split("/PackingTable/")[-1][-60:], "overlap_depth_xyz_m": [round(v, 3) for v in depth]})
res["initial_check_link_level"] = {"robot_links": len(links), "table_mesh_parts": len(parts), "link_vs_tablepart_aabb_overlaps": fine[:20], "count": len(fine)}
res["initial_check"] = {"robot_aabb_min": [round(v, 3) for v in rb[0]], "robot_aabb_max": [round(v, 3) for v in rb[1]], "foot_bottom_minus_floor": round(rb[0][2] - floor_z, 4),
                        "feet_on_or_above_floor": bool(rb[0][2] - floor_z > -0.005), "env_overlap": overlaps}
# ---- 스크린샷(초기 배치)
shots = []
try:
    from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file
    vp = get_active_viewport(); vp.camera_path = cam["prim"]
    def shot(name, eye, target):
        set_camera_view(eye=eye, target=target, camera_prim_path=cam["prim"])
        for _ in range(30): app.update()
        f = os.path.join(a.out, f"igris_vla_scene_{a.tag}_{name}.png"); capture_viewport_to_file(vp, f)
        for _ in range(10): app.update()
        shots.append(f)
    shot("init_front", cam["eye"], cam["target"])
    for v in cfg.get("extra_views", []): shot(f"init_{v['name']}", v["eye"], v["target"])
except Exception as ex: vp = None; res["viewport_error"] = str(ex)
# ---- 기본 물리
def tilt(q): return float(np.degrees(np.arccos(np.clip(1 - 2 * (float(q[1]) ** 2 + float(q[2]) ** 2), -1, 1))))
series = []; peak = vram()[0]
if not a.freeze:
    world.play(); steps = int(a.secs * 50); tw = time.time(); obj = stage.GetPrimAtPath(cfg["environment"][1]["prim"]) if len(cfg["environment"]) > 1 else None
    for k in range(steps):
        world.step(render=True)
        if k % 25 == 0 or k == steps - 1:
            p, q = art.get_world_pose(); qd = art.get_joint_velocities(); peak = max(peak, vram()[0]); lows = sorted((aabb(l)[0][2], l.GetName()) for l in links); zmin = lows[0][0]; lowest = lows[0][1]
            series.append({"t": round((k + 1) / 50.0, 2), "base_z": round(float(p[2]), 4), "robot_zmin_minus_floor": round(zmin - floor_z, 4), "tilt_deg": round(tilt(q), 2),
                           "max_abs_qd": round(float(np.abs(qd).max()), 3), "lowest_link": lowest, "finite": bool(np.isfinite(qd).all() and np.isfinite(p).all())})
    wall = time.time() - tw; pen = min(s["robot_zmin_minus_floor"] for s in series); up = [s for s in series if s["tilt_deg"] < 20]
    res["physics"] = {"sim_secs": a.secs, "wall_secs": round(wall, 2), "realtime_factor": round(a.secs / wall, 2), "all_finite": all(s["finite"] for s in series),
                      "min_zmin_minus_floor_while_upright": min([s["robot_zmin_minus_floor"] for s in up], default=None), "min_zmin_minus_floor_overall": pen,
                      "base_keeps_sinking": bool(len(series) > 3 and series[-1]["base_z"] < series[-3]["base_z"] - 0.005), "note_zmin": "zmin은 시각 메시 AABB 기준(충돌 형상은 단순화되어 있어 넘어진 뒤 수 cm 차이 가능)", "table_aabb_after": aabb(stage.GetPrimAtPath(cfg["environment"][0]["prim"])),
                      "object_aabb_after": aabb(obj) if obj else None, "series": series}
    res["balance_observation"] = {"upright_at_end": bool(series[-1]["tilt_deg"] < 20 and series[-1]["base_z"] > floor_z + 0.8 * stand), "note": "성공 기준 아님(균형 제어기 없음, 초기자세 PD 유지뿐)"}
    if vp is not None: shot("after_physics", cam["eye"], cam["target"])
res["vram_mib"] = {"peak_during_run": peak, "total": vram()[1]}; res["screenshots"] = shots; res["elapsed_s"] = round(time.time() - t0, 1)
js = os.path.join(a.out, f"igris_vla_scene_{a.tag}.json"); json.dump(res, open(js, "w"), indent=1, default=str); print("RESULT_JSON", js, flush=True)
if a.hold > 0:                                                                                      # 사용자가 직접 확인: 초기 배치로 되돌려 멈춘 채 창을 열어 둔다(Play로 물리 재생 가능)
    reset_pose(); world.pause(); set_camera_view(eye=cam["eye"], target=cam["target"], camera_prim_path=cam["prim"]); th = time.time()
    while time.time() - th < a.hold and app.is_running(): app.update()
app.close()
