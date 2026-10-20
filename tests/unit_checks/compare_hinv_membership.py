from pathlib import Path
import numpy as np
import pandas as pd
from astropy.io import fits

ROOT = Path.home() / "voidh0-linux-work"
PROJECT = ROOT / "VOIDHzero"
H = 0.674

SN_FILE = PROJECT / "data/external/wp2_sh0es_calibrator_xyz_om0315_h0674.csv"
FITS_FILE = ROOT / "vast_sdss_dr7_output_unitfix/vollim_dr7_cbp_102709_unitfix_VoidFinder_Output.fits"
OUT_FILE = PROJECT / "data/external/wp2_sh0es_void_membership_unitfix_om0315.csv"


def col(df, candidates, context):
    names = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in names:
            return names[candidate.lower()]
    raise ValueError(f"{context}: benötigte Spalte fehlt. Vorhanden: {list(df.columns)}")


def xyz(df, context):
    columns = [
        col(df, [axis, f"{axis}_Mpc"], f"{context}.{axis}")
        for axis in ("x", "y", "z")
    ]
    return df[columns].to_numpy(dtype=float)


def load_spheres(hdul, extension):
    df = pd.DataFrame(hdul[extension].data)
    df.columns = [str(c).strip() for c in df.columns]

    coords = xyz(df, extension)
    radii = df[col(df, ["radius"], f"{extension}.radius")].to_numpy(dtype=float)
    id_column = col(df, ["void", "void_id", "id"], f"{extension}.ID")
    ids = df[id_column].astype(str).to_numpy()

    valid = np.isfinite(coords).all(axis=1) & np.isfinite(radii) & (radii > 0)
    return coords[valid], radii[valid], ids[valid]


def main():
    for path in (SN_FILE, FITS_FILE):
        if not path.exists():
            raise FileNotFoundError(path)

    sn = pd.read_csv(SN_FILE)
    sn.columns = [str(c).strip() for c in sn.columns]
    cid_col = col(sn, ["CID", "SN", "SNID"], "Supernova-ID")
    if sn[cid_col].duplicated().any():
        raise ValueError("Doppelte Supernova-IDs in der Eingabedatei.")

    # Eingabekoordinaten sind physikalische Mpc.
    # Die h=1-Void-Koordinaten werden numerisch in h^-1 Mpc interpretiert.
    sn_coords = xyz(sn, "SN-CSV") * H

    with fits.open(FITS_FILE, memmap=True) as hdul:
        max_coords, max_radii, max_ids = load_spheres(hdul, "MAXIMALS")
        hole_coords, hole_radii, hole_ids = load_spheres(hdul, "HOLES")

    print(f"Kalibratoren: {len(sn)}")
    print(f"MAXIMALS-Kugeln: {len(max_radii)}")
    print(f"HOLES-Kugeln: {len(hole_radii)}")
    print(f"SN-Koordinatenskalierung: {H}")

    rows = []
    for i, row in sn.reset_index(drop=True).iterrows():
        point = sn_coords[i]
        dmax = np.linalg.norm(max_coords - point, axis=1)
        dhole = np.linalg.norm(hole_coords - point, axis=1)
        in_max = dmax <= max_radii
        in_holes = dhole <= hole_radii

        max_matches = sorted(set(max_ids[in_max]))
        hole_matches = sorted(set(hole_ids[in_holes]))

        rows.append({
            "CID": str(row[cid_col]),
            "x_hinv_Mpc": point[0],
            "y_hinv_Mpc": point[1],
            "z_hinv_Mpc": point[2],
            "n_maximal_spheres": int(in_max.sum()),
            "maximal_void_ids": ";".join(max_matches),
            "n_hole_spheres": int(in_holes.sum()),
            "hole_void_ids": ";".join(hole_matches),
            "inside_any_maximal": bool(in_max.any()),
            "inside_any_hole": bool(in_holes.any()),
            "inside_any_sphere": bool(in_max.any() or in_holes.any()),
        })

    result = pd.DataFrame(rows)
    result.to_csv(OUT_FILE, index=False)

    nmax = int(result["inside_any_maximal"].sum())
    nhole = int(result["inside_any_hole"].sum())
    nany = int(result["inside_any_sphere"].sum())
    n_multi = int((
        result["n_maximal_spheres"].gt(1)
        | result["n_hole_spheres"].gt(1)
    ).sum())

    print("\n=== Ergebnisse ===")
    print(f"In mindestens einer MAXIMALS-Kugel: {nmax}")
    print(f"In mindestens einer HOLES-Kugel:    {nhole}")
    print(f"In mindestens einer Kugel insgesamt: {nany}")
    print(f"Außerhalb aller Kugeln:              {len(result) - nany}")
    print(f"Mehrere Treffer innerhalb eines Typs: {n_multi}")
    print(f"Neue CSV: {OUT_FILE}")
    print("\nKalibratoren mit Treffern:")
    hits = result[result["inside_any_sphere"]]
    print(hits[["CID", "maximal_void_ids", "hole_void_ids"]].to_string(index=False))


if __name__ == "__main__":
    main()
