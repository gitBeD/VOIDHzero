# WP2 — Kalibrator-Zuordnung

Detailstand zu WP2 (COVE). Überblick und Schichtarchitektur: `docs/architecture.md`.
Datierte Einordnung: `docs/notes/wp2_coverage_2026-10-20.md`.

**Stand:** 20.10.2026
**Konvention:** *entschieden* / *vorgeschlagen* / *offen* sind getrennt gekennzeichnet.
Als "vorgeschlagen" markierte Punkte sind noch keine Projektkonvention.

## 1 Stichprobe und Positionen

- Die Datei enthält 77 als Kalibratoren markierte Zeilen; nach Deduplizierung
  nach CID verbleiben **43 eindeutige** Kalibrator-Supernovae. Die 77 sind
  Lichtkurven-Einträge verschiedener Pipelines (`IDSURVEY`), nicht 77 Galaxien.
  Das löst die "77 vs. 42"-Unstimmigkeit im Exposé (Riess et al. 2022 zählen
  eindeutige Wirtsgalaxien).
- `load_pantheon_calibrators()` dedupliziert standardmäßig (`deduplicate=True`),
  behält die erste Zeile je CID; `find_duplicate_cids()` macht Duplikate sichtbar.
  *Einschränkung:* reiner CID-Exakt-Match; Fälle wie `2005df` vs. `2005df_ANU`
  werden nicht zusammengeführt.
- `HOST_RA`/`HOST_DEC` sind im Release durchgehend `-999`. `wp2_cove._resolve_position()`
  fällt daher auf die SN-Koordinaten zurück; jede `CalibratorDiagnosisRow` trägt
  `position_source` (`host` / `sn_position` / `missing`). Alle 43 haben verwendbare
  SN-Koordinaten. SN-Positionen sind nicht automatisch eine unabhängig
  verifizierte Wirtsposition; der SIMBAD-/NED-Audit bleibt ein separater Schritt.
- **Offen (vorgeschlagen):** Δf_void pro **Wirtsgalaxie** zählen, nicht pro SN;
  mehrere SNe im selben Wirt sind keine unabhängigen Umgebungsmessungen.

## 2 Coverage-Diagnose (Befunde)

- **0 von 43** Kalibratoren haben einen SDSS-Spektral-Match innerhalb von 3″.
- 29 Positionen liegen außerhalb des umschließenden RA/Dec-Rechtecks des
  Tracerkatalogs; bei den übrigen 14 liegt das nächste Katalogobjekt 166–852″ entfernt.
- Die gespeicherte VAST-Maske hat 360 × 180 Zellen (1°); 8.903 von 64.800 sind
  markiert. Rasterdiagnose: 14 Positionen in markierten, 29 in unmarkierten Bins.
  Das ist eine **Obergrenze** für die Überlappung; radiale Abdeckung ist noch
  nicht geprüft.
- Die Maske stammt aus dem für VoidFinder vorbereiteten Katalog und ist daher
  keine unabhängige Bestätigung der offiziellen SDSS-Abdeckung.

**Erklärung:** `vollim_dr7_cbp_102709.dat` (Pan et al. 2012) beginnt selbst erst
bei `z ≈ 0,01`. Die Kalibratoren liegen überwiegend darunter (nur `2007A`,
z = 0,0168, und `1999dq`, z = 0,0131 erreichen die Untergrenze). Cepheiden-Wirte
sind generell auf ≲ 40 Mpc (`z ≲ 0,011`) beschränkt. Die 0/43-Quote ist damit eine
*strukturelle Folge der Katalogkonstruktion*, kein Bug in `crossmatch_sdss_spec()`.
Sie beweist weder fehlende offizielle Survey-Abdeckung noch das Fehlen einer
verwertbaren räumlichen Zuordnung gegenüber einer Void-Karte.

Das im Exposé (Abschnitt 9) formulierte Risiko "unzureichende Überlappung von
Distanzkalibratoren und 3D-Galaxienkartierung" ist damit für den SDSS-DR7-Pfad
quantitativ belegt (Host-Match 0/43).

