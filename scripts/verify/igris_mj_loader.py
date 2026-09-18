"""Official IGRIS-C MuJoCo xacro loader (mirrors igris_c_description_public/scripts/mujoco_file_test.py)."""
import xml.etree.ElementTree as ET
from pathlib import Path
import mujoco, xacro
XACRO = Path.home() / "igris_ws/src/igris_c_description_public/mujoco/igris_c_v2.xml.xacro"
def load(parallel="false", fixed="true", base_type="pelvis", end_effector="dummy"):
    p = xacro.process_file(str(XACRO), mappings=dict(base_type=base_type, parallel=parallel, end_effector=end_effector, fixed=fixed))
    r = ET.fromstring(p.toxml()); c = r.find("compiler")
    for k in ("meshdir", "texturedir"):
        v = c.get(k, "").strip()
        if v and not Path(v).is_absolute(): c.set(k, str((XACRO.parent / v).resolve()))
    return mujoco.MjModel.from_xml_string(ET.tostring(r, encoding="unicode"))
if __name__ == "__main__":
    print("mujoco", mujoco.__version__)
    for par in ("true", "false"):
        m = load(parallel=par)
        print(f"parallel={par}: nq={m.nq} nv={m.nv} njnt={m.njnt} nu={m.nu} nbody={m.nbody} nmesh={m.nmesh} dt={m.opt.timestep}")
