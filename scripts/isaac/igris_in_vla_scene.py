"""기존 G1 시뮬 환경(바닥·작업대·소품·배경·조명·재질) + 공식 IGRIS-C 1대. Isaac Lab 불필요.
장면 정의: config/vla_scene.yaml (사용자 최종 장면 설정 .py의 값을 옮겨 적고 sha256으로 출처 고정).
  1) 새 장면 레이어에 환경 USD를 reference로 배치(원본 자산·백업 무수정, 재질/kinematic은 이 레이어의 override),
  2) G1 자리는 비활성(active=false) prim으로만 기록,
  3) 공식 IGRIS-C USD를 reference로 추가(Bake/Flatten 등 로봇 물리를 건드리는 변환 없음),
  4) x,y,yaw는 G1 자리 기준, z = 바닥 raycast 높이 + IGRIS 공식 기립 높이(+여유) 로 재계산,
  5) 자산 누락·초기 겹침·발 높이 점검 → 수 초 물리 → 관통/유한성/VRAM 기록 → 다중 시점 스크린샷.
실행: bash ~/igris_ws/scripts/run_igris_vla_scene.sh [--headless] [--secs 5] [--hold 600]
제어기 없이 서 있는 것은 성공 기준이 아니다(넘어짐은 정상 범주, 바닥 관통·NaN·자산 누락이 실패).
골반 고정(기본 on)은 월드에 매단 지지 상태이며 균형 제어가 아니다. 끄기: --no-fix / --no-appearance."""
import argparse, json, math, os, re, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument("--headless", action="store_true"); ap.add_argument("--secs", type=float, default=5.0); ap.add_argument("--hold", type=float, default=0.0)
ap.add_argument("--config", default=os.path.expanduser("~/igris_ws/config/vla_scene.yaml")); ap.add_argument("--tag", default="run")
ap.add_argument("--out", default=os.path.expanduser("~/igris_ws/data/isaac")); ap.add_argument("--freeze", action="store_true", help="물리를 돌리지 않고 초기 배치만 표시")
ap.add_argument("--fix", dest="fix", action="store_true", default=None, help="골반 고정 켬(기본: YAML igris.fix.enabled)"); ap.add_argument("--no-fix", dest="fix", action="store_false")
ap.add_argument("--fix-link", default=None, help="고정할 링크: auto(=양쪽 Joint_Hip_Pitch의 부모, 골반) | root | 링크명")
ap.add_argument("--appearance", dest="appearance", action="store_true", default=None); ap.add_argument("--no-appearance", dest="appearance", action="store_false")
ap.add_argument("--arm-test", dest="arm_test", action="store_true", default=None, help="물리 중 팔 관절에 사인파 목표를 주어 움직임 확인")
ap.add_argument("--cameras", dest="cameras", action="store_true", default=None); ap.add_argument("--no-cameras", dest="cameras", action="store_false")
ap.add_argument("--viewport-camera", default="scene", help="GUI viewport: scene | head_left | head_right | hand_left | hand_right")
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
FIX = ig.get("fix", {}); fix_on = FIX.get("enabled", True) if a.fix is None else a.fix; fix_link_sel = a.fix_link or FIX.get("link", "auto")
APP = yaml.safe_load(open(os.path.expanduser(ig.get("appearance_config", "~/igris_ws/config/igris_appearance.yaml")))); app_on = APP.get("enabled", True) if a.appearance is None else a.appearance
scene_dir = os.path.join(ROOTS.get("isaac_root", a.out), "scenes"); os.makedirs(scene_dir, exist_ok=True)
def new_sublayer(name):  # 별도 override 레이어(파일) — 루트 장면 레이어의 subLayer. 원본 USD는 reference로만 쓰인다
    path = os.path.join(scene_dir, name); os.path.exists(path) and os.remove(path); L = Sdf.Layer.CreateNew(path); stage.GetRootLayer().subLayerPaths.append(path); return L
