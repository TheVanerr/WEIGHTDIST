"""Extract the Turkish section (pages 1-12) of the multilingual PDF into a separate 12-page PDF."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from grade import REPORT_DIR
import pymupdf
src = os.path.join(REPORT_DIR, "C061176_Ayak_Yuk_Dagilimi_Raporu_TR_EN_DE.pdf")
dst = os.path.join(REPORT_DIR, "C061176_Ayak_Yuk_Dagilimi_Raporu.pdf")
d = pymupdf.open(src); n = len(d) // 3
tr = pymupdf.open(); tr.insert_pdf(d, from_page=0, to_page=n - 1); tr.save(dst)
print("written", dst, n, "pages")
