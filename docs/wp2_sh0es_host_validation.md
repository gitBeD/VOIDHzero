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
- 35 unique hosts

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

7 of 35 unique hosts were resolved consistently by SIMBAD and NED
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

### NED query timeouts

25 of 35 unique hosts returned a SIMBAD resolution but a NED
`query_error` caused by a 60-second read timeout.

These cases are unresolved due to service accessibility and are
not interpreted as scientific host mismatches.

They remain `review_required` until an independent NED resolution
can be obtained.

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