#!/usr/bin/env python3
"""Diagnose der Winkel-/Radialabdeckung und SDSS-Nachbarschaft für Pantheon+SH0ES."""

from pathlib import Path
import pickle
import sys

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]

PANTHEON = ROOT / "Pantheon+SH0ES.dat"
SDSS = Path(
    "/home/pctu/vast-voidfinder/data/reference/"
    "sdss_dr7/vollim_dr7_cbp_102709.fits"
)
MASK_FILE = Path(
    "/home/pctu/vast-voidfinder/results/reference_sdss_dr7/"
    "vollim_dr7_cbp_102709_mask.pickle"
)
OUT = ROOT / "results" / "wp2_coverage_diagnostic.csv"

# Dieselben Parameter wie in der bestehenden VAST-Referenzkonfiguration.
OMEGA_M = 0.26
H = 1.0
Z_MIN = 0.0
Z_MAX = 0.1026

# Die Datei liegt im separaten VAST-Quellbaum.
VAST_PYTHON = Path("/home/pctu/VAST-v1.3.0/python")
sys.path.insert(0, str(VAST_PYTHON))


def load_pantheon():
    """Liest Pantheon+SH0ES und dedupliziert nach CID."""
    df = pd.read_csv(PANTHEON, sep=r"\s+", comment="#")

    required = {"CID", "zHD", "RA", "DEC", "IS_CALIBRATOR"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Fehlende Pantheon-Spalten: {sorted(missing)}")

    df = df[df["IS_CALIBRATOR"].astype(str).str.lower().isin(
        {"1", "true", "t"}
    )].copy()

    # HOST_RA/HOST_DEC sind in der aktuellen Datei Platzhalter (-999).
    # Daher werden hier die SN-Positionen RA/DEC verwendet.
    df = df.drop_duplicates(subset="CID", keep="first").copy()
    df["RA"] = pd.to_numeric(df["RA"], errors="coerce")
    df["DEC"] = pd.to_numeric(df["DEC"], errors="coerce")
    df["zHD"] = pd.to_numeric(df["zHD"], errors="coerce")
    df = df.dropna(subset=["RA", "DEC", "zHD"])
    return df


def load_mask():
    with MASK_FILE.open("rb") as f:
        loaded = pickle.load(f)

    if not isinstance(loaded, tuple) or len(loaded) != 3:
        raise ValueError("Unerwartetes Maskenformat; erwartet wird (mask, resolution, dist_limits).")

    mask, resolution, dist_limits = loaded
    mask = np.asarray(mask, dtype=bool)
    resolution = int(resolution)
    dist_limits = np.asarray(dist_limits, dtype=float)

    if mask.ndim != 2 or len(dist_limits) != 2:
        raise ValueError("Ungültige Maskenform oder dist_limits.")

    return mask, resolution, dist_limits


def comoving_distance_mpc_h(z_values):
    """Verwendet nach Möglichkeit exakt VASTs eigene Distanzfunktion."""
    try:
        from vast.voidfinder.distance import z_to_comoving_dist
        z32 = np.asarray(z_values, dtype=np.float32)
        return np.asarray(
            z_to_comoving_dist(z32, OMEGA_M, H), dtype=float
        )
    except Exception as exc:
        raise RuntimeError(
            "VASTs z_to_comoving_dist konnte nicht importiert/ausgeführt "
            "werden. Bitte VASTs Python-Umgebung aktivieren; es wird "
            "bewusst keine Ersatzkosmologie verwendet."
        ) from exc


def angular_mask_check(ra_deg, dec_deg, mask, resolution):
    """Prüft die RA/Dec-Maskenzelle nach dem Raster von generate_mask()."""
    ra = float(ra_deg) % 360.0
    dec = float(dec_deg)

    if not (-90.0 <= dec <= 90.0):
        return False, None, None

    i_ra = int(np.floor(ra * resolution))
    i_dec = int(np.floor((dec + 90.0) * resolution))

    # Die Indizes müssen innerhalb der tatsächlichen Maske liegen.
    if not (0 <= i_ra < mask.shape[0] and 0 <= i_dec < mask.shape[1]):
        return False, i_ra, i_dec

    return bool(mask[i_ra, i_dec]), i_ra, i_dec


def main():
    for path in (PANTHEON, SDSS, MASK_FILE):
        if not path.exists():
            raise FileNotFoundError(path)

    pantheon = load_pantheon()
    mask, resolution, dist_limits = load_mask()

    with fits.open(SDSS, memmap=True) as hdul:
        table = hdul[1].data
        names = {name.lower(): name for name in table.names}
        for col in ("ra", "dec", "z"):
            if col not in names:
                raise ValueError(f"SDSS-FITS-Spalte fehlt: {col}")

        sdss_ra = np.asarray(table[names["ra"]], dtype=float)
        sdss_dec = np.asarray(table[names["dec"]], dtype=float)
        sdss_z = np.asarray(table[names["z"]], dtype=float)

    good = (
        np.isfinite(sdss_ra)
        & np.isfinite(sdss_dec)
        & np.isfinite(sdss_z)
        & (sdss_dec >= -90)
        & (sdss_dec <= 90)
    )
    sdss_ra, sdss_dec, sdss_z = (
        sdss_ra[good], sdss_dec[good], sdss_z[good]
    )

    sdss_coords = SkyCoord(
        ra=sdss_ra * u.deg, dec=sdss_dec * u.deg, frame="icrs"
    )

    sn_dist = comoving_distance_mpc_h(pantheon["zHD"].to_numpy())

    rows = []
    for (_, sn), radial_distance in zip(pantheon.iterrows(), sn_dist):
        ra = float(sn["RA"]) % 360.0
        dec = float(sn["DEC"])
        z_sn = float(sn["zHD"])

        angular_covered, ra_bin, dec_bin = angular_mask_check(
            ra, dec, mask, resolution
        )

        radial_covered = bool(
            np.isfinite(radial_distance)
            and dist_limits[0] <= radial_distance <= dist_limits[1]
        )

        # Nächster Katalogeintrag nur nach Winkelabstand, ohne z-Vorfilter.
        sn_coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
        nearest_idx, sep2d, _ = sn_coord.match_to_catalog_sky(sdss_coords)

        nearest_idx = int(np.asarray(nearest_idx).reshape(-1)[0])
        nearest_sep_arcsec = float(np.asarray(sep2d.arcsec).reshape(-1)[0])
        nearest_z = float(sdss_z[nearest_idx])



        if angular_covered and radial_covered:
            status = "mask_angular_and_radial_covered"
        elif not angular_covered and not radial_covered:
            status = "outside_angular_mask_and_radial_limits"
        elif not angular_covered:
            status = "outside_angular_mask"
        else:
            status = "outside_radial_limits"

        rows.append({
            "CID": str(sn["CID"]),
            "sn_ra_deg": ra,
            "sn_dec_deg": dec,
            "zHD": z_sn,
            "sn_comoving_distance_mpc_h": float(radial_distance),
            "mask_angular_coverage": angular_covered,
            "mask_ra_bin": ra_bin,
            "mask_dec_bin": dec_bin,
            "radial_coverage": radial_covered,
            "radial_min_mpc_h": float(dist_limits[0]),
            "radial_max_mpc_h": float(dist_limits[1]),
            "nearest_sdss_sep_arcsec": nearest_sep_arcsec,
            "nearest_sdss_ra_deg": float(sdss_ra[nearest_idx]),
            "nearest_sdss_dec_deg": float(sdss_dec[nearest_idx]),
            "nearest_sdss_z": nearest_z,
            "nearest_sdss_dz": abs(nearest_z - z_sn),
            "coverage_status": status,
        })

    result = pd.DataFrame(rows).sort_values("CID")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)

    print(f"Pantheon-Kalibratoren (eindeutige CID): {len(result)}")
    print(f"SDSS-Katalogobjekte: {len(sdss_ra)}")
    print(f"Maskenform: {mask.shape}; Auflösung: {resolution}")
    print(f"Radialgrenzen (Mpc/h): {dist_limits.tolist()}")
    print("\ncoverage_status:")
    print(result["coverage_status"].value_counts(dropna=False).to_string())
    print("\nMaskenabdeckung:")
    print(result["mask_angular_coverage"].value_counts(dropna=False).to_string())
    print("\nRadialabdeckung:")
    print(result["radial_coverage"].value_counts(dropna=False).to_string())
    print(f"\nCSV geschrieben: {OUT}")


if __name__ == "__main__":
    main()
