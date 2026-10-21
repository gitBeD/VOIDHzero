# voidh0

**Galaxien in kosmischen Void-Umgebungen als möglicher systematischer Faktor für H₀**

Analyse-Framework und Diagnosewerkzeuge für ein Multi-Survey-Projekt, das untersucht, ob die großräumige kosmische Umgebung einer Galaxie (Void, Wand, Filament) systematische Residuen in den Distanzindikatoren zur H₀-Kalibrierung erzeugt.

**Status (Stand 21.10.2026): Konzeptphase, Hypothesentest, kein Ergebnis zu H₀.**
Das Repository enthält das Framework-Gerüst (WP0) und Diagnosen zur Kalibrator-Zuordnung (WP2), die gegen echte Daten laufen. Es gibt noch **keine** Aussage zu Δμ_env, Δf_void oder ΔH₀. Alle WP2-Befunde sind Sensitivitäts- und Machbarkeitsprüfungen.

## Wissenschaftlicher Status

Detailstand: [`docs/wp2_calibrators.md`](docs/wp2_calibrators.md). Jede Zahl verweist auf ein Dokument oder Skript.

### Gesichert (Datenaufbereitung und Prüfungen)

| Befund | Beleg |
|---|---|
| Die Pantheon+-Datei enthält 77 Kalibratorzeilen (`IS_CALIBRATOR=1`), das sind Lichtkurven-Einträge verschiedener Pipelines. Nach Deduplizierung nach `CID` bleiben **43 CIDs**. Die Deduplizierung ist ein reiner Exakt-Match; Fälle wie `2005df` und `2005df_ANU` werden nicht zusammengeführt. | `docs/wp2_calibrators.md` §1 |
| `HOST_RA`/`HOST_DEC` sind im Release durchgehend `-999`. Die Zuordnung verwendet daher die SN-Koordinaten (`position_source = sn_position`). | `docs/wp2_calibrators.md` §1 |
| Host-Referenztabelle: 43 CID-Zeilen, 37 Wirtsgalaxien. Zwei CID-Host-Zuordnungen wurden gegen Riess et al. (2022) korrigiert (`2005W` → NGC 691, `1998dh` → NGC 7541). SIMBAD und NED stimmen für **30 von 37** Hosts innerhalb 1″ überein, 7 Hosts haben eine vorläufige SIMBAD-Referenz (`review_required`). Die 1″-Schwelle ist ein Konsistenzflag, kein wissenschaftlicher Matching-Radius. | `docs/wp2_sh0es_host_validation.md` |
| SDSS-Crossmatch gegen `vollim_dr7_cbp_102709.dat` (3″): **0 von 43** Treffer. Das ist eine strukturelle Folge der Katalogkonstruktion (Untergrenze `z ≈ 0,01`), kein Softwarefehler. Die Aussage gilt für diesen Katalog, nicht für SDSS insgesamt. | `docs/wp2_calibrators.md` §2, `results/wp2_coverage_diagnostic.csv` |
| Die komovierende Distanzfunktion in VAST skalierte bei `h ≠ 1` zusätzlich mit 1/h. Nach der lokalen Korrektur liefern `h = 0,674` und `h = 1,0` identische Distanzen (z = 0,01 / 0,05 / 0,10 → 29,908 / 148,109 / 292,590 Mpc/h). | `docs/wp2_sh0es_void_membership_unitfix.md` §2 |

### Vorläufig

| Befund | Beleg | Vorbehalt |
|---|---|---|
| 29 der 43 Kalibratorpositionen liegen außerhalb des umschließenden RA/Dec-Rechtecks des Tracerkatalogs, 14 in markierten Zellen der gespeicherten VAST-Winkelmaske (obere Grenze der Überlappung). | `docs/wp2_calibrators.md` §2 | Die Maske stammt aus dem für VoidFinder vorbereiteten Katalog und bestätigt die offizielle SDSS-Abdeckung nicht unabhängig. Radiale Abdeckung noch nicht abschließend geprüft. |
| VoidFinder-Lauf nach der Distanzkorrektur (Ωm = 0,315, h = 0,674): 875 MAXIMALS, 44.423 HOLES. **9 von 43** SN-Positionen liegen in mindestens einer Kugel. Identisch zum Kontrolllauf mit h = 1. | `docs/wp2_sh0es_void_membership_unitfix.md` §3–4 | Geometrischer Kugeltest, keine Void/Wall-Klassifikation. MAXIMALS- und HOLES-Treffer dürfen nicht addiert werden. |
| Der Lauf vor der Korrektur (2.760 MAXIMALS, 220.596 HOLES) ergab 10 von 43. Drei CIDs wechseln gegenüber dem korrigierten Lauf (`2003du`, `2005cf`, `2012ht`). | ebenda | Alter Lauf nicht als physikalische Referenz verwenden. |
| Redshift-Variantenvergleich (43 Kalibratoren): Verschiebung gegenüber `zHD` im Median 1,22 Mpc/h (`zCMB`) bzw. 2,15 Mpc/h (`zHEL`), maximal 4,40 bzw. 5,86 Mpc/h, rein radial. | `docs/wp2_redshift_variant_comparison.md` | Positionssensitivitätstest, kein H₀-Ergebnis. |

