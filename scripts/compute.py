"""Mass, CG and foot-load calculation for C061176 washing machine assembly."""
import json, os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from grade import G, M as MC, RESULT_DIR, INSTANCES, display
os.makedirs(RESULT_DIR, exist_ok=True)

recs = json.load(open(INSTANCES, encoding="utf-8"))

# ---------------- material / density assumptions (g/cm3) ----------------
MAT = {
 "AISI316_SAC":   (G["rho_sheet"], display("AISI 316 (1.4401) sac / profil / işlenmiş paslanmaz")),
 "A4_INOX":       (G["rho_fastener"], display("A4 (316) paslanmaz bağlantı elemanı")),
 "GALV_CELIK":    (7.85, "Galvanizli karbon çeliği bağlantı elemanı"),
 "CELIK":         (7.85, "Çelik (dişli, vana, rulman yuvası vb.)"),
 "POMPA":         (7.00, "Santrifüj pompa + motor (efektif yoğunluk)"),
 "MOTOR_FAN":     (6.00, "Elektrik motoru / fan / redüktör (efektif yoğunluk)"),
 "ELEKTRIK":      (3.00, "Pano elektrik bileşeni: kontaktör, sürücü, klemens (efektif)"),
 "PVC_KANAL":     (1.45, "PVC kablo kanalı"),
 "HORTUM":        (1.00, "Hortum + püskürtme tabancası (efektif)"),
 "TEKERLEK":      (4.50, "Tekerlek (PU + çelik çatal, efektif)"),
 "PEDAL":         (1.20, "Ayak pedalı şalter (yerde, ayaklara yük vermez)"),
}
EXPLICIT = MC["explicit_materials"]
PVC_FLEX = set(MC["pvc_flex_parts"])
FLEX = MC["flex_panel_token"]

def classify(r):
    n = r["name"]; path = r["path"]
    if n in EXPLICIT: return EXPLICIT[n]
    if "GALV" in n: return "GALV_CELIK"
    if "INOX" in n: return "A4_INOX"
    if FLEX in path:
        if n in PVC_FLEX: return "PVC_KANAL"
        v=r["volume_mm3"]; a=r["area_mm2"]; t=2*v/a if a>0 else 99
        lb=r["bbox_local"]; d=sorted([lb[3]-lb[0],lb[4]-lb[1],lb[5]-lb[2]])
        if t<=2.1 and d[2]>=190 and r["nsolids"]==1: return "AISI316_SAC"  # pano gövdesi / montaj plakası
        return "ELEKTRIK"
    return "AISI316_SAC"

rows=[]
for r in recs:
    v=r["volume_mm3"]
    if v<=0 or r["cg"][0] is None:
        rows.append(dict(idx=r["idx"], name=r["name"], path=r["path"], material="(hacimsiz/hatalı)", density=0, volume_cm3=0, mass_kg=0, x=np.nan,y=np.nan,z=np.nan, t_est=0, nsolids=r["nsolids"], group="EXCLUDED_NOVOL", bbox=r["bbox_global"]))
        continue
    m=classify(r); rho=MAT[m][0]
    mass=v/1000*rho/1000  # kg
    if MC["trolley_root"] in r["path"].split("/"): grp="TROLLEY"
    elif m=="PEDAL": grp="FLOOR_ITEM"
    else: grp="MACHINE"
    a=r["area_mm2"]; t=2*v/a if a>0 else 0
    rows.append(dict(idx=r["idx"], name=r["name"], path=r["path"], material=m, density=rho, volume_cm3=v/1000, mass_kg=mass,
                     x=r["cg"][0], y=r["cg"][1], z=r["cg"][2], t_est=t, nsolids=r["nsolids"], group=grp,
                     bbox=r["bbox_global"]))
df=pd.DataFrame(rows)

def agg(d):
    M=d.mass_kg.sum()
    cg=np.array([(d.mass_kg*d.x).sum(), (d.mass_kg*d.y).sum(), (d.mass_kg*d.z).sum()])/M
    return M, cg

