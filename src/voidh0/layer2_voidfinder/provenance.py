"""Provenienz-Metadaten fuer externe VoidFinder-Laeufe.

Motivation (Exposé Abschnitt 9, "Kosmologie-Zirkularitaet nicht ausraeumbar"):
`VASTVoidFinderAdapter` liest eine extern (z.B. in WSL2) erzeugte VoidFinder-
Ausgabe ein und muss dabei dieselbe Referenzkosmologie verwenden, mit der
VoidFinder dort lief -- sonst sind die (ra,dec,z)->(x,y,z)-Sphere-Vergleiche
in `classify()` inkonsistent, ohne dass das an irgendeiner Stelle sichtbar
waere. Bisher war das nur eine Doku-Empfehlung (docs/architecture.md);
dieses Modul macht daraus eine tatsaechlich geprüfte Bedingung.

Funktionsweise: Direkt nach einem externen VoidFinder-Lauf (auf der
WSL2/Linux-Seite) wird `write_provenance()` aufgerufen und schreibt eine
JSON-Sidecar-Datei neben die `.fits`-Ausgabe (`<output>.provenance.json`).
Sie haelt fest: mit welcher Kosmologie (H0, Om0) gerechnet wurde, welcher
Eingabekatalog (per SHA-256-Hash) verwendet wurde, und wann/womit der Lauf
geschah. `VASTVoidFinderAdapter` liest diese Sidecar-Datei beim Einlesen der
`.fits`-Datei und bricht ab (statt still falsche Ergebnisse zu produzieren),
wenn Kosmologie oder Eingabekatalog nicht zur aktuellen Schicht-0-Konfiguration
passen.

Bewusst als einfache, lesbare JSON-Datei (kein FITS-Header-Trick): so bleibt
die Provenienz auch ohne astropy einsehbar/pruefbar, und Header-Konventionen
der externen VAST-Installation muessen nicht angenommen werden.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..layer0_cosmology import ReferenceCosmology


def compute_file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """SHA-256-Hash einer Datei, blockweise gelesen (auch fuer grosse Kataloge geeignet)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass
class VoidFinderProvenance:
    """Provenienz-Metadaten eines externen VoidFinder-Laufs."""

    cosmology_name: str
    H0_km_s_Mpc: float
    Om0: float
    source_catalog_path: str
    source_catalog_sha256: str
    created_utc: str
    voidfinder_version: str = "unknown"
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "VoidFinderProvenance":
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


def sidecar_path_for(output_fits_path: str | Path) -> Path:
    return Path(str(output_fits_path) + ".provenance.json")


def write_provenance(
    output_fits_path: str | Path,
    cosmology: ReferenceCosmology,
    source_catalog_path: str | Path,
    voidfinder_version: str = "unknown",
    notes: str = "",
) -> Path:
    """Schreibt die Provenienz-Sidecar-Datei fuer einen VoidFinder-Lauf.

    Wird auf der Seite ausgefuehrt, wo VoidFinder tatsaechlich lief (z.B.
    WSL2/Linux), direkt nach dem Lauf -- siehe `scripts/write_voidfinder_
    provenance.py` fuer ein aufrufbares Kommandozeilen-Skript.
    """
    provenance = VoidFinderProvenance(
        cosmology_name=cosmology.name,
        H0_km_s_Mpc=cosmology.H0_km_s_Mpc,
        Om0=cosmology.Om0,
        source_catalog_path=str(source_catalog_path),
        source_catalog_sha256=compute_file_sha256(source_catalog_path),
        created_utc=datetime.now(timezone.utc).isoformat(),
        voidfinder_version=voidfinder_version,
        notes=notes,
    )
    path = sidecar_path_for(output_fits_path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(provenance.to_dict(), fh, indent=2, ensure_ascii=False, sort_keys=True)
    return path


def read_provenance(output_fits_path: str | Path) -> VoidFinderProvenance | None:
    """Liest die Provenienz-Sidecar-Datei, falls vorhanden; sonst None."""
    path = sidecar_path_for(output_fits_path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return VoidFinderProvenance.from_dict(raw)


class ProvenanceMismatchError(ValueError):
    """Kosmologie oder Eingabekatalog der Provenienz passen nicht zur aktuellen Konfiguration."""


class ProvenanceMissingError(ValueError):
    """Es wurde keine Provenienz-Sidecar-Datei gefunden, obwohl eine verlangt ist."""


def validate_provenance(
    provenance: VoidFinderProvenance | None,
    cosmology: ReferenceCosmology,
    require: bool = True,
    rtol: float = 1e-6,
    expected_source_catalog_path: str | Path | None = None,
) -> None:
    """Prueft eine geladene Provenienz gegen die aktuell aktive Schicht-0-Kosmologie.

    Wirft `ProvenanceMissingError`, wenn `require=True` und keine Provenienz
    vorliegt. Wirft `ProvenanceMismatchError`, wenn H0/Om0 (relative Toleranz
    `rtol`) oder -- falls angegeben -- der erwartete Quellkatalog-Pfad nicht
    uebereinstimmen. Bei `require=False` und fehlender Provenienz wird
    stillschweigend nichts geprueft (Opt-out fuer schnelle Experimente,
    NICHT empfohlen fuer publikationsreife Laeufe).
    """
    if provenance is None:
        if require:
            raise ProvenanceMissingError(
                "Keine Provenienz-Sidecar-Datei (*.provenance.json) gefunden. "
                "Ohne sie kann nicht automatisch geprueft werden, ob der externe "
                "VoidFinder-Lauf dieselbe Kosmologie verwendet hat wie Schicht 0 "
                "hier (Exposé Abschnitt 9, 'Kosmologie-Zirkularitaet'). "
                "Sidecar mit write_provenance() erzeugen, oder explizit "
                "require_provenance=False setzen, um diese Pruefung zu ueberspringen "
                "(nicht empfohlen)."
            )
        return

    h0_ok = abs(provenance.H0_km_s_Mpc - cosmology.H0_km_s_Mpc) <= rtol * cosmology.H0_km_s_Mpc
    om0_ok = abs(provenance.Om0 - cosmology.Om0) <= rtol * cosmology.Om0
    if not (h0_ok and om0_ok):
        raise ProvenanceMismatchError(
            f"Kosmologie-Mismatch zwischen externem VoidFinder-Lauf und aktueller "
            f"Schicht-0-Konfiguration: Lauf verwendete H0={provenance.H0_km_s_Mpc}, "
            f"Om0={provenance.Om0} (Kosmologie '{provenance.cosmology_name}'), "
            f"aktuell aktiv ist H0={cosmology.H0_km_s_Mpc}, Om0={cosmology.Om0} "
            f"(Kosmologie '{cosmology.name}'). Die (ra,dec,z)->(x,y,z)-Sphere-"
            f"Vergleiche in classify() waeren mit dieser Abweichung inkonsistent "
            f"(Exposé Abschnitt 9, 'Kosmologie-Zirkularitaet'). Entweder dieselbe "
            f"Kosmologie fuer den externen Lauf verwenden, oder hier explizit "
            f"cosmology=<die-beim-Lauf-verwendete-Kosmologie> uebergeben."
        )

    if expected_source_catalog_path is not None:
        expected = str(expected_source_catalog_path)
        if provenance.source_catalog_path != expected:
            raise ProvenanceMismatchError(
                f"Provenienz nennt einen anderen Quellkatalog "
                f"({provenance.source_catalog_path!r}) als erwartet ({expected!r}). "
                "Pruefen, ob die richtige VoidFinder-Ausgabe eingelesen wird."
            )
