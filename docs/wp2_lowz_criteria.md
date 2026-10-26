# WP2 — Kriterien für die Low-z-Katalogprüfung (H₀-Arm)

**Status:** Entscheidungskriterien vor der eigentlichen Auswertung
**Zweck:** Vorab entscheiden, ob der H₀-Arm mit einem Low-z-Katalog sinnvoll fortgeführt werden kann oder ob WP3/Forecast priorisiert werden soll.

**Bezüge im Projekt:** `docs/wp2_calibrators.md`, Abschnitt 2.1; Exposé, Abschnitte 5 und 9.

Alle unten genannten Schwellenwerte sind pragmatische Projektgrenzen. Sie sind keine universellen astrophysikalischen Standards und müssen vor der Auswertung bestätigt und anschließend unverändert angewendet werden.

## 0. Registrierung und Dokumentation

| Eintrag | Festlegung |
|---|---|
| Kriterien-Dokument | `docs/wp2_lowz_criteria.md` |
| Baseline-Commit vor der Auswertung | `[BASELINE-COMMIT-HASH]` |
| Commit-Zeitstempel | Nach dem Commit mit `git log -1 --format="%H %cI %s"` protokollieren |
| Bereits gesehene Ergebnisse vor diesem Commit | `[keine / konkret beschreiben]` |
| Kandidatenkatalog | 2MRS, vorläufige Auswahl: \(K_s \leq 11{,}75\) |
| Fallbacks | Siehe Abschnitt 6 |

Der Hash des Commits, der dieses Dokument selbst enthält, wird **nicht** in das Dokument eingetragen. Er wird nach dem Commit separat im Arbeitsprotokoll bzw. Run-Manifest dokumentiert. Bereits vor dem Commit bekannte Ergebnisse müssen transparent festgehalten werden.

## 1. Prüfschritte und Entscheidungskriterien

Die Prüfung erfolgt in dieser Reihenfolge:

1. **Katalogeignung:** Sind die SH0ES-Kalibratoren im relevanten Gebiet durch den Katalog abgedeckt?
2. **Geometrische Eignung:** Sind Maske, Auswahlfunktion und radiale Vollständigkeit ausreichend?
3. **Klassifikationsstabilität:** Bleibt die Void-/Wall-Zuordnung bei plausiblen Varianten stabil?
4. **Statistische Eignung:** Gibt es genügend klassifizierbare Kalibrator-Hosts, um \(f_{\rm void}\) sinnvoll einzuschränken?
5. **Vergleichbarkeit:** Ist eine konsistente Void-Fraktion für die Hubble-Flow-Stichprobe bestimmbar?

Insbesondere wird keine H₀-Interpretation vorgenommen, wenn die Vergleichbarkeit der beiden Stichproben nicht gegeben ist.

### C1 — Katalog- und Volumenabdeckung der Kalibrator-Hosts

**Ausgangsstichprobe:** 43 SH0ES-SNe in 37 unterschiedlichen Host-Galaxien. Die Host-Galaxie ist die unabhängige Einheit für die hier betrachtete Host-Klassifikation.

Für jeden der 37 Hosts dokumentieren:

- Position innerhalb der tatsächlichen Winkelmaske des Kandidatenkatalogs;
- galaktische Breite \(|b|\), mit ergänzenden Prüfungen bei \(|b|\geq 5^\circ, 8^\circ, 10^\circ, 15^\circ\);
- Distanz bzw. verwendete Rotverschiebung und deren Bezugssystem;
- ob der Host innerhalb des vorab festgelegten radialen Bereichs liegt, in dem die verwendete volumenbegrenzte Tracer-Stichprobe vollständig ist;
- Ausschlussgrund, falls der Host nicht abgedeckt oder nicht auswertbar ist.

**Pragmatische Schwelle:** Mindestens 90 % der 37 Hosts sollen sowohl geometrisch abgedeckt als auch innerhalb des festgelegten radialen Vollständigkeitsbereichs liegen.

