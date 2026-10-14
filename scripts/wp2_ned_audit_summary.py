#!/usr/bin/env python3
"""WP2 -- Auswertung von wp2_ned_position_audit.csv (alle Hosts).

Rein lesend/beschreibend. Aendert keine Datei ausser der optionalen --out-CSV.
Spaltennamen entsprechen der echten Audit-Ausgabe (NED_*-Praefix).

Beschreibt, wie sich NEDs Fiducial-Position zur Gesamtheit der NED-
Positionsmessungen verhaelt. Wichtig zur Interpretation: die NED-Positionsliste
mischt Messungen sehr unterschiedlicher Qualitaet und Epoche (Maxima von
37-129" kommen vor). Der Median ueber diese Liste ist deshalb ein
BESCHREIBENDES Streumass, kein Wahrheitswert fuer das Galaxienzentrum.
Das Skript trifft keine Entscheidung ueber Schwellen.
"""
from __future__ import annotations

import argparse
import csv
import statistics

C_COUNT = "NED_position_count"
C_MIN = "NED_min_separation_arcsec"
C_MED = "NED_median_separation_arcsec"
C_MAX = "NED_max_separation_arcsec"
C_N10 = "NED_count_le_1.0_arcsec"
C_N20 = "NED_count_le_2.0_arcsec"
C_FCOUNT = "NED_fiducial_count"
C_FSEP = "NED_fiducial_separation_arcsec"
C_FREF = "NED_fiducial_reference"
REQUIRED = [C_COUNT, C_MIN, C_MED, C_MAX, C_N10, C_N20, C_FCOUNT, C_FSEP, C_FREF,
            "source_host", "normalized_query_name", "audit_status"]


def f(x):
    if x is None or str(x).strip() in ("", "None", "nan"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit-csv", default="data/external/wp2_ned_position_audit.csv")
    ap.add_argument("--threshold", type=float, default=1.0,
                    help="Schwelle in arcsec, nur zum Einsortieren der Anzeige (keine Entscheidung)")
    ap.add_argument("--out", default=None, help="optional: Pro-Host-Tabelle als CSV schreiben")
    a = ap.parse_args()

    with open(a.audit_csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Spalten fehlen in {a.audit_csv}: {missing}\nVorhanden: {reader.fieldnames}")
        rows = list(reader)

    ok = [r for r in rows if r["audit_status"] == "resolved"]
    nok = [r for r in rows if r["audit_status"] != "resolved"]
    T = a.threshold
    print(f"{len(rows)} Hosts, {len(ok)} mit audit_status=resolved, {len(nok)} andere.")
    for r in nok:
        print(f"  NICHT ausgewertet: {r['source_host']} status={r['audit_status']} note={r['audit_note']}")

    recs = []
    for r in ok:
        n = f(r[C_COUNT])
        rec = {
            "source_host": r["source_host"], "name": r["normalized_query_name"], "n": n,
            "min": f(r[C_MIN]), "med": f(r[C_MED]), "max": f(r[C_MAX]),
            "fid": f(r[C_FSEP]), "fid_ref": r[C_FREF], "fid_count": f(r[C_FCOUNT]),
            "frac1": (f(r[C_N10]) / n) if n else None,
            "frac2": (f(r[C_N20]) / n) if n else None,
        }
        recs.append(rec)

    odd = [x for x in recs if x["fid_count"] != 1]
    if odd:
        print(f"\nHINWEIS: {len(odd)} Hosts haben NED_fiducial_count != 1: "
              + ", ".join(f"{x['source_host']}({x['fid_count']})" for x in odd))

    meds = sorted(x["med"] for x in recs if x["med"] is not None)
    fids = sorted(x["fid"] for x in recs if x["fid"] is not None)
    print(f"\n=== Verteilung ueber {len(recs)} Hosts (Abstand zu SIMBAD, arcsec) ===")
    print(f"  Fiducial:  min={fids[0]:.3f}  median={statistics.median(fids):.3f}  max={fids[-1]:.3f}")
    print(f"  Median:    min={meds[0]:.3f}  median={statistics.median(meds):.3f}  max={meds[-1]:.3f}")

    fid_pass = [x for x in recs if x["fid"] is not None and x["fid"] <= T]
    fid_fail = [x for x in recs if x["fid"] is not None and x["fid"] > T]
    print(f"\n=== Fiducial-Regel (<= {T}\") ===")
    print(f"  besteht: {len(fid_pass)}   besteht nicht: {len(fid_fail)}")

    def med_ok(x):
        return x["med"] is not None and x["med"] <= T
    both = [x for x in fid_pass if med_ok(x)]
    fid_only_pass = [x for x in fid_pass if not med_ok(x)]
    med_only_pass = [x for x in fid_fail if med_ok(x)]
    both_fail = [x for x in fid_fail if not med_ok(x)]
    print(f"\n=== Kreuztabelle Fiducial x Median (Schwelle {T}\") ===")
    print(f"                       Median <= {T}\"   Median > {T}\"")
    print(f"  Fiducial <= {T}\"       {len(both):>6}          {len(fid_only_pass):>6}")
    print(f"  Fiducial >  {T}\"       {len(med_only_pass):>6}          {len(both_fail):>6}")

    def show(title, items):
        print(f"\n--- {title} ({len(items)}) ---")
        print(f"  {'host':<8} {'fid':>8} {'median':>8} {'min':>8} {'n':>4} {'<=1\"':>6} {'<=2\"':>6}  fiducial-ref")
        for x in sorted(items, key=lambda z: z["fid"] if z["fid"] is not None else 0, reverse=True):
            print(f"  {x['source_host']:<8} {x['fid']:>8.3f} {x['med']:>8.3f} {x['min']:>8.3f} "
                  f"{int(x['n']):>4} {x['frac1']:>6.0%} {x['frac2']:>6.0%}  {x['fid_ref']}")

    show("Fiducial > Schwelle, Median <= Schwelle", med_only_pass)
    show("Fiducial > Schwelle UND Median > Schwelle", both_fail)
    show("Fiducial <= Schwelle, aber Median > Schwelle", fid_only_pass)

    from collections import Counter
    refs = Counter(x["fid_ref"] for x in recs)
    print("\n=== Fiducial-Referenzen (alle Hosts) ===")
    for ref, cnt in refs.most_common():
        fails = sum(1 for x in fid_fail if x["fid_ref"] == ref)
        print(f"  {ref:<28} {cnt:>3} Hosts, davon Schwelle verfehlt: {fails}")

    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(recs[0].keys()))
            w.writeheader()
            w.writerows(recs)
        print(f"\nPro-Host-Tabelle: {a.out}")


if __name__ == "__main__":
    main()
