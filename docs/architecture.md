# Architektur

Dieses Dokument beschreibt die Umsetzung von Abschnitt 6 des Exposés
("Theoretischer und methodischer Rahmen") als Code und hält den aktuellen
Projektstatus fest.

**Stand:** 20.10.2026
**Konvention:** Aussagen sind getrennt nach *entschieden*, *vorgeschlagen* und
*offen*. Nichts, was als "vorgeschlagen" markiert ist, ist bereits Projektkonvention.

---

## 1. Die zentrale Designregel

> Kein Analyseschritt oberhalb von Schicht 2 darf einen survey-spezifischen
> Namen, eine survey-spezifische Spalte oder eine survey-spezifische Maske
> kennen — alles Survey-Spezifische lebt in Schicht 1 und 2.

Konkret umgesetzt durch:

1. **`TracerCatalog`** (Schicht 1) und **`VoidCatalog`** (Schicht 2) sind die
   einzigen Datenstrukturen, die Schicht 3 aufwärts sehen. Sie tragen
   ausschließlich normalisierte Feldnamen (`ra_deg`, `z`, `environment_class`, …).
2. Jeder Survey-/Void-Finder-spezifische Adapter ist eine Unterklasse von
   `TracerAdapter` bzw. `VoidFinderAdapter`. Ein Wechsel des Basis-Surveys
   (Meilenstein **M3**) bedeutet: neue Unterklasse schreiben, Schicht 3–5
   unverändert lassen.
3. Schicht 0 (Kosmologie) ist orthogonal zu allem: Sie kennt weder Survey noch
   Void-Finder, sondern liefert nur Distanzmaße auf Basis der einen
   eingefrorenen Referenzkosmologie.

## 2. Status auf einen Blick

| Baustein | Status |
|---|---|
| WP0 — Grundgerüst, alle 6 Schichten, Blinding-Protokoll | erledigt (Blinding-Seed noch Demo) |
| WP1 — `SDSSDR7TracerAdapter`, maskenbasierte Randoms | erledigt |
| Schicht 2 — `VASTVoidFinderAdapter` + Provenienz-Erzwingung | erledigt, gegen echten Lauf verifiziert (siehe Abschnitt 6) |
| Referenz-SN-Ia-Kompilation | entschieden: Pantheon+ & SH0ES |
| RF-D — kontinuierliche Umgebungsdichte | umgesetzt (`layer3_environment/density.py`) |
| WP2 — Kalibrator-Zuordnung | in Arbeit; Coverage-Diagnose liegt vor, Void/Wall-Klassifikation ausstehend |
| M4 — Machbarkeitsentscheidung | offen, siehe Abschnitt 10 und `wp2_calibrators.md` |

Es gibt weiterhin **keinen Nachweis** einer H₀-Abhängigkeit von der kosmischen
Umgebung. Der bisherige Fortschritt betrifft Datenaufbereitung, Validierung und
Machbarkeit.

---

## 3. Kosmologie und Zirkularität (Exposé Abschnitt 9)

Void-Kataloge sind selbst kosmologieabhängig konstruiert (Redshift → Distanz
braucht bereits eine Kosmologie). Schicht 0 als *einzige* Quelle für Distanzmaße
stellt sicher, dass

- dieselbe Referenzkosmologie in den Void-Finder-Adaptern (Schicht 2) und in der
  finalen H₀-Propagation (Schicht 5) verwendet wird,
- eine Änderung der Referenzkosmologie ein bewusster, versionierter Schritt ist
  (Änderung von `configs/cosmology.yaml`, dokumentiert im Analyseplan-Changelog).

Der geforderte **Invarianztest** ist damit direkt durchführbar:
`scripts/run_demo_pipeline.py` (oder ein WP1-Äquivalent mit echten Daten) zweimal
mit unterschiedlichen `configs/cosmology.yaml`-Varianten laufen lassen und prüfen,
ob der Umgebungs-Step (Schicht 4) stabil bleibt.

**Aktuelle Referenz (Schicht 0):** `H0 = 67.4 km/s/Mpc`, `Om0 = 0.315`, flach ΛCDM.

**VAST-Konvention (Quelltextprüfung):** komovierende Distanz,
`Ωm = 0,26`, `h = 1`, Längen in Mpc/h, Funktion `z_to_comoving_dist`.

