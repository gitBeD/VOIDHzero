#!/usr/bin/env python3
"""WP2-Diagnose: vierstufiges Flag je Pantheon+/SH0ES-Kalibrator-Wirt.

Siehe Exposé Abschnitt 9 und docs/architecture.md, Abschnitt
"WP2-Diagnosekriterium: Kalibrator-Umgebungs-Überlappung".

Verwendung:
    python3 scripts/wp2_calibrator_diagnosis.py \
        --pantheon data/external/Pantheon+SH0ES.dat \
        [--sdss-catalog /pfad/zu/vollim_dr7_cbp_102709.fits] \
        [--out data/external/wp2_diagnosis.csv]

Ohne --sdss-catalog wird nur Flag 1 (Position bekannt) berechnet; Flag 2
(SDSS-Spec-Match) bleibt "nicht geprüft" (kein SDSS-Katalog übergeben).
Flags 3/4 (Umgebungsklassifikation) sind aktuell IMMER "pending", weil noch
kein echter VoidFinder-Lauf vorliegt (siehe docs/architecture.md, Abschnitt
"echte VAST/VoidFinder-Anbindung" -- WSL2/Linux-Voraussetzung).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from voidh0.wp2_cove import (  # noqa: E402
    build_diagnosis_table,
    load_pantheon_calibrators,
    summarize,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pantheon", required=True, help="Pfad zu Pantheon+SH0ES.dat")
    parser.add_argument(
        "--sdss-catalog", default=None, help="Pfad zur SDSS-DR7-Katalogdatei (optional)"
    )
    parser.add_argument("--radius-arcsec", type=float, default=3.0)
    parser.add_argument("--z-tol", type=float, default=0.005)
    parser.add_argument("--out", default=None, help="CSV-Ausgabepfad (optional)")
    args = parser.parse_args()

    calibrators = load_pantheon_calibrators(args.pantheon)
    print(f"{len(calibrators)} Kalibrator-Zeilen (IS_CALIBRATOR=1) in {args.pantheon} gefunden.")

    sdss_ra = sdss_dec = sdss_z = None
    if args.sdss_catalog:
        from voidh0.layer1_tracers import SDSSDR7TracerAdapter

        adapter = SDSSDR7TracerAdapter(args.sdss_catalog, n_synthetic_randoms=0)
        tracers = adapter.load()
        objs = ~tracers.is_random
        sdss_ra = tracers.ra_deg[objs]
        sdss_dec = tracers.dec_deg[objs]
        sdss_z = tracers.z[objs]
        print(f"SDSS-Katalog geladen: {len(sdss_ra)} Objekte.")
    else:
        print("Kein --sdss-catalog angegeben -- Flag 2 (SDSS-Spec-Match) wird übersprungen.")

    rows = build_diagnosis_table(
        calibrators,
        sdss_ra,
        sdss_dec,
        sdss_z,
        radius_arcsec=args.radius_arcsec,
        z_tol=args.z_tol,
    )

    print(f"\n{'CID':<14} {'z':>9} {'Position':>9} {'Quelle':>12} {'SDSS-Spec':>10} {'Umgebung':>10}")
    for r in rows:
        pos = "ja" if r.has_position else "NEIN"
        sdss = "-" if r.sdss_spec_match is None else ("ja" if r.sdss_spec_match else "nein")
        env = "pending" if r.environment_class is None else r.environment_class
        print(f"{r.cid:<14} {r.z:>9.5f} {pos:>9} {r.position_source:>12} {sdss:>10} {env:>10}")

    n_host = sum(1 for r in rows if r.position_source == "host")
    n_sn_fallback = sum(1 for r in rows if r.position_source == "sn_position")
    n_missing = sum(1 for r in rows if r.position_source == "missing")
    print("\n=== Positionsquelle (Transparenz fuer Flag 1) ===")
    print(f"  aus HOST_RA/HOST_DEC:  {n_host}")
    print(f"  Fallback auf SN-RA/DEC: {n_sn_fallback}")
    print(f"  keine Position:         {n_missing}")

    summary = summarize(rows)
    print("\n=== Zusammenfassung (kumulativ) ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "cid", "host_ra", "host_dec", "z", "has_position", "position_source",
                    "sdss_spec_match", "sdss_match_sep_arcsec",
                    "environment_robust", "environment_class",
                ]
            )
            for r in rows:
                writer.writerow(
                    [
                        r.cid, r.host_ra, r.host_dec, r.z, r.has_position, r.position_source,
                        r.sdss_spec_match, r.sdss_match_sep_arcsec,
                        r.environment_robust, r.environment_class,
                    ]
                )
        print(f"\nCSV geschrieben nach: {out_path}")


if __name__ == "__main__":
    main()
