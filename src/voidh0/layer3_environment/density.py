"""Schicht 3 -- kontinuierliche Umgebungsdichte (RF-D).

Zweiter, paralleler Pfad neben der diskreten void/wall-Klassifikation aus
`classify.py` (Exposé Abschnitt 9, offene Entscheidung: "Wird Umgebung als
diskrete Klasse oder kontinuierliche Dichtevariable modelliert?
(Empfehlung: beides, diskret als vorregistrierte Primaeranalyse)").

Rechercheergebnis, das die Implementierung hier bestimmt (siehe
docs/architecture.md, RF-D-Ticket): Der zweite VAST-Algorithmus V²/Vsquared
berechnet zwar intern eine Voronoi-Tesselation, aber seine STANDARD-
Ausgabedatei (`GALZONE`-HDU: nur `gal`, `zone`, `depth`, `edge`, `out`)
exportiert die Zellvolumina NICHT. Eine Wiederverwendung waere also kein
"kostenloses Nebenprodukt", sondern erfordert einen nicht-standardmaessigen
Eingriff in den externen V²-Lauf. Diese Klasse implementiert stattdessen
eine EIGENSTAENDIGE Voronoi-Dichteschaetzung direkt mit `scipy.spatial`
(bereits Kernabhaengigkeit des Projekts) -- ohne jede VAST- oder damit
Windows-Abhaengigkeit, vollstaendig lokal testbar.

Methode: 3D-Voronoi-Tesselation der Tracer-Positionen (kartesisch, ueber
Schicht 0 aus ra/dec/z); die lokale Dichte eines Objekts ist umgekehrt
proportional zum Volumen seiner Voronoi-Zelle. Objekte, deren Zelle
unbeschraenkt ist (liegen auf der konvexen Huelle der Punktwolke, typisch
fuer Randobjekte der Survey-Maske), bekommen KEIN endliches Dichte-Datum --
sie werden als `is_edge_cell=True` markiert, analog zum "edge"-Label in
`classify.py`.

Bewusste Vereinfachung (siehe auch `layer1_tracers/mask_randoms.py` fuer
dieselbe Art Kompromiss): keine explizite Randoms-/Masken-Korrektur der
Tesselation selbst -- reale Randobjekte innerhalb der Survey-Maske, aber
nahe am tatsaechlichen Rand der Tracer-Punktwolke, koennen trotzdem
kuenstlich grosse (unterschaetzte Dichte) Zellen bekommen. Fuer eine
publikationsreife Analyse waere eine Tesselation ueber Tracer+Randoms
gemeinsam (mit anschliessendem Verwerfen der Randoms-Zellen) der naechste
Verfeinerungsschritt.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import ConvexHull, Voronoi

from ..geometry import ra_dec_z_to_xyz
from ..layer0_cosmology import ReferenceCosmology


@dataclass
class ContinuousDensityResult:
    """Ergebnis der Voronoi-basierten Dichteschaetzung fuer eine Menge von Objekten."""

    object_id: np.ndarray
    cell_volume_h3Mpc3: np.ndarray  # Voronoi-Zellvolumen in (h^-1 Mpc)^3, NaN falls edge-Zelle
    log_density_contrast: np.ndarray  # log10(rho / rho_median), NaN falls edge-Zelle
    is_edge_cell: np.ndarray  # bool: Zelle unbeschraenkt (Punkt auf konvexer Huelle)

    def n_edge_cells(self) -> int:
        return int(np.sum(self.is_edge_cell))

    def n_usable(self) -> int:
        return int(np.sum(~self.is_edge_cell))


def voronoi_cell_volumes(points_xyz: np.ndarray) -> np.ndarray:
    """Berechnet das Voronoi-Zellvolumen fuer jeden Punkt in `points_xyz` (N, 3).

    Unbeschraenkte Zellen (Punkt liegt auf der konvexen Huelle der
    Punktwolke, hat also mindestens eine Zellwand "im Unendlichen") erhalten
    `np.nan` statt eines Volumens -- ein Randobjekt-Artefakt der endlichen
    Punktwolke, kein physikalisch sinnvoller Dichtewert.
    """
    points_xyz = np.asarray(points_xyz, dtype=float)
    n = len(points_xyz)
    if n < 5:
        raise ValueError(
            f"voronoi_cell_volumes: mindestens 5 Punkte fuer eine 3D-Tesselation "
            f"noetig, {n} gegeben."
        )

    vor = Voronoi(points_xyz)
    volumes = np.full(n, np.nan)

    for i, region_index in enumerate(vor.point_region):
        region = vor.regions[region_index]
        if len(region) == 0 or -1 in region:
            # -1 markiert einen Vertex "im Unendlichen" -> unbeschraenkte Zelle
            continue
        vertices = vor.vertices[region]
        try:
            volumes[i] = ConvexHull(vertices).volume
        except Exception:
            # Entartete (z.B. coplanare) Zellen -- seltener Grenzfall bei
            # synthetischen/regulaeren Punktgittern; als edge behandeln.
            continue

    return volumes


def compute_local_density(
    object_id: np.ndarray,
    ra_deg: np.ndarray,
    dec_deg: np.ndarray,
    z: np.ndarray,
    cosmology: ReferenceCosmology,
) -> ContinuousDensityResult:
    """Kontinuierliche Umgebungsdichte fuer eine Menge von Objekten (RF-D).

    Parameters
    ----------
    object_id, ra_deg, dec_deg, z : Zielobjekte (z.B. SN-Ia-Wirte), gleiche
        Laenge. Fuer eine realistische Analyse sollten hier alle Tracer der
        volumenlimitierten Stichprobe uebergeben werden (nicht nur die
        Zielobjekte selbst) -- die Dichte am Ort eines Zielobjekts wird
        sinnvollerweise aus der *gesamten* umgebenden Tracer-Verteilung
        geschaetzt, siehe Docstring-Hinweis in `layer3_environment/__init__.py`.
    cosmology : Schicht-0-Referenzkosmologie fuer die (ra,dec,z)->(x,y,z)-
        Umrechnung (Kosmologie-Konsistenz, siehe Exposé Abschnitt 9).
    """
    x, y, zc = ra_dec_z_to_xyz(ra_deg, dec_deg, z, cosmology)
    points = np.column_stack([x, y, zc])

    volumes = voronoi_cell_volumes(points)
    is_edge = np.isnan(volumes)

    finite_volumes = volumes[~is_edge]
    if len(finite_volumes) == 0:
        raise ValueError(
            "compute_local_density: alle Zellen sind unbeschraenkt (edge) -- "
            "zu wenige oder zu raeumlich konzentrierte Punkte fuer eine "
            "sinnvolle Tesselation."
        )

    mean_volume = float(np.median(finite_volumes))
    # log10(rho/rho_ref) = log10(vol_ref/vol) = -log10(vol/vol_ref)
    #
    # Bewusst der MEDIAN statt des arithmetischen Mittels als Referenz:
    # Voronoi-Zellvolumina sind rechtsschief verteilt (wenige, aber sehr
    # grosse randnahe endliche Zellen koennen den Mittelwert stark nach oben
    # ziehen), sodass ein Mittelwert-basierter Kontrast fast alle typischen
    # Zellen als "ueberdicht" ausweisen wuerde -- ein Artefakt der
    # Verteilungsform, nicht der tatsaechlichen Umgebungsdichte. Der Median
    # ist gegenueber dieser Schiefe robust und in der Dichteschaetzungs-
    # Literatur die uebliche Wahl.
    log_density_contrast = np.full(len(points), np.nan)
    log_density_contrast[~is_edge] = -np.log10(volumes[~is_edge] / mean_volume)

    return ContinuousDensityResult(
        object_id=np.asarray(object_id),
        cell_volume_h3Mpc3=volumes,
        log_density_contrast=log_density_contrast,
        is_edge_cell=is_edge,
    )
