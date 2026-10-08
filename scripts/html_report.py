"""Generate a self-contained multilingual (TR/EN/DE) A4-paged HTML report with print-to-PDF button."""
import base64, io, os, sys, html, datetime
sys.path.insert(0, os.path.dirname(__file__))
from i18n import LANGS
from grade import G, M, REPORT_DIR
from report_multi import build_content, today, T
from PIL import Image

OUT_HTML = os.path.join(REPORT_DIR, "C061176_Rapor.html")

_img_cache = {}
def img_data_uri(path):
    if path in _img_cache: return _img_cache[path]
    im = Image.open(path).convert("RGB")
    if im.width > 1600:
        im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    if "chart" in os.path.basename(path):
        im.save(buf, "PNG", optimize=True); mime = "image/png"
    else:
        im.save(buf, "JPEG", quality=84, optimize=True); mime = "image/jpeg"
    uri = f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()
    _img_cache[path] = uri
    return uri

FLAGS = {
 "tr": '<svg viewBox="0 0 30 20"><rect width="30" height="20" fill="#e30a17"/><circle cx="11" cy="10" r="6" fill="#fff"/><circle cx="12.5" cy="10" r="4.8" fill="#e30a17"/><polygon fill="#fff" points="18.5,10 15.1,11.1 17.2,8.2 17.2,11.8 15.1,8.9"/></svg>',
 "en": '<svg viewBox="0 0 60 30"><clipPath id="c"><rect width="60" height="30"/></clipPath><g clip-path="url(#c)"><rect width="60" height="30" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="2"/><path d="M30,0 V30 M0,15 H60" stroke="#fff" stroke-width="10"/><path d="M30,0 V30 M0,15 H60" stroke="#C8102E" stroke-width="6"/></g></svg>',
 "de": '<svg viewBox="0 0 30 20"><rect width="30" height="6.67" fill="#000"/><rect y="6.67" width="30" height="6.67" fill="#dd0000"/><rect y="13.33" width="30" height="6.67" fill="#ffce00"/></svg>',
}

