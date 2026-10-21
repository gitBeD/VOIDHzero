# SH0ES-Kalibratoren: Void-Mitgliedschaft und Distanz-Unit-Fix

## 1. Ziel

Untersucht wird die geometrische Mitgliedschaft von 43 SH0ES/Pantheon+
Kalibrator-Supernovae in den von VAST ausgegebenen MAXIMALS- und HOLES-Kugeln.
Verglichen werden der ursprüngliche Lauf mit h=0.674, ein Kontrolllauf mit
h=1.0 und ein korrigierter Lauf mit h=0.674.

Die Analyse ist eine Sensitivitätsprüfung der Void-Katalogisierung. Sie ist
kein Nachweis eines Umgebungseffekts auf die gemessene Hubble-Konstante H0.

## 2. Korrektur der Distanzberechnung

In `VAST/python/vast/voidfinder/distance.pyx` wurde die Berechnung der
komovierenden Distanz geändert.

Vorher:

    H0 = 100.0 * h
    out_dists_array[idx] = integral * (c / H0)

Korrigiert:

    out_dists_array[idx] = integral * (c / 100.0)

Die unabhängige Fallback-Berechnung in
`VAST/python/vast/voidfinder/voidfinder.py` wurde analog geändert:

Vorher:

    r_gal = c * galaxy_table['redshift'].data / (100 * h)

Korrigiert:

    r_gal = c * galaxy_table['redshift'].data / 100.0

Ziel der Änderung ist, numerische Distanzen in der dokumentierten Konvention
Mpc/h (h^-1 Mpc) auszugeben, statt die Distanzwerte bei festem h zusätzlich
mit 1/h zu skalieren.

Ein Test der kompilierten Erweiterung ergab für h=0.674 und h=1.0 dieselben
Distanzwerte für z=[0.01, 0.05, 0.10], nämlich ungefähr
[29.908228, 148.10931, 292.59027].

Die Änderung wurde in der installierten Cython-Erweiterung getestet. Die
vollständige Pipeline und sämtliche Einheitenkonventionen müssen unabhängig
davon weiter validiert werden, bevor die Resultate als endgültige physikalische
Void-Geometrie interpretiert werden.

## 3. Verwendete Läufe

### Alter Lauf

- FITS:
  `vast_sdss_dr7_output/vollim_dr7_cbp_102709_VoidFinder_Output.fits`
- Parameter: Omega_M=0.315, h=0.674
- MAXIMALS: 2760
- HOLES: 220596
- Kalibrator-Treffer in mindestens einer Kugel: 10 von 43

Dieser Lauf wurde vor der Distanzkorrektur erstellt. Seine numerischen
Koordinaten und Radien sind wegen der bekannten Einheiteninkonsistenz nicht
ohne Weiteres mit denen des korrigierten Laufs als physikalische Längen
vergleichbar.

### Kontrolllauf h=1

- FITS:
  `vast_sdss_dr7_output_hinv/vollim_dr7_cbp_102709_hinv_VoidFinder_Output.fits`
- Parameter: Omega_M=0.315, h=1.0
- MAXIMALS: 875
- HOLES: 44423
- Kalibrator-Treffer: 9 von 43

Dieser Lauf ist ein Einheitenkontrolllauf. Er ist nicht als unabhängige
Kosmologie mit H0=100 km/s/Mpc zu interpretieren.

### Korrigierter Unit-Fix-Lauf

- FITS:
  `vast_sdss_dr7_output_unitfix/vollim_dr7_cbp_102709_unitfix_VoidFinder_Output.fits`
- Parameter: Omega_M=0.315, H0=67.4 km/s/Mpc, h=0.674
- MAXIMALS: 875
- HOLES: 44423
- Kalibrator-Treffer: 9 von 43

Die Gesamtmitgliedschaft der 43 Kalibratoren stimmt im Kontrolllauf und im
Unit-Fix-Lauf vollständig überein. Das bedeutet nicht, dass alle Void-Zentren,
Radien oder Void-IDs zwischen den Katalogen identisch sind.

## 4. Ergebnis der Mitgliedschaft

| CID | Alter Lauf | Kontrolllauf h=1 | Unit-Fix |
|---|---|---|---|
| 1994ae | Treffer | Treffer | Treffer |
| 1995al | Treffer | Treffer | Treffer |
| 1999cp | Treffer | Treffer | Treffer |
| 2001bg | Treffer | Treffer | Treffer |
| 2002cr | Treffer | Treffer | Treffer |
| 2003du | Treffer | außerhalb | außerhalb |
| 2005cf | Treffer | außerhalb | außerhalb |
| 2007af | Treffer | Treffer | Treffer |
| 2012ht | außerhalb | Treffer | Treffer |
| 2019np | Treffer | Treffer | Treffer |
| ASASSN-15so | Treffer | Treffer | Treffer |

Zusammenfassung:

- Alter Lauf: 10/43 Treffer.
- Kontrolllauf: 9/43 Treffer.
- Unit-Fix-Lauf: 9/43 Treffer.
- Geänderte Gesamtmitgliedschaft zwischen altem Lauf und Unit-Fix: 3 CIDs
  (2003du, 2005cf, 2012ht).
- Geänderte Gesamtmitgliedschaft zwischen Kontrolllauf und Unit-Fix: 0 CIDs.

MAXIMALS- und HOLES-Kugeln sind unterschiedliche geometrische Darstellungen.
Die Trefferzahlen dieser beiden Typen dürfen nicht addiert werden, weil
Kugeln überlappen können. Die Gesamtmitgliedschaft zählt jede Supernova
höchstens einmal.

## 5. Grenzfallanalyse