res["layers"] = {}
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
world.stop()                                                                                      # 바닥만 측정했으면 물리를 내리고(파싱 해제) 최종 배치·레이어 작성 후 다시 파싱한다
stand = float(ig["standing_base_height"]); base_z = floor_z + stand + float(ig.get("clearance", 0.01)); place(robot, (gx, gy, base_z), qyaw)
for _ in range(5): app.update()
# ---- (레이어 1) 골반 고정: 현재 자세의 월드 포즈에 FixedJoint(world→link). 나머지 관절·강체·충돌은 그대로
art_root_prim = [p for p in Usd.PrimRange(robot) if p.HasAPI(UsdPhysics.ArticulationRootAPI)][0]
hips = [p for p in Usd.PrimRange(robot) if p.IsA(UsdPhysics.Joint) and re.fullmatch(r"Joint_Hip_Pitch_(Left|Right)", p.GetName())]
hip_parents = sorted(set(UsdPhysics.Joint(h).GetBody0Rel().GetTargets()[0].name for h in hips)); pelvis_name = hip_parents[0] if len(hip_parents) == 1 else None
res["root_body"] = {"articulation_root": art_root_prim.GetPath().pathString, "root_children_joints": [j.GetName() for j in Usd.PrimRange(art_root_prim) if j.IsA(UsdPhysics.Joint)][:6], "pelvis_link(parent of hip joints)": pelvis_name}
fix_res = {"enabled": bool(fix_on)}
if fix_on:
    link_name = art_root_prim.GetName() if fix_link_sel == "root" else (pelvis_name if fix_link_sel == "auto" else fix_link_sel); link_prim = next(p for p in Usd.PrimRange(robot) if p.GetName() == link_name and p.HasAPI(UsdPhysics.RigidBodyAPI))
    fixL = new_sublayer("igris_fix_pelvis.usda"); res["layers"]["fix"] = fixL.identifier
    with Usd.EditContext(stage, Usd.EditTarget(fixL)):
        M = UsdGeom.Xformable(link_prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()); Mt = M.RemoveScaleShear(); pos = Mt.ExtractTranslation(); rot = Mt.ExtractRotationQuat()
        J = UsdPhysics.FixedJoint.Define(stage, link_prim.GetPath().AppendChild("WorldFixedJoint_igris_sim")); J.CreateBody1Rel().SetTargets([link_prim.GetPath()])
        J.CreateLocalPos0Attr().Set(Gf.Vec3f(pos)); J.CreateLocalRot0Attr().Set(Gf.Quatf(rot.GetReal(), *rot.GetImaginary())); J.CreateLocalPos1Attr().Set(Gf.Vec3f(0, 0, 0)); J.CreateLocalRot1Attr().Set(Gf.Quatf(1, 0, 0, 0))
        is_root = link_prim.GetPath() == art_root_prim.GetPath()
        if is_root:  # Isaac Lab fix_root_link 방식: 루트 API를 부모로 옮겨 PhysX가 고정 베이스 articulation으로 파싱하게 한다
            parent = art_root_prim.GetParent(); UsdPhysics.ArticulationRootAPI.Apply(parent)
            try:
                from pxr import PhysxSchema; PhysxSchema.PhysxArticulationAPI.Apply(parent)
                for attr in art_root_prim.GetAttributes():
                    if attr.GetName().startswith("physxArticulation:") and attr.HasAuthoredValue(): parent.CreateAttribute(attr.GetName(), attr.GetTypeName()).Set(attr.Get())
                art_root_prim.RemoveAPI(PhysxSchema.PhysxArticulationAPI)
            except Exception as ex: res["fix_physx_api_note"] = str(ex)
            art_root_prim.RemoveAPI(UsdPhysics.ArticulationRootAPI); art_root_path = parent.GetPath().pathString
        else:        # 루트가 아닌 링크(골반): articulation 밖의 world 구속으로 잡는다(관절 트리는 그대로)
            J.GetPrim().CreateAttribute("physics:excludeFromArticulation", Sdf.ValueTypeNames.Bool).Set(True); art_root_path = art_root_prim.GetPath().pathString
    fix_res.update({"fixed_link": link_name, "mode": "fixed-base articulation (root API moved to parent)" if is_root else "world constraint joint (excludeFromArticulation)", "joint_prim": J.GetPath().pathString,
                    "anchor_world_pos": [round(float(v), 4) for v in pos], "anchor_world_quat_wxyz": [round(rot.GetReal(), 4)] + [round(float(v), 4) for v in rot.GetImaginary()]}); fixL.Save()
