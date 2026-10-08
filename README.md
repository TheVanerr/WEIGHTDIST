# Weight Distribution on Feet — ortak hesap/rapor motoru

Kok klasor ortak motoru icerir; her makine kendi klasorunde tutulur.

```
WEIGHT DISTRUBUTION/
  .venv/, requirements.txt, scripts/          <- ortak motor (STEP okuma, hesap, 3D render, PDF/HTML rapor)
  KBN 1B P DS MULTİ 1350/                     <- makine klasoru (C061176)
     C061176.STEP
     machine.json                             <- makineye ozgu ayarlar
     output/        (316 ara sonuclar: instances.json, meshes/, summary.json, fig_tr|en|de/)
     output_304/    (304 ara sonuclar)
     AISI 316/      (raporlar: 12 sayfa TR PDF, 36 sayfa TR+EN+DE PDF, HTML, xlsx)
     AISI 304/
```

## Bir makine icin calistirma
Ortam degiskenleri: `MACHINE` = makine klasoru, `GRADE` = 316 (varsayilan) veya 304.
```
set MACHINE=KBN 1B P DS MULTİ 1350
set GRADE=316
.venv\Scripts\python.exe scripts\extract_step.py            # STEP -> output/instances.json + meshes (yalnizca bir kez, kaliteden bagimsiz)
.venv\Scripts\python.exe -X utf8 scripts\compute.py          # kutle, AM, ayak yukleri -> summary.json, xlsx
.venv\Scripts\python.exe -X utf8 scripts\figures.py          # 3D render + grafikler (tr en de)
.venv\Scripts\python.exe -X utf8 scripts\report_multi.py     # 36 sayfalik PDF (TR+EN+DE) -> "<makine>/AISI <kalite>/"
.venv\Scripts\python.exe -X utf8 scripts\html_report.py      # HTML rapor (dil secimi + PDF ciktisi butonu)
.venv\Scripts\python.exe -X utf8 scripts\tr_pdf.py           # 36 sayfalik PDF'ten 12 sayfalik TR PDF
```
`set GRADE=304` ile ayni adimlar (extract_step haric) 304 icin tekrarlanir.

## Yeni makine eklerken
1. Yeni klasor olustur, STEP dosyasini ve `machine.json` dosyasini koy (ornek: KBN klasorundeki dosya).
   machine.json alanlari: step, feet_part (ayak taban parcasi), pad_d_mm, trolley_root (varsa araba alt montaji),
   caster_parts, flex_panel_token (elektrik panosu alt montaji), pvc_flex_parts, explicit_materials
   (pompa/motor/fan/hortum/pedal vb. parca -> malzeme sinifi), tank (ic olculer ve su seviyesi), basket_path_token, payload_kg.
2. Parca sinif/yogunluk tablosu `scripts/compute.py` icindeki `MAT`; kalite tanimlari `scripts/grade.py`.
3. Rapor metinleri `scripts/i18n.py` icinde (TR/EN/DE). Makineye ozgu aciklamalar (alt montaj tanimlari `sub_desc`,
   satin alma parcalari `comp` / `comp_desc`, genel boyutlar `model_rows`, yorum paragraflari) yeni makine icin guncellenmelidir.
4. `scripts/tools/highlight.py` parca tanimlama icin yardimci render araci (eksen/ayak/araba tespiti).

## Kurulum
```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt pymupdf networkx
```
