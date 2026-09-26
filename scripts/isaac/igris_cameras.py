"""IGRIS-C RGB 카메라 4개(머리 좌/우 눈, 좌/우 손바닥) — 공식 robot_cfg.py 값 기반. config/igris_cameras.yaml 로 정의.
- 별도 override 레이어(igris_cameras.usda)에 링크 자식 Camera prim 작성 → 링크를 따라 움직임. 로봇 USD·물리 무변경.
- isaacsim.sensors.camera.Camera 로 렌더/캡처(RGB + distance_to_image_plane), 자기 메시 가림·프레임 갱신 통계, PNG/4분할 저장.
- 손 카메라 학습용 640×480 출력(extend/letterbox)과 머리 좌|우 결합 cam_head(1280×480)."""
import math, os
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom
M_ROS = np.diag([1.0, -1.0, -1.0])                                 # USD 카메라(x우,y상,-z전방) → ROS 광학(x우,y하,z전방)
M_WORLD = np.array([[0, 0, -1.0], [-1.0, 0, 0], [0, 1.0, 0]])      # USD 카메라 → world(x전방,y좌,z상)
def q2R(q):
    w, x, y, z = q; return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def R2q(R):
    m = Gf.Matrix3d(*[float(v) for v in R.T.reshape(-1)]); q = m.ExtractRotation().GetQuat(); return (q.GetReal(), *q.GetImaginary())  # Gf는 row-vector 규약 → 전치
def qmul(a, b):
    aw, ax, ay, az = a; bw, bx, by, bz = b; return (aw*bw-ax*bx-ay*by-az*bz, aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw)
def axis_angle(axis, deg):
    h = math.radians(deg)/2; n = math.sqrt(sum(c*c for c in axis)); s = math.sin(h)/n; return (math.cos(h), axis[0]*s, axis[1]*s, axis[2]*s)
def conv_to_usd(rot, conv):
    R = q2R(rot); d = R @ ([0, 0, 1] if conv == "ros" else [1, 0, 0]); Rusd = R @ (M_ROS if conv == "ros" else M_WORLD); return R2q(Rusd), d / np.linalg.norm(d)
def fov(fx, fy, W, H): return round(2*math.degrees(math.atan(W/2/fx)), 1), round(2*math.degrees(math.atan(H/2/fy)), 1)
def build_specs(cfg):
    specs = []
    for side in ("left", "right"):
        h = cfg["head"][side]; rm = h["rot_mode"]; rot = qmul(axis_angle(rm["axis"], rm["deg"]), tuple(rm["base"])); q, d = conv_to_usd(rot, h["convention"]); pos = np.array(h["official_pos"]) + h["axial_offset_m"]*d
        specs.append(dict(role=f"head_{side}", name=h["prim"], link=h["link"], W=h["width"], H=h["height"], intr=list(h["intrinsic"]), dist=list(h["distortion"]), clip=list(h["clipping"]), official_pos=list(h["official_pos"]), pos=[round(float(v), 6) for v in pos],
                          axial_offset_m=h["axial_offset_m"], rot_conv=[round(v, 6) for v in rot], convention=h["convention"], q_usd=[round(float(v), 6) for v in q], optical_axis_link=[round(float(v), 4) for v in d], output="official"))
    tr = cfg["hands"].get("train_output", {"mode": "none"})
    for side in ("left", "right"):
        h = cfg["hands"][side]; rot = tuple(h["rot"]); q, d = conv_to_usd(rot, h["convention"]); pos = np.array(h["official_pos"]) + h["axial_offset_m"]*d
        base = dict(role=f"hand_{side}", link=h["link"], clip=list(h["clipping"]), official_pos=list(h["official_pos"]), pos=[round(float(v), 6) for v in pos], axial_offset_m=h["axial_offset_m"], rot_conv=[round(v, 6) for v in rot], convention=h["convention"], q_usd=[round(float(v), 6) for v in q], optical_axis_link=[round(float(v), 4) for v in d], dist=list(h["distortion"]))
        specs.append(dict(base, name=h["prim"], W=h["width"], H=h["height"], intr=list(h["intrinsic"]), output="official"))
        if tr.get("mode", "none") != "none":
            fx, fy, cx, cy = h["intrinsic"]; s = tr["width"]/h["width"]; Wt, Ht = tr["width"], tr["height"]
            if tr["mode"] == "extend": intr = [fx*s, fy*s, cx*s, cy*s + (Ht - h["height"]*s)/2]; Hr = Ht
            else: intr = [fx*s, fy*s, cx*s, cy*s]; Hr = int(round(h["height"]*s))          # letterbox: 640×400 렌더 후 패딩
            specs.append(dict(base, name=f'{h["prim"]}_train', W=Wt, H=Hr, intr=[round(v, 4) for v in intr], output=f'train_{tr["mode"]}', pad_to=(Wt, Ht), dataset_key=tr["names"][side]))
    for s in specs: s["hfov_deg"], s["vfov_deg"] = fov(s["intr"][0], s["intr"][1], s["W"], s["H"])
    return specs
