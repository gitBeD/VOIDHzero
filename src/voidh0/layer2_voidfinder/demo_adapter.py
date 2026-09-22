"""Synthetischer Demo-VoidFinderAdapter.

Ein stark vereinfachter, rein geometrischer "Void-Finder": findet lokale
Minima der projizierten Punktdichte auf einem Raster und definiert Voids als
Kugeln um diese Minima. Dies ist NICHT VoidFinder/VAST und NICHT ZOBOV -- es
ist ein Platzhalter, der dieselbe Schnittstelle bedient, damit Schicht 3-5
sofort gegen echte VoidCatalog/Classify-Semantik entwickelt werden koennen.
"""
from __future__ import annotations

import numpy as np
from scipy import spatial

from ..layer1_tracers.base import TracerCatalog
from .base import VoidCatalog, VoidFinderAdapter


class DemoVoidFinderAdapter(VoidFinderAdapter):
    algorithm_name = "demo_sphere_v0"

    def __init__(self, n_voids: int = 8, seed: int = 7) -> None:
        self._n_voids = n_voids
        self._seed = seed

    def find_voids(self, tracers: TracerCatalog) -> VoidCatalog:
        rng = np.random.default_rng(self._seed)
        objs = ~tracers.is_random
        ra = tracers.ra_deg[objs]
        dec = tracers.dec_deg[objs]
        z = tracers.z[objs]

        # Platzhalter-Void-Findung: zufaellige Kandidatenpunkte, Radius so
        # gewaehlt, dass die lokale Tracer-Dichte unterdurchschnittlich ist.
        idx = rng.choice(len(ra), size=min(self._n_voids, len(ra)), replace=False)
        tree = spatial.cKDTree(np.column_stack([ra, dec, z * 100]))  # grobe, dimensionslose Metrik

        radii = []
        for i in idx:
            point = np.array([ra[i], dec[i], z[i] * 100])
            dists, _ = tree.query(point, k=15)
            radii.append(float(np.median(dists)) * 1.5)

        void_id = np.array([f"{self.algorithm_name}_{k}" for k in range(len(idx))])
        return VoidCatalog(
            void_id=void_id,
            center_ra_deg=ra[idx],
            center_dec_deg=dec[idx],
            center_z=z[idx],
            effective_radius_h1Mpc=np.array(radii),
            algorithm=self.algorithm_name,
        )

    def classify(
        self, ra_deg: np.ndarray, dec_deg: np.ndarray, z: np.ndarray, voids: VoidCatalog
    ) -> np.ndarray:
        labels = np.full(len(ra_deg), "wall", dtype=object)
        for c_ra, c_dec, c_z, r in zip(
            voids.center_ra_deg, voids.center_dec_deg, voids.center_z, voids.effective_radius_h1Mpc
        ):
            d = np.sqrt(
                (ra_deg - c_ra) ** 2 + (dec_deg - c_dec) ** 2 + ((z - c_z) * 100) ** 2
            )
            labels[d < r] = "void"
        return labels
