"""Render 3D report figures with PyVista + charts with matplotlib, for every language in i18n.LANGS.
Usage: python scripts/figures.py [lang ...]   (default: all languages) -> output/fig_<lang>/"""
import json, os, sys, numpy as np, pandas as pd, pyvista as pv
sys.path.insert(0, os.path.dirname(__file__))
from i18n import T as T_RAW, LANGS, fmt0, fmt1
from grade import G, RESULT_DIR, MESH_DIR, localize
T = localize(T_RAW)
pv.OFF_SCREEN = True
pv.global_theme.font.family = "arial"

S = json.load(open(f"{RESULT_DIR}/summary.json", encoding="utf-8"))
df = pd.read_csv(f"{RESULT_DIR}/parts_mass.csv")
langs = sys.argv[1:] or LANGS

MAT_COLOR = {
 "AISI316_SAC": "#b9c0c7", "A4_INOX": "#8a96a3", "GALV_CELIK": "#6b7785", "CELIK": "#5c6670",
 "POMPA": "#2a78d6", "MOTOR_FAN": "#eb6834", "ELEKTRIK": "#1baf7a", "PVC_KANAL": "#eda100",
 "HORTUM": "#e87ba4", "TEKERLEK": "#008300", "PEDAL": "#7a4bd6",
}

def load(idx):
    p = f"{MESH_DIR}/{idx:04d}.stl"
    return pv.read(p) if os.path.exists(p) else None

print("loading meshes...")
meshes = {}
for _, r in df.iterrows():
    if r.mass_kg > 0:
        m = load(int(r.idx))
        if m is not None and m.n_points:
            meshes[int(r.idx)] = m
bymat = {}
for _, r in df.iterrows():
    if int(r.idx) in meshes:
        bymat.setdefault(r.material, []).append(meshes[int(r.idx)])
matmesh = {k: pv.MultiBlock(v).combine() for k, v in bymat.items()}
machine_idx = [int(i) for i in df[df.group == "MACHINE"].idx if int(i) in meshes]
trolley_idx = [int(i) for i in df[df.group == "TROLLEY"].idx if int(i) in meshes]
all_mesh = pv.MultiBlock([meshes[i] for i in meshes]).combine()
machine_mesh = pv.MultiBlock([meshes[i] for i in machine_idx]).combine()
trolley_mesh = pv.MultiBlock([meshes[i] for i in trolley_idx]).combine()
feet_mesh = pv.MultiBlock([meshes[int(r.idx)] for _, r in df.iterrows() if "C001734" in str(r.path) and int(r.idx) in meshes]).combine()
clipZ = machine_mesh.clip(normal=(0, 0, 1), origin=(0, 0, 0))
clipX = machine_mesh.clip(normal=(-1, 0, 0), origin=(380, 0, 0))
print("meshes ready")

feet = np.array(S["feet"]["xyz"])
feet3 = feet[:, [0, 2, 1]]  # (x, y, z)
cases = S["cases"]
tank = S["water"]["tank"]
water_box = pv.Box(bounds=(tank["x0"], tank["x1"], tank["y_bottom_lo"], tank["level"], tank["z0"], tank["z1"]))
GRAY = "#c9ced4"

def new_plotter(size=(1800, 1300), shape=(1, 1)):
    pl = pv.Plotter(off_screen=True, window_size=size, shape=shape, border=False)
    pl.set_background("white")
    return pl

def axes(pl):
    pl.add_axes(xlabel="X", ylabel="Y", zlabel="Z", line_width=3)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "DejaVu Sans"

