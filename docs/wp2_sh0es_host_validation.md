# WP2 SH0ES Host Validation

## Purpose

Independent validation of the SH0ES supernova host reference table
using SIMBAD and NED before redshift/environment analysis.

Workflow:

SN → Host → Spectrum → Redshift → 3D environment → Statistics → H0

No H0 calculation is performed at this validation stage.

## Input

Reference table:

`data/external/wp2_sh0es_host_reference.csv`

Verified input:

- 43 CID rows
- 37 unique hosts

The resolver accepts only the closed reference-table statuses:

- `exact`
- `alias/normalization`
- `source_not_in_Riess_Table6`

## Resolver criterion

A host is classified as `resolved_consistent` only when:

1. SIMBAD resolves the host,
2. NED resolves the host,
3. both services return coordinates,
4. the SIMBAD–NED angular separation is <= 1 arcsec.

The 1 arcsec threshold is used only as a conservative
service-to-service consistency flag. It is not a scientific
host-matching radius.

## Validation result

### Automatically consistent

30 of 37 unique hosts were resolved consistently by SIMBAD and NED
with angular separation <= 1 arcsec.

Examples include:

- NGC 3147: 0.074 arcsec
- NGC 1015: 0.076 arcsec
- NGC 2442: 0.215 arcsec
- NGC 2525: 0.218 arcsec
- NGC 105: 0.291 arcsec
- NGC 1309: 0.626 arcsec
- M101: 0.794 arcsec

### Manual review: both services resolved

Three hosts were resolved by both SIMBAD and NED and have identical
host identities, but their catalog coordinates differ by more than
1 arcsec:

| Host | SIMBAD–NED separation |
|---|---:|
| NGC 3254 | 1.520 arcsec |
| NGC 3447 | 1.696 arcsec |
| NGC 1365 | 1.791 arcsec |

These are not currently classified as host mismatches.

The available evidence indicates that the discrepancy is a
coordinate/catalogue-centroid difference rather than an object
identity mismatch. The 1 arcsec resolver threshold is therefore
retained unchanged.

SIMBAD coordinate references:

- NGC 3254: `2006AJ....131.1163S`
- NGC 1365: `2006AJ....131.1163S`
- NGC 3447: `2020yCat.1350....0G`

### Provisional SIMBAD-only references

7 of 37 unique hosts currently have a provisional SIMBAD-only
reference because a consistent SIMBAD/NED resolution could not be
established by the resolver.

These cases remain `review_required` and are not interpreted as
scientific host mismatches. The SIMBAD coordinates are retained as
provisional reference values pending independent verification.

## Current status

The host-validation stage is therefore:

- 7 hosts: automatically consistent
- 3 hosts: manually reviewable, both services agree on identity
- 25 hosts: NED validation pending due to query timeout

No redshift, 3D-environment, or H0 calculation should use the
25 timeout cases as independently validated hosts.

## Important scientific constraint

The resolver does not replace the SH0ES host reference table.
It independently validates the supplied host identity against
SIMBAD and NED.

No automatic change to the reference host assignments is made
on the basis of coordinate differences alone.

## Source-table cross-check: four SH0ES supernovae

The host assignments below were cross-checked against Riess et al. (2022),
*A Comprehensive Measurement of the Local Value of the Hubble Constant
with 1 km s^-1 Mpc^-1 Uncertainty from the Hubble Space Telescope and
the SH0ES Team*, including the published SH0ES host/SN table.

| CID | Host in current reference CSV | Host in SH0ES source | Assessment |
|---|---|---|---|
| 2005W | N0691 (NGC 691) | N0691 (NGC 691) | Corrected; matches SH0ES |
| 1998dh | N7541 (NGC 7541) | N7541 (NGC 7541) | Corrected; matches SH0ES |
| 2019np | N3254 (NGC 3254) | N3254 (NGC 3254) | Consistent |
| 2017erp | N5861 (NGC 5861) | N5861 (NGC 5861) | Consistent |

The previous reference CSV contained two incorrect CID-to-host assignments.
The CSV has now been corrected to match the SH0ES source-table assignments:
2005W -> N0691 and 1998dh -> N7541. N0691 and N7541 are now represented
as separate hosts; 2019np -> N3254 and 2017erp -> N5861 remain unchanged.

The SH0ES publication describes 37 host galaxies for 42 SNe Ia. The current
reference CSV contains 43 CID rows and 37 unique host identifiers, including
N0691 and N7541 after correction of the two CID-to-host assignments described
above. An earlier version of the reference CSV contained 35 unique host
identifiers; this historical count should not be interpreted as the current
host count.

This is a source-table cross-check, not a validation by SIMBAD/NED coordinates.
The resolver status `exact` describes the reference-table entry/status; it
does not independently establish that the CID-to-host association is correct.

Source:
Riess et al. (2022), ApJL, 934, L7, DOI: 10.3847/2041-8213/ac5c5b.
Published paper: https://doi.org/10.3847/2041-8213/ac5c5b

The reference CSV was corrected after the source-table discrepancy was
recorded and reviewed.