mach=df[df.group=="MACHINE"]; trol=df[df.group=="TROLLEY"]
M_mach, cg_mach = agg(mach)
M_trol, cg_trol = agg(trol)
print(f"Machine dry mass {M_mach:.1f} kg, CG {cg_mach}")
print(f"Trolley mass {M_trol:.1f} kg, CG {cg_trol}")
print(df.groupby("material").mass_kg.sum().sort_values(ascending=False))

# ---------------- feet ----------------
feet=[r for r in recs if r["name"]==MC["feet_part"]]
feet_xy=[]
for f in feet:
    b=f["bbox_global"]; feet_xy.append(((b[0]+b[3])/2, (b[2]+b[5])/2, b[1]))
feet_xy=np.array(feet_xy)
def label(x,z):
    return ("Ön" if x>0 else "Arka")+"-"+("Sol" if z>0 else "Sağ")
order=np.lexsort((-feet_xy[:,1], -feet_xy[:,0]))  # sort by x desc then z desc
feet_xy=feet_xy[order]
feet_names=[f"F{i+1} ({label(x,z)})" for i,(x,z,_) in enumerate(feet_xy)]
print("feet:", list(zip(feet_names, feet_xy.round(1))))
pad_d=float(MC["pad_d_mm"])
pad_area_cm2=np.pi*(pad_d/10)**2/4

def reactions(M, cg, pts):
    """Rigid body on n equal-stiffness vertical springs -> least squares equilibrium (minimum-norm) solution."""
    n=len(pts)
    A=np.vstack([np.ones(n), pts[:,0], pts[:,1]])
    b=np.array([M, M*cg[0], M*cg[2]])
    R=np.linalg.pinv(A)@b
    return R

# ---------------- load cases ----------------
# water tank: inner box X[157,651] Z[-573,720], bottom plate bbox Y[231,270] (eğimli), level assumed 550 mm
tank=MC["tank"]
Lx=(tank["x1"]-tank["x0"])/1000; Lz=(tank["z1"]-tank["z0"])/1000
h_box=(tank["level"]-tank["y_bottom_hi"])/1000
V_box=Lx*Lz*h_box
V_wedge=Lx*Lz*(tank["y_bottom_hi"]-tank["y_bottom_lo"])/1000/2
V_water=V_box+V_wedge  # m3
M_water=V_water*1000*0.998
y_water=(tank["y_bottom_hi"]+tank["level"])/2
cg_water=np.array([(tank["x0"]+tank["x1"])/2, y_water, (tank["z0"]+tank["z1"])/2])
print(f"water {V_water*1000:.0f} L -> {M_water:.0f} kg, cg {cg_water}")

# basket payload: assumed 300 kg, uniformly in basket -> CG at basket centre
basket=df[df.path.str.contains(MC["basket_path_token"], regex=False)]
Mb, cgb = agg(basket)
print(f"basket mass {Mb:.1f} kg cg {cgb}")
M_payload=float(MC["payload_kg"])
cg_payload=np.array([cgb[0], float(MC["payload_y_mm"]), cgb[2]])

cases={}
def combine(items):
    M=sum(m for m,_ in items); cg=sum(m*np.array(c) for m,c in items)/M
    return M,cg
cases["A_kuru"]=combine([(M_mach,cg_mach)])
cases["B_su"]=combine([(M_mach,cg_mach),(M_water,cg_water)])
cases["C_su_yuk"]=combine([(M_mach,cg_mach),(M_water,cg_water),(M_payload,cg_payload)])
res={}
for k,(M,cg) in cases.items():
    R=reactions(M,cg,feet_xy[:,:2])
    res[k]=dict(mass=M, cg=cg.tolist(), R=R.tolist(), R_N=(R*9.81).tolist(), pressure_bar=(R*9.81/(pad_area_cm2*1e-4)/1e5).tolist())
    print(k, f"M={M:.1f} kg cg=({cg[0]:.0f},{cg[1]:.0f},{cg[2]:.0f})", "R=", R.round(1), "sum", R.sum().round(1))

