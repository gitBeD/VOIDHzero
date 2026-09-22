"""Schicht 2 -- Void-Definition.

Liefert eine normalisierte Void-Tabelle plus eine Klassifikationsfunktion
(Punkt -> void/wand/unklar) fuer einen konkreten Void-Finder-Algorithmus
(z.B. VoidFinder/VAST nach Hoyle & Vogeley bzw. El-Ad & Piran, oder ZOBOV-
basierte Verfahren wie VIDE/REVOLVER, siehe Exposé Abschnitt 6).

RF-B ("Robustheit der Klassifikation") verlangt ausdruecklich mindestens zwei
unabhaengige Void-Finder-Implementierungen dieses Interfaces (Erfolgskriterium
Abschnitt 5: "stabil ueber mindestens zwei unabhaengige Void-Finder-
Algorithmen").
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from ..layer1_tracers.base import TracerCatalog


@dataclass
class VoidCatalog:
    """Normalisierte Ausgabe eines VoidFinderAdapter.

    Attribute
    ---------
    void_id : eindeutige, algorithmus-praefixierte IDs.
    center_ra_deg, center_dec_deg, center_z : Void-Zentren.
    effective_radius_h1Mpc : effektiver Void-Radius in h^-1 Mpc (Schicht-0-Einheit).
    algorithm : Name/Version des Void-Finder-Algorithmus (Provenienz).
    """

    void_id: np.ndarray
    center_ra_deg: np.ndarray
    center_dec_deg: np.ndarray
    center_z: np.ndarray
    effective_radius_h1Mpc: np.ndarray
    algorithm: str

    def __len__(self) -> int:
        return len(self.void_id)


class VoidFinderAdapter(ABC):
    """Interface fuer Schicht-2-Void-Finder-Adapter."""

    #: kurzer, stabiler Bezeichner, u.a. fuer Provenienz-Logging und RF-B
    algorithm_name: str

    @abstractmethod
    def find_voids(self, tracers: TracerCatalog) -> VoidCatalog:
        """Berechnet den Void-Katalog aus einem normalisierten Tracer-Katalog."""

    @abstractmethod
    def classify(
        self, ra_deg: np.ndarray, dec_deg: np.ndarray, z: np.ndarray, voids: VoidCatalog
    ) -> np.ndarray:
        """Klassifiziert Zielpunkte relativ zu einem Void-Katalog.

        Rueckgabe: Array von Strings aus {"void", "wall", "edge", "unclassified"}
        -- "edge" markiert Randobjekte an der Survey-Maske (siehe Exposé
        Abschnitt 9, "Randeffekte durch die Survey-Maske").
        """
