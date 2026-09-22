# Architektur

Dieses Dokument beschreibt die Umsetzung von Abschnitt 6 des Exposés
("Theoretischer und methodischer Rahmen") als Code.

## Die zentrale Designregel

> Kein Analyseschritt oberhalb von Schicht 2 darf einen survey-spezifischen
> Namen, eine survey-spezifische Spalte oder eine survey-spezifische Maske
> kennen — alles Survey-Spezifische lebt in Schicht 1 und 2.

Konkret umgesetzt durch:

1. **`TracerCatalog`** (Schicht 1) und **`VoidCatalog`** (Schicht 2) sind die
   einzigen Datenstrukturen, die Schicht 3 aufwärts jemals sehen. Sie tragen
   ausschließlich normalisierte Feldnamen (`ra_deg`, `z`, `environment_class`, …).
2. Jeder Survey-/Void-Finder-spezifische Adapter ist eine konkrete
   Unterklasse von `TracerAdapter` bzw. `VoidFinderAdapter`. Ein Wechsel des
   Basis-Surveys (Meilenstein **M3**) bedeutet: neue Unterklasse schreiben,
   Schicht 3–5 unverändert lassen.
3. Schicht 0 (Kosmologie) ist orthogonal zu allem: sie kennt weder Survey
   noch Void-Finder, sondern liefert nur Distanzmaße auf Basis der einen
   eingefrorenen Referenzkosmologie.

## Zirkularität (Exposé Abschnitt 9)

Void-Kataloge sind selbst kosmologieabhängig konstruiert (Redshift → Distanz
braucht bereits eine Kosmologie). Die Trennung von Schicht 0 als *einzige*
Quelle für Distanzmaße stellt sicher, dass:

- dieselbe Referenzkosmologie sowohl in den Void-Finder-Adaptern (Schicht 2)
  als auch in der finalen H0-Propagation (Schicht 5) verwendet wird,
- eine Änderung der Referenzkosmologie ein bewusster, versionierter Schritt
  ist (Änderung von `configs/cosmology.yaml`, dokumentiert im Analyseplan-
  Changelog), nicht ein impliziter Seiteneffekt.

Der geforderte **Invarianztest** (Zeile "Kosmologie-Zirkularität nicht
ausräumbar" in der Risikotabelle) ist mit diesem Aufbau direkt durchführbar:
`scripts/run_demo_pipeline.py` (oder ein WP1-Äquivalent mit echten Daten)
zweimal mit unterschiedlichen `configs/cosmology.yaml`-Varianten laufen lassen
und prüfen, ob der Umgebungs-Step (Schicht 4) stabil bleibt.

## Robustheitsflag (WP1)

`layer3_environment.assign_environment` implementiert den "dreistufigen
Robustheitsflag" aus dem WP1-Zielprodukt:

| Flag | Bedeutung |
|---|---|
| `robust` | alle beigezogenen Void-Finder-Algorithmen stimmen überein |
| `marginal` | Mehrheit, aber keine Einstimmigkeit |
| `edge_excluded` | Patt, oder mindestens ein Algorithmus meldet Randnähe zur Maske |

RF-B ("Wie stabil ist die Void/Wand-Zuordnung über verschiedene
Void-Finder-Algorithmen … hinweg?") wird operationalisiert, indem
`assign_environment` mit den Labels von ≥ 2 `VoidFinderAdapter`-Implementierungen
aufgerufen wird und der Anteil `robust` vs. `marginal` vs. `edge_excluded`
selbst zum berichteten Ergebnis wird.

## Blinding-Protokoll (WP0)

`layer4_statistics.Blinder` implementiert ein simples Commitment-Schema:

1. Vor jeder Analyse wird ein geheimer Seed gewählt (nicht im Repository!).
2. `Blinder(secret_seed=...).commitment_hash()` — ein SHA-256-Hash des Seeds
   — wird **vor** der Analyse dokumentiert (z. B. im eingefrorenen Analyseplan,
   siehe `scripts/freeze_analysis_plan.py`).
3. Alle Residuen werden mit `Blinder.blind(...)` verschoben, bevor sie das
   Team sieht.
4. Bei Meilenstein **M6 (Entblindung)** wird der Seed offengelegt; jeder kann
   dessen SHA-256-Hash gegen den vorab dokumentierten Commitment-Hash prüfen
   und dann `Blinder.unblind(...)` anwenden.

Dies verhindert nicht *Data Snooping* im Sinne multipler Tests — dafür sind
die vorab (Abschnitt 5) festgelegten Erfolgskriterien zuständig — sondern
*Confirmation Bias* während der Methodenentwicklung.

## Offene Punkte, bevor WP0 als abgeschlossen gelten kann

Diese Liste ist eine Eins-zu-eins-Übertragung von Exposé Abschnitt 9,
"Offene Entscheidungen":

- [ ] finaler Basis-Survey + Katalogversion (Phase 1) → `configs/cosmology.yaml`
      und ein echter `TracerAdapter` ersetzen `DemoTracerAdapter`
- [ ] Referenz-SN-Ia-Kompilation festlegen
- [ ] diskrete vs. kontinuierliche Umgebungsvariable: aktuell ist
      `layer3_environment` rein diskret (void/wall); eine kontinuierliche
      Dichtevariable ist als zweiter, paralleler Pfad zu ergänzen (RF-D)
- [ ] Kollaborationsrahmen
- [ ] Rechenressourcen/Datenvolumen für Phase 3 (Rubin/Roman)
- [ ] echter, sicher verwahrter Blinding-Seed (aktuell nur Demo-Default in
      `scripts/freeze_analysis_plan.py`)
- [ ] Schwellenwert für das Nullergebnis-Erfolgskriterium
      (`SUCCESS_CRITERIA["null_result"]["max_H0_contribution_percent"]`)
- [ ] Mindeststichprobengröße für das Abbruchkriterium
      (`SUCCESS_CRITERIA["abort_criterion"]["min_calibrator_sample_size"]`)
