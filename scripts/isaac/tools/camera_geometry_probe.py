"""IGRIS-C USD 시각 메시 기준 카메라 기하 점검(읽기 전용). 공식 카메라 포즈(robot_cfg.py)를 링크 좌표계로 놓고
  1) 광학 중심이 메시 내부인지, 2) 광축 전방 첫 충돌 거리, 3) FOV 격자 근접 가림 비율, 4) 눈/손바닥 구멍 탐색용 깊이맵(PNG)을 만든다.
실행: source scripts/env_isaac.sh && python scripts/isaac/tools/camera_geometry_probe.py <robot.usd> <outdir>"""
import json, math, os, sys, time
import numpy as np
from isaacsim import SimulationApp
app = SimulationApp({"headless": True})
from pxr import Usd, UsdGeom, Gf
from PIL import Image
usd, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True); stage = Usd.Stage.Open(usd); xc = UsdGeom.XformCache(Usd.TimeCode.Default())
def q2R(w, x, y, z):
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def qmul(a, b):
    aw, ax, ay, az = a; bw, bx, by, bz = b; return (aw*bw-ax*bx-ay*by-az*bz, aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw)
def axis_angle(axis, deg):
    h = math.radians(deg)/2; n = math.sqrt(sum(c*c for c in axis)); s = math.sin(h)/n; return (math.cos(h), axis[0]*s, axis[1]*s, axis[2]*s)
def link_mesh(link):
    Minv = np.array(xc.GetLocalToWorldTransform(link).GetInverse()); V = []; F = []; n0 = 0
    for p in Usd.PrimRange(link, Usd.TraverseInstanceProxies()):
        if not p.IsA(UsdGeom.Mesh) or "collision" in p.GetPath().pathString.lower(): continue
        if any(s in ("collisions",) for s in p.GetPath().pathString.split("/")): continue
        m = UsdGeom.Mesh(p); pts = np.array(m.GetPointsAttr().Get()); M = np.array(xc.GetLocalToWorldTransform(p)) @ Minv
        pl = (np.c_[pts, np.ones(len(pts))] @ M)[:, :3]; cnt = np.array(m.GetFaceVertexCountsAttr().Get()); idx = np.array(m.GetFaceVertexIndicesAttr().Get()); k = 0
        for c in cnt:
            for t in range(1, c-1): F.append((idx[k]+n0, idx[k+t]+n0, idx[k+t+1]+n0))
            k += c
        V.append(pl); n0 += len(pl)
    V = np.vstack(V); F = np.array(F); return V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
def raycast(T, O, D, tmax=10.0):  # Möller–Trumbore, 배치 광선 → 첫 충돌 거리(없으면 inf)와 충돌 횟수
    A, B, C = T; e1 = B-A; e2 = C-A; best = np.full(len(O), np.inf); cnt = np.zeros(len(O), int)
    for s in range(0, len(O), 256):
        o = O[s:s+256][:, None, :]; d = D[s:s+256][:, None, :]
        pv = np.cross(d, e2[None]); det = np.einsum("ijk,ijk->ij", e1[None].repeat(len(o), 0), pv); ok = np.abs(det) > 1e-12; inv = np.where(ok, 1.0/np.where(ok, det, 1), 0)
        tv = o - A[None]; u = np.einsum("ijk,ijk->ij", tv, pv)*inv; qv = np.cross(tv, e1[None]); v = np.einsum("ijk,ijk->ij", d.repeat(e1.shape[0], 1), qv)*inv; t = np.einsum("ijk,ijk->ij", e2[None].repeat(len(o), 0), qv)*inv
        hit = ok & (u >= 0) & (v >= 0) & (u+v <= 1) & (t > 1e-6) & (t < tmax); t = np.where(hit, t, np.inf); best[s:s+256] = t.min(1); cnt[s:s+256] = hit.sum(1)
    return best, cnt
# 공식 카메라 정의(robot_cfg.py). 광축/상/우 벡터를 링크 좌표계로: ROS(z 전방, x 우, y 하) / world(x 전방, y 좌, z 상)
def cam_axes(rot, conv):
    R = q2R(*rot); return (R @ [0, 0, 1], R @ [0, -1, 0], R @ [1, 0, 0]) if conv == "ros" else (R @ [1, 0, 0], R @ [0, 0, 1], R @ [0, -1, 0])
base = (0.5, -0.5, 0.5, -0.5)
CAMS = {"LeftRgbCamera": ("Link_Neck_Pitch", (0.095516, 0.026076, 0.121), qmul(axis_angle((0, 0, 1), 14.0), base), "ros", (433.3, 433.3, 320, 240, 640, 480)),
        "RightRgbCamera": ("Link_Neck_Pitch", (0.095516, -0.026076, 0.121), qmul(axis_angle((0, 0, 1), -14.0), base), "ros", (433.3, 433.3, 320, 240, 640, 480)),
        "l_hand_camera_link": ("Left_Hand", (-0.024420, 0.010317, 0.034793), (0.281491451510162, -0.813343087073706, -0.479715245579771, -0.170613213422809), "world", (115.669608, 115.546655, 159.669481, 96.948254, 320, 200)),
        "r_hand_camera_link": ("Right_Hand", (-0.024420, -0.010317, 0.034793), (0.280192038750642, 0.813790055664715, -0.479987262874607, 0.169854037927043), "world", (115.459869, 115.422582, 157.159381, 91.929442, 320, 200))}
