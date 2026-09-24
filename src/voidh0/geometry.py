"""Gemeinsame geometrische Hilfsfunktionen, schichtunabhaengig.

`ra_dec_z_to_xyz` wird sowohl von Schicht 2 (`layer2_voidfinder.vast_adapter`,
fuer den Vergleich gegen VoidFinder-Spheres) als auch von Schicht 3
(`layer3_environment.density`, fuer die Voronoi-basierte Dichteschaetzung,
RF-D) gebraucht. Damit Schicht 3 nicht rueckwaerts von Schicht 2 abhaengt
(verstoesst gegen die Designregel aus Exposé Abschnitt 6: "Kein
Analyseschritt oberhalb von Schicht 2 darf ... survey-/void-finder-
spezifisches kennen"), lebt die Funktion hier, ausserhalb der
Schichten-Hierarchie, und wird von beiden importiert.
"""
from __future__ import annotations

import numpy as np

from .layer0_cosmology import ReferenceCosmology


def ra_dec_z_to_xyz(
    ra_deg: np.ndarray, dec_deg: np.ndarray, z: np.ndarray, cosmology: ReferenceCosmology
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wandelt (ra, dec, z) in kartesische (x, y, z) in h^-1 Mpc um.

    Rechtshaendiges System, dec von der Aequatorialebene aus gemessen,
    comoving distance aus der uebergebenen Schicht-0-Referenzkosmologie.
    Dieselbe Konvention wie VAST (`vast.voidfinder.ra_dec_to_xyz`).
    """
    ra_rad = np.deg2rad(np.asarray(ra_deg, dtype=float))
    dec_rad = np.deg2rad(np.asarray(dec_deg, dtype=float))
    r = np.atleast_1d(cosmology.comoving_distance_h1Mpc(z))

    x = r * np.cos(dec_rad) * np.cos(ra_rad)
    y = r * np.cos(dec_rad) * np.sin(ra_rad)
    z_cart = r * np.sin(dec_rad)
    return x, y, z_cart
