from pathlib import Path

import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import SkyCoord, search_around_sky
from astropy.io import fits


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PANTHEON_PATH = PROJECT_ROOT / "Pantheon+SH0ES.dat"
NSA_PATH = PROJECT_ROOT.parent / "nsa_v1_0_1.fits"

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "external" / "wp2_nsa_dlr_diagnosis.csv"
)

# Deliberately generous candidate-generation radius.
# This is NOT a host-selection threshold.
SEARCH_RADIUS = 300.0 * u.arcsec


# ---------------------------------------------------------------------------
# DLR reference values from the independently checked 2011fe control case
# NSAID 259087
# ---------------------------------------------------------------------------

CONTROL_2011FE = {
    "cid": "2011fe",
    "nsaid": 259087,

    "separation_arcsec": 81.140022,
    "a_arcsec": 115.638275,
    "b_arcsec": 54.491403,
    "dlr_arcsec": 87.243493,
    "d_dlr": 0.930041,
}

REFERENCE_TOLERANCE = {
    "separation_arcsec": 1e-3,
    "a_arcsec": 1e-3,
    "b_arcsec": 1e-3,
    "dlr_arcsec": 1e-3,
    "d_dlr": 1e-5,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sdss_spectroscopic_provenance(zsrc, plate, mjd, fiberid):
    """
    Operational SDSS spectroscopic provenance criterion used in WP2.

    NSA Z is not treated as SDSS-derived merely because an SDSS identifier
    exists somewhere in the row. We require ZSRC='sdss' and valid
    PLATE/MJD/FIBERID.
    """
    return (
        str(zsrc).strip().lower() == "sdss"
        and int(plate) > 0
        and int(mjd) > 0
        and int(fiberid) > 0
    )


def calculate_dlr(sn_coord, galaxy_coord, a_arcsec, ba, pa_deg):
    """
    Calculate directional light radius and normalized separation.

    NSA interpretation used here:
        a  = SERSIC_TH50  [major-axis 50%-light radius]
        b  = a * SERSIC_BA
        PA = SERSIC_PHI

    DLR(phi) = (a*b) /
               sqrt((a*sin(phi))^2 + (b*cos(phi))^2)

    phi is measured relative to the galaxy major axis.
    """
    a = float(a_arcsec)
    q = float(ba)
    pa = float(pa_deg)

    b = a * q

    galaxy = SkyCoord(
        ra=galaxy_coord.ra,
        dec=galaxy_coord.dec,
        frame="icrs",
    )

    separation = galaxy.separation(sn_coord)
    position_angle = galaxy.position_angle(sn_coord)

    phi = (position_angle - pa * u.deg).wrap_at(180 * u.deg)
    phi_rad = phi.to_value(u.rad)

    denominator = np.sqrt(
        (a * np.sin(phi_rad)) ** 2
        + (b * np.cos(phi_rad)) ** 2
    )

    dlr = (a * b) / denominator

    separation_arcsec = separation.to_value(u.arcsec)

    return (
        separation_arcsec,
        b,
        dlr,
        separation_arcsec / dlr,
        position_angle.to_value(u.deg),
        phi.to_value(u.deg),
    )


def check_2011fe_reference(row):
    """
    Verify that the vectorized calculation reproduces the independently
    established 2011fe / NSAID 259087 reference geometry.
    """
    if row["CID"] != CONTROL_2011FE["cid"]:
        return

    if int(row["NSAID"]) != CONTROL_2011FE["nsaid"]:
        return

    checks = {
        "separation_arcsec": (
            row["separation_arcsec"],
            CONTROL_2011FE["separation_arcsec"],
            REFERENCE_TOLERANCE["separation_arcsec"],
        ),
        "a_arcsec": (
            row["a_arcsec"],
            CONTROL_2011FE["a_arcsec"],
            REFERENCE_TOLERANCE["a_arcsec"],
        ),
        "b_arcsec": (
            row["b_arcsec"],
            CONTROL_2011FE["b_arcsec"],
            REFERENCE_TOLERANCE["b_arcsec"],
        ),
        "dlr_arcsec": (
            row["dlr_arcsec"],
            CONTROL_2011FE["dlr_arcsec"],
            REFERENCE_TOLERANCE["dlr_arcsec"],
        ),
        "d_dlr": (
            row["d_dlr"],
            CONTROL_2011FE["d_dlr"],
            REFERENCE_TOLERANCE["d_dlr"],
        ),
    }

    failed = []

    for name, (actual, expected, tolerance) in checks.items():
        if not np.isclose(
            actual,
            expected,
            atol=tolerance,
            rtol=0.0,
        ):
            failed.append(
                f"{name}: actual={actual:.9f}, "
                f"expected={expected:.9f}, "
                f"tolerance={tolerance}"
            )

    if failed:
        raise RuntimeError(
            "2011fe DLR reference check FAILED:\n"
            + "\n".join(failed)
        )

    print("2011fe DLR reference check: PASS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== NSA DLR diagnosis ===")
    print(f"Pantheon+: {PANTHEON_PATH}")
    print(f"NSA:       {NSA_PATH}")
    print(f"Output:    {OUTPUT_PATH}")
    print(f"Search radius: {SEARCH_RADIUS.to_value(u.arcsec):.1f} arcsec")
    print()

    # -----------------------------------------------------------------------
    # Pantheon+
    # -----------------------------------------------------------------------

    table = pd.read_csv(
        PANTHEON_PATH,
        sep=r"\s+",
        engine="python",
    )

    calibrators = table[
        table["IS_CALIBRATOR"].astype(str).str.upper().eq("1")
    ].copy()

    # One representative row per CID.
    calibrators = (
        calibrators
        .sort_values(["CID"])
        .drop_duplicates(subset="CID", keep="first")
        .reset_index(drop=True)
    )

    print(f"Unique Pantheon+ calibrators: {len(calibrators)}")

    sn_coords = SkyCoord(
        ra=calibrators["RA"].to_numpy(dtype=float) * u.deg,
        dec=calibrators["DEC"].to_numpy(dtype=float) * u.deg,
        frame="icrs",
    )

    # -----------------------------------------------------------------------
    # NSA
    # -----------------------------------------------------------------------

    with fits.open(NSA_PATH, memmap=True) as hdul:
        data = hdul[1].data

        ra = np.asarray(data["RA"], dtype=float)
        dec = np.asarray(data["DEC"], dtype=float)
        nsaid = np.asarray(data["NSAID"], dtype=np.int64)

        z = np.asarray(data["Z"], dtype=float)
        zsrc = np.asarray(data["ZSRC"]).astype(str)

        isdss = np.asarray(data["ISDSS"], dtype=np.int64)
        izcat = np.asarray(data["IZCAT"], dtype=np.int64)

        plate = np.asarray(data["PLATE"], dtype=np.int64)
        mjd = np.asarray(data["MJD"], dtype=np.int64)
        fiberid = np.asarray(data["FIBERID"], dtype=np.int64)

        sersic_th50 = np.asarray(data["SERSIC_TH50"], dtype=float)
        sersic_ba = np.asarray(data["SERSIC_BA"], dtype=float)
        sersic_phi = np.asarray(data["SERSIC_PHI"], dtype=float)
        sersic_ok = np.asarray(data["SERSIC_OK"], dtype=np.int64)

    TH50_SENTINEL = 159.7578125
    TH50_SENTINEL_ATOL = 1e-6

    valid_position = (
        np.isfinite(ra)
        & np.isfinite(dec)
    )

    valid_dlr_geometry = (
        np.isfinite(sersic_th50)
        & np.isfinite(sersic_ba)
        & np.isfinite(sersic_phi)
        & (sersic_th50 > 0)
        & (sersic_ba > 0)
        & (sersic_ba <= 1)
    )


    usable = valid_position & valid_dlr_geometry



    print(f"NSA rows: {len(data)}")
    print(f"NSA rows with valid DLR geometry: {np.count_nonzero(usable)}")
    print()

    nsa_coords = SkyCoord(
        ra=ra[usable] * u.deg,
        dec=dec[usable] * u.deg,
        frame="icrs",
    )

    nsaid_u = nsaid[usable]
    z_u = z[usable]
    zsrc_u = zsrc[usable]
    isdss_u = isdss[usable]
    izcat_u = izcat[usable]
    plate_u = plate[usable]
    mjd_u = mjd[usable]
    fiberid_u = fiberid[usable]

    th50_u = sersic_th50[usable]
    ba_u = sersic_ba[usable]
    phi_u = sersic_phi[usable]
    sersic_ok_u = sersic_ok[usable]

    # -----------------------------------------------------------------------
    # Candidate generation
    # -----------------------------------------------------------------------

    idx_sn, idx_nsa, sep2d, _ = search_around_sky(
        sn_coords,
        nsa_coords,
        SEARCH_RADIUS,
    )

    print(f"Candidate pairs within search radius: {len(idx_sn)}")
    print()

    rows = []

    sentinel_excluded_counts = {}

    for i_sn, i_nsa, separation in zip(
        idx_sn,
        idx_nsa,
        sep2d,
    ):
        i_sn = int(i_sn)
        i_nsa = int(i_nsa)

        sn_coord = sn_coords[i_sn]
        galaxy_coord = nsa_coords[i_nsa]

        cid = str(calibrators.iloc[i_sn]["CID"])
        zhd = float(calibrators.iloc[i_sn]["zHD"])

        if np.isclose(
                th50_u[i_nsa],
                TH50_SENTINEL,
                atol=TH50_SENTINEL_ATOL,
                rtol=0,
        ):
            sentinel_excluded_counts[cid] = (
                    sentinel_excluded_counts.get(cid, 0) + 1
            )
            continue

        separation_arcsec, b_arcsec, dlr_arcsec, d_dlr, position_angle_deg, phi_deg = (
            calculate_dlr(
                sn_coord=sn_coord,
                galaxy_coord=galaxy_coord,
                a_arcsec=th50_u[i_nsa],
                ba=ba_u[i_nsa],
                pa_deg=phi_u[i_nsa],
            )
        )

        sdss_spec = sdss_spectroscopic_provenance(
            zsrc=zsrc_u[i_nsa],
            plate=plate_u[i_nsa],
            mjd=mjd_u[i_nsa],
            fiberid=fiberid_u[i_nsa],
        )

        rows.append(
            {
                "CID": cid,
                "SN_RA": float(calibrators.iloc[i_sn]["RA"]),
                "SN_DEC": float(calibrators.iloc[i_sn]["DEC"]),
                "zHD": zhd,

                "NSAID": int(nsaid_u[i_nsa]),
                "NSA_RA": float(ra[usable][i_nsa]),
                "NSA_DEC": float(dec[usable][i_nsa]),

                "separation_arcsec": separation_arcsec,

                "SERSIC_TH50": float(th50_u[i_nsa]),
                "SERSIC_BA": float(ba_u[i_nsa]),
                "SERSIC_PHI": float(phi_u[i_nsa]),
                "SERSIC_OK": int(sersic_ok_u[i_nsa]),

                "a_arcsec": float(th50_u[i_nsa]),
                "b_arcsec": b_arcsec,
                "position_angle_deg": position_angle_deg,
                "phi_deg": phi_deg,
                "dlr_arcsec": dlr_arcsec,
                "d_dlr": d_dlr,

                "NSA_Z": float(z_u[i_nsa]),
                "delta_z": abs(float(z_u[i_nsa]) - zhd),
                "ZSRC": str(zsrc_u[i_nsa]).strip(),

                "ISDSS": int(isdss_u[i_nsa]),
                "IZCAT": int(izcat_u[i_nsa]),
                "PLATE": int(plate_u[i_nsa]),
                "MJD": int(mjd_u[i_nsa]),
                "FIBERID": int(fiberid_u[i_nsa]),

                "SDSS_SPECTROSCOPIC_PROVENANCE": sdss_spec,
            }
        )

    result = pd.DataFrame(rows)



    if result.empty:
        raise RuntimeError(
            "No NSA candidates found within the search radius."
        )

    result["N_TH50_SENTINEL_EXCLUDED"] = (
        result["CID"]
        .map(sentinel_excluded_counts)
        .fillna(0)
        .astype(int)
    )

    n_pairs_excluded = int(sum(sentinel_excluded_counts.values()))
    n_cids_affected = int(sum(1 for v in sentinel_excluded_counts.values() if v > 0))

    print(f"\n=== TH50-Sentinel-Filter ===")
    print(f"  Ausgeschlossene Kandidatenpaare gesamt: {n_pairs_excluded}")
    print(f"  Betroffene Kalibratoren (CIDs):         {n_cids_affected} von {len(calibrators)}")
    if n_pairs_excluded == 0:
        print(
            "  WARNUNG: Filter hat 0 Treffer erzielt -- "
            "Sentinel-Wert, Toleranz oder Indexierung pruefen."
        )

    # Sort within each SN by increasing DLR.
    result = result.sort_values(
        ["CID", "d_dlr", "separation_arcsec"]
    ).reset_index(drop=True)

    # Candidate rank per calibrator.
    result["DLR_RANK"] = (
        result.groupby("CID", sort=False)
        .cumcount()
        + 1
    )

    # -----------------------------------------------------------------------
    # 2011fe control validation
    # -----------------------------------------------------------------------

    control = result[
        (result["CID"] == CONTROL_2011FE["cid"])
        & (result["NSAID"] == CONTROL_2011FE["nsaid"])
    ]

    if control.empty:
        raise RuntimeError(
            "2011fe / NSAID 259087 was not found within the diagnostic "
            "search radius."
        )

    control_row = control.iloc[0]
    check_2011fe_reference(control_row)

    # -----------------------------------------------------------------------
    # Write CSV
    # -----------------------------------------------------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    best = (
        result
        .sort_values(["CID", "d_dlr"])
        .groupby("CID", as_index=False)
        .first()
    )

    print("=== Summary ===")
    print(f"Unique calibrators: {len(calibrators)}")
    print(f"NSA candidate pairs: {len(result)}")
    print(f"Calibrators with >=1 NSA candidate: {best['CID'].nunique()}")
    print()

    print("Best DLR candidate per calibrator:")
    print(
        best[
            [
                "CID",
                "NSAID",
                "d_dlr",
                "separation_arcsec",
                "SERSIC_OK",
                "NSA_Z",
                "ZSRC",
                "PLATE",
                "MJD",
                "FIBERID",
                "SDSS_SPECTROSCOPIC_PROVENANCE",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"CSV written: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()