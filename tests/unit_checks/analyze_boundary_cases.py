from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits

PROJECT = Path.cwd()
ROOT = Path.home() / "voidh0-linux-work"

SN_FILE = PROJECT / "data/external/wp2_sh0es_calibrator_xyz_om0315_h0674.csv"

RUNS = {
    "alt_h0674": {
        "fits": ROOT / (
            "vast_sdss_dr7_output/"
            "vollim_dr7_cbp_102709_VoidFinder_Output.fits"
        ),
        "sn_scale": 1.0,
    },
    "unitfix": {
        "fits": ROOT / (
            "vast_sdss_dr7_output_unitfix/"
            "vollim_dr7_cbp_102709_unitfix_VoidFinder_Output.fits"
        ),
        "sn_scale": 0.674,
    },
}

CIDS = ["2003du", "2005cf", "2012ht"]
OUT = PROJECT / "data/external/wp2_sh0es_boundary_cases_3sn_om0315.csv"

sn = pd.read_csv(SN_FILE, dtype={"CID": str})
sn["CID"] = sn["CID"].str.strip()
sn = sn.set_index("CID")

results = []

for cid in CIDS:
    if cid not in sn.index:
        raise ValueError(f"CID {cid} fehlt in {SN_FILE}")

    row = sn.loc[cid]
    xyz_physical = row[["x_Mpc", "y_Mpc", "z_Mpc"]].to_numpy(dtype=float)

    for run_name, cfg in RUNS.items():
        fits_path = cfg["fits"]
        if not fits_path.exists():
            raise FileNotFoundError(f"FITS-Datei fehlt: {fits_path}")

        # Umrechnung in die jeweilige Koordinateneinheit des Void-Katalogs.
        xyz_sn = xyz_physical * cfg["sn_scale"]

        with fits.open(fits_path, memmap=True) as hdul:
            for sphere_type in ["MAXIMALS", "HOLES"]:
                data = hdul[sphere_type].data

                centers = np.column_stack([
                    np.asarray(data["x"], dtype=float),
                    np.asarray(data["y"], dtype=float),
                    np.asarray(data["z"], dtype=float),
                ])
                radii = np.asarray(data["radius"], dtype=float)
                void_ids = np.asarray(data["void"])

                distances = np.linalg.norm(centers - xyz_sn, axis=1)
                gaps = distances - radii
                inside = gaps <= 0

                # Oberfläche mit dem kleinsten absoluten Abstand.
                nearest_idx = int(np.argmin(np.abs(gaps)))

                # Kleinster signierter Abstand: negativ genau dann,
                # wenn mindestens eine Kugel den Punkt enthält.
                deepest_idx = int(np.argmin(gaps))

                results.append({
                    "CID": cid,
                    "run": run_name,
                    "sphere_type": sphere_type,
                    "n_spheres": len(radii),
                    "n_containing": int(inside.sum()),
                    "inside_any": bool(inside.any()),
                    "min_signed_gap": float(gaps[deepest_idx]),
                    "deepest_gap_void_id": int(void_ids[deepest_idx]),
                    "nearest_surface_gap_abs": float(abs(gaps[nearest_idx])),
                    "nearest_surface_signed_gap": float(gaps[nearest_idx]),
                    "nearest_surface_void_id": int(void_ids[nearest_idx]),
                    "nearest_surface_inside": bool(inside[nearest_idx]),
                    "coordinate_scale": cfg["sn_scale"],
                })

result = pd.DataFrame(results)
result.to_csv(OUT, index=False)

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)

print("=== Grenzfallanalyse ===")
print("SN-Koordinatenquelle:", SN_FILE)
print("Ergebnisdatei:", OUT)
print("Abstände in der jeweiligen FITS-Koordinateneinheit.")
print("Negativer Abstand = innerhalb; positiver Abstand = außerhalb.")
print()
print(result[[
    "CID", "run", "sphere_type", "n_containing",
    "min_signed_gap", "deepest_gap_void_id",
    "nearest_surface_signed_gap", "nearest_surface_void_id",
    "nearest_surface_inside",
]].to_string(index=False, float_format=lambda x: f"{x:.6f}"))
