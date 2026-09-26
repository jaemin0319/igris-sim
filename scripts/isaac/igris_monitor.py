"""IGRIS 카메라 모니터: Isaac Sim 한 창의 아래쪽에 [HEAD STEREO (L|R)] [LEFT HAND] [RIGHT HAND] 를 도킹해 실시간 표시.
기존 카메라 센서(igris_cameras.make_sensors)의 RGBA를 omni.ui ByteImageProvider 로 그린다 — 카메라·뷰포트 추가 생성 없음, 포즈·화각 불변.
G1(vla_ws/unitree_sim_isaaclab sim_main.py '3-camera bottom monitor')의 방식(메인 뷰포트 아래 도킹 + 우측 연속 도킹)을 따르되, 머리 좌|우 결합 때문에 뷰포트 창 대신 이미지 창을 쓴다."""
import asyncio, os
import numpy as np
LABELS = {"head": "HEAD STEREO (L | R)", "left": "LEFT HAND", "right": "RIGHT HAND"}
class CameraMonitor:
    def __init__(self, sensors, specs, bottom_fraction=0.30):
        import omni.ui as ui
        self.ui = ui; self.sensors = sensors; self.specs = {s["role"]: s for s in specs if s["output"] == "official"}
        self.names = {"head": (self.specs["head_left"]["name"], self.specs["head_right"]["name"]), "left": (self.specs["hand_left"]["name"],), "right": (self.specs["hand_right"]["name"],)}
        self.sizes = {"head": (self.specs["head_left"]["W"] * 2, self.specs["head_left"]["H"]), "left": (self.specs["hand_left"]["W"], self.specs["hand_left"]["H"]), "right": (self.specs["hand_right"]["W"], self.specs["hand_right"]["H"])}
        self.providers = {}; self.windows = {}; self.last = {}; self.gpu_keep = {}; self.frame = 0; self.docked = None
        for key in ("head", "left", "right"):
            W, H = self.sizes[key]; prov = ui.DynamicTextureProvider(f"igris_monitor_{key}"); self.providers[key] = prov
            ph = np.full((H, W, 4), 40, np.uint8); ph[..., 3] = 255; prov.set_data_array(ph, [W, H])                       # 창 생성 전 자리표시 텍스처(크기 확정)
            win = ui.Window(LABELS[key], width=W // 2, height=H // 2 + 30, flags=ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_NO_COLLAPSE)
            with win.frame:
                with ui.VStack(spacing=2):
                    ui.Label(f"{LABELS[key]}  {W}x{H}", height=18, style={"font_size": 16, "color": 0xFF00FF00, "margin": 4})
                    ui.ImageWithProvider(prov, fill_policy=ui.IwpFillPolicy.IWP_PRESERVE_ASPECT_FIT, style={"alignment": ui.Alignment.CENTER})   # 종횡비 유지
            self.windows[key] = win
        asyncio.ensure_future(self._dock(bottom_fraction))
    async def _dock(self, frac):
        import omni.kit.app
        from omni.kit.viewport.utility import get_active_viewport_window
        app = omni.kit.app.get_app(); ui = self.ui
        for _ in range(3): await app.next_update_async()
        main = get_active_viewport_window(); title = getattr(main, "title", None) or "Viewport"
        r1 = ui.dock_window_in_window(LABELS["head"], title, ui.DockPosition.BOTTOM, frac); await app.next_update_async()
        r2 = ui.dock_window_in_window(LABELS["left"], LABELS["head"], ui.DockPosition.RIGHT, 0.40); await app.next_update_async()   # 폭 비율: head 8:3 ≈ 60%, 손 각 20%
        r3 = ui.dock_window_in_window(LABELS["right"], LABELS["left"], ui.DockPosition.RIGHT, 0.50); await app.next_update_async()
        for w in self.windows.values(): w.dock_tab_bar_visible = False
        self.docked = (r1, r2, r3); print("[monitor] docked under", title, self.docked, flush=True)
    def _grab(self, key):
        """센서 RGBA(CPU numpy)를 결합 — 머리는 좌|우 hstack. 반환: numpy uint8 (H,W,4) contiguous"""
        ims = []
        for n in self.names[key]:
            rgba = self.sensors[n].get_rgba()
            if rgba is None or np.asarray(rgba).size == 0: return None
            ims.append(np.asarray(rgba)[..., :4])
        im = np.ascontiguousarray(np.hstack(ims) if len(ims) > 1 else ims[0], dtype=np.uint8); im[..., 3] = 255; return im
    def update(self, every=1):
        self.frame += 1
        if self.frame % every: return
        for key, prov in self.providers.items():
            im = self._grab(key)
            if im is None: continue
            H, W = im.shape[:2]; prov.set_data_array(im, [W, H]); self.gpu_keep[key] = im   # DynamicTextureProvider: 배열 업로드(ui_provider_test*.png 로 확인한 방식)
            if self.frame <= 2: print(f"[monitor] {key} frame shape={im.shape} dtype={im.dtype} contiguous={im.flags['C_CONTIGUOUS']}", flush=True)
            self.last[key] = im[..., :3].copy()
    def snapshot(self):  # 검증용: 현재 모니터 셀의 픽셀 통계
        return {k: {"mean": round(float(v.mean()), 1), "std": round(float(v.std()), 1), "dark_frac": round(float((v.max(-1) < 8).mean()), 3), "shape": list(v.shape)} for k, v in self.last.items()}
    def diff(self, other):
        return {k: round(float(np.abs(self.last[k].astype(int) - other[k].astype(int)).mean()), 2) for k in self.last if k in other}
    def copy_last(self): return {k: v.copy() for k, v in self.last.items()}
def capture_app_window(path, app_obj, frames=3):
    """전체 Isaac Sim 창(스왑체인) 스크린샷. omni.renderer_capture 사용."""
    import omni.renderer_capture
    cap = omni.renderer_capture.acquire_renderer_capture_interface(); cap.capture_next_frame_swapchain(path)
    for _ in range(frames): app_obj.update()
    return os.path.exists(path)
