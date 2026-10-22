
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path.cwd()
DATA = BASE / "data" / "external"

REFERENCE = DATA / "wp2_sh0es_host_reference.csv"
RESOLVED = DATA / "wp2_sh0es_host_resolved_corrected.csv"

# Find the local Pantheon+SH0ES table without assuming one exact location.
candidates = [
    DATA / "Pantheon+SH0ES.dat",
    DATA / "PantheonPlusSH0ES.dat",
    BASE / "Pantheon+SH0ES.dat",
    BASE / "PantheonPlusSH0ES.dat",
]
candidates += list(BASE.glob("**/Pantheon+SH0ES.dat"))

pantheon_path = next((p for p in candidates if p.is_file()), None)

if pantheon_path is None:
    raise FileNotFoundError(
        "Pantheon+SH0ES.dat not found. Place/find the local data file, "
        "then add its path to candidates in this script."
    )

# Cosmology
OMEGA_M = 0.315
H0 = 67.4
C_KMS = 299792.458
REDSHIFT_COLUMNS = ["zHD", "zCMB", "zHEL"]

reference = pd.read_csv(REFERENCE, dtype={"CID": str})
resolved = pd.read_csv(RESOLVED)

pantheon = pd.read_csv(
    pantheon_path,
    sep=r"\s+",
    comment="#",
    dtype={"CID": str},
)

# Validate required Pantheon columns.
required_pantheon = {"CID", *REDSHIFT_COLUMNS}
missing = required_pantheon - set(pantheon.columns)

if missing:
    raise ValueError(f"Missing Pantheon columns: {sorted(missing)}")

# Validate required resolver columns.
required_resolved = {
    "normalized_query_name",
    "SIMBAD_RA_deg",
    "SIMBAD_DEC_deg",
    "NED_RA_deg",
    "NED_DEC_deg",
    "reference_RA_deg",
    "reference_DEC_deg",
    "reference_status",
    "reference_source",
    "resolver_status",
    "SIMBAD_NED_separation_arcsec",
}
missing = required_resolved - set(resolved.columns)

if missing:
    raise ValueError(f"Missing resolver columns: {sorted(missing)}")

# One row per SN; keep source_host from the reference table.
# The resolver table contains source_host too, so drop it before merging.
resolved_for_merge = resolved.drop(
    columns=["source_host"],
    errors="ignore",
)

sn = reference.merge(
    resolved_for_merge,
    on="normalized_query_name",
    how="left",
    validate="many_to_one",
    indicator="host_merge_status",
)

# Check repeated Pantheon CIDs for conflicting redshift values.
conflicts = (
    pantheon.groupby("CID")[REDSHIFT_COLUMNS]
    .nunique(dropna=False)
    .gt(1)
    .any(axis=1)
)

if conflicts.any():
    raise ValueError(
        "Widersprüchliche Rotverschiebungswerte für CIDs: "
        + ", ".join(conflicts[conflicts].index.astype(str))
    )

# Identical repeated CID/redshift rows are reduced to one row per CID.
pantheon_unique = pantheon[
    ["CID", *REDSHIFT_COLUMNS]
].drop_duplicates()

# Attach redshifts, requiring one Pantheon row per CID.
sn = sn.merge(
    pantheon_unique,
    on="CID",
    how="left",
    validate="one_to_one",
    indicator="pantheon_merge_status",
)

# Coordinate sanity checks and SIMBAD/NED angular separation.
ra = pd.to_numeric(sn["reference_RA_deg"], errors="coerce")
dec = pd.to_numeric(sn["reference_DEC_deg"], errors="coerce")

sra = pd.to_numeric(sn["SIMBAD_RA_deg"], errors="coerce")
sdec = pd.to_numeric(sn["SIMBAD_DEC_deg"], errors="coerce")

nra = pd.to_numeric(sn["NED_RA_deg"], errors="coerce")
ndec = pd.to_numeric(sn["NED_DEC_deg"], errors="coerce")


def angular_sep_arcsec(ra1, dec1, ra2, dec2):
    """Great-circle separation, with angles in degrees."""
    a1, d1, a2, d2 = np.deg2rad([ra1, dec1, ra2, dec2])

    cosang = (
        np.sin(d1) * np.sin(d2)
        + np.cos(d1) * np.cos(d2) * np.cos(a1 - a2)
    )

    return (
        np.rad2deg(np.arccos(np.clip(cosang, -1.0, 1.0)))
        * 3600.0
    )


sn["SIMBAD_NED_separation_recomputed_arcsec"] = np.nan

both = (
    sra.notna()
    & sdec.notna()
    & nra.notna()
    & ndec.notna()
)

sn.loc[both, "SIMBAD_NED_separation_recomputed_arcsec"] = [
    angular_sep_arcsec(a, b, c, d)
    for a, b, c, d in zip(
        sra[both],
        sdec[both],
        nra[both],
        ndec[both],
    )
]

sn["reference_coordinates_valid"] = (
    ra.notna()
    & dec.notna()
    & ra.ge(0)
    & ra.lt(360)
    & dec.ge(-90)
    & dec.le(90)
)

sn["host_coordinate_source_present"] = sn["reference_source"].notna()

sn["pantheon_redshifts_present"] = (
    sn[REDSHIFT_COLUMNS].notna().all(axis=1)
)

sn["host_review_flag"] = (
    ~sn["reference_coordinates_valid"]
    | ~sn["host_coordinate_source_present"]
    | sn["resolver_status"].ne("resolved_consistent")
    | sn["pantheon_merge_status"].ne("both")
)