## 3 Vier Flags je Kalibrator-Wirt

1. SDSS-photometrische Deckung vorhanden?
2. SDSS-spektroskopischer Redshift vorhanden?
3. Umgebungsklassifikation mit hinreichender Robustheitsstufe möglich?
4. Resultierende Void/Wand-Klassifikation.

## 4 Redshift-Konvention (offen — Vorschlag)

Zu wählen ist, welche Pantheon+-Spalte die Kalibratorpositionen bestimmt:

| Spalte | Bedeutung | Status |
|---|---|---|
| `zHEL` | heliozentrisch | Kandidat |
| `zCMB` | CMB-Bezug | Kandidat |
| `zHD` | für das Hubble-Diagramm aufbereitet | bisher in `data/external/wp2_sh0es_calibrator_xyz.csv` verwendet; **keine** getroffene Entscheidung |

**Vorgeschlagen (nicht entschieden):** Die Void-Karte wurde im Redshift-Raum aus
beobachteten Redshifts gebaut. Primärvariante daher `zCMB` oder `zHEL`, je nach
tatsächlichem Bezugssystem des Tracerkatalogs (in den Quelldaten zu prüfen).
`zHD` enthält nach bisherigem Kenntnisstand Pekuliargeschwindigkeitskorrekturen
und eignet sich als Sensitivitätsvariante, nicht als Primärvariante. Bei
D < 40 Mpc entsprechen ca. 300 km/s etwa 3 h⁻¹ Mpc, vergleichbar mit der
Void-Randzone.

Die Entscheidung ist anhand des Analyseziels und der VAST-Referenzlaufkonvention
zu begründen, nicht durch stilles Umschalten der Spalte.

## 5 Kartesische Kalibratorkoordinaten

`data/external/wp2_sh0es_calibrator_xyz.csv`: 43 Zeilen, 43 eindeutige CIDs, keine
fehlenden Werte, maximale Abweichung zwischen `sqrt(x²+y²+z²)` und `r` ca.
8,9·10⁻⁹ Mpc/h. Das validiert die interne Rechenkonsistenz, **nicht** die
Redshift-Wahl, die Wirtsidentifikation oder die Void-Klassifikation.

## 6 Pekuliargeschwindigkeiten

Ein präzise gemessener Redshift ergibt keine gleich präzise Position. Getrennt zu
behandeln: Messunsicherheit des Redshifts, Unsicherheit der komovierenden Distanz,
Pekuliargeschwindigkeiten. Eine Sensitivitätsanalyse der Umgebungsklassifikation
gegenüber Redshift-Variante und plausiblen Pekuliargeschwindigkeiten ist **noch
nicht** durchgeführt.

## 7 Host-Zuordnung über NSA und DLR

Empfohlener Folgeschritt nach dem 0/43-Befund: NASA-Sloan Atlas (NSA) statt
`vollim_dr7_cbp_102709.dat` als Quelle für den Host-Crossmatch. Douglass et al.
(2023) sind selbst auf NSA umgestiegen, weil NSA große Galaxien besser behandelt
(kein Shredding). Host-Zuordnung per Directional Light Radius (DLR) in
`scripts/wp2_nsa_dlr_diagnosis.py`.

**Empirische NSA-v1.0.1-Qualitätsregel (27.09.2026):**
`SERSIC_TH50 = 159,7578125″` tritt in 4.802 von 641.409 NSA-Einträgen (0,75 %)
exakt identisch auf, zusammen mit Sérsic-Indizes an den Modellgrenzen
(`n = 0,5` bzw. `6,0`). Zusatzbefunde: exakte dyadische Zahl (`20449/128`);
über den gesamten Himmel verteilt (kein lokales Deblending-Cluster).
Interpretation als algorithmische Begrenzung ist **empirisch, nicht durch die
offizielle NSA-Dokumentation bestätigt.**

