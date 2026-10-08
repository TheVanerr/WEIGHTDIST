import json, sys, os, numpy as np, pyvista as pv
pv.OFF_SCREEN=True
recs = json.load(open("output/instances.json", encoding="utf-8"))
byname={}
for r in recs:
    byname.setdefault(r["name"],[]).append(r)
def load(idx):
    p=f'output/meshes/{idx:04d}.stl'
    return pv.read(p) if os.path.exists(p) else None
all_mesh = pv.read("output/all_decim.vtp") if os.path.exists("output/all_decim.vtp") else None
if all_mesh is None:
    bl=pv.MultiBlock()
    for r in recs:
        if r["volume_mm3"]>0:
            m=load(r["idx"])
            if m is not None and m.n_points: bl.append(m)
    all_mesh=bl.combine().extract_surface()
    all_mesh.save("output/all_decim.vtp")
names=sys.argv[1:]
pl=pv.Plotter(off_screen=True, shape=(2,(len(names)+1)//2), window_size=(1800,1200), border=False)
for i,n in enumerate(names):
    pl.subplot(i%2, i//2)
    pl.add_mesh(all_mesh, color="#d0d4d8", opacity=0.15)
    rs=byname[n]
    bl=pv.MultiBlock()
    for r in rs:
        m=load(r["idx"])
        if m is not None: bl.append(m)
    hm=bl.combine()
    pl.add_mesh(hm, color="red")
    pl.add_text(f"{n} x{len(rs)}", font_size=10)
    pl.set_background("white")
    pl.view_vector((1,0.7,1), viewup=(0,1,0))
pl.screenshot(f"output/hl_{names[0]}.png")
# close-ups
pl2=pv.Plotter(off_screen=True, shape=(2,(len(names)+1)//2), window_size=(1800,1200), border=False)
for i,n in enumerate(names):
    pl2.subplot(i%2, i//2)
    rs=byname[n]
    bl=pv.MultiBlock()
    for r in rs[:1]:
        m=load(r["idx"])
        if m is not None: bl.append(m)
    hm=bl.combine()
    pl2.add_mesh(hm, color="#8899aa", show_edges=False)
    pl2.add_text(f"{n}", font_size=10)
    pl2.set_background("white")
    pl2.view_vector((1,0.7,1), viewup=(0,1,0))
pl2.screenshot(f"output/cu_{names[0]}.png")
print("ok")