### Offen

- **Primäre Rotverschiebungsvariante.** Bisher wird `zHD` verwendet; das ist eine vorläufige Konvention und nach Sicht erster Ergebnisse gewählt, also explorativ. Vorgeschlagen ist `zCMB` oder `zHEL`, abhängig vom Bezugssystem des Tracerkatalogs. Die Primärvariante ist vor der Klassifikation festzuschreiben.
- **Mindeststichprobengröße** (`min_calibrator_sample_size`), gezählt pro Wirtsgalaxie, vor der Klassifikation zu committen.
- **Zählung pro Wirtsgalaxie statt pro Supernova** (mehrere SNe im selben Wirt sind keine unabhängigen Umgebungsmessungen).
- **Entkopplung des Host-Matches** (Winkel-Footprint, radiale Abdeckung und Randabstand als getrennte Zähler).
- **NSA als Tracerkatalog.** Geplant, nicht validiert. Ergebnisse gelten als eigene Analysevariante, da der Katalogwechsel Void-Geometrie und Auswahlfunktion verändern kann.
- **Host-Zuordnung über NSA und DLR** (`scripts/wp2_nsa_dlr_diagnosis.py`). Die Regel zum Sentinel-Wert `SERSIC_TH50 = 159,7578125″` ist empirisch und nicht durch die NSA-Dokumentation bestätigt.
- **Sensitivität gegenüber Pekuliargeschwindigkeiten.** Noch nicht durchgeführt.

### Hinweis zu älteren Angaben

Frühere Fassungen des Exposés nennen 2.760 Voids und eine Verteilung von 3 void / 11 wall / 29 edge bei den Kalibratoren. Diese Zahlen stammen aus dem Lauf **vor** der Distanzkorrektur und werden hier nicht weiterverwendet. Der Wert „67 % Edge“ beschreibt nicht klassifizierbare Positionen und ist keine Aussage über die Umgebung der Galaxien.

## Bekannte Einschränkungen

- **SN-Positionen statt Wirtspositionen.** Die Void-Mitgliedschaft wird mit SN-Koordinaten berechnet. Die Host-Validierung betrifft die Wirtsidentität und die Wirtskoordinaten, sie ersetzt die Positionen in der Mitgliedschaftsrechnung nicht.
- **Kosmologie.** Der Redshift-Variantenvergleich verwendet Ωm = 0,26 und h = 1, die VoidFinder-Läufe Ωm = 0,315. Der Einfluss ist laut Dokumentation klein, ist aber zu klären und bei jeder Zuordnung explizit zu setzen (`cosmology=`).
- **VAST-Korrektur außerhalb dieses Repos.** Die Distanzkorrektur wurde in der lokal installierten VAST-Erweiterung (`distance.pyx`, `voidfinder.py`) vorgenommen. Die Pipeline ist nur mit diesem Patch reproduzierbar. Siehe `patches/` und die Provenienzdatei.
- **Void-IDs** sind zwischen Läufen keine stabilen Objektidentitäten.
- **Einheiten.** Die Distanzkorrektur beseitigt die erkannte h-Abhängigkeit. Maskengenerierung, Gitterparameter, Randbedingungen und FITS-Metadaten sind noch nicht vollständig auf Einheitenkonsistenz validiert.

## Architektur

Das Paket `voidh0` bildet sechs Schichten auf Python-Subpakete ab. Designregel: Kein Analyseschritt oberhalb von Schicht 2 darf einen survey-spezifischen Namen, eine survey-spezifische Spalte oder Maske kennen.

| Schicht | Paket | Zweck |
|---|---|---|
| 0 – Kosmologie | `voidh0.layer0_cosmology` | eine eingefrorene Referenzkosmologie |
| 1 – Tracer | `voidh0.layer1_tracers` | Survey-Adapter (Galaxientabelle, Maske, Randoms) |
| 2 – Void-Definition | `voidh0.layer2_voidfinder` | Void-Finder-Adapter |
| 3 – Umgebungszuordnung | `voidh0.layer3_environment` | Zielobjekt → Umgebungsklasse + Vertrauensmaß; kontinuierliche Voronoi-Dichteschätzung (RF-D) |
| 4 – Statistik | `voidh0.layer4_statistics` | Step-/Regressionsmodelle, Blinding |
| 5 – Interpretation | `voidh0.layer5_interpretation` | Propagation auf H₀, Forecast |