> **Hinweis:** Die VAST-Defaults (`Ωm = 0,26`) weichen von der Schicht-0-Referenz
> (`Ωm = 0,315`) ab. Die Provenienzprüfung (Abschnitt 6) bricht bei abweichendem
> H0/Om0 absichtlich ab. Wo Distanzen für den VoidFinder-Raum berechnet werden
> (insbesondere Kalibratorpositionen in WP2), ist die Kosmologie des
> VoidFinder-Laufs explizit über `cosmology=` zu übergeben, nicht still die
> Schicht-0-Default-Kosmologie zu verwenden.

---

## 4. Schicht 1 — SDSS-DR7-Tracer (WP1)

**Entschieden:** Basis-Survey ist die volumenlimitierte SDSS-DR7-Hauptstichprobe
(`z ≲ 0,11`, `M_r < -20,09`), identisch zum Referenz-Survey von VoidFinder/VAST
(Douglass, Veyrat & BenZvi 2023, ApJS 265, 7). Eingabeformat ist 1:1 kompatibel
zur VAST-API (`ra`, `dec`, `redshift`, `rabsmag`).

```python
from voidh0.layer1_tracers import SDSSDR7TracerAdapter

adapter = SDSSDR7TracerAdapter(
    catalog_path="/pfad/zu/vollim_dr7_cbp_102709.dat",
    randoms_path="/pfad/zu/einem/random-katalog.dat",  # optional
)
tracers = adapter.load()
```

Bezugsquellen (nicht im Repository):

- VAST-Beispielkatalog `vollim_dr7_cbp_102709.dat` im GitHub-Repo `DESI-UR/VAST`
  (`VAST/example_scripts/`)
- Void-Kataloge zu Douglass, Veyrat & BenZvi (2023), auf Zenodo

Benötigt `astropy` (nur für diesen Adapter); der Rest des Frameworks bleibt astropy-frei.

**Randoms (erledigt):** Standardmäßig `randoms_mode="mask"`
(`layer1_tracers/mask_randoms.py`): aus dem Datenkatalog abgeleitete, gepixelte
Fußabdruckmaske; sphärisch korrekte Randoms (uniform in RA, uniform in sin(Dec),
Zellen flächengewichtet); Redshifts per Resampling aus der empirischen n(z).
`footprint_area_deg2()` liefert die sphärisch exakte Maskenfläche.
`randoms_mode="bbox"` bleibt zum Vergleich erhalten.

*Bewusste Einschränkung:* keine echte photometrische Survey-Maske (Mangle-Polygone
bzw. offizielle HEALPix-Maske mit Bohrlöchern für helle Sterne, Plattenränder).
Dafür bräuchte es `pymangle` oder die offizielle SDSS-DR7-Maskendatei.

---

## 5. Void-Finder-Familien: VoidFinder vs. V²

- **VoidFinder** ist ein Sphere-Growing-Algorithmus (El-Ad & Piran 1997;
  Hoyle & Vogeley 2002). Voids sind Vereinigungen von Kugeln (`MAXIMALS`/`HOLES`).
  Es gibt **keine** Voronoi-Zellvolumina als Zwischenergebnis.
- **V² (Vsquared)** ist der zweite, ZOBOV-basierte Watershed-Algorithmus im
  VAST-Toolkit (Voronoi-Tesselation, Neyrinck 2008). Er ist der in Exposé
  Abschnitt 6 vorgesehene "ZOBOV-basierte Kreuzcheck" und wird für RF-B
  (≥ 2 unabhängige Algorithmen) gebraucht.
- Die V²-`.fits`-Ausgabe (`GALZONE`-HDU: `gal`, `zone`, `depth`, `edge`, `out`)
  exportiert **keine** Zellvolumina.

---

## 6. Schicht 2 — VAST/VoidFinder-Anbindung

`VASTVoidFinderAdapter` (`layer2_voidfinder/vast_adapter.py`) liest die offizielle
VAST-Ausgabedatei (`[survey_name]_VoidFinder_Output.fits`; HDUs `MAXIMALS`, `HOLES`,
optional `MASK`) ein. Er führt VoidFinder **nicht** in-process aus: VAST wird
unter Windows offiziell nicht unterstützt (Cython-Kern, fehlender `fork()`).

