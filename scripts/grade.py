# -*- coding: utf-8 -*-
"""Stainless grade configuration. Select with environment variable GRADE=316 (default) or GRADE=304."""
import os

GRADES = {
    "316": dict(grade="316", en="1.4401", rho_sheet=8.00, rho_fastener=8.00, fastener="A4", rho_txt_tr="8,0", rho_txt_en="8.0", other="304",
                result_dir="output", report_dir="AISI 316"),
    "304": dict(grade="304", en="1.4301", rho_sheet=7.90, rho_fastener=7.90, fastener="A2", rho_txt_tr="7,9", rho_txt_en="7.9", other="316",
                result_dir="output_304", report_dir="AISI 304"),
}
G = GRADES[os.environ.get("GRADE", "316")]

# ---- machine folder: set MACHINE env var (folder name or path containing machine.json + STEP) ----
MACHINE_DIR = os.environ.get("MACHINE")
if not MACHINE_DIR or not os.path.isfile(os.path.join(MACHINE_DIR, "machine.json")):
    raise SystemExit("MACHINE ortam degiskeni ayarlanmali ve klasorde machine.json bulunmali. Ornek:  set MACHINE=KBN 1B P DS MULTİ 1350")
import json as _json
M = _json.load(open(os.path.join(MACHINE_DIR, "machine.json"), encoding="utf-8"))
RESULT_DIR = os.path.join(MACHINE_DIR, G["result_dir"])
REPORT_DIR = os.path.join(MACHINE_DIR, G["report_dir"])
MESH_DIR = os.path.join(MACHINE_DIR, "output", "meshes")          # geometry is grade independent
INSTANCES = os.path.join(MACHINE_DIR, "output", "instances.json")
STEP_PATH = os.path.join(MACHINE_DIR, M["step"])

def display(s):
    """Replace internal 316-based class names / labels for display when another grade is active."""
    if G["grade"] == "316" or not isinstance(s, str):
        return s
    reps = [("304 veya karbon", "316 veya karbon"), ("304 or carbon", "316 or carbon"), ("304 oder Kohlenstoffstahl", "316 oder Kohlenstoffstahl"),
            ("AISI 316", "AISI " + G["grade"]), ("AISI316", "AISI" + G["grade"]), ("1.4401", G["en"]),
            ("8,0 kg/dm³", G["rho_txt_tr"] + " kg/dm³"), ("8.0 kg/dm³", G["rho_txt_en"] + " kg/dm³"),
            ("A4 (316)", G["fastener"] + " (" + G["grade"] + ")"), ("A4 inox", G["fastener"] + " inox"), ("A4 stainless", G["fastener"] + " stainless"),
            ("A4-Edelstahl", G["fastener"] + "-Edelstahl"), ("A4_INOX", G["fastener"] + "_INOX"), ("(316)", "(" + G["grade"] + ")")]
    for a, b in reps:
        s = s.replace(a, b)
    return s

def localize(obj):
    """Recursively apply display() to all strings in a nested dict/list structure."""
    if isinstance(obj, str): return display(obj)
    if isinstance(obj, dict): return {k: localize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return type(obj)(localize(v) for v in obj)
    return obj
