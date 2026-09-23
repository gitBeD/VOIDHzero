"""Echter Schicht-2-Adapter: liest die offizielle VoidFinder/VAST-Ausgabe.

WICHTIGER HINWEIS ZUR PLATTFORM: VAST/VoidFinder (Douglass et al. 2022,
JOSS 7(77), 4033; Algorithmus nach El-Ad & Piran 1997 / Hoyle & Vogeley 2002)
wird von den Autoren ausdruecklich NICHT unter Windows unterstuetzt -- der
Cython-Kern laesst sich dort nicht zuverlaessig kompilieren, und VoidFinder
braucht zusaetzlich den POSIX-`fork()`-Systemaufruf, den Windows nicht hat
(siehe https://vast.readthedocs.io/en/latest/VAST_install.html).

Dieser Adapter fuehrt VoidFinder deshalb NICHT in-process aus. Stattdessen
liest er das offizielle VAST-Ausgabeformat (`[survey_name]_VoidFinder_
Output.fits`, mit den FITS-Table-HDUs `MAXIMALS` und `HOLES`, optional
`MASK`) ein -- die eigentliche Berechnung laeuft extern (z.B. in WSL2, einer
Linux-VM oder einem Cluster) mit der offiziellen VAST-Installation und den
Beispielskripten aus `VAST/example_scripts/` (`SDSS_VoidFinder_dr7.py`).
Damit ist dies eine ECHTE VAST-Anbindung (kein Nachbau des Algorithmus),
nur mit einem expliziten Berechnungs-/Lese-Split statt einem in-process-Aufruf.

Spalten laut offizieller VAST-Dokumentation
(https://vast.readthedocs.io/en/latest/VoidFinder_examples.html#output):

MAXIMALS-HDU (eine Zeile pro Void -- der maximale, groesste Void definierende
Sphere): x, y, z, radius, void (eindeutige Void-ID), r (comoving distance),
ra, dec -- alle Laengen in Mpc/h.

HOLES-HDU (mehrere Zeilen pro Void moeglich -- alle Spheren, deren Union den
Void bildet): x, y, z, radius, void (verweist auf dieselbe Void-ID wie in
MAXIMALS).

Fuer `classify()` gilt nach VAST-eigener Definition: ein Objekt liegt in
einem Void, wenn es innerhalb IRGENDEINER Sphere aus der HOLES-Tabelle liegt
(nicht nur der Maximal-Sphere) -- siehe "Is my object in a void?" in der
VAST-Doku. Diese Klasse haelt die HOLES-Tabelle daher intern vor (nicht Teil
des allgemeinen `VoidCatalog`-Interfaces aus Schicht 2, das nur die
Maximal-Sphere-Zusammenfassung transportiert) und nutzt sie fuer eine
sphaerengenaue Klassifikation.

Kosmologie-Konsistenz (Exposé Abschnitt 9, "Kosmologie-Zirkularitaet"): die
(ra, dec, z) -> (x, y, z)-Umrechnung MUSS dieselbe Kosmologie (H0, Om0)
verwenden, mit der VoidFinder extern aufgerufen wurde. Dieser Adapter nutzt
dafuer standardmaessig Schicht 0 (`load_reference_cosmology()`) -- wird
VoidFinder extern mit einer ANDEREN Kosmologie aufgerufen, muss das explizit
per `cosmology=`-Argument uebergeben werden, sonst sind die (x,y,z)-Vergleiche
inkonsistent.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..layer0_cosmology import ReferenceCosmology, load_reference_cosmology
from ..layer1_tracers.base import TracerCatalog
from .base import VoidCatalog, VoidFinderAdapter


def ra_dec_z_to_xyz(
    ra_deg: np.ndarray, dec_deg: np.ndarray, z: np.ndarray, cosmology: ReferenceCosmology
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wandelt (ra, dec, z) in kartesische (x, y, z) in h^-1 Mpc um.

    Dieselbe Konvention wie VAST (`vast.voidfinder.ra_dec_to_xyz`): rechts-
    haendiges System, dec von der Aequatorialebene aus gemessen, comoving
    distance aus Schicht-0-Referenzkosmologie.
    """
    ra_rad = np.deg2rad(np.asarray(ra_deg, dtype=float))
    dec_rad = np.deg2rad(np.asarray(dec_deg, dtype=float))
    r = np.atleast_1d(cosmology.comoving_distance_h1Mpc(z))

    x = r * np.cos(dec_rad) * np.cos(ra_rad)
    y = r * np.cos(dec_rad) * np.sin(ra_rad)
    z_cart = r * np.sin(dec_rad)
    return x, y, z_cart