Details: [`docs/architecture.md`](docs/architecture.md). Die Schichten 1 und 2 sind als austauschbare Interfaces angelegt (Meilenstein M3).

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Die Kosmologie in Schicht 0 ist eine kleine, selbst getestete FlatΛCDM-Implementierung (numpy/scipy) ohne `astropy`-Abhängigkeit. Die VoidFinder-Läufe benötigen zusätzlich VAST (Version 1.7.9, Linux) mit dem Distanz-Patch aus `patches/`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Zusätzliche Prüfungen: `tests/unit_checks/analyze_boundary_cases.py` (Grenzfallanalyse der Void-Mitgliedschaft).

## Reproduzierbarkeit

Die Aufrufparameter stehen im Kopf des jeweiligen Skripts.

| Skript | Zweck |
|---|---|
| `scripts/wp2_calibrator_diagnosis.py`, `scripts/wp2_cove.py` | Kalibratorliste, Positionsauflösung, Flag-Diagnose |
| `scripts/wp2_coverage_diagnostic.py` | Winkel- und Radialabdeckung, SDSS-Crossmatch (→ `results/wp2_coverage_diagnostic.csv`) |
| `scripts/wp2_sh0es_host_resolver.py` | Host-Validierung gegen SIMBAD und NED |
| `scripts/wp2_ned_position_audit.py`, `scripts/wp2_ned_audit_summary.py` | NED-Positionsaudit und Zusammenfassung |
| `scripts/wp2_sh0es_cartesian.py`, `scripts/wp2_sh0es_cartesian_run_cosmology.py` | Kartesische Kalibratorkoordinaten |
| `scripts/wp2_compare_redshift_variants.py` | Vergleich von `zHD`, `zCMB`, `zHEL` |
| `scripts/check_vast_distance_units.py`, `scripts/verify_mask_indexing.py` | VAST-Einheiten- und Maskenprüfungen |
| `scripts/wp2_nsa_diagnosis.py`, `scripts/wp2_nsa_dlr_diagnosis.py`, `scripts/nsa_sersic_th50_audit.py`, `scripts/wp2_dlr_control_2011fe.py` | NSA-Host-Zuordnung über DLR und Qualitätsaudit |
| `scripts/wp2_independent_crossmatch.py` | unabhängiger Crossmatch |
| `scripts/write_voidfinder_provenance.py` | Provenienzdatei je VoidFinder-Lauf |
| `scripts/freeze_analysis_plan.py` | eingefrorener Analyseplan (SHA-256) |

Der Analyseplan wird erst eingefroren, wenn Primärvariante, Klassifikationsregeln, Mindeststichprobengröße und Umgang mit Randfällen festgelegt sind.

## Daten und Lizenzen

Nicht versioniert (siehe `.gitignore`): `Pantheon+SH0ES.dat`, `nsa_v1_0_1.fits`, `vollim_dr7_cbp_102709.*` und die Rohantworten des NED-Audits. Diese Datensätze unterliegen ihren eigenen Lizenzen und Zitierpflichten (Pantheon+/SH0ES, NASA-Sloan Atlas, Pan et al. 2012). Eine Projektlizenz gilt nicht automatisch für sie.

Abgeleitete Tabellen liegen unter `data/external/` (u. a. Host-Referenztabelle, kartesische Kalibratorkoordinaten, Mitgliedschaftsdateien, Redshift-Variantenvergleich) und unter `results/`.

## Repository-Layout

```
voidh0/
├── configs/            # Schicht 0: Referenzkosmologie
├── data/external/      # abgeleitete Tabellen, Drittanbieter-Rohdaten (nicht versioniert)
├── docs/               # architecture.md, WP2-Dokumentation
├── patches/            # lokale Patches an Drittsoftware (VAST)
├── results/            # Diagnoseergebnisse (CSV)
├── scripts/            # WP0/WP2-Skripte
├── src/voidh0/         # sechs Schichten
└── tests/
```

## Bezug zum Arbeitsplan

Das Repository deckt WP0 (Setup) und Teile von WP2 (Kalibrator-Zuordnung, COVE) ab. WP2 ist nicht abgeschlossen: Die Go/No-Go-Entscheidung für den H₀-Arm (Meilenstein M4) steht aus und hängt an Primärvariante, radialer Abdeckung und Mindeststichprobengröße.

## Lizenz und Zitation

Eine Projektlizenz ist noch nicht festgelegt.
