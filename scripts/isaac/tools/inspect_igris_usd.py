"""IGRIS USD 조사: 루트 바디/관절 트리, 재질·바인딩·텍스처·displayColor. 읽기 전용."""
import json, os, sys
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade
usd = sys.argv[1]; stage = Usd.Stage.Open(usd); out = {"usd": usd, "layers": [l.identifier.split("/usd/")[-1] for l in stage.GetUsedLayers()]}
dp = stage.GetDefaultPrim(); out["default_prim"] = dp.GetPath().pathString
roots = [p.GetPath().pathString for p in stage.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)]; out["articulation_root"] = roots
joints = [p for p in stage.Traverse() if p.IsA(UsdPhysics.Joint)]; tree = {}
for j in joints:
    J = UsdPhysics.Joint(j); b0 = [t.name for t in J.GetBody0Rel().GetTargets()]; b1 = [t.name for t in J.GetBody1Rel().GetTargets()]; tree.setdefault(b0[0] if b0 else "WORLD", []).append(f"{j.GetName()}[{j.GetTypeName().replace('Physics','')}]->{b1[0] if b1 else '?'}")
out["root_children"] = tree.get("base_link", []); out["world_joints"] = tree.get("WORLD", []); out["joint_types"] = {}
for j in joints: out["joint_types"][j.GetTypeName()] = out["joint_types"].get(j.GetTypeName(), 0) + 1
bodies = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]; out["rigid_bodies"] = len(bodies)
bl = stage.GetPrimAtPath(roots[0]) if roots else None
if bl: out["root_mass"] = UsdPhysics.MassAPI(bl).GetMassAttr().Get() if bl.HasAPI(UsdPhysics.MassAPI) else None
mats = [p for p in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()) if p.IsA(UsdShade.Material)]; out["materials"] = []
for m in mats[:40]:
    info = {"path": m.GetPath().pathString[-70:]}
    for sh in Usd.PrimRange(m):
        if sh.IsA(UsdShade.Shader):
            S = UsdShade.Shader(sh); info["shader_id"] = S.GetIdAttr().Get() or str(S.GetSourceAsset("mdl")) ; info["inputs"] = {i.GetBaseName(): str(i.Get())[:60] for i in S.GetInputs()}
    out["materials"].append(info)
meshes = [p for p in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh)]; vis = []; bound = 0; dc = 0
for m in meshes:
    purpose = UsdGeom.Imageable(m).ComputePurpose(); mat, rel = UsdShade.MaterialBindingAPI(m).ComputeBoundMaterial(); col = UsdGeom.Gprim(m).GetDisplayColorAttr().Get()
    bound += bool(mat); dc += bool(col); path = m.GetPath().pathString
    if "collision" not in path.lower() and len(vis) < 400: vis.append({"mesh": path.replace(out["default_prim"], "")[-80:], "purpose": purpose, "material": mat.GetPath().pathString[-50:] if mat else None, "displayColor": [round(c, 3) for c in col[0]] if col else None})
out["mesh_count"] = len(meshes); out["meshes_with_bound_material"] = bound; out["meshes_with_displayColor"] = dc; out["visual_meshes"] = vis
json.dump(out, open(sys.argv[2], "w"), indent=1); print("WROTE", sys.argv[2]); app.close()
