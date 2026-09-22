"""Synthetischer Demo-TracerAdapter.

Erzeugt eine reproduzierbare, rein synthetische Punktwolke -- KEIN echter
Survey. Zweck: Schicht 3-5 koennen gegen eine stabile, sofort verfuegbare
TracerCatalog-Instanz entwickelt und getestet werden, bevor in WP1/WP2 ein
echter Survey-Adapter (spektroskopische Basis-Stichprobe) angebunden wird.

Ein solcher Demo-Adapter darf NIE in einer wissenschaftlichen Auswertung
verwendet werden -- er dient ausschliesslich der Framework-Entwicklung
(vgl. Exposé Abschnitt 9: methodische Fallstricke, Reproduzierbarkeit).
"""
from __future__ import annotations

import numpy as np

from .base import TracerAdapter, TracerCatalog


class DemoTracerAdapter(TracerAdapter):
    name = "demo_synthetic_v0"

    def __init__(
        self,
        n_objects: int = 2000,
        n_randoms: int = 20000,
        z_min: float = 0.01,
        z_max: float = 0.11,
        seed: int = 42,
    ) -> None:
        self._n_objects = n_objects
        self._n_randoms = n_randoms
        self._z_min = z_min
        self._z_max = z_max
        self._seed = seed

    def redshift_limits(self) -> tuple[float, float]:
        return (self._z_min, self._z_max)

    def footprint_area_deg2(self) -> float:
        # Demo-Fussabdruck: ein einfaches RA/Dec-Rechteck.
        return 20.0 * 20.0

    def load(self) -> TracerCatalog:
        rng = np.random.default_rng(self._seed)

        def _sample(n: int):
            ra = rng.uniform(150.0, 170.0, size=n)
            dec = rng.uniform(-10.0, 10.0, size=n)
            z = rng.uniform(self._z_min, self._z_max, size=n)
            return ra, dec, z

        ra_o, dec_o, z_o = _sample(self._n_objects)
        ra_r, dec_r, z_r = _sample(self._n_randoms)

        ra = np.concatenate([ra_o, ra_r])
        dec = np.concatenate([dec_o, dec_r])
        z = np.concatenate([z_o, z_r])
        is_random = np.concatenate(
            [np.zeros(self._n_objects, dtype=bool), np.ones(self._n_randoms, dtype=bool)]
        )
        object_id = np.array(
            [f"{self.name}_{i}" for i in range(self._n_objects + self._n_randoms)]
        )
        mask_value = np.ones_like(z)

        # synthetische, unnormalisierte "extra" Groesse (z.B. log Stellarmasse)
        log_mstar = rng.normal(10.0, 0.6, size=len(z))

        return TracerCatalog(
            survey_name=self.name,
            object_id=object_id,
            ra_deg=ra,
            dec_deg=dec,
            z=z,
            mask_value=mask_value,
            is_random=is_random,
            extra={"log_mstar": log_mstar},
        )
