# WP2: Low-z-Katalogprüfung -- vorab festgelegte Kriterien

**Status:** Entwurf zur fachlichen Freigabe\
**Zweck:** Vor der Auswertung festlegen, wann ein öffentlicher
Low-z-Katalog als ausreichende Grundlage für die
Void/Wall-Klassifikation der SH0ES-Wirte gilt. Die Kriterien sollen vor
der Zählung und vor der Auswahl der finalen Stichprobe versioniert und
committet werden.

## 1. Ausgangslage

-   Die aktuelle Host-Koordinatenprüfung umfasst 43 Kalibrator-SNe und
    37 unterschiedliche Wirte.
-   Alle 43 Kalibratoren liegen bei r ≤ 50 Mpc/h; im vorhandenen
    VoidFinder-Katalog gibt es in diesem lokalen Bereich nahezu keine
    Tracer.
-   Daher ist die aktuelle Void/Wall-Klassifikation der Kalibratoren
    nicht belastbar.
-   Als erster öffentlicher Kandidat soll der 2MASS Redshift Survey
    (2MRS) geprüft werden. Weitere Kandidaten sind 6dFGS und
    Cosmicflows-4; der NSA allein löst die Footprint-Beschränkung des
    SDSS nicht.

Die Angaben zu Umfang, Vollständigkeit und Himmelsabdeckung von 2MRS
sind Suchhinweise und müssen anhand der Primärdokumentation und der
tatsächlich verwendeten Katalogdatei verifiziert werden, bevor sie als
methodische Grundlage gelten.

## 2. Vorab festgelegte Kriterien

Die folgenden Schwellen sind **Vorschläge zur Entscheidung**, keine
bereits validierten statistischen Standards. Sie müssen vor der
Auswertung bestätigt oder geändert werden. Nach Sichtung der Ergebnisse
sollten sie nicht rückwirkend angepasst werden, ohne die Änderung zu
dokumentieren.

### C1 -- Himmelsabdeckung der Wirte

**Maß:** Anteil der 37 unterschiedlichen Wirte, deren Positionen im
nutzbaren Himmelsbereich des Katalogs liegen und nicht durch die
gewählte Maske bzw. Zone of Avoidance ausgeschlossen sind.

**Vorläufiger Zielwert:** mindestens 90 % der Wirte; zusätzlich die
absolute Zahl der abgedeckten Wirte angeben.

**Berichtspflicht:** Ergebnisse für mehrere galaktische Breitengrenzen,
mindestens \|b\| ≥ 5°, 8°, 10° und 15°. Die Maskendefinition des
konkreten Katalogs hat Vorrang vor einer pauschalen Breitengrenze.

### C2 -- Lokale Tracerdichte

**Maß:** Zahl der Galaxien aus einer vorab definierten,
volumenbegrenzten Tracer-Stichprobe innerhalb von 10 Mpc/h um jeden
Wirt. Als Sensitivitätsanalyse zusätzlich 20 Mpc/h berichten.

**Vorläufiger Zielwert:** mindestens 10 geeignete Tracer innerhalb von
10 Mpc/h pro klassifiziertem Wirt.

**Wichtige Einschränkung:** Eine Mindestzahl von 10 Tracern allein
garantiert keine zuverlässige Void/Wall-Klassifikation. Die Schwelle ist
ein Screening-Kriterium. Die tatsächliche Stabilität der Klassifikation
muss separat geprüft werden. Zu dokumentieren sind außerdem die
Distanzdefinition, das Bezugssystem, die Behandlung von Messfehlern und
die Vollständigkeit der Stichprobe.

### C3 -- Stabilität der Klassifikation

**Maß:** Anteil der Wirte, deren Void/Wall-Klasse sich zwischen den
vorab festgelegten Redshift-Varianten ändert, insbesondere zHEL und
zCMB, sofern beide Varianten methodisch sinnvoll berechnet werden
können.

**Vorläufiger Zielwert:** höchstens 20 % Klassenwechsel unter den
Wirten, die in allen verglichenen Varianten auswertbar sind.

**Berichtspflicht:** absolute Zahl und Anteil der Klassenwechsel, die
Zahl der in jeder Variante auswertbaren Wirte sowie die Behandlung
unklassifizierter Fälle. Varianten müssen ansonsten dieselben Katalog-,
Masken- und Stichprobenregeln verwenden.

### C4 -- Auswertbare Host-Stichprobe

**Maß:** Zahl der unterschiedlichen Wirte, die alle vorab festgelegten
Abdeckungs-, Dichte- und Qualitätsanforderungen erfüllen und eine
belastbare Klasse erhalten.

**Vorläufiger Zielwert:** mindestens 16 klassifizierbare Wirte.

Dieser Schwellenwert ist ein pragmatischer Mindestwert, kein Ersatz für
eine Power- bzw. Unsicherheitsanalyse. Die statistische Präzision hängt
unter anderem vom tatsächlichen Void-Anteil, der Abhängigkeit zwischen
Wirten und der Messunsicherheit ab. Wenn weniger als 16 Wirte auswertbar
sind, ist die Umweltanalyse als explorativ zu kennzeichnen; die
Ergebnisse dürfen nicht als präzise Messung des Umwelteinflusses
interpretiert werden.

## 3. Methodische Sperrpunkte vor der Zählung

Vor dem Zählen der Tracer und vor dem Vergleich der Host-Klassen müssen
folgende Entscheidungen dokumentiert sein:

