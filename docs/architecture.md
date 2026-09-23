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
"Offene Entscheidungen".

- [x] finaler Basis-Survey + Katalogversion (Phase 1): **SDSS DR7
      Hauptstichprobe, volumenlimitiert, z ≲ 0,11, M_r < -20,09** — identisch
      zum Referenz-Survey von VoidFinder/VAST (Douglass, Veyrat & BenZvi 2023,
      ApJS 265, 7). `SDSSDR7TracerAdapter` (`layer1_tracers/sdss_dr7_adapter.py`)
      ersetzt `DemoTracerAdapter` für echte Daten; Eingabeformat ist 1:1
      kompatibel zur offiziellen VAST-API (`ra`, `dec`, `redshift`, `rabsmag`
      als `ascii.commented_header`/FITS/HDF5).
- [x] **Referenz-SN-Ia-Kompilation festgelegt**: **Pantheon+ & SH0ES**
      (Scolnic et al. 2022, ApJ 938, 113; Brout et al. 2022, ApJ 938, 110;
      Riess et al. 2022, ApJL 934, L7). 1701 Lichtkurven für 1550
      spektroskopisch bestätigte SNe Ia, `0.001 < z < 2.26`, öffentlich unter
      https://github.com/PantheonPlusSH0ES/DataRelease.
      **Begründung** (direkt WP2/RF-C-relevant): Pantheon+ ist die einzige
      der drei geprüften Kompilationen (Pantheon+, Union3, DES-SN5YR), die
      öffentlich **individuelle Koordinaten sowohl der Kalibrator-Stichprobe
      (Cepheiden-/TRGB-Wirte, per `IS_CALIBRATOR`-Flag markiert) als auch der
      Hubble-Flow-Stichprobe** liefert — exakt das Cross-Match-Datenpaar, das
      WP2 (COVE, Δf_void) braucht. Union3 liegt nur als gebinnte
      Distanzmodul-Tabelle vor (keine Einzelobjekt-Koordinaten); DES-SN5YR
      fixiert H0 extern statt eine eigene Kalibrator-Host-Stichprobe zu
      führen. Beide sind daher für die "Kalibrator vs. Hubble-Flow"-
      Fragestellung strukturell schlechter geeignet, obwohl sie für reine
      Kosmologie-Fits attraktiv sind.
      **Standardisierung**: übernommen (SALT2-Standardisierung wie von
      Pantheon+ veröffentlicht), nicht neu gefittet — Kapazität bleibt für
      den Umgebungs-Step statt für einen SN-Standardisierungs-Neufit.
      **Optional**: Union3 als Robustheits-Cross-Check in WP4/WP5, falls
      Zeit vorhanden ist — nicht als Ersatz für Pantheon+.
      **Offener Folgepunkt (RF-D-Ticket)**: kontinuierliche
      Umgebungsdichte-Variable als zweiter, paralleler Pfad neben der
      diskreten void/wall-Klassifikation (Schicht 3, nicht Schicht 2 — die
      Layer-Regel aus Abschnitt 6 gilt auch hier). Naheliegendster Ansatz:
      VoidFinder/VAST führt für die Void-Identifikation intern bereits eine
      Voronoi-Tesselation durch; falls dieses Zwischenergebnis aus einem
      externen VAST-Lauf mit exportiert werden kann, ließe sich die lokale
      Dichte daraus für Schicht 3 wiederverwenden, statt sie separat (z.B.
      per kNN-Distanz oder Kernel-Dichteschätzung) neu zu berechnen — spart
      Rechenzeit und hält Konsistenz mit der diskreten Klassifikation
      automatisch. Ob das technisch zugänglich ist, ist vor der Umsetzung zu
      prüfen (offen).
- [ ] Kollaborationsrahmen
- [ ] Rechenressourcen/Datenvolumen für Phase 3 (Rubin/Roman)
- [ ] echter, sicher verwahrter Blinding-Seed (aktuell nur Demo-Default in
      `scripts/freeze_analysis_plan.py`)
- [ ] Schwellenwert für das Nullergebnis-Erfolgskriterium
      (`SUCCESS_CRITERIA["null_result"]["max_H0_contribution_percent"]`)
