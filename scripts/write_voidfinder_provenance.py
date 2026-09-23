#!/usr/bin/env python3
"""Schreibt eine Provenienz-Sidecar-Datei nach einem externen VoidFinder-Lauf.

Auf der Seite ausfuehren, wo VoidFinder tatsaechlich lief (z.B. WSL2/Linux),
DIREKT nach dem Lauf -- BEVOR die `.fits`-Ausgabe zurueck nach Windows kopiert
wird. Die entstehende `<output>.fits.provenance.json`-Datei muss mitkopiert
werden; `VASTVoidFinderAdapter` sucht sie automatisch neben der `.fits`-Datei.

Verwendung:
    python3 scripts/write_voidfinder_provenance.py \\
        --output survey_VoidFinder_Output.fits \\
        --source-catalog vollim_dr7_cbp_102709.dat \\
        --voidfinder-version "1.x (git rev abc1234)" \\
        --notes "Erster WP1-Lauf, Default-Parameter"

Nutzt standardmaessig die Schicht-0-Referenzkosmologie aus configs/cosmology.yaml
-- WICHTIG: das ist nur korrekt, wenn VoidFinder tatsaechlich mit genau dieser
Kosmologie aufgerufen wurde (H0, Om0 als VoidFinder-Parameter). Falls mit
einer anderen Kosmologie gerechnet wurde, --h0 und --om0 explizit angeben.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from voidh0.layer0_cosmology import ReferenceCosmology, load_reference_cosmology  # noqa: E402
from voidh0.layer2_voidfinder.provenance import write_provenance  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, help="Pfad zur VoidFinder-.fits-Ausgabedatei")
    parser.add_argument("--source-catalog", required=True, help="Pfad zum Eingabekatalog, mit dem VoidFinder lief")
    parser.add_argument("--h0", type=float, default=None, help="H0 in km/s/Mpc, falls abweichend von Schicht 0")
    parser.add_argument("--om0", type=float, default=None, help="Om0, falls abweichend von Schicht 0")
    parser.add_argument("--cosmology-name", default=None, help="Name, falls --h0/--om0 gesetzt sind")
    parser.add_argument("--voidfinder-version", default="unknown")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    if args.h0 is not None or args.om0 is not None:
        if args.h0 is None or args.om0 is None:
            parser.error("--h0 und --om0 muessen zusammen angegeben werden")
        cosmology = ReferenceCosmology(
            name=args.cosmology_name or "custom_cli_cosmology",
            H0_km_s_Mpc=args.h0,
            Om0=args.om0,
        )
    else:
        cosmology = load_reference_cosmology()

    output_path = Path(args.output)
    source_path = Path(args.source_catalog)

    if not output_path.exists():
        print(f"WARNUNG: {output_path} existiert nicht (noch) -- Sidecar wird trotzdem geschrieben.", file=sys.stderr)
    if not source_path.exists():
        print(f"FEHLER: Quellkatalog {source_path} nicht gefunden -- kann keinen Hash berechnen.", file=sys.stderr)
        sys.exit(1)

    sidecar = write_provenance(
        output_path,
        cosmology,
        source_path,
        voidfinder_version=args.voidfinder_version,
        notes=args.notes,
    )
    print(f"Provenienz geschrieben nach: {sidecar}")
    print(f"  Kosmologie: {cosmology.name} (H0={cosmology.H0_km_s_Mpc}, Om0={cosmology.Om0})")
    print(f"  Quellkatalog: {source_path}")
    print()
    print("WICHTIG: Diese .provenance.json-Datei zusammen mit der .fits-Datei")
    print("zurueckkopieren (z.B. nach Windows) -- VASTVoidFinderAdapter sucht sie")
    print("automatisch daneben und bricht sonst standardmaessig ab.")


if __name__ == "__main__":
    main()
