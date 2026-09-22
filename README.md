# voidh0

**Galaxien in kosmischen Void-Umgebungen als möglicher systematischer Faktor für H₀**

Repository-Skelett für WP0 ("Setup: Referenzkosmologie, Repository, Datenprovenienz,
Blinding-Protokoll") aus dem Exposé vom 19. September 2026. Status: Konzeptphase —
dies ist ein **Analyse-Framework-Gerüst**, kein wissenschaftliches Ergebnis.

## Architekturprinzip

> "Kein Analyseschritt oberhalb von Schicht 2 darf einen survey-spezifischen Namen,
> eine survey-spezifische Spalte oder eine survey-spezifische Maske kennen — alles
> Survey-Spezifische lebt in Schicht 1 und 2."

Das Paket `voidh0` bildet die sechs Schichten aus Abschnitt 6 des Exposés 1:1 auf
Python-Subpakete ab:

| Schicht | Paket | Zweck |
|---|---|---|
| 0 — Kosmologie | `voidh0.layer0_cosmology` | eine einzige, explizit eingefrorene Referenzkosmologie |
| 1 — Tracer | `voidh0.layer1_tracers` | Survey-Adapter (Galaxientabelle, Maske, Randoms) |
| 2 — Void-Definition | `voidh0.layer2_voidfinder` | Void-Finder-Adapter (Void-Tabelle, Klassifikation) |
| 3 — Umgebungszuordnung | `voidh0.layer3_environment` | Zielobjekt → Umgebungsklasse + Vertrauensmaß |
| 4 — Statistik | `voidh0.layer4_statistics` | Step-/Regressionsmodelle, Blinding |
| 5 — Interpretation | `voidh0.layer5_interpretation` | Propagation auf H₀, Forecast |

Jede Schicht ist als Interface (abstrakte Basisklasse) plus Referenzimplementierung
angelegt, damit Schicht 1/2 später ausgetauscht werden können (M3 — "Survey-Austausch":
Tracer-Adapter getauscht, Schicht 3–5 unverändert lauffähig), ohne Schicht 3–5
anzufassen.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Absichtlich **keine** Abhängigkeit von `astropy`: Die Kosmologie in Schicht 0 ist
eine ca. 40-zeilige, selbst getestete FlatΛCDM-Implementierung (numpy/scipy), damit
die Referenzkosmologie exakt reproduzierbar und diff-bar im Repository liegt, statt
implizit von der installierten astropy-Version abzuhängen.

## Schnellstart

```bash
python3 scripts/freeze_analysis_plan.py
```

Schreibt einen signierten (SHA-256-Hash) "eingefrorenen Analyseplan" nach
`analysis_plan/frozen_plan.json` — das Kriterium für Meilenstein **M6 (Entblindung)**
ist erst erfüllbar, wenn dieser Hash vor der Entblindung dokumentiert wurde.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

(`unittest` statt `pytest`, um die Zahl der externen Abhängigkeiten in dieser
frühen Phase klein zu halten; `pytest` kann optional über `pip install -e ".[dev]"`
ergänzt werden.)

## Repository-Layout

```
voidh0/
├── configs/
│   └── cosmology.yaml          # Schicht 0: die EINE Referenzkosmologie
├── src/voidh0/
│   ├── layer0_cosmology/       # H0, Om0, Flatness — eingefroren, versioniert
│   ├── layer1_tracers/         # abstrakter TracerAdapter (Schicht 1)
│   ├── layer2_voidfinder/      # abstrakter VoidFinderAdapter (Schicht 2)
│   ├── layer3_environment/     # Umgebungsklassifikation + Vertrauensmaß
│   ├── layer4_statistics/      # Step-Modell + Blinding-Protokoll
│   └── layer5_interpretation/  # Δμ_env → ΔH0-Propagation
├── scripts/
│   └── freeze_analysis_plan.py # WP0-Artefakt: "Eingefrorener Analyseplan"
├── tests/
└── docs/
    └── architecture.md
```

## Bezug zum Arbeitsplan (Abschnitt 7 des Exposés)

Dieses Repository deckt **WP0** ab. Es enthält bewusst noch **keine** echten
Datenprodukte (Survey-Katalog, VoidFinder-Output, SN-Kompilation) — das ist WP1/WP2.
Alle Layer-1/2-Klassen hier sind Interfaces mit synthetischen Demo-Implementierungen,
damit Schicht 3–5 von Anfang an gegen eine stabile Schnittstelle entwickelt und
getestet werden können, bevor echte Survey-Daten angebunden werden.
