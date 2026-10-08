"""Read STEP assembly with XCAF, export per-instance geometry data + STL meshes."""
import sys, json, time, os, re
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.XCAFApp import XCAFApp_Application
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.IFSelect import IFSelect_RetDone
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopLoc import TopLoc_Location
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.Interface import Interface_Static

if len(sys.argv) >= 3:
    step_path, out_dir = sys.argv[1], sys.argv[2]
else:
    sys.path.insert(0, os.path.dirname(__file__))
    from grade import STEP_PATH, MACHINE_DIR
    step_path, out_dir = STEP_PATH, os.path.join(MACHINE_DIR, "output")
os.makedirs(os.path.join(out_dir, "meshes"), exist_ok=True)

t0 = time.time()
app = XCAFApp_Application.GetApplication_s()
doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
reader.SetColorMode(True)
status = reader.ReadFile(step_path)
assert status == IFSelect_RetDone, "read failed"
print(f"read ok {time.time()-t0:.1f}s", flush=True)
reader.Transfer(doc)
print(f"transfer ok {time.time()-t0:.1f}s", flush=True)

shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

def label_name(lbl):
    n = TDataStd_Name()
    if lbl.FindAttribute(TDataStd_Name.GetID_s(), n):
        return n.Get().ToExtString()
    return ""

def decode_step_name(s):
    # names like 'C002916_M6x20 GALV.IMBUS C\X2\0130\X0\VATA' are already decoded by OCC usually
    return s

records = []
counter = [0]
def walk(lbl, loc, path):
    name = label_name(lbl)
    if shape_tool.IsAssembly_s(lbl):
        comps = TDF_LabelSequence()
        shape_tool.GetComponents_s(lbl, comps)
        for i in range(1, comps.Length()+1):
            c = comps.Value(i)
            cloc = shape_tool.GetLocation_s(c)
            ref = TDF_Label()
            if shape_tool.GetReferredShape_s(c, ref):
                walk(ref, loc.Multiplied(cloc), path + [name])
            else:
                walk(c, loc.Multiplied(cloc), path + [name])
    elif shape_tool.IsReference_s(lbl):
        ref = TDF_Label()
        shape_tool.GetReferredShape_s(lbl, ref)
        cloc = shape_tool.GetLocation_s(lbl)
        walk(ref, loc.Multiplied(cloc), path)
    else:
        shape_local = shape_tool.GetShape_s(lbl)
        if shape_local.IsNull():
            return
        # local props
        exp = TopExp_Explorer(shape_local, TopAbs_SOLID)
        nsolids = 0
        while exp.More():
            nsolids += 1; exp.Next()
        try:
            vp = GProp_GProps(); BRepGProp.VolumeProperties_s(shape_local, vp)
            sp = GProp_GProps(); BRepGProp.SurfaceProperties_s(shape_local, sp)
            vol = vp.Mass(); area = sp.Mass()
        except Exception as e:
            print("props fail", counter[0], name, e, flush=True)
            vol = -1.0; area = -1.0
        bb = Bnd_Box(); BRepBndLib.Add_s(shape_local, bb, False)
        lx0, ly0, lz0, lx1, ly1, lz1 = bb.Get() if not bb.IsVoid() else (0,)*6
        shape_glob = shape_local.Moved(loc)
        try:
            vg = GProp_GProps(); BRepGProp.VolumeProperties_s(shape_glob, vg)
            cg = vg.CentreOfMass()
            cg = [cg.X(), cg.Y(), cg.Z()]
        except Exception as e:
            cg = [None, None, None]
        bbg = Bnd_Box(); BRepBndLib.Add_s(shape_glob, bbg, False)
        gx0, gy0, gz0, gx1, gy1, gz1 = bbg.Get() if not bbg.IsVoid() else (0,)*6
        idx = counter[0]; counter[0] += 1
        rec = dict(idx=idx, name=name, path="/".join(path), nsolids=nsolids,
                   volume_mm3=vol, area_mm2=area,
                   cg=cg,
                   bbox_local=[lx0, ly0, lz0, lx1, ly1, lz1],
                   bbox_global=[gx0, gy0, gz0, gx1, gy1, gz1])
        records.append(rec)
        # mesh export
        if vol != 0:
            try:
                BRepMesh_IncrementalMesh(shape_glob, 1.0, False, 0.3, True)
                w = StlAPI_Writer(); w.ASCIIMode = False
                w.Write(shape_glob, os.path.join(out_dir, "meshes", f"{idx:04d}.stl"))
            except Exception as e:
                print("mesh fail", idx, name, e, flush=True)
        if idx % 25 == 0:
            print(f"  {idx} instances... {time.time()-t0:.0f}s", flush=True)

roots = TDF_LabelSequence()
shape_tool.GetFreeShapes(roots)
print("free shapes:", roots.Length(), flush=True)
for i in range(1, roots.Length()+1):
    walk(roots.Value(i), TopLoc_Location(), [])

with open(os.path.join(out_dir, "instances.json"), "w", encoding="utf-8") as f:
    json.dump(records, f, indent=1, ensure_ascii=False)
print(f"done: {len(records)} instances, {time.time()-t0:.0f}s", flush=True)