Die Bedingung \(|b|\geq 10^\circ\) ist nur ein grober Proxy für die Zone of Avoidance und ersetzt nicht die tatsächliche Katalogmaske. Geometrische Abdeckung ist außerdem nicht gleichbedeutend mit ausreichender lokaler Tracerdichte oder einer belastbaren Void-/Wall-Klassifikation.

**Zu berichten:** Anzahl und Anteil der abgedeckten Hosts; Resultate für die genannten \(|b|\)-Grenzen; getrennte Zählungen für Maskenabdeckung, radiale Vollständigkeit und tatsächliche Klassifizierbarkeit.

### C2 — Lokale Tracerdichte und Randbehandlung

Für jeden Host werden mindestens folgende Größen berechnet und gespeichert:

- Zahl der Tracer innerhalb von 10 und 20 \(h^{-1}\,\mathrm{Mpc}\);
- Abstand zum nächsten Tracer;
- lokale Dichte relativ zum Median einer klar definierten und dokumentierten Dichteschätzung (im Projekt als RF-D-Estimator bezeichnet; konkrete Definition und Implementierung müssen im Analyseprotokoll angegeben werden);
- Abstand zur Kataloggrenze und zur Maskengrenze;
- Kennzeichnung, ob die betrachteten Suchvolumina vollständig innerhalb des gültigen Katalogvolumens liegen.

**Pragmatischer Screening-Wert:** Mindestens 10 Tracer innerhalb von 10 \(h^{-1}\,\mathrm{Mpc}\). Bei 10 unabhängigen Zählereignissen liegt die reine Poisson-Relativeunsicherheit größenordnungsmäßig bei \(1/\sqrt{10}\approx 32\,\%\); Galaxien-Clustering kann die tatsächliche Streuung vergrößern. Dieser Wert ist deshalb nur ein Screening-Kriterium und kein Nachweis einer belastbaren Klassifikation.

Eine Kugel, die die gültige Winkelmaske oder die Grenze des radial vollständigen Volumens schneidet, darf nicht ohne Korrektur als leer interpretiert werden. Solche Fälle werden als `edge` bzw. `unclassified` markiert und nicht automatisch als `void` oder `wall` gezählt. Die konkrete Randlogik muss vor der Auswertung festgelegt und für alle Stichproben gleich angewendet werden.

### C3 — Stabilität gegenüber Rotverschiebungs- und Koordinatenvarianten

Die Void-Geometrie wird für den Variantenvergleich festgehalten. Variiert werden zunächst die Host-Positionen bzw. die für die Hosts verwendeten Rotverschiebungen, nicht die Void-Geometrie selbst. Falls eine Variante eine neue Geometrie oder einen neuen Katalog erfordert, ist sie als separate Analyse zu kennzeichnen.

Vorgesehene Varianten:

- **V0 — Primärvariante:** Rotverschiebungsdefinition, die zum Bezugssystem der Tracer-Daten passt. Für 2MRS ist das Bezugssystem anhand der konkreten Katalogspalten und Metadaten zu verifizieren; „heliozentrisch“ darf nicht ungeprüft angenommen werden.
- **V1 — alternatives Rotverschiebungssystem:** die jeweils andere geeignete Variante aus `zHEL` und `zCMB`, sofern die verfügbaren Daten diese Definitionen enthalten und sie fachlich vergleichbar sind.
- **V2 — `zHD`:** Sensitivitätsvariante. `zHD` ist nicht automatisch mit einer beobachteten Tracer-Rotverschiebung austauschbar; Definition und Umrechnung müssen dokumentiert werden.
- **V3 — Host-Koordinaten:** Vergleich der SIMBAD- und NED-Koordinaten für die sieben bereits markierten Fälle. Die konkreten Koordinatenquellen und verwendeten Werte sind festzuhalten.

Für jede Variante berichten:

- Anzahl der Hosts in `void`, `wall`, `edge` und sonstigen `unclassified`-Kategorien;
- Anzahl der in beiden verglichenen Varianten klassifizierbaren Hosts;
- absolute Zahl und Anteil der Klassenwechsel;
- vollständige Übergangsmatrix zwischen den Kategorien, einschließlich `edge`/`unclassified`;
- Liste der betroffenen Hosts und Ursache, soweit bestimmbar.

