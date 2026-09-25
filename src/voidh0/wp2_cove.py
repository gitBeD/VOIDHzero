"""WP2 -- Kalibrator-Umgebungs-Diagnose (COVE-Vortest).

Siehe Exposé Abschnitt 9 ("Neu: Kalibrator-Umgebungs-Überlappung") und
docs/architecture.md ("WP2-Diagnosekriterium"). Vor Festlegung des
endgültigen H0-Arm-Designs (Ende WP2) wird pro Kalibrator-Wirt ein
vierstufiges Diagnoseflag erhoben:

  1. Position bekannt (Pantheon+ HOST_RA/HOST_DEC nicht -999)?
  2. SDSS-DR7-spektroskopischer Match vorhanden (Winkel- + Redshift-Toleranz)?
  3. Umgebungsklassifikation mit hinreichender Robustheitsstufe möglich?
  4. resultierende Void/Wand-Klassifikation.

Flags 3/4 benötigen einen echten VoidFinder-Lauf (`VASTVoidFinderAdapter`)
und sind `None` ("pending"), solange keiner vorliegt (siehe
docs/architecture.md, Abschnitt "echte VAST/VoidFinder-Anbindung" --
WSL2/Linux-Voraussetzung, aktuell noch nicht verfügbar).

Bewusst schichtunabhängig (wie `geometry.py`): kombiniert Schicht 1
(`SDSSDR7TracerAdapter`) und potenziell Schicht 2/3, ist selbst aber kein
Layer, sondern eine WP2-spezifische Anwendung des Frameworks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

MISSING_COORD = -999.0


@dataclass
class CalibratorDiagnosisRow:
    """Ein Diagnosezeile pro Kalibrator-Wirt (vierstufiges Flag)."""

    cid: str
    host_ra: float
    host_dec: float
    z: float
    has_position: bool  # Flag 1
    position_source: str  # "host" | "sn_position" | "missing" -- siehe load_pantheon_calibrators
    sdss_spec_match: bool | None  # Flag 2 (None = nicht geprüft, keine SDSS-Daten übergeben)
    sdss_match_sep_arcsec: float | None
    environment_robust: bool | None  # Flag 3 (None = pending, kein VoidFinder-Lauf)
    environment_class: str | None  # Flag 4 (None = pending)


def load_pantheon_calibrators(path: str | Path) -> np.ndarray:
    """Lädt nur die Kalibrator-Zeilen (IS_CALIBRATOR == 1) aus Pantheon+SH0ES.dat.

    Erwartet das offizielle Pantheon+/SH0ES-DataRelease-Format
    (leerzeichengetrennt, erste Zeile = Spaltennamen), u.a. mit den Spalten
    `CID`, `zHD`, `HOST_RA`, `HOST_DEC`, `IS_CALIBRATOR`.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Pantheon+-Datei nicht gefunden: {path}. Beziehbar unter "
            "https://github.com/PantheonPlusSH0ES/DataRelease "
            "(Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat)."
        )
    data = np.genfromtxt(path, names=True, dtype=None, encoding="utf-8")
    required = {"CID", "zHD", "HOST_RA", "HOST_DEC", "IS_CALIBRATOR"}
    missing = required - set(data.dtype.names)
    if missing:
        raise KeyError(
            f"Erwartete Spalten fehlen in {path}: {missing}. "
            f"Vorhandene Spalten: {data.dtype.names}"
        )
    is_cal = data["IS_CALIBRATOR"].astype(int) == 1
    return data[is_cal]


def angular_separation_deg(
    ra1: np.ndarray, dec1: np.ndarray, ra2: np.ndarray, dec2: np.ndarray
) -> np.ndarray:
    """Sphärische Winkeltrennung (Großkreis) in Grad, vektorisiert (Haversine-artig)."""
    ra1r, dec1r = np.deg2rad(ra1), np.deg2rad(dec1)
    ra2r, dec2r = np.deg2rad(ra2), np.deg2rad(dec2)
    cos_sep = np.sin(dec1r) * np.sin(dec2r) + np.cos(dec1r) * np.cos(dec2r) * np.cos(
        ra1r - ra2r
    )
    return np.rad2deg(np.arccos(np.clip(cos_sep, -1.0, 1.0)))


def crossmatch_sdss_spec(
    host_ra: float,
    host_dec: float,
    host_z: float,
    sdss_ra: np.ndarray,
    sdss_dec: np.ndarray,
    sdss_z: np.ndarray,
    radius_arcsec: float = 3.0,
    z_tol: float = 0.005,
) -> tuple[bool, float | None]:
    """Prüft, ob ein SDSS-Tracer innerhalb `radius_arcsec` UND `z_tol` existiert.

    Grobe RA/Dec-Box-Vorfilterung vor der exakten sphärischen Distanz, damit
    das auch gegen große SDSS-Stichproben (>100k Objekte) für jeden einzelnen
    Kalibrator schnell bleibt, ohne eine volle Paarmatrix aufzubauen.

    Rückgabe: (match_gefunden, kleinste_separation_in_arcsec_oder_None).
    """
    if len(sdss_ra) == 0:
        return False, None

    radius_deg = radius_arcsec / 3600.0
    dec_min, dec_max = host_dec - radius_deg, host_dec + radius_deg
    cos_dec = max(np.cos(np.deg2rad(host_dec)), 1e-6)
    ra_pad = radius_deg / cos_dec
    ra_min, ra_max = host_ra - ra_pad, host_ra + ra_pad

    box = (
        (sdss_dec >= dec_min)
        & (sdss_dec <= dec_max)
        & (sdss_ra >= ra_min)
        & (sdss_ra <= ra_max)
        & (np.abs(sdss_z - host_z) <= z_tol)
    )
    if not np.any(box):
        return False, None

    sep = angular_separation_deg(host_ra, host_dec, sdss_ra[box], sdss_dec[box])
    best_sep_arcsec = float(np.min(sep) * 3600.0)
    return best_sep_arcsec <= radius_arcsec, best_sep_arcsec