Umsetzung (nur in der DLR-Pipeline):

- `TH50_SENTINEL = 159.7578125`, `TH50_SENTINEL_ATOL = 1e-6`
- Kandidat wird aus dem DLR-Ranking entfernt, der Kalibrator bleibt erhalten
- kein Petrosian-Fallback (`PETRO_TH50` kann bei großen nahen Galaxien um Faktor
  ~80 zu klein sein; Befund SN 2011fe)
- Bleibt kein valider Kandidat, lautet der Status "keine vertrauenswürdige
  Geometrie gefunden", nicht "kein Host"
- Ausschlüsse werden je Kalibrator als `n_excluded_sentinel` mitgezählt
- `SERSIC_N = 0,5`/`6,0` allein ist kein Ausschlusskriterium

## 8 Konzeptionell offen: Rolle des Host-Matches

Für Δf_void braucht man vermutlich keinen Tracer-Match der Wirtsgalaxie, sondern
Position und Distanz relativ zur Void-Karte (Punkt-in-Kugel-Test gegen `HOLES`
plus Randflag). Den Host-Match braucht man für Wirtseigenschaften in WP4, die
ohnehin aus anderen Quellen kommen (SH0ES-Tabellen, NED, WISE/GALEX).

**Vorgeschlagen (nicht entschieden):** den 3″-Host-Match aus dem M4-Kriterium
entfernen und stattdessen drei getrennte Zähler verwenden:

1. Winkel-Footprint
2. radiale Abdeckung (Kalibratordistanz gegenüber `dist_limits` des VoidFinder-Laufs)
3. Randabstand zur Survey-/Void-Katalog-Grenze

Vermutlicher Flaschenhals ist die radiale Abdeckung: Liegt die Untergrenze des
volumenlimitierten Samples über den Kalibratordistanzen, ist der SDSS-Pfad für den
H₀-Arm faktisch erledigt, und eine lokale Alternative rückt in den Vordergrund
(2MRS-basierter Void-Katalog, Cosmicflows-Rekonstruktion, erweiterte
Kalibratorstichprobe via JWST/TRGB/JAGB, invertierte Analyselogik; volle
Formulierung im Exposé, Abschnitt 9).

## 9 Mindest-N-Schwelle (offen, vor Klassifikation festlegen)

Sobald Kalibratoren in Void/Wall eingeteilt sind, ist jede Schwelle post hoc.
Die Schwelle (`SUCCESS_CRITERIA["abort_criterion"]["min_calibrator_sample_size"]`)
ist daher **vor** der Klassifikation zu committen.

Überschlag zur Orientierung (nicht Teil der Analyse): Bei N ≈ 14 und
f_void ≈ 0,2 beträgt der Binomialfehler etwa ±0,11;
ΔH₀/H₀ ≈ 0,46 · Δf_void · Δμ_env, mit Δμ_env ≈ 0,05–0,1 mag und Δf_void ≲ 0,2
etwa 0,5–1 %. Eine solche Stichprobe könnte bestenfalls eine Obergrenze liefern.

## 10 Nächste Schritte (Reihenfolge)

1. Redshift-Bezugssystem des Tracerkatalogs klären; Primärvariante festschreiben.
2. Distanzen und XYZ für `zHEL`, `zCMB`, `zHD` gegenüberstellen und Unterschiede
   dokumentieren.
3. VAST-Kompatibilität prüfen (Bezugssystem, Kosmologie, Distanzdefinition).
4. Crossmatch entkoppeln: nächster Katalogeintrag allein nach Winkelabstand, dann
   Redshiftdifferenz, Maskenstatus und radiale Abdeckung separat.
5. Survey-Abdeckung unabhängig validieren (offizielle Survey-Maske, wenn möglich).
6. Radiale Abdeckung gegen `dist_limits` prüfen.
7. Mindest-N-Schwelle committen.
8. Erst danach Void-/Wall-/Edge-Klassifikation berichten; dann M4-Entscheidung.

---
