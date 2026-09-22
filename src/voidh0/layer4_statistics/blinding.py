"""Schicht 4 -- Blinding-Protokoll.

WP0 verlangt ein Blinding-Protokoll als Teil des "eingefrorenen Analyseplans"
(Exposé Abschnitt 7). Zweck: verhindern, dass die Kenntnis des Vorzeichens/der
Groessenordnung des gemessenen Umgebungs-Steps waehrend der Methodenentwicklung
(WP1-WP4) die Analysewahl beeinflusst ("looking at the answer").

Prinzip: Ein additiver Offset wird aus einem *geheimen*, projektinternen Seed
deterministisch erzeugt und auf alle Residuen addiert, bevor irgendjemand im
Team sie sieht. Der Offset wird erst bei der Entblindung (Meilenstein M6)
aufgedeckt. Diese Klasse macht KEINE Aussage darueber, wo/wie der Seed
tatsaechlich sicher aufbewahrt wird (organisatorische Frage, nicht Code) --
sie stellt nur den deterministischen Mechanismus bereit.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np


@dataclass(frozen=True)
class Blinder:
    """Deterministischer additiver Blinding-Offset.

    Der Offset wird aus `secret_seed` per SHA-256 abgeleitet, liegt in
    [-max_abs_offset, +max_abs_offset] mag und ist bei fixem Seed reproduzierbar,
    aber ohne Kenntnis des Seeds nicht vorhersagbar.
    """

    secret_seed: str
    max_abs_offset_mag: float = 0.1

    def _digest_float(self) -> float:
        h = hashlib.sha256(self.secret_seed.encode("utf-8")).hexdigest()
        # nimm die ersten 8 Hex-Zeichen als Integer, normiere auf [0, 1)
        as_int = int(h[:8], 16)
        return as_int / 0xFFFFFFFF

    @property
    def offset_mag(self) -> float:
        u = self._digest_float()  # in [0, 1)
        return (2.0 * u - 1.0) * self.max_abs_offset_mag

    def blind(self, residuals_mag: np.ndarray) -> np.ndarray:
        return np.asarray(residuals_mag) + self.offset_mag

    def unblind(self, blinded_residuals_mag: np.ndarray) -> np.ndarray:
        return np.asarray(blinded_residuals_mag) - self.offset_mag

    def commitment_hash(self) -> str:
        """SHA-256-Hash des Seeds -- vor der Entblindung veroeffentlichbar/dokumentierbar,
        ohne den Seed selbst preiszugeben (Commitment-Schema).
        """
        return hashlib.sha256(self.secret_seed.encode("utf-8")).hexdigest()