# trolley casters
cast=[r for r in recs if r["name"] in set(MC["caster_parts"])]
cpts=np.array([((b[0]+b[3])/2,(b[2]+b[5])/2) for b in [c["bbox_global"] for c in cast]])
Rt=reactions(M_trol,cg_trol,cpts)
print("trolley casters", cpts.round(0), Rt.round(1))

# sensitivity per 100 kg payload at basket centre & per 100 mm water
R100=reactions(100.0, cg_payload, feet_xy[:,:2])
Rw=reactions(Lx*Lz*0.1*998, cg_water, feet_xy[:,:2])
summary=dict(
  machine=dict(mass=M_mach, cg=cg_mach.tolist()), trolley=dict(mass=M_trol, cg=cg_trol.tolist(), casters=cpts.tolist(), R=Rt.tolist()),
  water=dict(volume_L=V_water*1000, mass=M_water, cg=cg_water.tolist(), tank=tank, L_per_100mm=Lx*Lz*0.1*1000),
  basket=dict(mass=Mb, cg=cgb.tolist()), payload=dict(mass=M_payload, cg=cg_payload.tolist()),
  feet=dict(names=feet_names, xyz=feet_xy.tolist(), pad_d=pad_d, pad_area_cm2=pad_area_cm2),
  cases=res, sens_payload100=R100.tolist(), sens_water100mm=Rw.tolist(),
  materials={k:dict(rho=v[0], desc=v[1]) for k,v in MAT.items()},
  by_material=df[df.group=="MACHINE"].groupby("material").mass_kg.sum().to_dict(),
  by_material_count=df[df.group=="MACHINE"].groupby("material").size().to_dict(),
  excluded_novol=df[df.group=="EXCLUDED_NOVOL"].name.tolist(),
  floor_items=df[df.group=="FLOOR_ITEM"][["name","mass_kg"]].to_dict("records"),
)
# subassembly breakdown (level 1 under root)
def lvl1(p):
    s=p.split("/"); return s[1] if len(s)>1 else "(kök seviye parça)"
mach2=mach.assign(sub=mach.path.map(lvl1))
def wavg(col):
    return lambda s: np.average(s, weights=mach2.loc[s.index,"mass_kg"])
sub=mach2.groupby("sub").agg(n=("mass_kg","size"), mass_kg=("mass_kg","sum"), x=("x", wavg("x")), y=("y", wavg("y")), z=("z", wavg("z"))).sort_values("mass_kg", ascending=False)
summary["subassemblies"]=sub.reset_index().to_dict("records")
print(sub.round(1))
summary["grade"]=G["grade"]; summary["machine"]=MC["name"]; summary["code"]=MC["code"]
json.dump(summary, open(f"{RESULT_DIR}/summary.json","w",encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
df.drop(columns=["bbox"]).to_csv(f"{RESULT_DIR}/parts_mass.csv", index=False, encoding="utf-8-sig")
# Excel
with pd.ExcelWriter(f"{RESULT_DIR}/C061176_kutle_listesi.xlsx") as xw:
    out=df.drop(columns=["bbox"]).copy()
    out["material"]=out["material"].map(display)
    out.columns=["idx","Parça","Montaj yolu","Malzeme sınıfı","Yoğunluk g/cm3","Hacim cm3","Kütle kg","CG X mm","CG Y mm","CG Z mm","Tahmini kalınlık mm","Katı sayısı","Grup"]
    out.to_excel(xw, sheet_name="Parçalar", index=False)
    g=df[df.group=="MACHINE"].groupby("name").agg(adet=("mass_kg","size"), malzeme=("material","first"), birim_kg=("mass_kg","first"), toplam_kg=("mass_kg","sum")).sort_values("toplam_kg", ascending=False)
    g.to_excel(xw, sheet_name="Makine özet (parça no)")
    sub.to_excel(xw, sheet_name="Alt montajlar")
    pd.DataFrame([dict(ayak=n, x=p[0], z=p[1], **{k:res[k]["R"][i] for k in res}) for i,(n,p) in enumerate(zip(feet_names,feet_xy))]).to_excel(xw, sheet_name="Ayak yükleri", index=False)
print("saved")
