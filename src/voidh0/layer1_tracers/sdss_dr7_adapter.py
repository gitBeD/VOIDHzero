"""Echter Schicht-1-Adapter: SDSS DR7 Hauptstichprobe, volumenlimitiert.

Beantwortet die offene Entscheidung aus Exposé Abschnitt 9 ("Welcher konkrete
Basis-Survey und welche Katalogversion bilden Phase 1?"): SDSS Data Release 7
(Hauptstichprobe/"Main Galaxy Sample"), volumenlimitiert auf z <~ 0.11 und
M_r < -20.09 -- exakt der Referenz-Survey, auf dem VoidFinder/VAST (Hoyle &
Vogeley 2002/2004, nach El-Ad & Piran 1997) seine peer-reviewten Void-Kataloge
aufbaut (Douglass, Veyrat & BenZvi 2023, ApJS 265, 7; VAST-Beispielkatalog
"vollim_dr7_cbp_102709.dat"). Das passt exakt zum "z <~ 0,11" aus Exposé
Abschnitt 6 und macht diesen Adapter direkt kompatibel mit dem offiziellen
VAST-Paket (DESI-UR/VAST) -- derselbe Katalog kann unveraendert auch dort
verwendet werden.

Erwartetes Eingabeformat (identisch zur VAST-eigenen API,
`vast.voidfinder.preprocessing.file_preprocess`): eine lokale Datei, lesbar
per `astropy.table.Table.read` als `ascii.commented_header`, FITS oder HDF5,
mit mindestens den Spalten `ra`, `dec`, `redshift` (oder `z`) und `rabsmag`
(absolute r-Band-Magnitude).

Bezugsquellen fuer eine echte Katalogdatei (NICHT im Repository enthalten --
Drittanbieter-Datenprodukt, mehrere zehn MB):
  - VAST-Beispielkatalog: `VAST/example_scripts/vollim_dr7_cbp_102709.dat`
    im GitHub-Repo `DESI-UR/VAST`
  - Peer-reviewte Void-Kataloge (Douglass, Veyrat & BenZvi 2023): Zenodo,
    Suche nach "VAST void catalogs for SDSS DR7"

Randoms: WICHTIG -- diese Klasse kann optional einen echten Random-Katalog
einlesen (`randoms_path`), oder ersatzweise grobe Bounding-Box-Randoms
generieren (`n_synthetic_randoms`). Letzteres ist AUSDRUECKLICH KEIN Ersatz
fuer einen maskenbasierten Random-Katalog (z.B. via der SDSS-DR7-
Fussabdruckmaske/pymangle) -- siehe Warnhinweis in `load()`. Ein echter,
maskenbasierter Random-Katalog ist einer der noch offenen WP1-Punkte
(siehe docs/architecture.md).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .base import TracerAdapter, TracerCatalog

# Absoluter r-Band-Helligkeitsschnitt des Standard-VAST/VoidFinder-
# volumenlimitierten SDSS-DR7-Katalogs (Pan et al. 2012; Douglass et al.
# 2022/2024; VAST-Default in filter_galaxies: magnitude_limit=-20.09).
DEFAULT_MAGNITUDE_LIMIT = -20.09

# Redshift-Obergrenze des VAST-2022/2024-Void-Katalogs fuer SDSS DR7 und
# entspricht dem in Exposé Abschnitt 6 genannten "z <~ 0,11".
DEFAULT_Z_MIN = 0.0
DEFAULT_Z_MAX = 0.114


class SDSSDR7TracerAdapter(TracerAdapter):
    """Schicht-1-Adapter fuer die volumenlimitierte SDSS-DR7-Hauptstichprobe.

    Alles Survey-Spezifische (Spaltennamen, Helligkeitsschnitt, Redshift-
    Grenzen, Dateiformat) lebt ausschliesslich in dieser Klasse -- Schicht 2
    aufwaerts sieht nur noch das normalisierte `TracerCatalog` (siehe
    Designregel in Exposé Abschnitt 6 / README.md).
    """

    name = "sdss_dr7_volume_limited"

    def __init__(
        self,
        catalog_path: str | Path,
        randoms_path: str | Path | None = None,
        z_min: float = DEFAULT_Z_MIN,
        z_max: float = DEFAULT_Z_MAX,
        magnitude_limit: float = DEFAULT_MAGNITUDE_LIMIT,
        ra_col: str = "ra",
        dec_col: str = "dec",
        redshift_col: str = "redshift",
        rabsmag_col: str = "rabsmag",
        n_synthetic_randoms: int = 0,
        seed: int = 0,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.randoms_path = Path(randoms_path) if randoms_path is not None else None
        self._z_min = z_min
        self._z_max = z_max
        self._magnitude_limit = magnitude_limit
        self._ra_col = ra_col
        self._dec_col = dec_col
        self._redshift_col = redshift_col
        self._rabsmag_col = rabsmag_col
        self._n_synthetic_randoms = n_synthetic_randoms
        self._seed = seed
        self._footprint_cache: tuple[float, float, float, float] | None = None

    def redshift_limits(self) -> tuple[float, float]:
        return (self._z_min, self._z_max)

    # -- interne Hilfsfunktionen ----------------------------------------

    @staticmethod
    def _require_astropy():
        try:
            from astropy.table import Table  # noqa: F401
        except ImportError as exc:  # pragma: no cover - Umgebungsabhaengig
            raise ImportError(
                "SDSSDR7TracerAdapter benoetigt astropy zum Einlesen des "
                "VAST-kompatiblen Katalogformats (ascii.commented_header / "
                "FITS / HDF5). Installation: `pip install astropy` oder "
                "`pip install -e \".[dev]\"`. Der Rest des voidh0-Frameworks "
                "(Schicht 0, 3-5) bleibt bewusst astropy-frei -- das ist eine "
                "lokale Abhaengigkeit nur dieses einen Survey-Adapters."
            ) from exc
        from astropy.table import Table

        return Table

    def _read_table(self, path: Path):
        Table = self._require_astropy()
        suffix = path.suffix.lower()
        if suffix in (".fits", ".fit"):
            return Table.read(path, format="fits")
        if suffix in (".h5", ".hdf5"):
            return Table.read(path, format="hdf5")
        return Table.read(path, format="ascii.commented_header")

    def _resolve_redshift_column(self, table) -> str:
        if self._redshift_col in table.colnames:
            return self._redshift_col
        if "z" in table.colnames:
            return "z"
        raise KeyError(
            f"Weder '{self._redshift_col}' noch 'z' als Spalte gefunden "
            f"(vorhandene Spalten: {table.colnames})"
        )

    # -- TracerAdapter-Interface -----------------------------------------

    def load(self) -> TracerCatalog:
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                f"Katalogdatei nicht gefunden: {self.catalog_path}. "
                "Siehe Moduldocstring fuer Bezugsquellen (VAST-Beispielkatalog "
                "oder Zenodo-Void-Kataloge zu Douglass, Veyrat & BenZvi 2023)."
            )

        table = self._read_table(self.catalog_path)
        z_col = self._resolve_redshift_column(table)

        ra = np.asarray(table[self._ra_col], dtype=float)
        dec = np.asarray(table[self._dec_col], dtype=float)
        z = np.asarray(table[z_col], dtype=float)

        keep = (z >= self._z_min) & (z <= self._z_max)

        rabsmag = None
        if self._rabsmag_col in table.colnames:
            rabsmag = np.asarray(table[self._rabsmag_col], dtype=float)
            # "fainter than magnitude_limit" ausschliessen: rabsmag ist eine
            # astronomische Magnitude, hellere Galaxien haben KLEINERE
            # (negativere) Werte. Behalten wird alles <= magnitude_limit.
            keep &= rabsmag <= self._magnitude_limit

        ra_o, dec_o, z_o = ra[keep], dec[keep], z[keep]
        n_obj = len(ra_o)
        if n_obj == 0:
            raise ValueError(
                "Nach Redshift-/Magnitudenschnitt sind keine Galaxien mehr "
                "uebrig -- z_min/z_max/magnitude_limit oder Spaltennamen pruefen."
            )

        object_id = np.array([f"{self.name}_{i}" for i in range(n_obj)])
        extra: dict = {}
        if rabsmag is not None:
            extra["rabsmag"] = rabsmag[keep]

        ra_r, dec_r, z_r = self._build_randoms(ra_o, dec_o, z_col, table)

        ra_all = np.concatenate([ra_o, ra_r])
        dec_all = np.concatenate([dec_o, dec_r])
        z_all = np.concatenate([z_o, z_r])
        is_random = np.concatenate(
            [np.zeros(n_obj, dtype=bool), np.ones(len(ra_r), dtype=bool)]
        )
        random_ids = np.array([f"{self.name}_random_{i}" for i in range(len(ra_r))])
        ids_all = np.concatenate([object_id, random_ids])
        mask_value = np.ones_like(z_all)

        self._footprint_cache = (
            float(ra_o.min()),
            float(ra_o.max()),
            float(dec_o.min()),
            float(dec_o.max()),
        )

        return TracerCatalog(
            survey_name=self.name,
            object_id=ids_all,
            ra_deg=ra_all,
            dec_deg=dec_all,
            z=z_all,
            mask_value=mask_value,
            is_random=is_random,
            extra=extra,
        )

    def _build_randoms(self, ra_o, dec_o, z_col, object_table):
        if self.randoms_path is not None:
            rtable = self._read_table(self.randoms_path)
            r_z_col = z_col if z_col in rtable.colnames else self._resolve_redshift_column(rtable)
            ra_r = np.asarray(rtable[self._ra_col], dtype=float)
            dec_r = np.asarray(rtable[self._dec_col], dtype=float)
            z_r = np.asarray(rtable[r_z_col], dtype=float)
            keep_r = (z_r >= self._z_min) & (z_r <= self._z_max)
            return ra_r[keep_r], dec_r[keep_r], z_r[keep_r]

        if self._n_synthetic_randoms > 0:
            # ACHTUNG: reine Bounding-Box-Randoms, NICHT maskenbasiert.
            # Fuer eine echte VoidFinder-Analyse braucht es einen
            # maskenbasierten Random-Katalog (z.B. via der SDSS-DR7-
            # Fussabdruckmaske/pymangle oder HEALPix-Maske) -- offener
            # WP1-Punkt, siehe docs/architecture.md. Diese Randoms sind nur
            # ein Platzhalter, um die TracerCatalog-Schnittstelle vollstaendig
            # zu bedienen, WAEHREND ein echter Random-Katalog noch fehlt.
            rng = np.random.default_rng(self._seed)
            ra_r = rng.uniform(ra_o.min(), ra_o.max(), size=self._n_synthetic_randoms)
            dec_r = rng.uniform(dec_o.min(), dec_o.max(), size=self._n_synthetic_randoms)
            z_r = rng.uniform(self._z_min, self._z_max, size=self._n_synthetic_randoms)
            return ra_r, dec_r, z_r

        return np.array([]), np.array([]), np.array([])

    def footprint_area_deg2(self) -> float:
        if self._footprint_cache is None:
            raise RuntimeError(
                "footprint_area_deg2() ist erst nach einem load()-Aufruf verfuegbar."
            )
        ra_min, ra_max, dec_min, dec_max = self._footprint_cache
        # Grobe Rechteck-Naeherung im RA/Dec-Bounding-Box-Sinn, NICHT
        # sphaerisch exakt und NICHT maskenkorrigiert -- Platzhalter,
        # analog zu den synthetischen Randoms ein offener WP1-Punkt.
        return (ra_max - ra_min) * (dec_max - dec_min)