else: art_root_path = art_root_prim.GetPath().pathString
res["pelvis_fix"] = fix_res
# ---- (레이어 2) 외형: 링크별 UsdPreviewSurface를 visuals 스코프에 strongerThanDescendants 바인딩(충돌·질량·관절 무관)
appL = new_sublayer("igris_appearance.usda"); res["layers"]["appearance"] = appL.identifier; app_stats = {}
with Usd.EditContext(stage, Usd.EditTarget(appL)):
    mats = {}
    for cname, c in APP["classes"].items():
        mat = UsdShade.Material.Define(stage, Sdf.Path(f"/World/Looks/IGRIS/{cname}")); sh = UsdShade.Shader.Define(stage, Sdf.Path(f"/World/Looks/IGRIS/{cname}/Shader")); sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*[float(v) for v in c["diffuse"]])); sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(c["roughness"])); sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(c["metallic"]))
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface"); mats[cname] = mat
    for lk in [p for p in Usd.PrimRange(robot) if p.HasAPI(UsdPhysics.RigidBodyAPI)]:
        cls = next((c for pat, c in APP["links"] if re.search(pat, lk.GetName())), None)
        if cls is None: app_stats.setdefault("unmapped", []).append(lk.GetName()); continue
        vis = lk.GetChild("visuals"); target = vis if vis.IsValid() else lk
        UsdShade.MaterialBindingAPI.Apply(target).Bind(mats[cls], bindingStrength=UsdShade.Tokens.strongerThanDescendants); app_stats[cls] = app_stats.get(cls, 0) + 1
appL.Save(); res["appearance"] = {"enabled": bool(app_on), "config": ig.get("appearance_config", "~/igris_ws/config/igris_appearance.yaml"), "links_per_class": app_stats, "reference_photos": APP.get("unmodeled") and "see config"}
if not app_on: stage.MuteLayer(appL.identifier)
# ---- (레이어 3) RGB 카메라 4개: 링크 자식 Camera prim (config/igris_cameras.yaml)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import igris_cameras as IC
CAMCFG = yaml.safe_load(open(os.path.expanduser(ig.get("cameras_config", "~/igris_ws/config/igris_cameras.yaml")))); cam_on = CAMCFG.get("enabled", True) if a.cameras is None else a.cameras
cam_specs = []; cam_sensors = {}
if cam_on:
    camL = new_sublayer("igris_cameras.usda"); res["layers"]["cameras"] = camL.identifier; cam_specs = IC.author(stage, camL, ig["prim"], IC.build_specs(CAMCFG))
res["placement"] = {"g1_slot_pos": g1["pos"], "g1_slot_rot_wxyz": g1["rot"], "igris_base_pos": [gx, gy, round(base_z, 4)], "igris_yaw_deg": round(math.degrees(yaw), 2),
                    "rule": "x,y,yaw from G1 slot (+xy_offset); z = floor_z(raycast) + standing_base_height + clearance (G1 z not copied)"}
scene_usda = os.path.join(scene_dir, "igris_in_vla_scene.usda"); stage.GetRootLayer().Export(scene_usda); res["scene_layer"] = scene_usda
roots = [art_root_path]; art = SingleArticulation(prim_path=roots[0], name="igris_c"); world.scene.add(art); world.reset()
names = list(art.dof_names); q0 = np.zeros(len(names), dtype=np.float32)
for i, n in enumerate(names):
    for pat, v in ig.get("init_joint_pos", {}).items():
        if re.fullmatch(pat, n): q0[i] = float(v)
def reset_pose():
    if not fix_on: art.set_world_pose(position=np.array([gx, gy, base_z]), orientation=np.array(qyaw)); art.set_linear_velocity(np.zeros(3)); art.set_angular_velocity(np.zeros(3))
    art.set_joint_positions(q0); art.set_joint_velocities(np.zeros_like(q0))
ctrl = art.get_articulation_controller(); kp, kd = [np.array(v, dtype=np.float32).copy() for v in ctrl.get_gains()]; matched = 0
for i, n in enumerate(names):
    for pat, (p_, d_) in ig.get("pd_gains", {}).items():
        if re.fullmatch(pat, n): kp[i], kd[i] = float(p_), float(d_); matched += 1; break
