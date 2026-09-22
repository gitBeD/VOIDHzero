"""Schicht 1 -- Tracer.

Liefert eine *normalisierte* Galaxientabelle, Maske und Randoms fuer einen
konkreten Survey. Alles Survey-Spezifische (Spaltennamen, Flags, Mag-Limits,
Fussabdruck) lebt ausschliesslich hier -- Schicht 3 aufwaerts kennt nur noch
die normalisierten Feldnamen in TracerCatalog.

Meilenstein M3 ("Survey-Austausch: Tracer-Adapter getauscht, Schicht 3-5
unveraendert lauffaehig") ist der Test dafuer, dass diese Grenze eingehalten
wurde: ein neuer TracerAdapter (z.B. fuer DESI oder Rubin/LSST, Phase 2/3 laut
Exposé Abschnitt 6) darf keine Aenderung an Schicht 3-5 erfordern.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class TracerCatalog:
    """Normalisierte Ausgabe eines TracerAdapter.

    Attribute
    ---------
    ra_deg, dec_deg, z : Positions- und Rotverschiebungsarrays gleicher Laenge.
    object_id : eindeutige, survey-praefixierte IDs (z.B. "sdss_1234").
    mask_value : Wert der Survey-Maske am Objektort (1 = innerhalb, 0 = maskiert).
    is_random : True fuer Random-Punkte (fuer Void-Finder-Randoms), sonst False.
    extra : optionale, NICHT normalisierte Zusatzspalten (z.B. Stellarmasse),
        die in Schicht 3 (Konfundierungskontrolle) verwendet werden duerfen,
        aber nirgends survey-spezifisch benannt sein sollten, wenn sie
        Schicht 4/5 erreichen.
    """

    survey_name: str
    object_id: np.ndarray
    ra_deg: np.ndarray
    dec_deg: np.ndarray
    z: np.ndarray
    mask_value: np.ndarray
    is_random: np.ndarray
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.object_id)
        for name in ("ra_deg", "dec_deg", "z", "mask_value", "is_random"):
            arr = getattr(self, name)
            if len(arr) != n:
                raise ValueError(f"TracerCatalog: Laengeninkonsistenz bei '{name}'")

    def __len__(self) -> int:
        return len(self.object_id)

    @property
    def n_objects(self) -> int:
        return int(np.sum(~self.is_random))

    @property
    def n_randoms(self) -> int:
        return int(np.sum(self.is_random))


class TracerAdapter(ABC):
    """Interface fuer Schicht-1-Survey-Adapter.

    Jede konkrete Implementierung kapselt genau einen Survey/eine Datenrelease
    (z.B. eine bestimmte spektroskopische Basis-Stichprobe, siehe Exposé
    Abschnitt 6, "Phase 1"/"Phase 2"). Oberhalb von Schicht 2 wird nur noch
    gegen `TracerCatalog` programmiert, nie gegen einen konkreten Adapter.
    """

    #: kurzer, stabiler Bezeichner, u.a. fuer Provenienz-Logging
    name: str

    @abstractmethod
    def load(self) -> TracerCatalog:
        """Laedt und normalisiert den Survey-Katalog inkl. Randoms."""

    @abstractmethod
    def footprint_area_deg2(self) -> float:
        """Effektive (maskierte) Himmelsflaeche des Surveys in deg^2."""

    @abstractmethod
    def redshift_limits(self) -> tuple[float, float]:
        """(z_min, z_max) der volumenlimitierten Stichprobe."""
