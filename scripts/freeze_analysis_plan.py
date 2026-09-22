#!/usr/bin/env python3
"""WP0-Artefakt: "Eingefrorener Analyseplan" (Exposé Abschnitt 7, Ergebnis von WP0).

Sammelt die aktuell fixierten, analyseplan-relevanten Groessen (Referenz-
kosmologie, Erfolgskriterien, Blinding-Commitment) und schreibt sie als
SHA-256-signiertes JSON nach analysis_plan/frozen_plan.json.

Verwendung:
    python3 scripts/freeze_analysis_plan.py [--seed SECRET_SEED]

Der Blinding-Seed sollte in der Praxis NICHT als Kommandozeilenargument in
der Shell-History landen -- hier nur als Demo-Default. Fuer den echten Lauf:
Seed z.B. per `read -s` interaktiv abfragen oder aus einer nicht versionierten
.env-Datei lesen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from voidh0.layer0_cosmology import load_reference_cosmology  # noqa: E402
from voidh0.layer4_statistics import Blinder  # noqa: E402

# Erfolgskriterien aus Exposé Abschnitt 5, hier als maschinenlesbarer Teil
# des Analyseplans festgehalten.
SUCCESS_CRITERIA = {
    "detection": {
        "description": "Umgebungs-Step >= 3 sigma, stabil ueber >= 2 unabhaengige "
        "Void-Finder-Algorithmen und 2 Umgebungsdefinitionen.",
        "min_significance_sigma": 3.0,
        "min_independent_void_finders": 2,
        "min_environment_definitions": 2,
    },
    "null_result": {
        "description": "Obergrenze mit ausreichender Praezision, um den Beitrag "
        "zur H0-Spannung auf unter einen vorab definierten Schwellenwert zu "
        "begrenzen. Schwellenwert vor Entblindung (M6) verbindlich festzulegen.",
        "max_H0_contribution_percent": None,  # vor M6 auszufuellen
    },
    "abort_criterion": {
        "description": "Faellt die Stichprobe der void-klassifizierbaren "
        "Kalibratoren/SNe unter die in WP2 bestimmte Mindestzahl, wird das "
        "Projekt auf die reine Umgebungscharakterisierung reduziert und der "
        "H0-Arm auf Rubin-Daten vertagt.",
        "min_calibrator_sample_size": None,  # von WP2 zu bestimmen
    },
}


def build_plan(blinding_seed: str) -> dict:
    cosmo = load_reference_cosmology()
    blinder = Blinder(secret_seed=blinding_seed)

    plan = {
        "project": "voidh0",
        "expose_stand": "2026-09-19",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_cosmology": cosmo.as_dict(),
        "success_criteria": SUCCESS_CRITERIA,
        "blinding_commitment_sha256": blinder.commitment_hash(),
        "note": "Der Blinding-Seed selbst ist NICHT in diesem Dokument enthalten "
        "-- nur sein Commitment-Hash. Entblindung (M6) deckt den Seed auf und "
        "erlaubt die Verifikation gegen diesen Hash.",
    }
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        default="CHANGE_ME_before_real_freeze",
        help="Geheimer Blinding-Seed (Demo-Default -- fuer echten Analyseplan aendern!)",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "analysis_plan" / "frozen_plan.json"),
    )
    args = parser.parse_args()

    plan = build_plan(args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    plan_bytes = json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    plan["plan_self_hash_sha256"] = hashlib.sha256(plan_bytes).hexdigest()

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"Analyseplan geschrieben nach: {out_path}")
    print(f"  Referenzkosmologie: {plan['reference_cosmology']['name']} "
          f"(H0={plan['reference_cosmology']['H0_km_s_Mpc']} km/s/Mpc, "
          f"Om0={plan['reference_cosmology']['Om0']})")
    print(f"  Blinding-Commitment (SHA-256): {plan['blinding_commitment_sha256']}")
    print(f"  Plan-Self-Hash (SHA-256): {plan['plan_self_hash_sha256']}")
    if args.seed == "CHANGE_ME_before_real_freeze":
        print(
            "\nWARNUNG: Demo-Seed verwendet. Vor dem echten Einfrieren (M6-Voraussetzung) "
            "mit --seed <echter_geheimer_seed> erneut ausfuehren.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