def author(stage, layer, robot_path, specs):
    """카메라 prim을 링크 자식으로 작성(레이어 layer). 내부 파라미터 → focalLength 24 + aperture. cx,cy 오프셋은 OpenCV pinhole API(센서 생성 시)로 준다."""
    with Usd.EditContext(stage, Usd.EditTarget(layer)):
        for s in specs:
            path = Sdf.Path(f'{robot_path}/{s["link"]}/{s["name"]}'); assert stage.GetPrimAtPath(path.GetParentPath()).IsValid(), f"link prim missing: {path.GetParentPath()}"
            cam = UsdGeom.Camera.Define(stage, path); p = cam.GetPrim(); fx, fy, cx, cy = s["intr"]; FL = 24.0
            cam.CreateFocalLengthAttr(FL); cam.CreateHorizontalApertureAttr(FL*s["W"]/fx); cam.CreateVerticalApertureAttr(FL*s["H"]/fy); cam.CreateHorizontalApertureOffsetAttr(0.0); cam.CreateVerticalApertureOffsetAttr(0.0)
            cam.CreateClippingRangeAttr(Gf.Vec2f(*[float(v) for v in s["clip"]])); cam.CreateProjectionAttr("perspective")
            xf = UsdGeom.Xformable(p); xf.ClearXformOpOrder(); xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*[float(v) for v in s["pos"]])); w, x, y, z = s["q_usd"]; xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(w, x, y, z))
            p.SetCustomDataByKey("igris_sim:camera_role", s["role"]); p.SetCustomDataByKey("igris_sim:output", s["output"]); s["prim_path"] = path.pathString
    layer.Save(); return specs
def make_sensors(stage, layer, specs):
    from isaacsim.sensors.camera import Camera
    sensors = {}
    for s in specs:
        cam = Camera(prim_path=s["prim_path"], resolution=(s["W"], s["H"])); cam.initialize(); cam.add_distance_to_image_plane_to_frame()
        fx, fy, cx, cy = s["intr"]
        with Usd.EditContext(stage, Usd.EditTarget(layer)):
            if any(abs(v) > 1e-12 for v in s["dist"]): cam.set_opencv_pinhole_properties(cx=cx, cy=cy, fx=fx, fy=fy, pinhole=list(s["dist"]) + [0.0]*(12-len(s["dist"]))); s["lens_model"] = "opencvPinhole"
            else: s["lens_model"] = "pinhole"
        layer.Save(); sensors[s["name"]] = cam
    return sensors
def capture(sensors, specs, self_occ_m=0.03):
    frames = {}
    for s in specs:
        cam = sensors[s["name"]]; rgba = cam.get_rgba(); fr = cam.get_current_frame(); depth = fr.get("distance_to_image_plane")
        rgb = np.asarray(rgba)[..., :3].copy() if rgba is not None and np.asarray(rgba).size else None; d = np.asarray(depth) if depth is not None and np.asarray(depth).size else None
        st = {"shape": None if rgb is None else list(rgb.shape), "mean": None if rgb is None else round(float(rgb.mean()), 1), "std": None if rgb is None else round(float(rgb.std()), 1), "dark_frac": None if rgb is None else round(float((rgb.max(-1) < 8).mean()), 3)}
        if d is not None and d.size: fin = np.isfinite(d); st["depth_min_m"] = round(float(d[fin].min()), 4) if fin.any() else None; st["self_occlusion_frac"] = round(float((d[fin] < self_occ_m).mean()), 3) if fin.any() else None; st["depth_median_m"] = round(float(np.median(d[fin])), 3) if fin.any() else None
        st["_depth"] = d; frames[s["name"]] = (rgb, st)
    return frames