Der vorzeichenbehaftete Abstand einer Supernova zur Kugeloberfläche ist

    gap = Abstand zum Kugelzentrum - Kugelradius

Ein negativer Wert bedeutet, dass die Supernova innerhalb dieser Kugel liegt;
ein positiver Wert bedeutet, dass sie außerhalb liegt.

Die folgende Tabelle verwendet den kleinsten vorzeichenbehafteten Abstand
über alle Kugeln des angegebenen Typs. Die Werte sind in der jeweiligen
FITS-Koordinateneinheit angegeben und wegen der bekannten Einheitenproblematik
zwischen altem und korrigiertem Lauf nicht direkt als physikalische Längen
vergleichbar.

| CID | Lauf | Kugeltyp | Anzahl enthaltender Kugeln | Kleinster vorzeichenbehafteter Abstand |
|---|---|---|---:|---:|
| 2003du | alt_h0674 | HOLES | 1 | -1.857524 |
| 2003du | unitfix | HOLES | 0 | +3.246771 |
| 2005cf | alt_h0674 | MAXIMALS | 1 | -1.239583 |
| 2005cf | unitfix | MAXIMALS | 0 | +1.487437 |
| 2005cf | alt_h0674 | HOLES | 2 | -1.303257 |
| 2005cf | unitfix | HOLES | 0 | +1.345679 |
| 2012ht | alt_h0674 | HOLES | 0 | +1.358101 |
| 2012ht | unitfix | MAXIMALS | 1 | -3.849442 |
| 2012ht | unitfix | HOLES | 6 | -3.849442 |

Bei 2012ht liegt die nächstgelegene HOLES-Oberfläche im Unit-Fix-Lauf etwa
0.217430 Koordinateneinheiten entfernt; die Supernova befindet sich knapp
innerhalb dieser Oberfläche. Die Werte zeigen, dass sich die geometrische
Zuordnung zwischen den Läufen ändert. Sie erklären nicht allein, welcher
Lauf die physikalisch korrekte Umgebung repräsentiert.

## 6. Reproduzierbarkeit

Projektwurzel:

    ~/voidh0-linux-work/VOIDHzero

SN-Koordinatenquelle:

    data/external/wp2_sh0es_calibrator_xyz_om0315_h0674.csv

Mitgliedschaftsdateien:

    data/external/wp2_sh0es_void_membership_maximals_and_holes_om0315_h0674.csv
    data/external/wp2_sh0es_void_membership_hinv_om0315.csv
    data/external/wp2_sh0es_void_membership_unitfix_om0315.csv

Grenzfallanalyse:

    python tests/unit_checks/analyze_boundary_cases.py

Die SN-CSV enthält physikalische Mpc-Koordinaten. Für den Vergleich mit dem
Unit-Fix-Katalog werden diese mit h=0.674 multipliziert, um sie in die
numerische h^-1-Mpc-Konvention des Void-Katalogs zu überführen.

Für den alten Lauf wurden die SN-Koordinaten ohne diesen Skalierungsfaktor
verwendet, entsprechend der ursprünglichen numerischen Geometrie. Dieser
Vergleich dient der Sensitivitätsanalyse und nicht einer Gleichsetzung der
beiden Einheitenkonventionen.

## 7. Einschränkungen und offene Validierung

1. **Host-Koordinaten:** In der zugrunde liegenden Kalibrator-Tabelle sind
   HOST_RA und HOST_DEC teilweise Platzhalter. SN-Koordinaten dienen dann nur
   als Näherung und sind keine verifizierten Koordinaten des Wirtsgalaxienzentrums.

2. **Rotverschiebung:** Die Wahl von zHD, zCMB oder zHEL ist eine eigene
   wissenschaftliche Entscheidung. Die aktuelle Koordinaten-CSV verwendet
   zHD und dokumentiert damit eine vorläufige Konvention.

3. **Einheiten:** Die Distanzkorrektur beseitigt die erkannte h-Abhängigkeit
   der Distanzfunktion. Die gesamte Pipeline, einschließlich Maskengenerierung,
   Gitterparameter, Grenzbedingungen und FITS-Metadaten, muss dennoch
   konsistent validiert werden.

4. **Void-IDs:** IDs sind zwischen unterschiedlichen Läufen keine stabilen
   Objektidentitäten. Gleiche IDs beweisen keine geometrische Identität;
   unterschiedliche IDs beweisen nicht automatisch einen physikalisch anderen
   Void.

5. **Kugelmitgliedschaft:** MAXIMALS- und HOLES-Treffer sind geometrische
   Tests und keine endgültige Klassifikation einer Supernova als innerhalb
   einer kosmischen Void liegend.

6. **Kosmologische Schlussfolgerung:** Diese Analyse testet keinen
   Umgebungseffekt auf H0. Dafür wären eine validierte Umgebungsdefinition,
   geprüfte Host-Positionen und eine statistische Analyse mit geeigneten
   Unsicherheiten und Kontrollen erforderlich.

## 8. Vorläufiges Fazit

Die korrigierte Distanzfunktion liefert für h=0.674 dieselben Testdistanzen
wie für h=1.0. Der Unit-Fix-Lauf reproduziert außerdem die Gesamtmitgliedschaft
des h=1-Kontrolllaufs für alle 43 Kalibratoren, während drei CIDs gegenüber
dem alten Lauf ihre Gesamtmitgliedschaft ändern.

Dies unterstützt die Verwendung des Unit-Fix-Laufs als vorläufige Referenz
für weitere Validierung. Es ist noch kein Beweis dafür, dass die gesamte
Void-Geometrie endgültig validiert ist oder dass ein Zusammenhang zwischen
Void-Umgebung und H0 besteht.