ctrl.set_gains(kps=kp, kds=kd); reset_pose(); art.apply_action(ArticulationAction(joint_positions=q0))
res["load"] = {"igris_usd": IGRIS_USD, "articulation_root": roots[0], "num_dof": int(art.num_dof), "pd_gain_joints": matched,
               "env_prims": {e["prim"]: sum(1 for _ in Usd.PrimRange(stage.GetPrimAtPath(e["prim"]), Usd.TraverseInstanceProxies())) for e in cfg["environment"]},
               "mesh_prims_total": sum(1 for p in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh))}
if cam_on:
    cam_sensors = IC.make_sensors(stage, camL, cam_specs); res["cameras"] = {"config": ig.get("cameras_config", "~/igris_ws/config/igris_cameras.yaml"), "specs": cam_specs, "captures": {}}
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
    VP_CHOICE = {sp["role"]: sp["prim_path"] for sp in cam_specs if sp["output"] == "official"}
    def shot(name, eye, target):
        set_camera_view(eye=eye, target=target, camera_prim_path=cam["prim"])
        for _ in range(30): app.update()
        f = os.path.join(a.out, f"igris_vla_scene_{a.tag}_{name}.png"); capture_viewport_to_file(vp, f)
        for _ in range(10): app.update()
        shots.append(f)
    if app_on:  # 같은 시점·조명에서 외형 전(레이어 mute)/후 비교
        stage.MuteLayer(appL.identifier); shot("before_appearance_front", cam["eye"], cam["target"]); shot("before_appearance_diag", cfg["extra_views"][0]["eye"], cfg["extra_views"][0]["target"]); stage.UnmuteLayer(appL.identifier)
    shot("init_front", cam["eye"], cam["target"])
    for v in cfg.get("extra_views", []): shot(f"init_{v['name']}", v["eye"], v["target"])
except Exception as ex: vp = None; res["viewport_error"] = str(ex)
if app_on:  # 레이어 mute/unmute는 스테이지 재구성을 일으켜 물리 텐서 뷰가 무효화된다 → 다시 초기화
    world.reset(); ctrl = art.get_articulation_controller(); ctrl.set_gains(kps=kp, kds=kd); reset_pose(); art.apply_action(ArticulationAction(joint_positions=q0)); world.step(render=True); world.pause()