**Pragmatische Schwelle für V0→V1:** Höchstens 20 % der 37 Hosts wechseln die Kategorie (bei 37 Hosts entspricht das höchstens 7 Hosts, da 8/37 bereits mehr als 20 % sind). Der Nenner und die Zahl der in beiden Varianten klassifizierbaren Hosts müssen immer mitberichtet werden. Die 20-%-Grenze gilt nur für den vorab definierten Vergleich V0→V1; andere Varianten werden separat ausgewiesen.

Wenn die Schwelle überschritten wird, ist die Variantenabhängigkeit als systematische Unsicherheit zu behandeln. Ob eine Schlussfolgerung noch vertretbar ist, hängt davon ab, ob diese Unsicherheit quantifiziert und im Ergebnis berücksichtigt werden kann.

### C4 — Statistische Eignung der Kalibrator-Stichprobe

Als klassifizierbar gelten für die Berechnung der Void-Fraktion zunächst nur Hosts mit eindeutiger Klassifikation `void` oder `wall`. `edge` und andere `unclassified`-Fälle werden nicht in den Nenner von \(f_{\rm void}\) aufgenommen, aber separat ausgewiesen.

\[
f_{\rm void}=\frac{N_{\rm void}}{N_{\rm void}+N_{\rm wall}}.
\]

**Pragmatische Schwelle:** Mindestens 16 klassifizierbare Hosts. Zusätzlich werden stets die Zahl der klassifizierbaren Hosts und der Anteil an allen 37 Hosts berichtet.

Für \(f_{\rm void}\) werden \(N_{\rm void}\), \(N_{\rm wall}\), der Nenner und ein 95-%-Wilson-Konfidenzintervall angegeben. Ein einfacher binomialer Standardfehler kann ergänzend berichtet werden, ersetzt das Intervall aber nicht. Bei \(n=37\) beträgt der maximale binomiale Standardfehler nahe \(f=0{,}5\) etwa 0,082; das ist **nicht** die Halbbreite eines 95-%-Wilson-Intervalls, die in diesem Fall ungefähr 0,16 beträgt. Wenn nur ein Teil der Hosts klassifizierbar ist, ist der tatsächlich verwendete Nenner kleiner und die Unsicherheit entsprechend neu zu berechnen.

Es gibt keine vorab festgelegte Mindestzahl pro Klasse. Bei sehr kleinen oder leeren Klassen wird die daraus folgende Begrenzung der Information ausdrücklich berichtet; ein Randwert kann weiterhin eine obere bzw. untere Schranke liefern.

### C5 — Vergleichbarkeit mit der Hubble-Flow-Stichprobe

Die für die H₀-Abschätzung benötigte Differenz der Void-Fraktionen ist nur interpretierbar, wenn Kalibrator- und Hubble-Flow-Stichprobe nach derselben Definition klassifiziert werden. Dafür müssen insbesondere übereinstimmen:

- Tracerkatalog und Auswahlfunktion;
- VoidFinder-Version und relevante Parameter;
- Winkelmaske und radiale Vollständigkeitsgrenze;
- Distanzdefinition und kosmologische Annahmen;
- Regeln für `void`, `wall`, `edge` und `unclassified`.

Die Void-Geometrie wird für den Vergleich aus demselben neu analysierten Tracerkatalog verwendet. Es ist zu dokumentieren, welche Hubble-Flow-SNe im gültigen Katalogvolumen liegen und welche wegen Maske, radialer Grenze oder fehlender Klassifizierbarkeit ausgeschlossen werden.

**Vorläufige pragmatische Schwellen, vor Auswertung zu bestätigen:**

- mindestens 100 Hubble-Flow-SNe innerhalb der relevanten Katalogabdeckung;
- diese Teilstichprobe umfasst mindestens 50 % der zuvor klar definierten Hubble-Flow-Referenzstichprobe.

Der Nenner für die 50-%-Bedingung muss explizit festgelegt werden. Berichtet werden Gesamtzahl, Zahl im gültigen Volumen, Zahl klassifizierbarer Objekte sowie die Abdeckung nach Rotverschiebung, Himmelsposition und relevanten Selektionskriterien. Die Void-Fraktion der abgedeckten Teilstichprobe ist mit der der gesamten Referenzstichprobe zu vergleichen, soweit eine konsistente Klassifikation möglich ist.

