#!/usr/bin/env python3
"""
update_titan.py — Reads BOM CSV and AUDIT_RESULTS.md from the private KIL folder
and prints component/BOM data that can be embedded in titan.html.

Usage:
    python update_titan.py

Reads from:
    ../Kinetic Intelligence Lab/designs/TITAN_FOC/bom/TITAN_FOC_BOM.csv
    ../Kinetic Intelligence Lab/designs/TITAN_FOC/AUDIT_RESULTS.md
"""

import csv
import re
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PRIVATE_DIR = SCRIPT_DIR.parent / "Kinetic Intelligence Lab"
BOM_CSV = PRIVATE_DIR / "designs" / "TITAN_FOC" / "bom" / "TITAN_FOC_BOM.csv"
AUDIT_MD = PRIVATE_DIR / "designs" / "TITAN_FOC" / "AUDIT_RESULTS.md"
SCHEMATICS_DIR = SCRIPT_DIR / "schematics"


def parse_bom(csv_path):
    """Parse BOM CSV into list of dicts."""
    entries = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comment = row.get("Comment", "").strip().strip('"')
            designators = row.get("Designator", "").strip().strip('"')
            footprint = row.get("Footprint", "").strip().strip('"')
            lcsc = row.get("LCSC Part Number", "").strip().strip('"')
            refs = [r.strip() for r in designators.split(",") if r.strip()]
            entries.append({
                "comment": comment,
                "designators": refs,
                "footprint": footprint,
                "lcsc": lcsc,
                "qty": len(refs),
            })
    return entries


def parse_audit(md_path):
    """Parse AUDIT_RESULTS.md component table."""
    components = []
    table_re = re.compile(
        r"\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(\S+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(-?[\d.]+)\s*\|"
    )
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            m = table_re.match(line.strip())
            if m:
                components.append({
                    "num": int(m.group(1)),
                    "ref": m.group(2),
                    "value": m.group(3).strip(),
                    "footprint": m.group(4).strip(),
                    "layer": m.group(5),
                    "x": float(m.group(6)),
                    "y": float(m.group(7)),
                    "rot": float(m.group(8)),
                })
    return components


def generate_js_components(components):
    """Generate JavaScript array literal for component data."""
    lines = ["const COMPONENTS = ["]
    for c in components:
        ref = c["ref"].replace("'", "\\'")
        val = c["value"].replace("'", "\\'")
        fp = c["footprint"].replace("'", "\\'")
        layer = c["layer"]
        lines.append(
            f"  {{ref:'{ref}',value:'{val}',footprint:'{fp}',"
            f"layer:'{layer}',x:{c['x']},y:{c['y']},rot:{c['rot']}}},"
        )
    lines.append("];")
    return "\n".join(lines)


def generate_js_bom(bom_entries):
    """Generate JavaScript array literal for BOM data."""
    lines = ["const BOM_DATA = ["]
    for e in bom_entries:
        comment = e["comment"].replace("'", "\\'")
        fp = e["footprint"].replace("'", "\\'")
        lcsc = e["lcsc"].replace("'", "\\'")
        refs = ",".join(e["designators"])
        lines.append(
            f"  {{comment:'{comment}',designators:'{refs}',"
            f"footprint:'{fp}',lcsc:'{lcsc}',qty:{e['qty']}}},"
        )
    lines.append("];")
    return "\n".join(lines)


def copy_schematics():
    """Copy schematic SVGs from known locations to schematics/ dir."""
    svg_sources = [
        PRIVATE_DIR / "designs" / "TITAN_FOC",
        Path(os.path.expanduser("~")) / "Downloads" / "sch_svgs",
    ]
    SCHEMATICS_DIR.mkdir(exist_ok=True)
    copied = 0
    for src_dir in svg_sources:
        if not src_dir.exists():
            continue
        for svg in src_dir.glob("*.svg"):
            if "TITAN_FOC" in svg.name:
                dest = SCHEMATICS_DIR / svg.name
                shutil.copy2(svg, dest)
                copied += 1
    return copied


def main():
    errors = []
    if not BOM_CSV.exists():
        errors.append(f"BOM CSV not found: {BOM_CSV}")
    if not AUDIT_MD.exists():
        errors.append(f"AUDIT_RESULTS.md not found: {AUDIT_MD}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    bom = parse_bom(BOM_CSV)
    components = parse_audit(AUDIT_MD)

    total_bom_refs = sum(e["qty"] for e in bom)
    lcsc_count = sum(1 for e in bom if e["lcsc"] and e["lcsc"] not in ("DIGIKEY_ONLY", "VERIFY_LCSC", ""))
    digikey_count = sum(1 for e in bom if e["lcsc"] == "DIGIKEY_ONLY")
    verify_count = sum(1 for e in bom if e["lcsc"] == "VERIFY_LCSC")

    print("=" * 60)
    print("TITAN_FOC Data Update")
    print("=" * 60)
    print(f"Components from AUDIT_RESULTS.md: {len(components)}")
    print(f"BOM line items: {len(bom)}")
    print(f"Total BOM references: {total_bom_refs}")
    print(f"LCSC parts (JLCPCB assemblable): {lcsc_count}")
    print(f"DigiKey-only parts: {digikey_count}")
    print(f"VERIFY_LCSC parts: {verify_count}")
    print()

    print("// --- Paste this into titan.html <script> section ---")
    print()
    print(generate_js_components(components))
    print()
    print(generate_js_bom(bom))
    print()

    svg_count = copy_schematics()
    if svg_count:
        print(f"// Copied {svg_count} schematic SVGs to schematics/")
    else:
        print("// No new schematic SVGs found to copy")

    print()
    print(f"// Updated {len(components)} components, {len(bom)} BOM entries, {svg_count} schematics")


if __name__ == "__main__":
    main()
