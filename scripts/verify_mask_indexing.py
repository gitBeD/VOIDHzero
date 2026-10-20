#!/usr/bin/env python3
"""Prueft, welche Index-Konvention zur VAST-MASK-HDU passt.

Selbstkonsistenz: Jede Galaxie des Katalogs muss in einer True-Zelle der Maske
liegen. Die richtige Konvention liefert ~100 %, falsche deutlich weniger.
Rein lesend. Keine Schwelle, keine Entscheidung.

Verwendung:
  python3 verify_mask_indexing.py --voidfinder-output ..._VoidFinder_Output.fits \
      --catalog VAST/example_scripts/vollim_dr7_cbp_102709.dat
"""
import argparse
import numpy as np

def conventions(res):
    f = np.floor
    return {
        "A  mask[ra*res, (dec+90)*res]   (Adapter-Annahme)": lambda ra, de: (f(ra*res), f((de+90)*res)),
        "B  mask[(dec+90)*res, ra*res]   (transponiert)":    lambda ra, de: (f((de+90)*res), f(ra*res)),
        "C  mask[ra*res, dec*res]         (ohne +90)":        lambda ra, de: (f(ra*res), f(de*res)),
        "D  mask[ra*res, (90-dec)*res]    (Dec gespiegelt)":  lambda ra, de: (f(ra*res), f((90-de)*res)),
    }

def evaluate(mask, res, ra, de):
    """Rueckgabe: {name: (Anteil in True-Zelle, Anteil ausserhalb des Index-Bereichs)}"""
    out = {}
    for name, fn in conventions(res).items():
        i, j = fn(np.asarray(ra, float), np.asarray(de, float))
        i, j = i.astype(int), j.astype(int)
        inside = (i >= 0) & (i < mask.shape[0]) & (j >= 0) & (j < mask.shape[1])
        hit = np.zeros(len(i), bool)
        hit[inside] = mask[i[inside], j[inside]].astype(bool)
        out[name] = (hit.mean(), 1.0 - inside.mean())
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voidfinder-output", required=True)
    ap.add_argument("--catalog", required=True)
    a = ap.parse_args()
    from astropy.io import fits
    from astropy.table import Table
    with fits.open(a.voidfinder_output, memmap=False) as h:
        print("HDUs:", [x.name for x in h])
        mask = np.array(h["MASK"].data, copy=True)
        hdr = h["MASK"].header
        res = int(hdr.get("MASKRES", hdr.get("RESOLUTI", 1)))
        print("MASK: shape", mask.shape, "dtype", mask.dtype, "res", res,
              "MASKRES" in hdr and "(MASKRES)" or "(RESOLUTI oder Default 1)")
    print(f"True-Zellen: {int(mask.astype(bool).sum())} von {mask.size} ({100*mask.astype(bool).mean():.1f} %)")
    t = Table.read(a.catalog, format="ascii.commented_header") if a.catalog.endswith(".dat") else Table.read(a.catalog)
    ra = np.asarray(t["ra"], float); de = np.asarray(t["dec"], float)
    print(f"Katalog: {len(t)} Galaxien, ra {ra.min():.2f}..{ra.max():.2f}, dec {de.min():.2f}..{de.max():.2f}\n")
    print(f"{'Konvention':<52} {'in True-Zelle':>14} {'ausserhalb Index':>17}")
    for name, (hit, oob) in evaluate(mask, res, ra, de).items():
        print(f"{name:<52} {100*hit:>13.2f}% {100*oob:>16.2f}%")

if __name__ == "__main__":
    main()
