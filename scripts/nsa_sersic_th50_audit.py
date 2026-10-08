#!/usr/bin/env python3
"""Rein lesende Stichprobenpruefung: wie haeufig ist SERSIC_TH50 == 159.7578125
(oder ein anderer per --value angegebener Verdachtswert) im gesamten NSA-
Katalog, und welche Begleitwerte (SERSIC_N/BA/PHI/OK, PETRO_TH50) haben die
betroffenen Eintraege?

Rein diagnostisch. Schreibt/aendert nichts an bestehenden Skripten oder Daten.

Verwendung:
    python3 scripts/nsa_sersic_th50_audit.py --nsa /pfad/zu/nsa_v1_0_1.fits
"""
from __future__ import annotations

import argparse

import numpy as np
from astropy.io import fits


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nsa", required=True)
    p.add_argument("--value", type=float, default=159.7578125)
    p.add_argument("--atol", type=float, default=1e-6, help="Toleranz fuer den Exakt-Vergleich")
    args = p.parse_args()

    with fits.open(args.nsa, memmap=True) as hdul:
        d = hdul[1].data
        th50 = np.array(d["SERSIC_TH50"], copy=True).astype(float)
        n = len(th50)

        hit = np.isclose(th50, args.value, atol=args.atol, rtol=0)
        n_hit = int(np.sum(hit))
        print(f"NSA-Katalog: {n} Galaxien")
        print(f"SERSIC_TH50 == {args.value} (atol={args.atol}): {n_hit} Treffer "
              f"({100 * n_hit / n:.4f} %)")

        finite = th50[np.isfinite(th50)]
        uniq, counts = np.unique(finite, return_counts=True)
        order = np.argsort(-counts)
        print(f"\nDistinkte SERSIC_TH50-Werte im Katalog: {len(uniq)}")
        print("Top 10 haeufigste Werte (Wert: Anzahl):")
        for i in order[:10]:
            marker = "  <-- Verdachtswert" if np.isclose(uniq[i], args.value, atol=args.atol) else ""
            print(f"  {uniq[i]:.7f}: {counts[i]}{marker}")

        if n_hit > 0:
            print(f"\nBegleitwerte der {n_hit} Treffer (erste 20):")
            idx = np.where(hit)[0][:20]
            names = d.columns.names
            extra_cols = [c for c in ("NSAID", "RA", "DEC", "SERSIC_N", "SERSIC_BA",
                                        "SERSIC_PHI", "SERSIC_OK", "PETRO_TH50", "Z") if c in names]
            header = "  ".join(f"{c:>12}" for c in extra_cols)
            print("  " + header)
            for i in idx:
                vals = "  ".join(f"{float(d[c][i]):12.5f}" if d[c].dtype.kind != "S"
                                  else f"{str(d[c][i]).strip():>12}" for c in extra_cols)
                print("  " + vals)

            ra_hit = np.array(d["RA"], copy=True)[hit]
            dec_hit = np.array(d["DEC"], copy=True)[hit]
            print(f"\nRA-Spannweite der Treffer: {ra_hit.min():.3f} - {ra_hit.max():.3f}")
            print(f"Dec-Spannweite der Treffer: {dec_hit.min():.3f} - {dec_hit.max():.3f}")
            print("(Falls das nur wenige Grad umfasst -> lokales Deblending-Cluster, "
                  "nicht katalogweiter Cutoff. Falls ueber den ganzen Himmel verteilt "
                  "-> spricht fuer einen algorithmischen Grenzwert.)")


if __name__ == "__main__":
    main()