- [ ] Mindeststichprobengröße für das Abbruchkriterium
      (`SUCCESS_CRITERIA["abort_criterion"]["min_calibrator_sample_size"]`)
- [x] **neuer WP1-Punkt, erledigt**: `SDSSDR7TracerAdapter` verwendet jetzt
      standardmäßig (`randoms_mode="mask"`) eine aus dem Datenkatalog
      abgeleitete, gepixelte Fußabdruckmaske (`layer1_tracers/mask_randoms.py`)
      statt einer reinen RA/Dec-Bounding-Box: sphärisch korrekte Zufalls­positionen
      innerhalb belegter Gitterzellen (uniform in RA, uniform in sin(Dec),
      Zellen flächengewichtet ausgewählt) und Redshifts durch Resampling aus
      der empirischen n(z)-Verteilung der Daten statt uniform in z.
      `footprint_area_deg2()` liefert nach einem `mask`-Lauf die sphärisch
      exakte Maskenfläche statt der groben Bounding-Box-Fläche.
      **Bewusste Einschränkung**: das ist noch keine echte photometrische
      Survey-Maske (Mangle-Polygone/offizielle HEALPix-Maske mit
      Bohrlöchern für helle Sterne, Plattenränder etc.) — dafür bräuchte es
      `pymangle` oder die offizielle SDSS-DR7-Maskendatei. Der alte
      `randoms_mode="bbox"` bleibt zu Vergleichszwecken erhalten.

## Echten SDSS-DR7-Katalog anbinden (WP1)

```python
from voidh0.layer1_tracers import SDSSDR7TracerAdapter

adapter = SDSSDR7TracerAdapter(
    catalog_path="/pfad/zu/vollim_dr7_cbp_102709.dat",
    randoms_path="/pfad/zu/einem/random-katalog.dat",  # optional
)
tracers = adapter.load()
```

Bezugsquellen für eine echte Katalogdatei (nicht im Repository, da
Drittanbieter-Datenprodukt mit mehreren zehn MB):

- VAST-Beispielkatalog `vollim_dr7_cbp_102709.dat` im GitHub-Repo `DESI-UR/VAST`
  (`VAST/example_scripts/`)
- Peer-reviewte Void-Kataloge zu Douglass, Veyrat & BenZvi (2023),
  ApJS 265, 7 — auf Zenodo unter "VAST void catalogs for SDSS DR7"

Benötigt zusätzlich `astropy` (nur für diesen einen Adapter, siehe
`pip install -e ".[dev]"`); der Rest des Frameworks bleibt astropy-frei.

Standardmäßig (`randoms_mode="mask"`) werden Randoms aus einer gepixelten
Fußabdruckmaske gezogen, die direkt aus dem eingelesenen Katalog abgeleitet
wird — kein zusätzlicher Dateibedarf. Für den einfacheren Vergleichsmodus:

```python
adapter = SDSSDR7TracerAdapter(
    catalog_path="...",
    n_synthetic_randoms=50_000,
    randoms_mode="bbox",  # statt "mask" (Default)
)
```

## Schicht 2: echte VAST/VoidFinder-Anbindung — WICHTIGER PLATTFORM-HINWEIS

`VASTVoidFinderAdapter` (`layer2_voidfinder/vast_adapter.py`) liest die
**offizielle VAST-Ausgabedatei** (`[survey_name]_VoidFinder_Output.fits`,
HDUs `MAXIMALS`/`HOLES`/optional `MASK`) ein — er führt VoidFinder NICHT
in-process aus. Grund: Die VAST-Entwickler unterstützen Windows offiziell
NICHT (Cython-Kern lässt sich dort nicht zuverlässig kompilieren, zusätzlich
fehlt der von VoidFinder benötigte POSIX-`fork()`-Systemaufruf) — siehe
https://vast.readthedocs.io/en/latest/VAST_install.html.

**Workflow für einen echten Lauf (auf Windows z. B. via WSL2):**

1. In WSL2/Linux (oder einer Linux-VM/einem Cluster): VAST offiziell
   installieren (`git clone https://github.com/DESI-UR/VAST`, dann
   `python setup.py install` gemäß deren Anleitung)