def project_points(stage, spec, names_paths, robot_path):
    """링크/prim 원점을 카메라 화소 좌표로 투영(왜곡 무시). 반환: {name: (u, v, depth_m, in_image)}"""
    xc = UsdGeom.XformCache(Usd.TimeCode.Default()); cam = stage.GetPrimAtPath(spec["prim_path"]); Mc = np.array(xc.GetLocalToWorldTransform(cam)).T  # 열벡터 규약
    Rc, tc = Mc[:3, :3], Mc[:3, 3]; fx, fy, cx, cy = spec["intr"]; out = {}
    for n, path in names_paths.items():
        pr = stage.GetPrimAtPath(path)
        if not pr.IsValid(): out[n] = None; continue
        pw = np.array(xc.GetLocalToWorldTransform(pr)).T[:3, 3]; pc = Rc.T @ (pw - tc)           # USD 카메라 좌표(x우, y상, -z전방)
        z = -pc[2]
        if z <= 1e-6: out[n] = {"behind": True}; continue
        u = fx*pc[0]/z + cx; v = -fy*pc[1]/z + cy; out[n] = {"u": round(float(u), 1), "v": round(float(v), 1), "depth_m": round(float(z), 3), "in_image": bool(0 <= u < spec["W"] and 0 <= v < spec["H"])}
    return out
def save(frames, specs, out, tag, cfg):
    from PIL import Image
    os.makedirs(out, exist_ok=True); files = {}; imgs = {}
    for s in specs:
        rgb, _ = frames[s["name"]]
        if rgb is None: continue
        if s.get("pad_to") and tuple(rgb.shape[1::-1]) != tuple(s["pad_to"]):
            Wt, Ht = s["pad_to"]; pad = np.zeros((Ht, Wt, 3), np.uint8); y0 = (Ht - rgb.shape[0])//2; pad[y0:y0+rgb.shape[0], :rgb.shape[1]] = rgb; rgb = pad
        imgs[s["name"]] = rgb; f = os.path.join(out, f'{tag}_{s["role"]}{"" if s["output"] == "official" else "_" + s["output"]}.png'); Image.fromarray(rgb).save(f); files[s["name"]] = f
        dep = frames[s["name"]][1].get("_depth")
        if dep is not None and s["output"] == "official" and s["role"].startswith("hand"):
            dv = np.clip(dep, 0, 0.3)/0.3; dimg = (255*(1-dv)).astype(np.uint8); dimg[~np.isfinite(dep)] = 0; dimg = np.stack([dimg]*3, -1); dimg[(dep < 0.03) & np.isfinite(dep)] = (255, 0, 0)   # 빨강 = 3 cm 이내(자기 메시)
            fd = f.replace(".png", "_depth.png"); Image.fromarray(dimg).save(fd); files[s["name"] + "_depth"] = fd
    hl, hr = [x for x in specs if x["role"] == "head_left"][0]["name"], [x for x in specs if x["role"] == "head_right"][0]["name"]
    if hl in imgs and hr in imgs:
        f = os.path.join(out, f'{tag}_{cfg["head"].get("stereo_output", "cam_head")}_1280x480.png'); Image.fromarray(np.hstack([imgs[hl], imgs[hr]])).save(f); files["cam_head"] = f
    quad = [n for n in (hl, hr, [x for x in specs if x["role"] == "hand_left" and x["output"] == "official"][0]["name"], [x for x in specs if x["role"] == "hand_right" and x["output"] == "official"][0]["name"]) if n in imgs]
    if len(quad) == 4:
        tiles = [Image.fromarray(imgs[n]).resize((640, 480)) for n in quad]; grid = Image.new("RGB", (1280, 960))
        for i, t in enumerate(tiles): grid.paste(t, ((i % 2)*640, (i//2)*480))
        f = os.path.join(out, f"{tag}_quad_preview.png"); grid.save(f); files["quad_preview"] = f
    return files