for lang in langs:
    L = T[lang]
    OUT = f"{RESULT_DIR}/fig_{lang}"; os.makedirs(OUT, exist_ok=True)
    feet_names = L["feet"]
    print("rendering", lang)

    # ---------- Fig 1: iso coloured by material ----------
    pl = new_plotter()
    for k, m in matmesh.items():
        pl.add_mesh(m, color=MAT_COLOR[k], label=L["mat_label"][k], smooth_shading=False)
    pl.add_legend(bcolor="white", face="rectangle", size=(0.26, 0.30), loc="upper right")
    axes(pl)
    pl.view_vector((1, 0.55, 0.9), viewup=(0, 1, 0))
    pl.camera.zoom(1.4)
    pl.add_text(L["fig1_title"], font_size=12, position="upper_left")
    pl.screenshot(f"{OUT}/fig1_iso_malzeme.png")

    # ---------- Fig 2: orthographic views ----------
    pl = new_plotter(size=(2100, 800), shape=(1, 3))
    views = [((1, 0, 0), (0, 1, 0)), ((0, 0, -1), (0, 1, 0)), ((0, 1, 0), (-1, 0, 0))]
    for i, (v, up) in enumerate(views):
        pl.subplot(0, i)
        pl.add_mesh(all_mesh, color=GRAY)
        pl.add_text(L["views"][i], font_size=11)
        pl.view_vector(v, viewup=up)
        pl.enable_parallel_projection()
    pl.screenshot(f"{OUT}/fig2_gorunusler.png")

    # ---------- Fig 3: bottom view ----------
    pl = new_plotter(size=(1600, 1400))
    pl.add_mesh(machine_mesh, color=GRAY, opacity=1.0)
    pl.add_mesh(trolley_mesh, color="#9aa3ad", opacity=0.6)
    pl.add_mesh(water_box, color="#2a78d6", opacity=0.45)
    pts = pv.PolyData(feet3 + np.array([0, -5, 0]))
    pl.add_point_labels(pts, feet_names, font_size=28, point_size=28, point_color="#eb6834", text_color="black", shape_color="white", shape_opacity=0.9, always_visible=True, bold=True)
    for key, col in (("A_kuru", "#d62728"), ("B_su", "#2a78d6"), ("C_su_yuk", "#1baf7a")):
        c = cases[key]["cg"]
        pl.add_mesh(pv.Sphere(radius=22, center=[c[0], -30, c[2]]), color=col)
    txt = chr(10).join(f"{lab}: X={cases[k]['cg'][0]:.0f} mm, Z={cases[k]['cg'][2]:.0f} mm" for k, lab in zip(("A_kuru", "B_su", "C_su_yuk"), L["cg_legend"]))
    pl.add_text(txt, position="lower_left", font_size=12)
    rect = pv.Rectangle([[728, -40, 728], [728, -40, -728], [-728, -40, -728]])
    pl.add_mesh(rect, style="wireframe", color="#eb6834", line_width=3)
    pl.add_text(L["fig3_title"], font_size=12)
    pl.view_vector((0, -1, 0.0001), viewup=(0, 0, 1))
    pl.enable_parallel_projection()
    pl.camera.zoom(1.7)
    pl.screenshot(f"{OUT}/fig3_alt_ayaklar_cg.png")

    # ---------- Fig 4: iso with CG sphere and foot loads ----------
    for key, fname in (("A_kuru", "fig4a_iso_yukler_kuru.png"), ("B_su", "fig4b_iso_yukler_su.png"), ("C_su_yuk", "fig4c_iso_yukler_su_yuk.png")):
        pl = new_plotter()
        pl.add_mesh(machine_mesh, color=GRAY, opacity=0.35)
        pl.add_mesh(trolley_mesh, color="#9aa3ad", opacity=0.15)
        if key != "A_kuru":
            pl.add_mesh(water_box, color="#2a78d6", opacity=0.5)
        c = cases[key]["cg"]; R = cases[key]["R"]
        pl.add_mesh(pv.Sphere(radius=45, center=c), color="#d62728")
        pl.add_mesh(pv.Line([c[0], 0, c[2]], c), color="#d62728", line_width=3)
        pl.add_point_labels(pv.PolyData(np.array([c])), [f"{L['cg']}  X={c[0]:.0f}  Y={c[1]:.0f}  Z={c[2]:.0f} mm"], font_size=22, point_size=1, text_color="black", shape_color="white", shape_opacity=0.9, always_visible=True)
        for f, r in zip(feet3, R):
            h = r * 1.2
            pl.add_mesh(pv.Cylinder(center=(f[0], -h / 2 - 20, f[2]), direction=(0, 1, 0), radius=45, height=h), color="#eb6834")
        pl.add_point_labels(pv.PolyData(feet3 + np.array([0, -60, 0])), [f"{n}\n{r:.0f} kg" for n, r in zip(feet_names, R)], font_size=24, point_size=1, text_color="black", shape_color="white", shape_opacity=0.95, always_visible=True, bold=True)
        pl.add_text(L["fig4_titles"][key] + f"   |   {L['total']} {cases[key]['mass']:.0f} kg", font_size=12)
        axes(pl)
        pl.view_vector((1, 0.6, 1), viewup=(0, 1, 0))
        pl.camera.zoom(1.25)
        pl.screenshot(f"{OUT}/{fname}")

    # ---------- Fig 5: sections ----------
    pl = new_plotter(size=(2000, 1000), shape=(1, 2))
    pl.subplot(0, 0)
    pl.add_mesh(clipZ, color=GRAY)
    pl.add_mesh(water_box.clip(normal=(0, 0, 1), origin=(0, 0, 0)), color="#2a78d6", opacity=0.7)
    for k in ("POMPA", "MOTOR_FAN"):
        pl.add_mesh(matmesh[k].clip(normal=(0, 0, 1), origin=(0, 0, 0)), color=MAT_COLOR[k])
    pl.add_text(L["fig5_titles"][0], font_size=11)
    pl.view_vector((0, 0, 1), viewup=(0, 1, 0)); pl.enable_parallel_projection()
    pl.subplot(0, 1)
    pl.add_mesh(clipX, color=GRAY)
    pl.add_mesh(water_box.clip(normal=(-1, 0, 0), origin=(380, 0, 0)), color="#2a78d6", opacity=0.7)
    pl.add_text(L["fig5_titles"][1], font_size=11)
    pl.view_vector((-1, 0, 0), viewup=(0, 1, 0)); pl.enable_parallel_projection()
    pl.screenshot(f"{OUT}/fig5_kesitler.png")

    # ---------- Fig 6: purchased components ----------
    pl = new_plotter()
    pl.add_mesh(machine_mesh, color=GRAY, opacity=0.18)
    labels, lpts = [], []
    comp = L["comp"]
    for _, r in df[df["name"].isin(comp.keys())].iterrows():
        m = meshes.get(int(r.idx))
        if m is None: continue
        pl.add_mesh(m, color=MAT_COLOR[r.material])
        labels.append(f"{comp[r['name']]}\n{r['name'].split('_')[0]}  {fmt1(r.mass_kg, lang)} kg"); lpts.append([r.x, r.y, r.z])
    pl.add_mesh(matmesh["ELEKTRIK"], color=MAT_COLOR["ELEKTRIK"])
    pl.add_point_labels(pv.PolyData(np.array(lpts)), labels, font_size=18, point_size=10, point_color="black", text_color="black", shape_color="white", shape_opacity=0.9, always_visible=True)
    pl.add_text(L["fig6_title"], font_size=12)
    axes(pl)
    pl.view_vector((1, 0.5, -1), viewup=(0, 1, 0))
    pl.screenshot(f"{OUT}/fig6_satinalma.png")

    # ---------- Fig 7: trolley ----------
    pl = new_plotter()
    pl.add_mesh(machine_mesh, color=GRAY, opacity=0.15)
    pl.add_mesh(trolley_mesh, color="#eb6834")
    cp = np.array(S["trolley"]["casters"]); Rt = S["trolley"]["R"]
    cpts3 = np.array([[c[0], -40, c[1]] for c in cp])
    pl.add_point_labels(pv.PolyData(cpts3), [f"T{i+1}: {fmt1(r, lang)} kg" for i, r in enumerate(Rt)], font_size=20, point_size=18, point_color="#2a78d6", text_color="black", shape_color="white", shape_opacity=0.9, always_visible=True)
    pl.add_text(L["fig7_title"].format(m=fmt1(S['trolley']['mass'], lang)), font_size=12)
    axes(pl)
    pl.view_vector((1, 0.6, 1), viewup=(0, 1, 0))
    pl.screenshot(f"{OUT}/fig7_araba.png")

    # ---------- Fig 8: feet close-up ----------
    pl = new_plotter(size=(1400, 1000))
    pl.add_mesh(feet_mesh, color="#8a96a3")
    f0 = feet3[0]
    pl.add_text(L["fig8_title"], font_size=12)
    pl.view_vector((1, 0.5, 1), viewup=(0, 1, 0))
    pl.camera.focal_point = (f0[0], 80, f0[2]); pl.camera.position = (f0[0] + 450, 320, f0[2] + 450)
    pl.screenshot(f"{OUT}/fig8_ayak.png")

    # ---------- Chart: feet loads ----------
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=200)
    keys = list(zip(("A_kuru", "B_su", "C_su_yuk"), L["chart_cases"], ("#2a78d6", "#eb6834", "#1baf7a")))
    x = np.arange(4); w = 0.26
    for j, (k, lab, col) in enumerate(keys):
        R = cases[k]["R"]
        bars = ax.bar(x + (j - 1) * w, R, w * 0.92, color=col, label=lab, zorder=3)
        for b, r in zip(bars, R):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 6, f"{r:.0f}", ha="center", va="bottom", fontsize=8, color="#333")
    ax.set_xticks(x); ax.set_xticklabels([n.replace(" (", "\n(") for n in feet_names], fontsize=9)
    ax.set_ylabel(L["chart_y"], fontsize=9)
    ax.set_title(L["chart_title"], fontsize=11, loc="left")
    ax.grid(axis="y", color="#e3e3e3", zorder=0); ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.0))
    ax.set_ylim(0, max(cases["C_su_yuk"]["R"]) * 1.25)
    fig.tight_layout(); fig.savefig(f"{OUT}/chart_ayak_yukleri.png"); plt.close(fig)

    sub = S["subassemblies"][:8]
    fig, ax = plt.subplots(figsize=(9, 3.8), dpi=200)
    names = [s["sub"] for s in sub][::-1]; vals = [s["mass_kg"] for s in sub][::-1]
    ax.barh(names, vals, color="#2a78d6", height=0.6, zorder=3)
    for i, v in enumerate(vals): ax.text(v + 5, i, f"{v:.0f} kg", va="center", fontsize=8, color="#333")
    ax.set_xlabel(L["chart2_x"], fontsize=9); ax.set_title(L["chart2_title"], fontsize=11, loc="left")
    ax.grid(axis="x", color="#e3e3e3", zorder=0); ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, max(vals) * 1.18)
    fig.tight_layout(); fig.savefig(f"{OUT}/chart_alt_montaj.png"); plt.close(fig)
    print("figures done", lang)