# Export host-coordinate audit.
audit_cols = [
    "CID",
    "source_host",
    "normalized_query_name",
    "status",
    "resolver_status",
    "reference_status",
    "reference_source",
    "reference_RA_deg",
    "reference_DEC_deg",
    "SIMBAD_main_id",
    "SIMBAD_RA_deg",
    "SIMBAD_DEC_deg",
    "NED_object_name",
    "NED_RA_deg",
    "NED_DEC_deg",
    "SIMBAD_NED_separation_arcsec",
    "SIMBAD_NED_separation_recomputed_arcsec",
    "host_merge_status",
    "pantheon_merge_status",
    "reference_coordinates_valid",
    "host_coordinate_source_present",
    "pantheon_redshifts_present",
    "host_review_flag",
]

audit = sn[audit_cols].copy()

audit_path = DATA / "wp2_sh0es_host_coordinate_audit.csv"
audit.to_csv(audit_path, index=False)


# Flat LCDM comoving radial distance in physical Mpc.
def comoving_distance_mpc(z):
    if not np.isfinite(z) or z <= 0:
        return np.nan

    # Simpson integration, with a fine fixed grid for reproducibility.
    n = 2000

    if n % 2:
        n += 1

    x = np.linspace(0.0, float(z), n + 1)

    e = np.sqrt(
        OMEGA_M * (1.0 + x) ** 3
        + (1.0 - OMEGA_M)
    )

    f = 1.0 / e

    integral = (x[1] - x[0]) / 3.0 * (
        f[0]
        + f[-1]
        + 4.0 * f[1:-1:2].sum()
        + 2.0 * f[2:-1:2].sum()
    )

    return (C_KMS / H0) * integral


# Calculate host-based Cartesian coordinates for each redshift variant.
rows = []

for _, row in sn.iterrows():
    ra_deg = row["reference_RA_deg"]
    dec_deg = row["reference_DEC_deg"]

    coords_ok = (
        pd.notna(ra_deg)
        and pd.notna(dec_deg)
        and 0 <= ra_deg < 360
        and -90 <= dec_deg <= 90
    )

    for zcol in REDSHIFT_COLUMNS:
        z = pd.to_numeric(
            pd.Series([row[zcol]]),
            errors="coerce",
        ).iloc[0]

        r = comoving_distance_mpc(z)
        valid = bool(
            coords_ok
            and np.isfinite(r)
            and row["resolver_status"] == "resolved_consistent"
        )

        if valid:
            ra_rad = np.deg2rad(ra_deg)
            dec_rad = np.deg2rad(dec_deg)

            x = r * np.cos(dec_rad) * np.cos(ra_rad)
            y = r * np.cos(dec_rad) * np.sin(ra_rad)
            zz = r * np.sin(dec_rad)
        else:
            x = y = zz = np.nan

        rows.append(
            {
                "CID": row["CID"],
                "source_host": row["source_host"],
                "redshift_column": zcol,
                "redshift": z,
                "Omega_M": OMEGA_M,
                "H0_km_s_Mpc": H0,
                "distance_Mpc": r,
                "host_RA_deg": ra_deg,
                "host_DEC_deg": dec_deg,
                "x_Mpc": x,
                "y_Mpc": y,
                "z_Mpc": zz,
                "host_coordinates_valid": bool(coords_ok),
                "resolver_status": row["resolver_status"],
                "reference_source": row["reference_source"],
                "valid_for_host_based_analysis": valid,
            }
        )

sens = pd.DataFrame(rows)

sens_path = DATA / "wp2_sh0es_redshift_sensitivity.csv"
sens.to_csv(sens_path, index=False)

# Summarize redshift sensitivity.
summary = (
    sens.groupby("redshift_column", dropna=False)
    .agg(
        n_rows=("CID", "size"),
        n_unique_SN=("CID", "nunique"),
        n_valid_distances=(
            "distance_Mpc",
            lambda x: int(x.notna().sum()),
        ),
        n_valid_host_based=("valid_for_host_based_analysis", "sum"),
        min_distance_Mpc=("distance_Mpc", "min"),
        median_distance_Mpc=("distance_Mpc", "median"),
        max_distance_Mpc=("distance_Mpc", "max"),
    )
    .reset_index()
)

summary["Omega_M"] = OMEGA_M
summary["H0_km_s_Mpc"] = H0

summary_path = DATA / "wp2_sh0es_redshift_sensitivity_summary.csv"
summary.to_csv(summary_path, index=False)

# Report results.
print(f"Pantheon-Datei: {pantheon_path}")
print(f"SN-Zeilen in Host-Referenz: {len(reference)}")
print(f"Eindeutige Hosts in Resolver-Tabelle: {len(resolved)}")

print(
    "SN-Zeilen ohne Resolver-Zuordnung: "
    f"{int(sn['host_merge_status'].ne('both').sum())}"
)

print(
    "SN-Zeilen ohne Pantheon-Match: "
    f"{int(sn['pantheon_merge_status'].ne('both').sum())}"
)

print(
    "SN mit gültigen Referenzkoordinaten: "
    f"{int(sn['reference_coordinates_valid'].sum())}/{len(sn)}"
)

print(
    "SN mit Prüfmarkierung: "
    f"{int(sn['host_review_flag'].sum())}/{len(sn)}"
)

print(
    "\nRotverschiebungs-Sensitivität "
    "(Entfernungen, noch keine Void-Mitgliedschaft):"
)

print(summary.to_string(index=False))

print("\nGeschriebene Dateien:")
print(audit_path)
print(sens_path)
print(summary_path)
