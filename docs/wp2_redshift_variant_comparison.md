# WP2: Sensitivitätsvergleich der Pantheon+-Redshift-Spalten

Vergleich von `zHD`, `zCMB` und `zHEL` für dieselben 43 kuratierten CIDs. Bestehende XYZ-Dateien werden nicht überschrieben.

Konvention: flache Lambda-CDM-Distanz, Omega_M=0.26, h=1.0, VAST-Skalierung Mpc/h; identische RA/DEC für alle Varianten.

Referenz für die Differenzen ist `zHD`. Dieser Vergleich ist eine Sensitivitätsanalyse, keine automatische Entscheidung über die wissenschaftlich passende Spalte.

| Variante vs. zHD | max. |Δr| (Mpc/h) | median |Δr| (Mpc/h) | max. XYZ-Verschiebung (Mpc/h) | mediane XYZ-Verschiebung (Mpc/h) | CIDs mit abweichendem z |
|---|---:|---:|---:|---:|---:|
| `zCMB` | 4.39999 | 1.2246 | 4.39999 | 1.2246 | 40/43 |
| `zHEL` | 5.8633 | 2.15099 | 5.8633 | 2.15099 | 42/43 |

## Interpretation und Grenzen

- Bei festen RA/DEC liegen alle Varianten auf derselben Sichtlinie; die XYZ-Verschiebung entspricht dem Betrag der radialen Verschiebung.
- Der Vergleich isoliert den Einfluss der Redshift-Spalte bei festgehaltener Distanzkonvention.
- Messfehler, Pekuliargeschwindigkeiten, Host-Positionsunsicherheit und Survey-Maske sind nicht eingerechnet.
- Die Distanzfunktion nutzt die VAST-nahe Skalenkonvention; vor einer finalen wissenschaftlichen Verwendung sollte die numerische Ausgabe stichprobenweise direkt gegen die installierte VAST-Funktion geprüft werden.

## Ausgaben

- Detail-CSV: `data/external/wp2_sh0es_redshift_variant_comparison.csv`
- Bericht: `docs/wp2_redshift_variant_comparison.md`

Die Detail-CSV enthält für jede CID alle drei Redshifts, Radien und XYZ-Koordinaten sowie Differenzen von `zCMB` und `zHEL` gegenüber `zHD`.