**Wenn C5 nicht erfüllt ist, wird keine interpretierbare \(\Delta f_{\rm void}\) für den H₀-Arm behauptet.** Der H₀-Arm wird gestoppt bzw. als nicht ausreichend abgesichert dokumentiert; WP3/Forecast wird priorisiert. Ein Wechsel zu einem anderen Katalog ist nur nach erneuter Prüfung und Dokumentation der Kriterien zulässig.

## 2. Methodische Festlegungen („locks“)

1. **Auswahlfunktion und volumenbegrenzte Stichprobe:** Für 2MRS sind die K-Band-Auswahl und die tatsächliche Vollständigkeit zu prüfen. Absoluthelligkeitsgrenze und maximaler radialer Bereich werden vor der Zählung festgelegt und dokumentiert. Unkorrigierte Zählungen aus einer fluxbegrenzten Stichprobe dürfen nicht als direkte Dichteschätzung interpretiert werden.
2. **Void-Geometrie neu bestimmen:** Eine SDSS-Void-Geometrie kann nicht einfach auf einen anders abgedeckten Katalog übertragen werden. VAST/VoidFinder muss mit dem neuen Tracerkatalog, der passenden Maske und der dokumentierten Auswahlfunktion ausgeführt werden. V² ist kein Referenzverfahren, solange der Fehler in `test_zobov_2_zones` nicht verstanden und geklärt ist.
3. **Rotverschiebungsrahmen:** Das Bezugssystem jeder verwendeten Rotverschiebung wird anhand der tatsächlichen Spalten und Metadaten verifiziert. Varianten werden als Sensitivitätstest dokumentiert.
4. **Distanzen und Software-Provenienz:** Distanzen werden konsistent in \(h^{-1}\,\mathrm{Mpc}\) unter dokumentierter Kosmologie angegeben. Für jeden Lauf werden mindestens VAST-Commit (einschließlich des relevanten Patches `2a04491`, falls verwendet), \(h\), \(\Omega_m\), Distanzkonvention, Katalogdatei und SHA-256-Hash des Katalogs sowie die Laufparameter protokolliert. Ein Provenance-Sidecar wird mit den Ergebnissen gespeichert.
5. **Maske und Ränder:** Zone of Avoidance, Katalogmaske und radiale Grenze sind Teil der Geometrie. Randobjekte werden explizit markiert; sie werden nicht stillschweigend als `void` oder `wall` klassifiziert.

## 3. Entscheidungsmatrix

| Prüfung | Ergebnis | Konsequenz |
|---|---|---|
| C1 — Abdeckung | Schwelle erfüllt | Mit C2 fortfahren |
| C1 — Abdeckung | Schwelle verfehlt | Kandidatenkatalog bzw. Stichprobe neu bewerten; keine H₀-Aussage aus dieser Stichprobe |
| C2 — Geometrie/Tracer | Screening und Randbehandlung dokumentiert | Mit C3 fortfahren; Screening allein gilt nicht als Klassifikationsnachweis |
| C2 — Geometrie/Tracer | Geometrie nicht zuverlässig | Katalog/Maskierung überarbeiten oder H₀-Arm stoppen |
| C3 — Stabilität | Varianten stabil oder Unsicherheit quantifizierbar | Weiter; Variantenstreuung berichten |
| C3 — Stabilität | Starke, nicht quantifizierbare Abhängigkeit | Keine robuste Einzelklassifikation behaupten; H₀-Interpretation nur bei belastbarer Systematik fortführen |
| C4 — Statistik | Mindestens 16 klassifizierbare Hosts | \(f_{\rm void}\) mit Wilson-Intervall berichten |
| C4 — Statistik | Weniger als 16 klassifizierbare Hosts | H₀-Arm als statistisch schwach kennzeichnen; WP3/Forecast priorisieren |
| C5 — Vergleichbarkeit | Beide Schwellen und konsistente Klassifikation erfüllt | \(\Delta f_{\rm void}\) berechnen und H₀-Forecast prüfen |
| C5 — Vergleichbarkeit | Vergleich nicht ausreichend | Keine interpretierbare \(\Delta f_{\rm void}\); H₀-Arm stoppen, WP3/Forecast priorisieren |

