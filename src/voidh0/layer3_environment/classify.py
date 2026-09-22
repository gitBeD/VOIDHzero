"""Schicht 3 -- Umgebungszuordnung.

Verknuepft Zielobjekte (z.B. SN-Ia-Wirte, Cepheiden-/TRGB-Kalibratoren) mit
einer Umgebungsklasse und einem Vertrauensmass. Diese Schicht kennt weder
survey- noch void-finder-spezifische Details mehr -- sie erhaelt nur noch
Klassifikationslabels von einem oder mehreren Schicht-2-Adaptern und
aggregiert sie zu einem projektinternen Robustheitsflag.

WP1-Zielprodukt (Exposé Abschnitt 7): "Umgebungskatalog mit dreistufigem
Robustheitsflag". Die drei Stufen hier: 'robust', 'marginal', 'edge_excluded'.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ROBUSTNESS_LEVELS = ("robust", "marginal", "edge_excluded")


@dataclass
class EnvironmentAssignment:
    """Ergebnis der Schicht-3-Umgebungszuordnung fuer eine Menge von Objekten."""

    object_id: np.ndarray
    environment_class: np.ndarray  # {"void", "wall", "unclassified"}
    robustness_flag: np.ndarray  # ROBUSTNESS_LEVELS
    n_algorithms_agree: np.ndarray  # int, wie viele Void-Finder-Labels uebereinstimmen
    n_algorithms_total: np.ndarray


def assign_environment(
    object_id: np.ndarray,
    labels_per_algorithm: dict[str, np.ndarray],
    edge_labels: tuple[str, ...] = ("edge",),
) -> EnvironmentAssignment:
    """Aggregiert Labels mehrerer Schicht-2-Void-Finder zu einer robusten Zuordnung.

    Parameters
    ----------
    object_id : IDs der Zielobjekte.
    labels_per_algorithm : Mapping Algorithmus-Name -> Label-Array (gleiche
        Laenge/Reihenfolge wie object_id), z.B.
        {"demo_sphere_v0": [...], "zobov_v1": [...]}.
        Erfolgskriterium (Exposé Abschnitt 5) verlangt Stabilitaet ueber
        *mindestens zwei* solcher Algorithmen -- diese Funktion ist bewusst
        so gebaut, dass sie mit einem oder mit vielen Algorithmen umgehen
        kann, damit RF-B direkt hierauf getestet werden kann.
    edge_labels : Labels, die als "an der Maske/Randobjekt" gelten
        (siehe Exposé Abschnitt 9, "Randeffekte durch die Survey-Maske").
    """
    if not labels_per_algorithm:
        raise ValueError("labels_per_algorithm darf nicht leer sein")

    n = len(object_id)
    algos = list(labels_per_algorithm.keys())
    for name, arr in labels_per_algorithm.items():
        if len(arr) != n:
            raise ValueError(f"Laengeninkonsistenz fuer Algorithmus '{name}'")

    stacked = np.array([np.asarray(labels_per_algorithm[a], dtype=object) for a in algos])
    # stacked.shape == (n_algorithms, n_objects)

    env_class = np.full(n, "unclassified", dtype=object)
    robustness = np.full(n, "edge_excluded", dtype=object)
    n_agree = np.zeros(n, dtype=int)
    n_total = np.full(n, len(algos), dtype=int)

    for i in range(n):
        col = stacked[:, i]
        is_edge = np.isin(col, edge_labels)
        if np.any(is_edge):
            env_class[i] = "unclassified"
            robustness[i] = "edge_excluded"
            n_agree[i] = 0
            continue

        values, counts = np.unique(col, return_counts=True)
        majority_idx = int(np.argmax(counts))
        env_class[i] = values[majority_idx]
        n_agree[i] = int(counts[majority_idx])

        if n_agree[i] == len(algos):
            robustness[i] = "robust"
        elif n_agree[i] > len(algos) / 2:
            robustness[i] = "marginal"
        else:
            robustness[i] = "edge_excluded"
            env_class[i] = "unclassified"

    return EnvironmentAssignment(
        object_id=np.asarray(object_id),
        environment_class=env_class,
        robustness_flag=robustness,
        n_algorithms_agree=n_agree,
        n_algorithms_total=n_total,
    )