def _resolve_position(entry) -> tuple[float, float, str]:
    """Ermittelt die beste verfügbare Position für einen Kalibrator-Wirt.

    Fallback-Reihenfolge: (1) dediziertes HOST_RA/HOST_DEC-Feld, falls
    gefüllt; (2) sonst die SN-eigene RA/DEC-Position, falls die Spalten
    existieren und gefüllt sind -- methodisch vertretbar, da eine Supernova
    innerhalb ihrer Wirtsgalaxie explodiert und die SN-Position auf der für
    einen Bogensekunden-/Bogenminuten-Crossmatch nötigen Genauigkeit eine
    gute Näherung für die Galaxienposition ist; (3) sonst "missing".

    Empirischer Befund (24.09.2026, echter Lauf gegen Pantheon+SH0ES.dat):
    HOST_RA/HOST_DEC sind im offiziellen Datenrelease durchgehend mit -999
    belegt (nicht befüllt) -- die SN-eigenen RA/DEC-Spalten sind dagegen
    gefüllt. Ohne diesen Fallback wäre Flag 1 für ALLE 77 Kalibratoren
    faelschlich "fehlt".
    """
    host_ra = float(entry["HOST_RA"])
    host_dec = float(entry["HOST_DEC"])
    if host_ra != MISSING_COORD and host_dec != MISSING_COORD:
        return host_ra, host_dec, "host"

    if "RA" in entry.dtype.names and "DEC" in entry.dtype.names:
        sn_ra = float(entry["RA"])
        sn_dec = float(entry["DEC"])
        if sn_ra != MISSING_COORD and sn_dec != MISSING_COORD:
            return sn_ra, sn_dec, "sn_position"

    return MISSING_COORD, MISSING_COORD, "missing"


def build_diagnosis_table(
    calibrators: np.ndarray,
    sdss_ra: np.ndarray | None = None,
    sdss_dec: np.ndarray | None = None,
    sdss_z: np.ndarray | None = None,
    radius_arcsec: float = 3.0,
    z_tol: float = 0.005,
    environment_lookup: dict | None = None,
) -> list[CalibratorDiagnosisRow]:
    """Baut die vierstufige Diagnosetabelle für eine Menge von Kalibratoren.

    `environment_lookup`: optionales Mapping `cid -> (robust: bool, class: str)`,
    z.B. aus einem echten `VASTVoidFinderAdapter.classify()`-Aufruf plus
    `assign_environment()` (Schicht 3) -- aktuell noch nicht automatisch
    verdrahtet, da kein echter VoidFinder-Lauf vorliegt (WSL2-Voraussetzung).
    """
    rows = []
    for entry in calibrators:
        cid = str(entry["CID"])
        host_ra, host_dec, position_source = _resolve_position(entry)
        z = float(entry["zHD"])
        has_position = position_source != "missing"

        sdss_match: bool | None = None
        sep_arcsec = None
        if has_position and sdss_ra is not None:
            sdss_match, sep_arcsec = crossmatch_sdss_spec(
                host_ra,
                host_dec,
                z,
                sdss_ra,
                sdss_dec,
                sdss_z,
                radius_arcsec=radius_arcsec,
                z_tol=z_tol,
            )

        env_robust = None
        env_class = None
        if environment_lookup is not None and cid in environment_lookup:
            env_robust, env_class = environment_lookup[cid]

        rows.append(
            CalibratorDiagnosisRow(
                cid=cid,
                host_ra=host_ra,
                host_dec=host_dec,
                z=z,
                has_position=has_position,
                position_source=position_source,
                sdss_spec_match=sdss_match,
                sdss_match_sep_arcsec=sep_arcsec,
                environment_robust=env_robust,
                environment_class=env_class,
            )
        )
    return rows



def summarize(rows: list[CalibratorDiagnosisRow]) -> dict:
    """Zusammenfassung der Diagnosetabelle: wie viele Kalibratoren überstehen
    jede der vier Stufen (kumulativ)."""
    n = len(rows)
    n_pos = sum(r.has_position for r in rows)
    n_sdss = sum(
        bool(r.sdss_spec_match) for r in rows if r.has_position and r.sdss_spec_match is not None
    )
    n_env_robust = sum(bool(r.environment_robust) for r in rows if r.sdss_spec_match)
    return {
        "n_total_calibrators": n,
        "n_with_position": n_pos,
        "n_sdss_spec_match": n_sdss,
        "n_environment_robust": n_env_robust,
    }
