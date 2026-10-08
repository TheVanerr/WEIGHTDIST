"""Build the multilingual PDF report: TR + EN + DE (12 pages each, 36 pages total).
Also exposes build_content(lang) used by the HTML generator."""
import json, datetime, os, sys, numpy as np, pandas as pd, matplotlib
sys.path.insert(0, os.path.dirname(__file__))
from i18n import T as T_RAW, LANGS, fmt0, fmt1, fmt2
from grade import G, RESULT_DIR, REPORT_DIR, localize, display
T = localize(T_RAW)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DVI", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")))
registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

S = json.load(open(f"{RESULT_DIR}/summary.json", encoding="utf-8"))
df = pd.read_csv(f"{RESULT_DIR}/parts_mass.csv")
os.makedirs(REPORT_DIR, exist_ok=True)
OUT_PDF = os.path.join(REPORT_DIR, "C061176_Ayak_Yuk_Dagilimi_Raporu_TR_EN_DE.pdf")
today = datetime.date.today().strftime("%d.%m.%Y")

cases = S["cases"]; feet = S["feet"]; mach = S["machine"]; water = S["water"]; trol = S["trolley"]
A, B, C = cases["A_kuru"], cases["B_su"], cases["C_su_yuk"]
tk = water["tank"]


# =====================================================================================
# Language-neutral content model: a list of "blocks" -> rendered by PDF and HTML backends
#   ("h1", text) ("h2", text) ("p", text) ("small", text) ("cap", text)
#   ("table", rows, colwidths_mm, opts) ("fig", path, width_mm, caption) ("pagebreak",) ("cover", ...)
# =====================================================================================
def build_content(lang):
    L = T[lang]; f0 = lambda x: fmt0(x, lang); f1 = lambda x: fmt1(x, lang); f2 = lambda x: fmt2(x, lang)
    FIG = f"{RESULT_DIR}/fig_{lang}"
    fn = L["feet"]
    nmach = sum(S["by_material_count"].values())
    blocks = []
    # ---- cover (page 1)
    blocks.append(("cover", L["title"], L["subtitle"], [L["cover_l1"], L["cover_l2"].format(date=today)]))
    blocks.append(("fig", f"{FIG}/fig1_iso_malzeme.png", 165, L["fig1_cap"]))
    rows = [L["summary_head"],
            [L["summary_mass"], f0(A["mass"]), f0(B["mass"]), f0(C["mass"])],
            [L["summary_cg"], " / ".join(f0(v) for v in A["cg"]), " / ".join(f0(v) for v in B["cg"]), " / ".join(f0(v) for v in C["cg"])]]
    for i, n in enumerate(fn):
        rows.append([L["summary_foot"].format(n=n), f0(A["R"][i]), f0(B["R"][i]), f0(C["R"][i])])
    rows.append([L["summary_max"], f"{f0(max(A['R']))} / {f2(max(A['R'])*9.81/1000)}", f"{f0(max(B['R']))} / {f2(max(B['R'])*9.81/1000)}", f"{f0(max(C['R']))} / {f2(max(C['R'])*9.81/1000)}"])
    blocks.append(("h2", L["summary_h"])); blocks.append(("table", rows, [52, 38, 38, 48], {}))
    blocks.append(("pagebreak",))
    # ---- page 2
    blocks.append(("h1", L["s1_h"])); blocks.append(("p", L["s1_p"]))
    blocks.append(("h2", L["model_h"]))
    mrows = [[L["item"], L["value"]]] + [[a, b.format(ninst=len(df), nmach=nmach, pad=f"{feet['pad_d']:.0f}")] for a, b in L["model_rows"]]
    blocks.append(("table", mrows, [40, 136], {}))
    blocks.append(("h2", L["method_h"])); blocks.append(("p", L["method_p"]))
    blocks.append(("h1", L["s2_h"])); blocks.append(("h2", L["s21_h"]))
    mat_rows = [L["mat_head"]]
    for k in ["AISI316_SAC", "MOTOR_FAN", "POMPA", "ELEKTRIK", "CELIK", "HORTUM", "PVC_KANAL", "GALV_CELIK", "A4_INOX"]:
        mat_rows.append([display(k), f2(S["materials"][k]["rho"]), L["mat_desc"][k], f1(S["by_material"].get(k, 0)), str(S["by_material_count"].get(k, 0))])
    mat_rows.append([L["mat_total"], "", "", f1(mach["mass"]), str(nmach)])
    blocks.append(("table", mat_rows, [26, 20, 84, 26, 20], {}))
    blocks.append(("small", L["mat_note"]))
    blocks.append(("pagebreak",))
    # ---- page 3
    blocks.append(("h2", L["s22_h"])); blocks.append(("p", L["s22_p"]))
    comp_rows = [L["comp_head"]]
    for n, d in L["comp_desc"].items():
        r = df[df["name"] == n].iloc[0]
        comp_rows.append([n.split("_")[0], d, f0(r.volume_cm3), f1(r.density), f1(r.mass_kg), L["no_floor"] if r.group == "FLOOR_ITEM" else L["yes"]])
    el = df[(df.material == "ELEKTRIK") & (df.group == "MACHINE")]
    comp_rows.append([L["comp_panel"], L["comp_panel_desc"], f0(el.volume_cm3.sum()), f1(3.0), f1(el.mass_kg.sum()), L["yes"]])
    blocks.append(("table", comp_rows, [26, 62, 20, 16, 20, 32], {}))
    blocks.append(("h2", L["s23_h"]))
    ex = [L["excl_head"]] + [[a, b.format(mt=f1(trol["mass"])), c] for a, b, c in L["excl_rows"]]
    blocks.append(("table", ex, [40, 56, 80], {}))
    blocks.append(("h2", L["s24_h"]))
    lw = [L["load_head"],
          [L["load_water"], L["load_water_a"].format(lx=tk["x1"]-tk["x0"], lz=tk["z1"]-tk["z0"], y0=tk["y_bottom_lo"], y1=tk["y_bottom_hi"], lvl=tk["level"]),
           L["load_water_v"].format(vol=f0(water["volume_L"]), mw=f0(water["mass"]), cx=f0(water["cg"][0]), cy=f0(water["cg"][1]), cz=f0(water["cg"][2]), per=f0(water["L_per_100mm"]))],
          [L["load_pay"], L["load_pay_a"], L["load_pay_v"].format(mp=f0(S["payload"]["mass"]))],
          [L["load_door"], L["load_door_a"], L["load_door_v"]]]
    blocks.append(("table", lw, [36, 80, 60], {}))
    blocks.append(("pagebreak",))
    # ---- page 4
    blocks.append(("h1", L["s3_h"]))
    blocks.append(("p", L["s3_p"].format(m=f1(mach["mass"]), x=f0(mach["cg"][0]), y=f0(mach["cg"][1]), z=f0(mach["cg"][2]))))
    blocks.append(("fig", f"{FIG}/chart_alt_montaj.png", 150, L["fig2_cap"]))
    sub_rows = [L["sub_head"]]
    for s in S["subassemblies"]:
        sub_rows.append([s["sub"], L["sub_desc"].get(s["sub"], ""), str(s["n"]), f1(s["mass_kg"]), f0(s["x"]), f0(s["y"]), f0(s["z"])])
    sub_rows.append([L["sub_total"], "", str(sum(s["n"] for s in S["subassemblies"])), f1(mach["mass"]), f0(mach["cg"][0]), f0(mach["cg"][1]), f0(mach["cg"][2])])
    blocks.append(("table", sub_rows, [34, 66, 14, 20, 14, 14, 14], {}))
    blocks.append(("cap", L["tbl3_cap"]))
    blocks.append(("pagebreak",))
    # ---- page 5
    blocks.append(("h1", L["s4_h"]))
    blocks.append(("fig", f"{FIG}/fig3_alt_ayaklar_cg.png", 150, L["fig3_cap"]))
    lr = [L["load_tbl_head"]]
    for i, n in enumerate(fn):
        x, z, _ = feet["xyz"][i]
        lr.append([n, f0(x), f0(z), f0(A["R"][i]), f2(A["R_N"][i]/1000), f0(B["R"][i]), f2(B["R_N"][i]/1000), f0(C["R"][i]), f2(C["R_N"][i]/1000), f1(C["pressure_bar"][i])])
    lr.append([L["total"], "", "", f0(A["mass"]), f2(A["mass"]*9.81/1000), f0(B["mass"]), f2(B["mass"]*9.81/1000), f0(C["mass"]), f2(C["mass"]*9.81/1000), ""])
    blocks.append(("table", lr, [26, 13, 13, 19, 13, 20, 13, 22, 13, 22], {"fs": 7.5}))
    blocks.append(("cap", L["tbl4_cap"].format(pad=f"{feet['pad_d']:.0f}", area=f1(feet["pad_area_cm2"]))))
    blocks.append(("pagebreak",))
    # ---- page 6
    blocks.append(("fig", f"{FIG}/chart_ayak_yukleri.png", 150, L["fig4_cap"]))
    blocks.append(("h2", L["comment_h"]))
    rmax = max(C["R"])
    blocks.append(("p", L["comment_p"].format(a2=f0(A["R"][1]), a4=f0(A["R"][3]), mw=f0(water["mass"]),
                                             d1=f0(B["R"][0]-A["R"][0]), d2=f0(B["R"][1]-A["R"][1]), d3=f0(B["R"][2]-A["R"][2]), d4=f0(B["R"][3]-A["R"][3]),
                                             s100=f"{S['sens_payload100'][0]:.0f}", w100=f0(water["L_per_100mm"]), wf=f"{S['sens_water100mm'][0]:.0f}", wr=f"{S['sens_water100mm'][2]:.0f}",
                                             rmax=f0(rmax), rdes=f0(rmax*1.25), rdesk=f1(rmax*1.25*9.81/1000))))
    blocks.append(("pagebreak",))
    # ---- pages 7-10
    blocks.append(("h1", L["s5_h"]))
    blocks.append(("fig", f"{FIG}/fig4a_iso_yukler_kuru.png", 150, L["fig5_cap"].format(m=f0(A["mass"]))))
    blocks.append(("fig", f"{FIG}/fig4b_iso_yukler_su.png", 150, L["fig6_cap"].format(m=f0(B["mass"]))))
    blocks.append(("pagebreak",))
    blocks.append(("fig", f"{FIG}/fig4c_iso_yukler_su_yuk.png", 155, L["fig7_cap"].format(m=f0(C["mass"]))))
    blocks.append(("fig", f"{FIG}/fig2_gorunusler.png", 170, L["fig8_cap"]))
    blocks.append(("pagebreak",))
    blocks.append(("fig", f"{FIG}/fig5_kesitler.png", 170, L["fig9_cap"]))
    blocks.append(("fig", f"{FIG}/fig6_satinalma.png", 150, L["fig10_cap"]))
    blocks.append(("pagebreak",))
    blocks.append(("fig", f"{FIG}/fig7_araba.png", 155, L["fig11_cap"].format(m=f1(trol["mass"]))))
    blocks.append(("fig", f"{FIG}/fig8_ayak.png", 120, L["fig12_cap"]))
    blocks.append(("pagebreak",))
    # ---- page 11
    blocks.append(("h1", L["s6_h"]))
    blocks.append(("p", L["s6_p"].format(mt=f1(trol["mass"]), mb=f0(S["basket"]["mass"]))))
    tr = [L["trol_head"]] + [[f"T{i+1}", f0(c[0]), f0(c[1]), f1(r)] for i, (c, r) in enumerate(zip(trol["casters"], trol["R"]))]
    blocks.append(("table", tr, [30, 30, 30, 30], {}))
    blocks.append(("h1", L["s7_h"])); blocks.append(("p", L["s7_p"]))
    blocks.append(("pagebreak",))
    # ---- page 12
    blocks.append(("h1", L["appA_h"]))
    g = df[df.group == "MACHINE"].groupby("name").agg(adet=("mass_kg", "size"), malzeme=("material", "first"), hacim=("volume_cm3", "first"), t=("t_est", "first"), birim=("mass_kg", "first"), toplam=("mass_kg", "sum")).sort_values("toplam", ascending=False).head(40)
    rows = [L["appA_head"]] + [[n[:34], str(r.adet), display(r.malzeme), f0(r.hacim), f1(r.t), f1(r.birim), f1(r.toplam)] for n, r in g.iterrows()]
    blocks.append(("table", rows, [52, 12, 28, 22, 22, 20, 20], {"fs": 7.5}))
    blocks.append(("cap", L["appA_note"]))
    return blocks


