"""Maskenbasierte Random-Generierung fuer Schicht-1-Adapter.

Ersetzt die reine RA/Dec-Bounding-Box-Naeherung durch:

1. eine **gepixelte Fussabdruckmaske**: ein RA/Dec-Gitter, bei dem eine Zelle
   als "im Survey" gilt, sobald sie mindestens `min_objects_per_cell`
   beobachtete Objekte enthaelt -- statt einer einzigen groben Bounding-Box
   ueber den gesamten Katalog.
2. **sphaerisch korrekte Zufallspositionen** innerhalb der belegten Zellen:
   uniform in RA, aber uniform in sin(Dec) statt in Dec selbst (sonst werden
   Pol-nahe Zellen systematisch ueberrepraesentiert), UND Zellen werden
   proportional zu ihrer tatsaechlichen Flaeche ausgewaehlt, nicht mit
   gleicher Wahrscheinlichkeit pro Zelle.
3. eine **empirische Redshift-Selektionsfunktion** n(z): Randoms werden aus
   der beobachteten z-Verteilung resampled (mit optionalem Gaussian-Jitter),
   nicht uniform in z gezogen -- das ist die im VoidFinder-Kontext uebliche
   Wahl (Randoms folgen derselben radialen Selektionsfunktion wie die Daten,
   vgl. Pan et al. 2012).

Bewusst OHNE healpy/pymangle-Abhaengigkeit: nur numpy/scipy (ohnehin
Kernabhaengigkeiten des Projekts), damit dieser Baustein ohne zusaetzliche,
auf manchen Plattformen schwer installierbare C-Extension-Pakete auskommt.

Grenzen dieser Naeherung (wichtig fuer die WP1-Dokumentation, siehe
docs/architecture.md): Eine gepixelte, aus den Daten selbst abgeleitete
Maske ist NICHT dasselbe wie eine echte photometrische Survey-Maske
(Mangle-Polygone oder eine offizielle HEALPix-Maske mit Bohrloechern fuer
helle Sterne, Plattenraender etc.). Sie glaettet solche Feinstrukturen weg.
Fuer eine publikationsreife Analyse ist der Ersatz durch eine echte
Survey-Maske (z.B. via pymangle gegen die SDSS-DR7-Fussabdruckdatei) ein
sinnvoller naechster Schritt -- diese Klasse ist der pragmatische
Zwischenschritt von "RA/Dec-Box" zu "echte Maske".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GriddedFootprintMask:
    """Gepixelte RA/Dec-Fussabdruckmaske, aus einem beobachteten Katalog abgeleitet."""

    ra_edges_deg: np.ndarray  # (n_ra+1,)
    dec_edges_deg: np.ndarray  # (n_dec+1,)
    occupied: np.ndarray  # bool, shape (n_ra, n_dec)
    min_objects_per_cell: int

    @property
    def n_occupied_cells(self) -> int:
        return int(np.sum(self.occupied))

    @property
    def n_total_cells(self) -> int:
        return int(self.occupied.size)

    def solid_angle_deg2(self) -> float:
        """Exakte sphaerische Flaeche der belegten Zellen in deg^2.

        Flaeche eines RA/Dec-Zellstreifens: dRA * (sin(dec_hi) - sin(dec_lo))
        [im Bogenmass], nicht dRA * dDec -- das waere die (falsche)
        flache Naeherung.
        """
        ra_widths_rad = np.deg2rad(np.diff(self.ra_edges_deg))
        dec_lo = np.deg2rad(self.dec_edges_deg[:-1])
        dec_hi = np.deg2rad(self.dec_edges_deg[1:])
        dec_term = np.sin(dec_hi) - np.sin(dec_lo)
        cell_area_sr = np.outer(ra_widths_rad, dec_term)
        cell_area_deg2 = cell_area_sr * (180.0 / np.pi) ** 2
        return float(np.sum(cell_area_deg2[self.occupied]))


def build_footprint_mask(
    ra_deg: np.ndarray,
    dec_deg: np.ndarray,
    cell_size_deg: float = 1.0,
    min_objects_per_cell: int = 1,
) -> GriddedFootprintMask:
    """Baut eine gepixelte Fussabdruckmaske aus den Positionen eines Katalogs.

    Parameters
    ----------
    cell_size_deg : Nominelle Kantenlaenge einer Gitterzelle in Grad (die
        tatsaechliche Kantenlaenge wird so angepasst, dass der gesamte
        RA/Dec-Bereich des Katalogs ganzzahlig aufgeteilt wird).
    min_objects_per_cell : Mindestanzahl beobachteter Objekte, damit eine
        Zelle als "im Survey liegend" gilt.
    """
    ra_deg = np.asarray(ra_deg, dtype=float)
    dec_deg = np.asarray(dec_deg, dtype=float)
    if len(ra_deg) == 0:
        raise ValueError("build_footprint_mask: leerer Katalog")

    ra_min, ra_max = float(ra_deg.min()), float(ra_deg.max())
    dec_min, dec_max = float(dec_deg.min()), float(dec_deg.max())

    n_ra = max(1, int(np.ceil((ra_max - ra_min) / cell_size_deg)))
    n_dec = max(1, int(np.ceil((dec_max - dec_min) / cell_size_deg)))

    ra_edges = np.linspace(ra_min, ra_max, n_ra + 1)
    dec_edges = np.linspace(dec_min, dec_max, n_dec + 1)

    counts, _, _ = np.histogram2d(ra_deg, dec_deg, bins=[ra_edges, dec_edges])
    occupied = counts >= min_objects_per_cell

    return GriddedFootprintMask(
        ra_edges_deg=ra_edges,
        dec_edges_deg=dec_edges,
        occupied=occupied,
        min_objects_per_cell=min_objects_per_cell,
    )


def sample_positions_in_mask(
    mask: GriddedFootprintMask, n_samples: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Zieht n_samples sphaerisch-uniforme (RA, Dec) innerhalb der belegten Zellen.

    Zwei Korrekturen gegenueber einer naiven Gitter-Ziehung:
    1. Zellen werden proportional zu ihrer TATSAECHLICHEN Flaeche gewaehlt
       (nicht mit gleicher Wahrscheinlichkeit pro Zelle).
    2. Innerhalb einer Zelle wird Dec uniform in sin(Dec) gezogen, nicht in
       Dec selbst (sonst Ueberdichte nahe der Zellgrenzen bei hohen |Dec|).
    """
    if n_samples <= 0:
        return np.array([]), np.array([])

    occ_idx = np.argwhere(mask.occupied)  # (n_occupied, 2) -> (i_ra, i_dec)
    if len(occ_idx) == 0:
        raise ValueError("Maske enthaelt keine belegten Zellen")

    ra_widths = np.diff(mask.ra_edges_deg)
    dec_lo_all = np.deg2rad(mask.dec_edges_deg[:-1])
    dec_hi_all = np.deg2rad(mask.dec_edges_deg[1:])
    dec_term_all = np.sin(dec_hi_all) - np.sin(dec_lo_all)

    i_ra_occ = occ_idx[:, 0]
    i_dec_occ = occ_idx[:, 1]
    cell_weights = ra_widths[i_ra_occ] * dec_term_all[i_dec_occ]
    cell_weights = cell_weights / cell_weights.sum()

    chosen = rng.choice(len(occ_idx), size=n_samples, p=cell_weights)
    chosen_i_ra = i_ra_occ[chosen]
    chosen_i_dec = i_dec_occ[chosen]

    ra_lo = mask.ra_edges_deg[chosen_i_ra]
    ra_hi = mask.ra_edges_deg[chosen_i_ra + 1]
    dec_lo_deg = mask.dec_edges_deg[chosen_i_dec]
    dec_hi_deg = mask.dec_edges_deg[chosen_i_dec + 1]

    ra_out = rng.uniform(ra_lo, ra_hi)

    sin_lo = np.sin(np.deg2rad(dec_lo_deg))
    sin_hi = np.sin(np.deg2rad(dec_hi_deg))
    dec_out = np.rad2deg(np.arcsin(rng.uniform(sin_lo, sin_hi)))

    return ra_out, dec_out


