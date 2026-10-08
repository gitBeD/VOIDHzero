from pathlib import Path

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.io import fits
import astropy.units as u


ROOT = Path(__file__).resolve().parents[1]

PANTHEON_PATH = ROOT / "Pantheon+SH0ES.dat"
NSA_PATH = ROOT.parent / "nsa_v1_0_1.fits"
OUTPUT_PATH = ROOT / "data" / "external" / "wp2_nsa_diagnosis.csv"

MATCH_RADIUS = 3.0 * u.arcsec
Z_TOL = 0.005


def load_pantheon_calibrators():
    table = pd.read_csv(PANTHEON_PATH, sep=r"\s+", engine="python")

    table = table[table["IS_CALIBRATOR"] == 1].copy()

    # One row per unique Pantheon CID.
    table = table.drop_duplicates(subset=["CID"]).reset_index(drop=True)

    return table


def main():
    pantheon = load_pantheon_calibrators()

    print(f"Pantheon calibrator rows: {len(pantheon)}")
    print(f"NSA file: {NSA_PATH}")

    with fits.open(NSA_PATH, memmap=True) as hdul:
        data = hdul[1].data

        ra = np.asarray(data["RA"], dtype=float)
        dec = np.asarray(data["DEC"], dtype=float)
        z = np.asarray(data["Z"], dtype=float)
        nsaid = np.asarray(data["NSAID"])
        zsrc = np.char.strip(np.asarray(data["ZSRC"]).astype(str))
        plate = np.asarray(data["PLATE"])
        mjd = np.asarray(data["MJD"])
        fiberid = np.asarray(data["FIBERID"])

        valid = (
            np.isfinite(ra)
            & np.isfinite(dec)
            & np.isfinite(z)
        )

        ra = ra[valid]
        dec = dec[valid]
        z = z[valid]
        nsaid = nsaid[valid]
        zsrc = zsrc[valid]
        plate = plate[valid]
        mjd = mjd[valid]
        fiberid = fiberid[valid]

    print(f"Usable NSA rows: {len(ra)}")

    nsa_coords = SkyCoord(
        ra=ra * u.deg,
        dec=dec * u.deg,
        frame="icrs",
    )

    results = []

    for row in pantheon.itertuples(index=False):
        cid = str(row.CID)

        sn_coord = SkyCoord(
            ra=float(row.RA) * u.deg,
            dec=float(row.DEC) * u.deg,
            frame="icrs",
        )

        idx, sep2d, _ = sn_coord.match_to_catalog_sky(nsa_coords)

        separation_arcsec = float(np.asarray(sep2d.to_value(u.arcsec)).item())
        nsa_match = separation_arcsec <= MATCH_RADIUS.to_value(u.arcsec)

        if nsa_match:
            matched_z = float(z[idx])
            delta_z = abs(matched_z - float(row.zHD))

            matched_nsaid = int(nsaid[idx])
            matched_zsrc = str(zsrc[idx])

            has_sdss_ids = (
                int(plate[idx]) > 0
                and int(mjd[idx]) > 0
                and int(fiberid[idx]) > 0
            )

            sdss_spec = (
                matched_zsrc == "sdss"
                and has_sdss_ids
            )
        else:
            matched_z = np.nan
            delta_z = np.nan
            matched_nsaid = -1
            matched_zsrc = ""
            has_sdss_ids = False
            sdss_spec = False

        results.append(
            {
                "CID": cid,
                "RA": float(row.RA),
                "DEC": float(row.DEC),
                "zHD": float(row.zHD),
                "NSA_match_3arcsec": nsa_match,
                "NSA_separation_arcsec": separation_arcsec,
                "NSAID": matched_nsaid,
                "NSA_Z": matched_z,
                "NSA_delta_z": delta_z,
                "NSA_redshift_match": (
                    nsa_match and delta_z <= Z_TOL
                ),
                "NSA_ZSRC": matched_zsrc,
                "NSA_has_SDSS_ids": has_sdss_ids,
                "NSA_SDSS_spectroscopic": sdss_spec,
            }
        )

    result = pd.DataFrame(results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print()
    print("=== Summary ===")
    print("Unique calibrators:", len(result))
    print(
        "NSA positional matches:",
        int(result["NSA_match_3arcsec"].sum()),
    )
    print(
        "NSA + redshift matches:",
        int(result["NSA_redshift_match"].sum()),
    )
    print(
        "NSA + SDSS spectroscopic provenance:",
        int(result["NSA_SDSS_spectroscopic"].sum()),
    )
    print()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