# =====================================================================================
# PDF backend
# =====================================================================================
H1 = ParagraphStyle("h1", fontName="DVB", fontSize=15, leading=19, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#1c3d5a"))
H2 = ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#1c3d5a"))
P = ParagraphStyle("p", fontName="DV", fontSize=9, leading=12.5, spaceAfter=4)
PS = ParagraphStyle("ps", fontName="DV", fontSize=7.5, leading=10, textColor=colors.HexColor("#444444"))
CAP = ParagraphStyle("cap", fontName="DVI", fontSize=8, leading=10.5, spaceBefore=2, spaceAfter=8, textColor=colors.HexColor("#444444"))
TITLE = ParagraphStyle("t", fontName="DVB", fontSize=22, leading=27, textColor=colors.HexColor("#1c3d5a"), spaceAfter=4)
SUB = ParagraphStyle("s", fontName="DV", fontSize=11, leading=15, textColor=colors.HexColor("#444444"))
TC = ParagraphStyle("tc", fontName="DV", fontSize=8, leading=10)
TCB = ParagraphStyle("tcb", fontName="DVB", fontSize=8, leading=10)

def pdf_table(data, colw, fs=8):
    data2 = [[Paragraph(str(c), TCB if i == 0 else TC) for c in row] for i, row in enumerate(data)]
    t = Table(data2, colWidths=[w * mm for w in colw], repeatRows=1)
    st = [("FONTNAME", (0, 0), (-1, -1), "DV"), ("FONTSIZE", (0, 0), (-1, -1), fs),
          ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b8c0c8")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe7ee"))]
    for i in range(1, len(data)):
        if i % 2 == 0: st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f5f7f9")))
    t.setStyle(TableStyle(st)); return t

