#!/usr/bin/env python3
"""Welche Einheit liefert VASTs z_to_comoving_dist? (Mpc/h oder Mpc)

Ruft die Funktion des tatsaechlich IMPORTIERTEN vast-Pakets mit (Omega_M, h)
auf und vergleicht mit zwei Referenzformeln:
   R1 = (c/100) * Integral dz/E(z)      -> Mpc/h  (h kuerzt sich heraus)
   R2 = R1 / h                          -> Mpc
Rein lesend. Keine Entscheidung ueber Schwellen.
"""
import numpy as np
from scipy.integrate import quad

C = 299792.458

def ref_mpc_over_h(z, om):
    f = lambda zz: 1.0 / np.sqrt(om * (1 + zz) ** 3 + (1 - om))
    return (C / 100.0) * np.array([quad(f, 0, zi)[0] for zi in np.atleast_1d(z)])

def classify(fn, om, hs, zs):
    out = []
    for h in hs:
        got = np.asarray(fn(np.asarray(zs, dtype=np.float32), om, h), dtype=float)
        r1 = ref_mpc_over_h(zs, om)
        r2 = r1 / h
        e1 = np.max(np.abs(got / r1 - 1)); e2 = np.max(np.abs(got / r2 - 1))
        label = "Mpc/h (R1)" if e1 < 1e-3 else ("Mpc (R2)" if e2 < 1e-3 else "WEDER NOCH")
        out.append((h, e1, e2, label, got[-1]))
    return out

def main():
    import vast
    print("vast importiert aus:", vast.__file__)
    print("vast Version:", getattr(vast, "__version__", "unbekannt"))
    try:
        from vast.voidfinder.preprocessing import z_to_comoving_dist as fn
    except ImportError:
        from vast.voidfinder.distance import z_to_comoving_dist as fn
    zs = [0.001, 0.01, 0.05, 0.1]
    print(f"\nOmega_M = 0.315, z = {zs}")
    print(f"{'h':>6} {'max|rel.Abw| vs Mpc/h':>24} {'vs Mpc':>10}  Einordnung   D(z=0.1)")
    for h, e1, e2, label, last in classify(fn, 0.315, [1.0, 0.674], zs):
        print(f"{h:>6} {e1:>24.2e} {e2:>10.2e}  {label:<11}  {last:.2f}")
    print("\nHinweis: Mpc/h bedeutet, dass die Ausgabe NICHT von h abhaengt (D(z=0.1) fuer h=1 und h=0.674 gleich).")

if __name__ == "__main__":
    main()