1.  **Katalogversion und Provenienz:** Quelle,
    Veröffentlichungs-/Versionsstand, Download-Datum, Dateiname und
    SHA-256-Hash.
2.  **Rotverschiebung und Bezugssystem:** Definition der im Katalog
    enthaltenen Redshifts sowie die für die Galaxienentfernungen
    verwendete Transformation. Die passende Kalibratorvariable darf
    nicht allein aufgrund des Spaltennamens ausgewählt werden; die
    jeweiligen Definitionen müssen geprüft werden.
3.  **Volumenbegrenzte Stichprobe:** Magnitudengrenze, angenommene
    K-Korrektur bzw. photometrische Korrekturen, verwendete Kosmologie
    und daraus abgeleitete absolute Helligkeitsgrenze. Die Grenze muss
    für das gesamte gewählte Volumen vollständig sein.
4.  **Entfernungsbereich:** vorab festgelegte innere und äußere Grenzen
    sowie konsistente Einheiten, insbesondere Mpc gegenüber Mpc/h.
5.  **Maske und Vollständigkeit:** galaktische Breitengrenze, bekannte
    Ausfälle und weitere Ausschlüsse.
6.  **VoidFinder-Konfiguration:** Software-Commit, kompilierte
    Erweiterung bzw. Build-Informationen, Parameter, Maske und
    Distanzmetrik.
7.  **Klassifikationsregel:** vorab definieren, wie eine Host-Position
    einer Void-/Wall-Klasse zugeordnet wird und wie Randfälle behandelt
    werden.
8.  **Sensitivitätsanalysen:** mindestens Redshift-Varianten und
    10-/20-Mpc/h-Zählradien; Änderungen der Volumenbegrenzung getrennt
    ausweisen.

## 4. Entscheidungsregel

Der H0-Arm wird mit einem alternativen Low-z-Katalog weitergeführt,
wenn:

-   die Katalogversion und die relevanten Spaltendefinitionen
    verifiziert sind;
-   die vorab festgelegte Host-Abdeckung erreicht wird;
-   eine methodisch begründete volumenbegrenzte Stichprobe gebildet
    werden kann;
-   die lokale Tracerdichte ausreichend ist und die
    Void/Wall-Klassifikation die Stabilitätsprüfung besteht;
-   die Zahl klassifizierbarer Wirte den vereinbarten Mindestwert
    erreicht.

Wenn diese Bedingungen nicht erfüllt sind, wird der H0-Arm mit diesem
Katalog nicht als belastbare Umweltmessung ausgewertet. Dann werden WP3
und der Forecast priorisiert; ein möglicher H0-Befund wird als nicht
ausreichend durch die lokale Katalogabdeckung abgesichert dokumentiert.

## 5. Ergebnisbericht

Für jeden geprüften Katalog werden mindestens dokumentiert:

-   abgedeckte Wirte: Anzahl und Anteil;
-   ausgeschlossene Wirte und jeweiliger Ausschlussgrund;
-   verwendete Stichprobe und Volumengrenze;
-   Tracerzahl innerhalb 10 und 20 Mpc/h pro Wirt (Median, Spannweite
    und Einzelwerte);
-   Zahl klassifizierbarer Wirte;
-   Void-/Wall-Zuordnung je Wirt;
-   Klassenwechsel zwischen den Redshift-Varianten;
-   Sensitivität gegenüber Maske und Stichprobenwahl;
-   Software-Commit, Parameter, Dateihashes und Reproduktionsanleitung.

## 6. Interpretation und Reichweite

Die maximale Zahl der Wirte beträgt nach dem derzeitigen Audit 37. Die
erreichbare Unsicherheit muss aus den tatsächlich klassifizierbaren
Daten und dem verwendeten statistischen Modell berechnet werden; eine
einfache Binomial-Näherung ist nur unter geeigneten Unabhängigkeits- und
Stichprobenannahmen gerechtfertigt.

Die im Projekt diskutierte Beziehung

ΔH0/H0 ≈ 0,46 · Δf_void · Δμ_env

sollte als Forecast-/Interpretationsbeziehung mit ihren Annahmen und
Einheiten dokumentiert werden. Sie ersetzt weder die Prüfung der
Klassifikation noch eine vollständige Unsicherheitsfortpflanzung.
Insbesondere sind die maximal plausible Differenz der
Umwelt-Distanzmoduli und der tatsächlich gemessene Void-Anteil separat
zu begründen.

Ein Nullresultat oder eine Obergrenze unter 1 % ist nicht automatisch
ein Scheitern: Es kann eine informative Einschränkung des möglichen
Umwelteinflusses sein. Diese Aussage ist jedoch erst nach erfolgreicher
Validierung der Datenabdeckung und der Klassifikation gerechtfertigt.

## 7. Freigabe vor Analyse

Vor Beginn der eigentlichen Tracerzählung bestätigt das Projektteam:

-   [ ] C1--C4 und die vorgeschlagenen Schwellenwerte sind akzeptiert
    oder schriftlich angepasst.
-   [ ] Katalog, Version und Maskenregeln sind festgelegt.
-   [ ] Redshift- und Distanzkonventionen sind verifiziert.
-   [ ] Volumenbegrenzung und Entfernungsbereich sind festgelegt.
-   [ ] VoidFinder-Commit und Konfiguration sind dokumentiert.
-   [ ] Dieses Dokument wurde committet, bevor die Ergebnisse der
    Tracerzählung betrachtet wurden.
