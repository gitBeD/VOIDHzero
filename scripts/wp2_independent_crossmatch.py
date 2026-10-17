#!/usr/bin/env python3
"""Unabhängiger angularer Crossmatch für Pantheon+/SH0ES-Kalibratoren.

Liest den originalen SDSS-DR7-FITS-Katalog und die bereits erzeugte
VoidFinder-Maske. Führt keinen VoidFinder-Lauf aus und filtert vor dem
angularen Nearest-Neighbor-Match nicht nach Rotverschiebung.
"""

from pathlib import Path
import csv
import pickle

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
import astropy.units as u


PANTHEON = Path("Pantheon+SH0ES.dat")
SDSS = Path(
    "/home/pctu/vast-voidfinder/data/reference/sdss_dr7/"
    "vollim_dr7_cbp_102709.fits"
)
MASK = Path(
    "/home/pctu/vast-voidfinder/results/reference_sdss_dr7/"
    "vollim_dr7_cbp_102709_mask.pickle"
)
OUT = Path("/tmp/wp2_independent_crossmatch.csv")


def main():
    # Pantheon+-Kalibratoren einlesen
    pantheon = Table.read(PANTHEON, format="ascii")
    required_pantheon = {"CID", "zHD", "RA", "DEC", "IS_CALIBRATOR"}
    missing = required_pantheon - set(pantheon.colnames)
    if missing:
        raise ValueError(f"Pantheon-Spalten fehlen: {sorted(missing)}")

    is_cal = np.asarray(pantheon["IS_CALIBRATOR"], dtype=int) == 1
    cal = pantheon[is_cal]

    # Ein Eintrag pro CID; gleiche CID mehrfach vorkommend nicht doppelt zählen
    seen = set()
    unique_rows = []
    for row in cal:
        cid = str(row["CID"]).strip()
        if cid not in seen:
            seen.add(cid)
            unique_rows.append(row)

    print(f"Kalibrator-Zeilen: {len(cal)}")
    print(f"Eindeutige CIDs:   {len(unique_rows)}")

    # Originalen FITS-Katalog einlesen. Seine Spalten heißen z, ra, dec, weight.
    sdss = Table.read(SDSS, format="fits")
    for col in ("ra", "dec", "z"):
        if col not in sdss.colnames:
            raise ValueError(f"SDSS-Spalte fehlt: {col}")

    ra = np.asarray(sdss["ra"], dtype=float)
    dec = np.asarray(sdss["dec"], dtype=float)
    z = np.asarray(sdss["z"], dtype=float)

    valid = (
        np.isfinite(ra)
        & np.isfinite(dec)
        & np.isfinite(z)
        & (dec >= -90.0)
        & (dec <= 90.0)
    )
    ra, dec, z = ra[valid] % 360.0, dec[valid], z[valid]

    print(f"SDSS-Katalogzeilen: {len(sdss)}")
    print(f"Verwendbare Objekte: {len(ra)}")

    # Bestehende Maske ausschließlich laden; keine Pipeline wird ausgeführt.
    with open(MASK, "rb") as f:
        mask_data = pickle.load(f)

    mask = np.asarray(mask_data[0], dtype=bool)
    resolution = float(mask_data[1])
    dist_limits = mask_data[2]

    print(f"Maskenform: {mask.shape}")
    print(f"Maskenauflösung: {resolution}")
    print(f"Masken-Distanzgrenzen: {dist_limits}")

    # Katalogkoordinaten einmalig vorbereiten.
    sdss_coords = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    results = []
    for row in unique_rows:
        cid = str(row["CID"]).strip()
        sn_ra = float(row["RA"])
        sn_dec = float(row["DEC"])
        sn_z = float(row["zHD"])

        # Winkel-Bin entsprechend dem VAST-Maskenraster.
        # Die Maske hat 360/resolution RA-Bins und 180/resolution Dec-Bins.
        ra_bin = int((sn_ra % 360.0) / resolution)
        dec_bin = int((sn_dec + 90.0) / resolution)

        if (
            0 <= ra_bin < mask.shape[0]
            and 0 <= dec_bin < mask.shape[1]
        ):
            mask_value = bool(mask[ra_bin, dec_bin])
        else:
            mask_value = None

        # Wichtig: rein angularer Match über den gesamten gültigen Katalog.
        # Es findet KEIN vorheriger Redshift-Filter statt.
        sn_coord = SkyCoord(
            ra=sn_ra * u.deg, dec=sn_dec * u.deg, frame="icrs"
        )
        nearest_idx, sep2d, _ = sn_coord.match_to_catalog_sky(sdss_coords)

        nearest_ra = float(ra[nearest_idx])
        nearest_dec = float(dec[nearest_idx])
        nearest_z = float(z[nearest_idx])
        sep_arcsec = float(np.asarray(sep2d.arcsec).item())
        dz = abs(sn_z - nearest_z)

        results.append(
            {
                "cid": cid,
                "sn_ra_deg": sn_ra,
                "sn_dec_deg": sn_dec,
                "sn_zHD": sn_z,
                "mask_ra_bin": ra_bin,
                "mask_dec_bin": dec_bin,
                "mask_value": mask_value,
                "nearest_sdss_ra_deg": nearest_ra,
                "nearest_sdss_dec_deg": nearest_dec,
                "nearest_sdss_z": nearest_z,
                "nearest_sep_arcsec": sep_arcsec,
                "abs_delta_z": dz,
                "within_3_arcsec": sep_arcsec <= 3.0,
            }
        )

    # Ergebnisse als separate CSV speichern.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCSV geschrieben: {OUT}")
    print(f"Kalibratoren ausgewertet: {len(results)}")
    print(
        "Angularer Match <= 3 arcsec: "
        f"{sum(r['within_3_arcsec'] for r in results)} / {len(results)}"
    )
    print("\nEinzelergebnisse:")
    for r in results:
        print(
            f"{r['cid']:<16} "
            f"sep={r['nearest_sep_arcsec']:10.3f}\"  "
            f"z_SN={r['sn_zHD']:.5f}  "
            f"z_SDSS={r['nearest_sdss_z']:.5f}  "
            f"|dz|={r['abs_delta_z']:.5f}  "
            f"mask={r['mask_value']}"
        )


if __name__ == "__main__":
    main()