## 4. H₀-Forecast und Interpretation

Für die projektinterne Abschätzung wird vorläufig verwendet:

\[
\frac{\Delta H_0}{H_0}\approx\frac{\ln 10}{5}\,\Delta f_{\rm void}\,\Delta\mu_{\rm env}
\approx 0{,}46\,\Delta f_{\rm void}\,\Delta\mu_{\rm env}.
\]

Diese Näherung setzt voraus, dass der betrachtete Umgebungs-Offset \(\Delta\mu_{\rm env}\) sich im Vergleich der Stichproben über die Differenz der Void-Fraktionen auswirkt. Definition, Vorzeichenkonvention und Anwendung auf die konkrete Analyse müssen im Forecast dokumentiert werden.

Eine frühere grobe Projektabschätzung mit \(\Delta\mu_{\rm env}\approx 0{,}1\) mag und einer Unsicherheit von ungefähr 0,08 in \(f_{\rm void}\) ergibt eine H₀-Größenordnung von etwa 0,4 %. Die 0,08 ist dabei höchstens eine grobe Standardfehler-Skala für eine Stichprobe von 37 Hosts nahe \(f=0{,}5\), **kein** 95-%-Konfidenzintervall. Für den tatsächlichen Forecast sind das beobachtete \(n_{\rm classifiable}\), das Wilson-Intervall, die Unsicherheit von \(\Delta f_{\rm void}\) und die Unsicherheit von \(\Delta\mu_{\rm env}\) einzusetzen. Die frühere Zahl von 0,4 % ist daher eine illustrative Überschlagsrechnung und kein validiertes Endergebnis.

Die im Projekt diskutierte Hubble-Spannung von ungefähr 8 % dient nur als Größenordnungsvergleich; sie ersetzt keine statistische Fehleranalyse. Ein kleiner oder nicht signifikanter Effekt ist ein gültiges Ergebnis und kann als obere Schranke berichtet werden.

## 5. Reihenfolge der Durchführung

1. Dieses Kriterien-Dokument vor der neuen Auswertung committen und Commit-Hash/Zeitstempel im externen Arbeitsprotokoll festhalten.
2. In Schritt 0 die \(|b|\)-Abdeckung der 37 Hosts prüfen.
3. Kandidatenkatalog laden; verwendete Spalten, Rotverschiebungsrahmen, Masken und Metadaten dokumentieren.
4. Auswahlfunktion, Absoluthelligkeitsgrenze und radialen Vollständigkeitsbereich festlegen und vor der Zählung protokollieren.
5. VoidFinder/VAST mit dem neuen Katalog und der passenden Maske ausführen; Konfiguration, Software-Commit und Provenienz speichern.
6. C1 bis C5 der Reihe nach auswerten und Tabellen/Übergangsmatrizen ablegen.
7. Entscheidung anhand der Matrix treffen, bevor der H₀-Forecast interpretiert wird.

## 6. Fallback-Kandidaten

- **6dFGS:** mögliche Ergänzung insbesondere für den südlichen Himmel; tatsächliche Eignung, Auswahlfunktion und Überlappung mit den Hosts prüfen.
- **Cosmicflows-4:** enthält Distanzinformationen, ist aber nicht ohne Weiteres eine homogene, volumenbegrenzte Redshift-Tracer-Stichprobe für VoidFinder.
- **NASA-Sloan Atlas (NSA):** SDSS-basierte Abdeckung; kann daher die grundsätzliche SDSS-Footprint-Beschränkung nicht automatisch beheben.

Diese Kandidaten sind Optionen zur Prüfung, keine bereits validierten Ersatzkataloge. Vor einer Auswahl müssen Abdeckung, Auswahlfunktion, Rotverschiebungsdefinition, Vollständigkeit und Eignung für eine konsistente Void-Geometrie anhand der jeweiligen Primärdokumentation geprüft werden.
