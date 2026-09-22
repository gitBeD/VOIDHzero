#!/usr/bin/env python3
"""Demo-Durchlauf durch alle sechs Schichten, auf rein synthetischen Daten.

Dies ist KEINE wissenschaftliche Analyse (siehe Warnhinweise in
layer1_tracers/demo_adapter.py und layer2_voidfinder/demo_adapter.py) --
es demonstriert lediglich, dass die Schichtgrenzen aus Exposé Abschnitt 6
tatsaechlich funktionieren: Schicht 0 laedt die Referenzkosmologie, Schicht 1
liefert einen Tracer-Katalog, Schicht 2 findet Voids und klassifiziert,
Schicht 3 aggregiert (hier: zwei "Algorithmen" durch zweimaliges Klassifizieren
mit verschiedenen Seeds simuliert, als Stand-in fuer RF-B), Schicht 4 fittet
den Umgebungs-Step und Schicht 5 propagiert ihn auf einen H0-Bias.

Verwendung:
    python3 scripts/run_demo_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from voidh0.layer0_cosmology import load_reference_cosmology  # noqa: E402
from voidh0.layer1_tracers import DemoTracerAdapter  # noqa: E402
from voidh0.layer2_voidfinder import DemoVoidFinderAdapter  # noqa: E402
from voidh0.layer3_environment import assign_environment  # noqa: E402
from voidh0.layer4_statistics import fit_environment_step  # noqa: E402
from voidh0.layer5_interpretation import propagate_to_H0_bias  # noqa: E402


def main() -> None:
    print("=== Schicht 0: Referenzkosmologie ===")
    cosmo = load_reference_cosmology()
    print(f"  {cosmo.name}: H0={cosmo.H0_km_s_Mpc} km/s/Mpc, Om0={cosmo.Om0}")

    print("\n=== Schicht 1: Tracer (Demo-Adapter, SYNTHETISCH) ===")
    tracer_adapter = DemoTracerAdapter(n_objects=2000, n_randoms=20000, seed=42)
    tracers = tracer_adapter.load()
    print(f"  Survey '{tracers.survey_name}': {tracers.n_objects} Objekte, "
          f"{tracers.n_randoms} Randoms, z in {tracer_adapter.redshift_limits()}")

    print("\n=== Schicht 2: Void-Finder (Demo-Adapter, SYNTHETISCH) ===")
    # Zwei "unabhaengige" Laeufe mit unterschiedlichem Seed als Stand-in fuer
    # RF-B (mehrere unabhaengige Void-Finder-Algorithmen).
    finder_a = DemoVoidFinderAdapter(n_voids=10, seed=11)
    finder_b = DemoVoidFinderAdapter(n_voids=10, seed=23)

    obj_mask = ~tracers.is_random
    ra_o, dec_o, z_o = tracers.ra_deg[obj_mask], tracers.dec_deg[obj_mask], tracers.z[obj_mask]
    ids_o = tracers.object_id[obj_mask]
    mass_o = tracers.extra["log_mstar"][obj_mask]

    voids_a = finder_a.find_voids(tracers)
    voids_b = finder_b.find_voids(tracers)
    labels_a = finder_a.classify(ra_o, dec_o, z_o, voids_a)
    labels_b = finder_b.classify(ra_o, dec_o, z_o, voids_b)
    print(f"  Algorithmus A ({finder_a.algorithm_name}): {len(voids_a)} Voids gefunden")
    print(f"  Algorithmus B ({finder_b.algorithm_name}): {len(voids_b)} Voids gefunden")

    print("\n=== Schicht 3: Umgebungszuordnung (Robustheitsflag) ===")
    assignment = assign_environment(
        ids_o, {finder_a.algorithm_name: labels_a, finder_b.algorithm_name: labels_b}
    )
    for level in ("robust", "marginal", "edge_excluded"):
        n = int(np.sum(assignment.robustness_flag == level))
        print(f"  {level:>14s}: {n} Objekte")

    print("\n=== Schicht 4: Statistikmodell (Umgebungs-Step) ===")
    usable = assignment.environment_class != "unclassified"
    env_indicator = (assignment.environment_class[usable] == "void").astype(float)
    mass_usable = mass_o[usable]

    # Rein synthetischer, injizierter Hubble-Residual-Stand-in (kein echter
    # Distanzindikator-Output -- reine Demonstration der Schnittstelle).
    rng = np.random.default_rng(0)
    demo_residual = 0.05 * env_indicator + 0.02 * (mass_usable - mass_usable.mean()) \
        + rng.normal(0, 0.1, size=usable.sum())

    fit_result = fit_environment_step(demo_residual, env_indicator, mass_usable)
    print("  " + fit_result.summary().replace("\n", "\n  "))

    print("\n=== Schicht 5: Propagation auf H0 (RF-E) ===")
    env_step_val, _ = fit_result.env_step_mag()
    demo_delta_f_void = 0.15  # Platzhalter fuer WP2/RF-C-Ergebnis
    bias = propagate_to_H0_bias(
        delta_mu_env_mag=env_step_val,
        delta_f_void=demo_delta_f_void,
        H0_ref_km_s_Mpc=73.0,
    )
    print("  " + bias.summary().replace("\n", "\n  "))

    print("\nHinweis: Alle Zahlen in diesem Lauf sind synthetisch/demonstrativ "
          "(siehe Docstrings der Demo-Adapter) und haben keinerlei "
          "wissenschaftliche Aussagekraft.")


if __name__ == "__main__":
    main()