class VASTVoidFinderAdapter(VoidFinderAdapter):
    """Schicht-2-Adapter, der eine extern erzeugte VAST-VoidFinder-Ausgabe einliest.

    Siehe Moduldocstring fuer die Windows-Einschraenkung und den Grund fuer
    den externen-Berechnung/interne-Auswertung-Split.
    """

    algorithm_name = "vast_voidfinder"

    def __init__(
        self,
        output_fits_path: str | Path,
        cosmology: ReferenceCosmology | None = None,
        edge_via_mask: bool = True,
    ) -> None:
        self.output_fits_path = Path(output_fits_path)
        self.cosmology = cosmology if cosmology is not None else load_reference_cosmology()
        self._edge_via_mask = edge_via_mask

        self._holes_x: np.ndarray | None = None
        self._holes_y: np.ndarray | None = None
        self._holes_z: np.ndarray | None = None
        self._holes_r: np.ndarray | None = None
        self._holes_void_id: np.ndarray | None = None
        self._mask: np.ndarray | None = None
        self._mask_resolution: int | None = None

    @staticmethod
    def _require_astropy():
        try:
            from astropy.io import fits  # noqa: F401
        except ImportError as exc:  # pragma: no cover - umgebungsabhaengig
            raise ImportError(
                "VASTVoidFinderAdapter benoetigt astropy zum Einlesen der "
                "VAST-FITS-Ausgabe. Installation: `pip install astropy` oder "
                "`pip install -e \".[dev]\"`."
            ) from exc
        from astropy.io import fits

        return fits

    def find_voids(self, tracers: TracerCatalog) -> VoidCatalog:
        """Liest die (extern erzeugte) VAST-Ausgabedatei ein.

        `tracers` wird NICHT zur Berechnung verwendet (die ist ja bereits
        extern geschehen) -- das Argument existiert nur, damit diese Klasse
        weiterhin dem gemeinsamen `VoidFinderAdapter`-Interface aus Schicht 2
        entspricht und austauschbar mit `DemoVoidFinderAdapter` bleibt
        (Designregel aus Exposé Abschnitt 6 / Meilenstein M3-Analogon fuer
        Schicht 2).
        """
        if not self.output_fits_path.exists():
            raise FileNotFoundError(
                f"VAST-Ausgabedatei nicht gefunden: {self.output_fits_path}. "
                "Diese Datei entsteht durch einen externen VoidFinder-Lauf "
                "(z.B. in WSL2/Linux mit der offiziellen VAST-Installation, "
                "siehe Moduldocstring)."
            )

        fits = self._require_astropy()
        with fits.open(self.output_fits_path, memmap=False) as hdul:
            names = [hdu.name for hdu in hdul]
            if "MAXIMALS" not in names:
                raise KeyError(
                    f"Keine 'MAXIMALS'-HDU in {self.output_fits_path} gefunden "
                    f"(vorhandene HDUs: {names}). Ist das eine echte "
                    "VoidFinder-Output-Datei?"
                )
            maximals = hdul["MAXIMALS"].data

            void_id = np.array(maximals["void"], copy=True)
            center_ra = np.array(maximals["ra"], dtype=float, copy=True)
            center_dec = np.array(maximals["dec"], dtype=float, copy=True)
            maximal_radius = np.array(maximals["radius"], dtype=float, copy=True)

            # MAXIMALS liefert ra/dec/r (comoving distance), aber keinen
            # Redshift direkt -- Rueckumrechnung r -> z ueber dieselbe
            # Schicht-0-Referenzkosmologie (Kosmologie-Konsistenz, siehe
            # Moduldocstring).
            r_h1mpc = np.array(maximals["r"], dtype=float, copy=True)
            center_z = self._comoving_h1mpc_to_z(r_h1mpc)

            if "HOLES" in names:
                holes = hdul["HOLES"].data
                self._holes_x = np.array(holes["x"], dtype=float, copy=True)
                self._holes_y = np.array(holes["y"], dtype=float, copy=True)
                self._holes_z = np.array(holes["z"], dtype=float, copy=True)
                self._holes_r = np.array(holes["radius"], dtype=float, copy=True)
                self._holes_void_id = np.array(holes["void"], copy=True)
            else:
                # Fallback, falls nur MAXIMALS vorhanden ist: die Maximal-
                # Spheres selbst als (einzige) "Holes" verwenden -- liefert
                # eine etwas konservativere (kleinere) Void-Klassifikation
                # als die volle Sphere-Union.
                x_m, y_m, z_m = self._ra_dec_r_to_xyz(center_ra, center_dec, r_h1mpc)
                self._holes_x, self._holes_y, self._holes_z = x_m, y_m, z_m
                self._holes_r = maximal_radius
                self._holes_void_id = void_id

            if self._edge_via_mask and "MASK" in names:
                self._mask = np.array(hdul["MASK"].data, dtype=bool, copy=True)
                header = hdul["MASK"].header
                self._mask_resolution = int(
                    header.get("MASKRES", header.get("RESOLUTI", 1))
                )

        return VoidCatalog(
            void_id=void_id,
            center_ra_deg=center_ra,
            center_dec_deg=center_dec,
            center_z=center_z,
            effective_radius_h1Mpc=maximal_radius,
            algorithm=self.algorithm_name,
        )

    def classify(
        self, ra_deg: np.ndarray, dec_deg: np.ndarray, z: np.ndarray, voids: VoidCatalog
    ) -> np.ndarray:
        """Sphaerengenaue Klassifikation gegen die HOLES-Tabelle (nicht nur MAXIMALS).

        Muss nach `find_voids()` aufgerufen werden (haelt die HOLES-Tabelle
        intern vor, siehe Moduldocstring).
        """
        if self._holes_x is None:
            raise RuntimeError(
                "classify() benoetigt vorher einen find_voids()-Aufruf "
                "(die HOLES-Tabelle wird dabei intern zwischengespeichert)."
            )

        ra_deg = np.asarray(ra_deg, dtype=float)
        dec_deg = np.asarray(dec_deg, dtype=float)
        z = np.asarray(z, dtype=float)

        x, y, zc = ra_dec_z_to_xyz(ra_deg, dec_deg, z, self.cosmology)

        labels = np.full(len(ra_deg), "wall", dtype=object)
        for hx, hy, hz, hr in zip(self._holes_x, self._holes_y, self._holes_z, self._holes_r):
            d = np.sqrt((x - hx) ** 2 + (y - hy) ** 2 + (zc - hz) ** 2)
            labels[d < hr] = "void"

        if self._mask is not None and self._mask_resolution is not None:
            outside = self._outside_mask(ra_deg, dec_deg)
            labels[outside] = "edge"

        return labels

    # -- interne Hilfsfunktionen ------------------------------------------

    def _comoving_h1mpc_to_z(self, r_h1mpc: np.ndarray) -> np.ndarray:
        """Invertiert Schicht 0s comoving_distance_h1Mpc(z) numerisch (bisection)."""
        from scipy.optimize import brentq

        h = self.cosmology.H0_km_s_Mpc / 100.0
        r_h1mpc = np.atleast_1d(r_h1mpc)
        out = np.empty_like(r_h1mpc, dtype=float)
        for i, r in enumerate(r_h1mpc):
            if r <= 0:
                out[i] = 0.0
                continue
            target_mpc = r / h

            def f(zz, target=target_mpc):
                return self.cosmology.comoving_distance_Mpc(zz) - target

            out[i] = brentq(f, 0.0, 5.0, xtol=1e-6)
        return out

    def _ra_dec_r_to_xyz(self, ra_deg, dec_deg, r_h1mpc):
        ra_rad = np.deg2rad(ra_deg)
        dec_rad = np.deg2rad(dec_deg)
        x = r_h1mpc * np.cos(dec_rad) * np.cos(ra_rad)
        y = r_h1mpc * np.cos(dec_rad) * np.sin(ra_rad)
        zc = r_h1mpc * np.sin(dec_rad)
        return x, y, zc

    def _outside_mask(self, ra_deg: np.ndarray, dec_deg: np.ndarray) -> np.ndarray:
        res = self._mask_resolution
        ra_idx = np.clip((ra_deg * res).astype(int), 0, self._mask.shape[0] - 1)
        dec_idx = np.clip(((dec_deg + 90.0) * res).astype(int), 0, self._mask.shape[1] - 1)
        inside = self._mask[ra_idx, dec_idx]
        return ~inside