links = {p.GetName(): p for p in stage.Traverse() if p.GetName() in ("Link_Neck_Pitch", "Left_Hand", "Right_Hand")}; res = {"usd": usd, "links": {k: v.GetPath().pathString for k, v in links.items()}}
meshes = {k: link_mesh(v) for k, v in links.items()}; res["triangles"] = {k: int(len(m[0])) for k, m in meshes.items()}
for name, (lk, pos, rot, conv, (fx, fy, cx, cy, W, H)) in CAMS.items():
    T = meshes[lk]; d, u, r = cam_axes(rot, conv); d /= np.linalg.norm(d); u /= np.linalg.norm(u); r /= np.linalg.norm(r)
    off = float(os.environ.get("PROBE_AXIAL_OFFSET_HAND" if lk != "Link_Neck_Pitch" else "PROBE_AXIAL_OFFSET_HEAD", "0")); c = np.array(pos) + off*d
    fwd, nf = raycast(T, c[None], d[None]); back, nb = raycast(T, c[None], -d[None]); inside = bool((nf[0] % 2) == 1)
    # FOV 격자(21x15) 근접 가림
    us = (np.linspace(0, W-1, 21)-cx)/fx; vs = (np.linspace(0, H-1, 15)-cy)/fy; D = np.array([(d + a*r - b*u) for b in vs for a in us]); D /= np.linalg.norm(D, axis=1, keepdims=True)
    t, _ = raycast(T, np.repeat(c[None], len(D), 0), D); near = t < 0.15; fin = np.isfinite(t)
    hist = {f"<{x*100:.0f}cm": round(float((t < x).mean()), 3) for x in (0.005, 0.01, 0.02, 0.03, 0.05, 0.10)}
    info = {"axial_offset_applied_m": off, "fov_grid_selfhit_frac_by_dist": hist, "link": lk, "prim_path": f"{res['links'][lk]}/{name}", "pos_link": pos, "rot_wxyz_conv": [round(v, 6) for v in rot], "convention": conv, "optical_axis_link": [round(v, 4) for v in d], "up_link": [round(v, 4) for v in u], "right_link": [round(v, 4) for v in r],
            "center_inside_mesh": inside, "hits_fwd": int(nf[0]), "hits_back": int(nb[0]), "first_hit_fwd_m": None if np.isinf(fwd[0]) else round(float(fwd[0]), 4), "first_hit_back_m": None if np.isinf(back[0]) else round(float(back[0]), 4),
            "fov_grid_blocked_within_0.15m_frac": round(float(near.mean()), 3), "fov_grid_min_hit_m": None if np.isinf(t.min()) else round(float(t.min()), 4), "fov_grid_max_hit_m": None if np.isinf(t[np.isfinite(t)].max()) else round(float(t[np.isfinite(t)].max()), 4), "fov_grid_nohit_frac": round(float(np.isinf(t).mean()), 3), "hfov_deg": round(2*math.degrees(math.atan(W/2/fx)), 1), "vfov_deg": round(2*math.degrees(math.atan(H/2/fy)), 1)}
    # 구멍 탐색 깊이맵: 광축에 수직인 면(±ext) 격자에서 전방 0.25 m 지점으로부터 -d 방향으로 광선 → 첫 충돌까지의 '깊이'(표면 뒤로 들어간 정도)
    ext, step = (0.06, 0.0008) if lk == "Link_Neck_Pitch" else (0.03, 0.0005); n = int(2*ext/step)+1; g = np.linspace(-ext, ext, n)
    O = np.array([c + 0.25*d + a*r + b*u for b in g[::-1] for a in g]); t2, _ = raycast(T, O, np.repeat(-d[None], len(O), 0), tmax=0.5)
    depth = 0.25 - t2; depth[np.isinf(t2)] = np.nan  # 표면의 광축상 위치(카메라 중심 기준, +는 중심보다 앞)
    dm = depth.reshape(n, n); finite = np.isfinite(dm); ref = np.nanpercentile(dm, 60) if finite.any() else 0
    img = np.zeros((n, n, 3), np.uint8); v = np.clip((dm - (ref-0.02))/0.04, 0, 1); img[..., 0] = img[..., 1] = img[..., 2] = (v*255).astype(np.uint8); img[~finite] = (255, 0, 255)
    cc = n//2; img[cc-1:cc+2, :, :] = (0, 255, 0); img[:, cc-1:cc+2, :] = (0, 255, 0)  # 녹색 십자 = 공식 광학 중심
    Image.fromarray(img).resize((n*3, n*3), Image.NEAREST).save(f"{out}/{name}_depthmap.png")
    info["depthmap"] = {"png": f"{out}/{name}_depthmap.png", "extent_m": ext, "step_m": step, "legend": "밝을수록 광축 방향으로 카메라 중심보다 앞(표면), 어두울수록 뒤(구멍/함몰), 마젠타=미충돌(관통), 녹색 십자=공식 중심",
                        "surface_axial_at_center_m": None if not np.isfinite(dm[cc, cc]) else round(float(dm[cc, cc]), 4), "through_hole_pixels": int((~finite).sum())}
    res[name] = info; print(name, {k: info[k] for k in ("center_inside_mesh", "first_hit_fwd_m", "fov_grid_blocked_within_0.15m_frac", "fov_grid_min_hit_m")}, flush=True)
try:
    import omni.usd.schema.omni_lens_distortion as lds; res["lens_distortion_module"] = os.path.dirname(lds.__file__)
except Exception as ex: res["lens_distortion_module"] = f"unavailable: {ex}"
try:
    import isaacsim.sensors.camera as sc; res["isaacsim_sensors_camera"] = "ok"
except Exception as ex: res["isaacsim_sensors_camera"] = f"unavailable: {ex}"
json.dump(res, open(f"{out}/probe.json", "w"), indent=1); print("WROTE", f"{out}/probe.json", flush=True); os._exit(0)