2. Den mit `SDSSDR7TracerAdapter` erzeugten Katalog (oder direkt die
   `vollim_dr7_cbp_102709.dat`) in `VAST/example_scripts/SDSS_VoidFinder_dr7.py`
   einsetzen und laufen lassen
3. Die entstehende `[survey_name]_VoidFinder_Output.fits` zurück nach Windows
   kopieren (WSL2 hat direkten Zugriff auf `C:\...`, umgekehrt auch)
4. In voidh0:
   ```python
   from voidh0.layer2_voidfinder import VASTVoidFinderAdapter

   adapter = VASTVoidFinderAdapter("/pfad/zu/survey_VoidFinder_Output.fits")
   voids = adapter.find_voids(tracers)  # tracers wird nur fuer Interface-
                                          # Kompatibilitaet erwartet, nicht
                                          # zur Berechnung verwendet
   labels = adapter.classify(ra, dec, z, voids)
   ```

**Kosmologie-Konsistenz (wichtig!):** Die (ra, dec, z) → (x, y, z)-Umrechnung
in `classify()` MUSS dieselbe Kosmologie verwenden, mit der VoidFinder extern
lief. Standardmäßig nutzt der Adapter Schicht 0
(`load_reference_cosmology()`); lief der externe VoidFinder-Aufwand mit
anderem `h`/`Ωm`, muss das per `cosmology=`-Argument übergeben werden —
sonst sind die Sphere-Vergleiche in `classify()` inkonsistent (genau die
"Kosmologie-Zirkularität" aus Abschnitt 9).

**Sphärengenaue Klassifikation:** Anders als `DemoVoidFinderAdapter` nutzt
`classify()` hier die volle `HOLES`-Tabelle (Union aller Spheres eines
Voids), nicht nur die Maximal-Sphere — exakt VASTs eigene Definition
("Is my object in a void?" in der VAST-Doku). Ist eine `MASK`-HDU in der
Ausgabedatei vorhanden, werden Objekte außerhalb der Survey-Maske als
`"edge"` markiert.

`DemoVoidFinderAdapter` bleibt für Framework-Entwicklung/Tests ohne
WSL2-Abhängigkeit nutzbar; `VASTVoidFinderAdapter` ist der Weg zu einem
echten, publikationsfähigen Void-Katalog.

## Kosmologie-Konsistenz jetzt geprüft, nicht nur dokumentiert

Der obige Abschnitt beschrieb die Kosmologie-Konsistenz-Anforderung bisher
nur als Empfehlung — `VASTVoidFinderAdapter` prüft sie jetzt tatsächlich
(`layer2_voidfinder/provenance.py`):

1. Direkt nach einem externen VoidFinder-Lauf (WSL2/Linux):
   ```bash
   python3 scripts/write_voidfinder_provenance.py \
       --output survey_VoidFinder_Output.fits \
       --source-catalog vollim_dr7_cbp_102709.dat
   ```
   Schreibt `survey_VoidFinder_Output.fits.provenance.json` daneben — hält
   fest, mit welcher Kosmologie (H0, Om0) und welchem (per SHA-256
   geprüften) Eingabekatalog gerechnet wurde.

2. Diese `.provenance.json`-Datei muss zusammen mit der `.fits`-Datei zurück
   nach Windows kopiert werden.

3. `VASTVoidFinderAdapter.find_voids()` liest sie automatisch und **bricht
   standardmäßig ab** (`ProvenanceMissingError`/`ProvenanceMismatchError`),
   wenn die Sidecar-Datei fehlt oder H0/Om0 nicht zur aktuell aktiven
   Schicht-0-Kosmologie passen — statt still falsche Ergebnisse zu liefern.
   Für schnelle Experimente ohne diese Prüfung: `require_provenance=False`
   (nicht empfohlen für publikationsreife Läufe).

Damit ist die "Kosmologie-Zirkularität" aus Abschnitt 9 an dieser Stelle
nicht mehr nur eine Doku-Empfehlung, sondern eine tatsächlich durchgesetzte
Bedingung.