def sample_redshifts_from_nz(
    z_observed: np.ndarray,
    n_samples: int,
    rng: np.random.Generator,
    smoothing_sigma: float = 0.0,
) -> np.ndarray:
    """Zieht Redshifts durch Resampling aus der empirischen n(z) der Daten.

    Randoms folgen damit derselben radialen Selektionsfunktion wie die
    beobachtete Stichprobe (Standardvorgehen bei VoidFinder-Randoms), statt
    einer uniformen z-Verteilung im Intervall [z_min, z_max], die die reale
    (durch den Helligkeitsschnitt getriebene) radiale Dichteabnahme ignoriert.

    `smoothing_sigma > 0` addiert Gaussian-Jitter, um die diskrete
    Resampling-Verteilung zu glaetten (vermeidet exakte Duplikate).
    """
    if n_samples <= 0:
        return np.array([])
    z_observed = np.asarray(z_observed, dtype=float)
    if len(z_observed) == 0:
        raise ValueError("sample_redshifts_from_nz: leere z_observed-Eingabe")

    drawn = rng.choice(z_observed, size=n_samples, replace=True)
    if smoothing_sigma > 0:
        drawn = drawn + rng.normal(0.0, smoothing_sigma, size=n_samples)
        drawn = np.clip(drawn, 0.0, None)
    return drawn