CSS = """
:root{--navy:#1c3d5a;--ink:#1a1a1a;--muted:#555;--line:#b8c0c8;--head:#dfe7ee;--zebra:#f5f7f9;--bg:#e9ecef}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif}
.toolbar{position:fixed;top:0;left:0;right:0;height:56px;background:#fff;border-bottom:1px solid #d0d5db;box-shadow:0 2px 8px rgba(0,0,0,.08);display:flex;align-items:center;gap:16px;padding:0 20px;z-index:100}
.toolbar .brand{font-family:Georgia,"Times New Roman",serif;font-weight:700;color:var(--navy);font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.toolbar .brand small{display:block;font-family:"Segoe UI",Arial,sans-serif;font-weight:400;color:var(--muted);font-size:11px}
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--navy);background:var(--navy);color:#fff;border-radius:6px;padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{background:#15304a}
.btn svg{width:16px;height:16px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.langs{display:flex;align-items:center;gap:6px;border:1px solid #d0d5db;border-radius:8px;padding:4px}
.langs .lbl{font-size:11px;color:var(--muted);padding:0 6px}
.lang{display:inline-flex;align-items:center;gap:6px;border:1px solid transparent;border-radius:6px;padding:5px 9px;font-size:12px;font-weight:600;cursor:pointer;background:transparent;color:#333}
.lang svg{width:22px;height:15px;border-radius:2px;box-shadow:0 0 0 1px rgba(0,0,0,.15)}
.lang.active{background:#eef3f8;border-color:var(--navy);color:var(--navy)}
.lang:hover{background:#f3f5f7}
.sheet{padding:76px 0 40px}
.report{display:none}.report.active{display:block}
.page{width:210mm;height:297mm;margin:0 auto 10mm;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.15),0 8px 24px rgba(0,0,0,.08);padding:16mm 17mm 16mm;position:relative;overflow:hidden;font-size:9pt;line-height:1.38}
.page .foot{position:absolute;left:17mm;right:17mm;bottom:8mm;display:flex;justify-content:space-between;font-size:7pt;color:#666;border-top:1px solid #e1e5ea;padding-top:4px}
h1{font-family:Georgia,"Times New Roman",serif;color:var(--navy);font-size:15pt;margin:10pt 0 6pt;font-weight:700}
h2{font-family:Georgia,"Times New Roman",serif;color:var(--navy);font-size:11.5pt;margin:8pt 0 4pt;font-weight:700}
p{margin:0 0 5pt}
.small{font-size:7.5pt;color:#444;line-height:1.3}
.cap{font-size:8pt;color:#444;font-style:italic;margin:2pt 0 8pt}
.cover{padding-top:22mm}
.cover .title{font-family:Georgia,"Times New Roman",serif;font-size:22pt;line-height:1.2;color:var(--navy);font-weight:700;margin:0 0 4pt}
.cover .sub{font-size:11pt;color:#444;margin:0 0 3pt}
.cover .rule{height:2px;background:var(--navy);margin:6mm 0 6mm;width:60mm}
table{border-collapse:collapse;width:100%;font-size:8pt;margin:3pt 0 4pt;table-layout:fixed}
th,td{border:1px solid var(--line);padding:2.5pt 3.5pt;vertical-align:middle;text-align:left;word-wrap:break-word}
th{background:var(--head);font-weight:700}
tr:nth-child(odd) td{background:var(--zebra)}
table.fs75{font-size:7.5pt}
figure{margin:4pt auto 2pt;text-align:center}
figure img{display:block;margin:0 auto;max-width:100%}
sub{font-size:70%}
@media print{
  @page{size:A4;margin:0}
  html,body{background:#fff}
  .toolbar{display:none}
  .sheet{padding:0}
  .page{margin:0;box-shadow:none;page-break-after:always;break-after:page}
  .page:last-child{page-break-after:auto;break-after:auto}
  .report{display:none}.report.active{display:block}
  tr:nth-child(odd) td{background:var(--zebra)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  th{background:var(--head)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

JS = """
const NAMES = %s;
function setLang(l){
  document.querySelectorAll('.report').forEach(r=>r.classList.toggle('active', r.dataset.lang===l));
  document.querySelectorAll('.lang').forEach(b=>b.classList.toggle('active', b.dataset.lang===l));
  document.documentElement.lang = l;
  document.title = NAMES[l].title;
  document.getElementById('brand-title').textContent = NAMES[l].title;
  document.getElementById('print-label').textContent = NAMES[l].print;
  document.getElementById('lang-label').textContent = NAMES[l].lang;
  try{localStorage.setItem('c061176_lang', l);}catch(e){}
}
document.querySelectorAll('.lang').forEach(b=>b.addEventListener('click',()=>setLang(b.dataset.lang)));
document.getElementById('print-btn').addEventListener('click',()=>window.print());
let start='tr'; try{start=localStorage.getItem('c061176_lang')||'tr';}catch(e){}
const q=new URLSearchParams(location.search).get('lang'); if(q&&NAMES[q]) start=q;
setLang(start);
"""

def esc(s): return s  # content already contains intended inline HTML (<b>, <sub>, <br/>)

def render_table(rows, colw, opts):
    tot = sum(colw)
    cls = ' class="fs75"' if opts.get("fs", 8) < 8 else ""
    h = [f"<table{cls}><colgroup>" + "".join(f'<col style="width:{w/tot*100:.1f}%">' for w in colw) + "</colgroup>"]
    h.append("<thead><tr>" + "".join(f"<th>{esc(str(c))}</th>" for c in rows[0]) + "</tr></thead><tbody>")
    for r in rows[1:]:
        h.append("<tr>" + "".join(f"<td>{esc(str(c))}</td>" for c in r) + "</tr>")
    h.append("</tbody></table>")
    return "".join(h)

def render_lang(lang):
    L = T[lang]
    pages, cur = [], []
    for b in build_content(lang):
        k = b[0]
        if k == "pagebreak":
            pages.append(cur); cur = []; continue
        if k == "cover":
            cur.append(f'<div class="cover"><div class="title">{b[1]}</div><div class="sub">{b[2]}</div><div class="rule"></div>' + "".join(f'<div class="sub">{x}</div>' for x in b[3]) + "</div>")
        elif k == "h1": cur.append(f"<h1>{b[1]}</h1>")
        elif k == "h2": cur.append(f"<h2>{b[1]}</h2>")
        elif k == "p": cur.append(f"<p>{b[1]}</p>")
        elif k == "small": cur.append(f'<p class="small">{b[1]}</p>')
        elif k == "cap": cur.append(f'<p class="cap">{b[1]}</p>')
        elif k == "table": cur.append(render_table(b[1], b[2], b[3]))
        elif k == "fig":
            cur.append(f'<figure><img src="{img_data_uri(b[1])}" style="width:{b[2]}mm" alt=""><figcaption class="cap">{b[3]}</figcaption></figure>')
    if cur: pages.append(cur)
    out = [f'<section class="report" data-lang="{lang}">']
    for i, pg in enumerate(pages, 1):
        out.append(f'<div class="page">{"".join(pg)}<div class="foot"><span>{L["footer"].format(date=today)}</span><span>{L["page"]} {i}</span></div></div>')
    out.append("</section>")
    return "\n".join(out), len(pages)

def main():
    names = {l: {"title": T[l]["title"], "print": T[l]["print_btn"], "lang": T[l]["lang_label"]} for l in LANGS}
    import json
    sections, counts = [], {}
    for l in LANGS:
        s, n = render_lang(l); sections.append(s); counts[l] = n
    lang_buttons = "".join(f'<button class="lang" data-lang="{l}" title="{T[l]["lang_name"]}">{FLAGS[l]}<span>{l.upper()}</span></button>' for l in LANGS)
    doc = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{T['tr']['title']}</title>
<style>{CSS}</style>
</head>
<body>
<div class="toolbar">
  <button class="btn" id="print-btn"><svg viewBox="0 0 24 24"><path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v7H6z"/></svg><span id="print-label">PDF</span></button>
  <div class="brand"><span id="brand-title"></span><small>{M["name"]} · {M["code"]} · AISI {G["grade"]} · {today}</small></div>
  <div class="langs"><span class="lbl" id="lang-label">Dil</span>{lang_buttons}</div>
</div>
<div class="sheet">
{chr(10).join(sections)}
</div>
<script>{JS % json.dumps(names, ensure_ascii=False)}</script>
</body>
</html>"""
    open(OUT_HTML, "w", encoding="utf-8").write(doc)
    print("HTML written:", OUT_HTML, "pages per language:", counts, "size MB:", round(os.path.getsize(OUT_HTML) / 1e6, 1))

if __name__ == "__main__":
    main()