def pdf_fig(path, w, cap):
    from PIL import Image as PI
    im = PI.open(path); ar = im.height / im.width
    return KeepTogether([Image(path, width=w * mm, height=w * ar * mm), Paragraph(cap, CAP)])

def pdf_story(lang):
    story = []
    for b in build_content(lang):
        k = b[0]
        if k == "cover":
            story += [Spacer(1, 25 * mm), Paragraph(b[1], TITLE), Paragraph(b[2], SUB), Spacer(1, 4 * mm)] + [Paragraph(x, SUB) for x in b[3]] + [Spacer(1, 8 * mm)]
        elif k == "h1": story.append(Paragraph(b[1], H1))
        elif k == "h2": story.append(Paragraph(b[1], H2))
        elif k == "p": story.append(Paragraph(b[1], P))
        elif k == "small": story.append(Paragraph(b[1], PS))
        elif k == "cap": story.append(Paragraph(b[1], CAP))
        elif k == "table": story.append(pdf_table(b[1], b[2], b[3].get("fs", 8)))
        elif k == "fig": story.append(pdf_fig(b[1], b[2], b[3]))
        elif k == "pagebreak": story.append(PageBreak())
    return story

if __name__ == "__main__":
    from reportlab.platypus import Flowable
    CUR = {"lang": LANGS[0]}
    class LangMarker(Flowable):
        def __init__(self, lang): Flowable.__init__(self); self.lang = lang; self.width = 0; self.height = 0
        def draw(self): CUR["lang"] = self.lang
    story = []
    for i, lang in enumerate(LANGS):
        if i: story.append(PageBreak())
        story.append(LangMarker(lang))
        story += pdf_story(lang)
    class Doc(SimpleDocTemplate):
        def afterPage(self):
            L = T[CUR["lang"]]
            c = self.canv
            c.saveState(); c.setFont("DV", 7); c.setFillColor(colors.HexColor("#666666"))
            c.drawString(20 * mm, 10 * mm, L["footer"].format(date=today))
            c.drawRightString(190 * mm, 10 * mm, f"{L['page']} {self.page}")
            c.restoreState()
    doc = Doc(OUT_PDF, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
              title="C061176 Weight Distribution on Feet Report (TR / EN / DE)", author="Weight distribution analysis")
    doc.build(story)
    print("PDF written:", OUT_PDF)