**Workflow (Linux/WSL2):**

1. VAST installieren (`git clone https://github.com/DESI-UR/VAST`; aktuelle
   Anleitung: https://vast.readthedocs.io/en/latest/VAST_install.html).
2. `example_scripts/SDSS_VoidFinder_dr7.py` auf der DR7-Stichprobe laufen lassen.
3. Provenienz-Sidecar direkt danach erzeugen:

   ```bash
   python3 scripts/write_voidfinder_provenance.py \
       --output survey_VoidFinder_Output.fits \
       --source-catalog vollim_dr7_cbp_102709.dat
   ```

4. `.fits` und `.fits.provenance.json` **gemeinsam** in das Projekt kopieren.
5. Einlesen:

   ```python
   from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

   adapter = VASTVoidFinderAdapter("/pfad/zu/survey_VoidFinder_Output.fits")
   voids = adapter.find_voids(tracers)   # tracers nur für Interface-Kompatibilität
   labels = adapter.classify(ra, dec, z, voids)
   ```

**Provenienz-Erzwingung:** `find_voids()` bricht standardmäßig ab
(`ProvenanceMissingError` / `ProvenanceMismatchError`), wenn die Sidecar-Datei
fehlt oder H0/Om0 nicht zur aktiven Schicht-0-Kosmologie passen. Der Eingabekatalog
wird per SHA-256 geprüft. `require_provenance=False` nur für Experimente.

**Klassifikation:** `classify()` nutzt die volle `HOLES`-Tabelle (Union aller
Sphären eines Voids), nicht nur die Maximal-Sphäre. Ist eine `MASK`-HDU vorhanden,
werden Objekte außerhalb der Maske als `"edge"` markiert.

`DemoVoidFinderAdapter` bleibt für Entwicklung/Tests ohne WSL2 nutzbar.

---

## 7. Schicht 3 — Umgebung

### 7.1 Robustheitsflag (WP1)

`layer3_environment.assign_environment` implementiert den dreistufigen Flag:

| Flag | Bedeutung |
|---|---|
| `robust` | alle beigezogenen Void-Finder stimmen überein |
| `marginal` | Mehrheit, aber keine Einstimmigkeit |
| `edge_excluded` | Patt, oder mindestens ein Algorithmus meldet Randnähe zur Maske |

RF-B wird operationalisiert, indem `assign_environment` mit den Labels von
≥ 2 `VoidFinderAdapter`-Implementierungen aufgerufen wird; der Anteil
`robust`/`marginal`/`edge_excluded` ist selbst ein berichtetes Ergebnis.

### 7.2 Kontinuierliche Umgebungsdichte (RF-D, umgesetzt)

Zweiter Pfad neben der diskreten void/wall-Klassifikation (Schicht 3, nicht
Schicht 2). Da V² keine Zellvolumina exportiert, ist die Wiederverwendung kein
kostenloses Nebenprodukt. **Gewählt:** eigene Voronoi-Tesselation mit
`scipy.spatial` (`layer3_environment/density.py`:
`compute_local_density()`, `voronoi_cell_volumes()`).

- Lokale Dichte = inverses Voronoi-Zellvolumen relativ zum **Median** (Zellvolumina
  sind rechtsschief; ein Mittelwert würde durch große Randzellen verzerrt).
- Unbeschränkte Zellen (Rand der Punktwolke) werden als `is_edge_cell=True`
  markiert statt mit einem irreführenden Endwert versehen.
- 22 Tests, laufen ohne astropy.

*Bewusste Einschränkung:* keine Randoms-/Masken-Korrektur der Tesselation selbst.
Objekte innerhalb der Maske, aber nahe am Rand der Tracer-Punktwolke, können
unterschätzte Dichte haben. Nächster Verfeinerungsschritt: Tesselation über
Tracer + Randoms gemeinsam.

---

## 8. Schicht 4 — Blinding-Protokoll (WP0)

`layer4_statistics.Blinder` implementiert ein Commitment-Schema:

1. Vor jeder Analyse wird ein geheimer Seed gewählt (nicht im Repository).
2. `Blinder(secret_seed=...).commitment_hash()` (SHA-256) wird **vor** der Analyse
   dokumentiert (`scripts/freeze_analysis_plan.py`).
3. Alle Residuen werden mit `Blinder.blind(...)` verschoben, bevor das Team sie sieht.
4. Bei M6 wird der Seed offengelegt; der Hash lässt sich prüfen, dann
   `Blinder.unblind(...)`.

Das verhindert *Confirmation Bias* bei der Methodenentwicklung, nicht
*Data Snooping* durch multiple Tests (dafür sind die vorab festgelegten
Erfolgskriterien zuständig).

---

## 9. Referenz-SN-Ia-Kompilation (entschieden)

**Pantheon+ & SH0ES** (Scolnic et al. 2022, ApJ 938, 113; Brout et al. 2022,
ApJ 938, 110; Riess et al. 2022, ApJL 934, L7). 1701 Lichtkurven, 1550
spektroskopisch bestätigte SNe Ia, `0,001 < z < 2,26`.
Quelle: https://github.com/PantheonPlusSH0ES/DataRelease.

**Begründung:** Pantheon+ ist unter den geprüften Kompilationen (Pantheon+,
Union3, DES-SN5YR) die einzige mit öffentlichen **Einzelobjekt-Koordinaten für
Kalibrator-Stichprobe (`IS_CALIBRATOR`) und Hubble-Flow-Stichprobe** — das
Datenpaar, das WP2 (COVE, Δf_void) braucht. Union3 liegt nur gebinnt vor;
DES-SN5YR fixiert H₀ extern.

**Standardisierung:** übernommen (SALT2 wie veröffentlicht), nicht neu gefittet.
**Optional:** Union3 als Robustheits-Cross-Check in WP4/WP5.

---

## 10. WP2 — Kalibrator-Zuordnung

Details: `docs/wp2_calibrators.md`

| Punkt | Status |
|---|---|
| Kalibratorstichprobe | entschieden: 43 eindeutige SNe (aus 77 Zeilen) |
| SDSS-Spec-Match (3″) | 0/43, strukturell erklärt (Tracerkatalog beginnt bei z ≈ 0,01) |
| Host-Zuordnung | NSA + DLR mit Sentinel-Regel, in Arbeit |
| Redshift-Spalte für Positionen | offen; Variantenvergleich liegt vor (Median 1,2–2,2 Mpc/h, Max 4,4–5,9); Vorschlag zCMB/zHEL, zHD als Sensitivität |
| Rolle des Host-Matches für M4 | offen; Vorschlag: nicht mehr M4-Kriterium |
| Mindest-N-Schwelle | offen; vor Klassifikation committen |
| Void/Wall-Klassifikation der Kalibratoren | ausstehend |

---

## 11. Offene Punkte, bevor WP0/M4 abgeschlossen sind

- [x] Basis-Survey und Katalogversion (SDSS DR7, Abschnitt 4)
- [x] Referenz-SN-Ia-Kompilation (Pantheon+ & SH0ES, Abschnitt 9)
- [x] RF-D umgesetzt (Abschnitt 7.2)
- [x] Maskenbasierte Randoms (Abschnitt 4)
- [ ] Redshift-Konvention für Kalibratorpositionen (`wp2_calibrators.md`, Abschnitt 4)
- [ ] Rolle des Host-Matches für M4 (`wp2_calibrators.md`, Abschnitt 8)
- [ ] Mindeststichprobengröße für das Abbruchkriterium
- [ ] Schwellenwert für das Nullergebnis-Kriterium
      (`SUCCESS_CRITERIA["null_result"]["max_H0_contribution_percent"]`)
- [ ] Echter, sicher verwahrter Blinding-Seed (aktuell Demo-Default in
      `scripts/freeze_analysis_plan.py`)
- [ ] Kollaborationsrahmen
- [ ] Rechenressourcen/Datenvolumen für Phase 3 (Rubin/Roman)

## 12. Epistemischer Status

Die 35 bisher dokumentierten Unit-Tests (`wp2_cove`, `SDSSDR7TracerAdapter`)
bestätigen getestete Softwarefunktionen, nicht die wissenschaftliche Gültigkeit
der Survey-Überlappung oder der Umweltklassifikation. Die vierstufige
WP2-Diagnose ist nicht abgeschlossen; die Void-/Wall-/Edge-Zuordnung der
Kalibratoren bleibt ausstehend, bis die räumliche Zuordnung nachvollziehbar
validiert ist.