# ---- 기본 물리
def tilt(q): return float(np.degrees(np.arccos(np.clip(1 - 2 * (float(q[1]) ** 2 + float(q[2]) ** 2), -1, 1))))
series = []; peak = vram()[0]
if not a.freeze:
    world.play(); steps = int(a.secs * 50); tw = time.time(); obj = stage.GetPrimAtPath(cfg["environment"][1]["prim"]) if len(cfg["environment"]) > 1 else None
    AT = ig.get("arm_test", {}); arm_on = AT.get("enabled", False) if a.arm_test is None else a.arm_test
    arm_idx = [i for i, n in enumerate(names) if any(re.fullmatch(p, n) for p in AT.get("joints", []))]; amp = float(AT.get("amplitude_rad", 0.4)); freq = float(AT.get("freq_hz", 0.3)); arm_log = []
    fixed_prim = stage.GetPrimAtPath(art_root_path if fix_res.get("fixed_link") is None else next(p.GetPath().pathString for p in Usd.PrimRange(robot) if p.GetName() == fix_res["fixed_link"])) if fix_on else None
    drift = []
    class _UsdPose:  # 물리→USD 변환 갱신을 읽는다(별도 RigidPrim 뷰를 만들면 articulation 텐서 뷰가 무효화되므로 사용하지 않음)
        def __init__(self, prim): self.prim = prim
        def get_world_pose(self):
            M = UsdGeom.Xformable(self.prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).RemoveScaleShear(); q = M.ExtractRotationQuat(); return np.array(M.ExtractTranslation()), np.array([q.GetReal(), *q.GetImaginary()])
    fixed_rp = _UsdPose(fixed_prim) if fixed_prim is not None else None
    cap_dir = os.path.join(a.out, "cameras"); moving_k = int(round(float(CAMCFG.get("capture", {}).get("moving_frame_time_s", 0.83))*50)); cap_frames = {}
    def cam_capture(label):
        if not cam_on: return
        for _ in range(6): app.update()
        fr = IC.capture(cam_sensors, cam_specs, float(CAMCFG.get("capture", {}).get("self_occlusion_depth_m", 0.03))); files = IC.save(fr, cam_specs, cap_dir, f"{a.tag}_{label}", CAMCFG)
        landmarks = {"mug": cfg["environment"][1]["prim"], "table": cfg["environment"][0]["prim"]}
        for side, pre in (("left", "l"), ("right", "r")): landmarks.update({f"{pre}_index_tip": f'{ig["prim"]}/{pre}_index_distal', f"{pre}_thumb_tip": f'{ig["prim"]}/{pre}_thumb_distal', f"{side}_hand": f'{ig["prim"]}/{side.capitalize()}_Hand'})
        proj = {sp["name"]: IC.project_points(stage, sp, landmarks, ig["prim"]) for sp in cam_specs if sp["output"] == "official"}
        res["cameras"]["captures"][label] = {"t_sim": round(float(k_now)/50.0, 2), "stats": {n: {k: v for k, v in st.items() if k != "_depth"} for n, (_, st) in fr.items()}, "files": files, "landmark_pixels": proj}; cap_frames[label] = {n: img for n, (img, _) in fr.items()}
    k_now = 0; cam_capture("static")
    for k in range(steps):
        k_now = k + 1
        if arm_on and arm_idx:
            tgt = q0.copy(); tgt[arm_idx] = q0[arm_idx] + amp * math.sin(2 * math.pi * freq * (k + 1) / 50.0); art.apply_action(ArticulationAction(joint_positions=tgt))
        world.step(render=True)
        if fixed_rp is not None and (k % 10 == 0 or k == steps - 1):
            fp, fq = fixed_rp.get_world_pose(); ap_ = np.array(fix_res["anchor_world_pos"]); aq = np.array(fix_res["anchor_world_quat_wxyz"]); dq = abs(float(np.dot(aq, np.array(fq, dtype=float))))
            drift.append({"t": round((k + 1) / 50.0, 2), "pos_err_m": round(float(np.linalg.norm(np.array(fp, dtype=float) - ap_)), 5), "ang_err_deg": round(float(np.degrees(2 * np.arccos(min(1.0, dq)))), 4)})
        if arm_on and arm_idx and (k % 10 == 0 or k == steps - 1):
            qj = art.get_joint_positions(); arm_log.append({"t": round((k + 1) / 50.0, 2), "q": [round(float(qj[i]), 3) for i in arm_idx]})
        if k + 1 == moving_k: cam_capture("moving")
        if k == steps - 1: cam_capture("end")
        if k % 25 == 0 or k == steps - 1:
            p, q = art.get_world_pose(); qd = art.get_joint_velocities(); peak = max(peak, vram()[0]); lows = sorted((aabb(l)[0][2], l.GetName()) for l in links); zmin = lows[0][0]; lowest = lows[0][1]
            series.append({"t": round((k + 1) / 50.0, 2), "base_z": round(float(p[2]), 4), "robot_zmin_minus_floor": round(zmin - floor_z, 4), "tilt_deg": round(tilt(q), 2),
                           "max_abs_qd": round(float(np.abs(qd).max()), 3), "lowest_link": lowest, "finite": bool(np.isfinite(qd).all() and np.isfinite(p).all())})
    wall = time.time() - tw; pen = min(s["robot_zmin_minus_floor"] for s in series); up = [s for s in series if s["tilt_deg"] < 20]
    res["physics"] = {"sim_secs": a.secs, "wall_secs": round(wall, 2), "realtime_factor": round(a.secs / wall, 2), "all_finite": all(s["finite"] for s in series),
                      "min_zmin_minus_floor_while_upright": min([s["robot_zmin_minus_floor"] for s in up], default=None), "min_zmin_minus_floor_overall": pen,
                      "base_keeps_sinking": bool(len(series) > 3 and series[-1]["base_z"] < series[-3]["base_z"] - 0.005), "note_zmin": "zmin은 시각 메시 AABB 기준(충돌 형상은 단순화되어 있어 넘어진 뒤 수 cm 차이 가능)", "table_aabb_after": aabb(stage.GetPrimAtPath(cfg["environment"][0]["prim"])),
                      "object_aabb_after": aabb(obj) if obj else None, "series": series}
    if fixed_rp is not None: res["pelvis_fix"]["hold_check"] = {"secs": a.secs, "max_pos_err_m": max(d["pos_err_m"] for d in drift), "max_ang_err_deg": max(d["ang_err_deg"] for d in drift), "samples": len(drift), "tolerance": {"pos_m": float(FIX.get("hold_tolerance", {}).get("pos_m", 0.005)), "ang_deg": float(FIX.get("hold_tolerance", {}).get("ang_deg", 1.0))},
                                                            "held": bool(max(d["pos_err_m"] for d in drift) < float(FIX.get("hold_tolerance", {}).get("pos_m", 0.005)) and max(d["ang_err_deg"] for d in drift) < float(FIX.get("hold_tolerance", {}).get("ang_deg", 1.0)))}
    if arm_on and arm_idx:
        qs = np.array([r["q"] for r in arm_log]); res["arm_test"] = {"joints": [names[i] for i in arm_idx], "commanded_amplitude_rad": amp, "freq_hz": freq, "observed_range_rad": [round(float(v), 3) for v in (qs.max(0) - qs.min(0))], "moved": bool((qs.max(0) - qs.min(0)).min() > 0.5 * amp), "samples": arm_log[::10]}
    if cam_on and "static" in cap_frames and "moving" in cap_frames:
        ver = {}
        for sp in cam_specs:
            n = sp["name"]; a0, a1 = cap_frames["static"].get(n), cap_frames["moving"].get(n); st0 = res["cameras"]["captures"]["static"]["stats"][n]; st1 = res["cameras"]["captures"]["moving"]["stats"][n]
            diff = None if a0 is None or a1 is None else round(float(np.abs(a0.astype(int) - a1.astype(int)).mean()), 2)
            ver[n] = {"rendered": a0 is not None and st0["std"] is not None and st0["std"] > 2.0, "not_black": st0["dark_frac"] is not None and st0["dark_frac"] < 0.5, "updates_between_poses": diff is not None and diff > 1.0, "mean_abs_diff_static_vs_moving": diff,
                      "self_occlusion_frac_static": st0.get("self_occlusion_frac"), "self_occlusion_frac_moving": st1.get("self_occlusion_frac"), "depth_min_m_static": st0.get("depth_min_m")}
            ver[n]["PASS"] = bool(ver[n]["rendered"] and ver[n]["not_black"] and ver[n]["updates_between_poses"] and (ver[n]["self_occlusion_frac_static"] or 0) < 0.15)   # 손: 화면 가장자리 손바닥 셸(2–3 cm) 7–8% 허용, 근거 docs/SETUP.md §10
        res["cameras"]["verdict"] = ver
    res["balance_observation"] = {"upright_at_end": bool(series[-1]["tilt_deg"] < 20 and series[-1]["base_z"] > floor_z + 0.8 * stand), "note": "성공 기준 아님(균형 제어기 없음, 초기자세 PD 유지뿐)"}
    if vp is not None: shot("after_physics", cam["eye"], cam["target"])
res["vram_mib"] = {"peak_during_run": peak, "total": vram()[1]}; res["screenshots"] = shots; res["elapsed_s"] = round(time.time() - t0, 1)
js = os.path.join(a.out, f"igris_vla_scene_{a.tag}.json"); json.dump(res, open(js, "w"), indent=1, default=str); print("RESULT_JSON", js, flush=True)
if a.hold > 0:                                                                                      # 사용자가 직접 확인: 초기 배치로 되돌려 멈춘 채 창을 열어 둔다(Play로 물리 재생 가능)
    reset_pose(); world.pause(); set_camera_view(eye=cam["eye"], target=cam["target"], camera_prim_path=cam["prim"])
    if a.viewport_camera != "scene" and vp is not None and a.viewport_camera in VP_CHOICE: vp.camera_path = VP_CHOICE[a.viewport_camera]; print("[viewport]", VP_CHOICE[a.viewport_camera], flush=True)
    th = time.time()
    while time.time() - th < a.hold and app.is_running(): app.update()
app.close()
