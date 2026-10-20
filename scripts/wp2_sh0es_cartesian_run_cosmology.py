


"""Create Cartesian comoving coordinates for the 43 Pantheon+SH0ES calibrators.

Run from the VOIDHzero repository root:
    python scripts/wp2_sh0es_cartesian.py

The script imports the distance conversion from the installed VAST VoidFinder
source tree so that the radial convention matches VAST. It never modifies the
input catalogs or reference VoidFinder outputs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PANTHEON = REPO / "Pantheon+SH0ES.dat"
OUT = REPO / "data" / "external" / "wp2_sh0es_calibrator_xyz_om0315_h0674.csv"
VAST_SRC = Path("/home/pctu/voidh0-linux-work/VAST/python")

OMEGA_M = 0.315
H = 0.674
Z_COLUMN = "zHD"  # Explicitly recorded in output; change only if project convention requires it.


def load_vast_distance_function():
    """Import VAST's own z_to_comoving_dist without reimplementing its cosmology."""
    if str(VAST_SRC) not in sys.path:
        sys.path.insert(0, str(VAST_SRC))
    try:
        from vast.voidfinder.distance import z_to_comoving_dist  # type: ignore
        return z_to_comoving_dist
    except ImportError:
        pass

    # Locate the actual definition if it lives in a different VAST module.
    import importlib
    import pkgutil
    import vast.voidfinder as vf

    for modinfo in pkgutil.iter_modules(vf.__path__, vf.__name__ + "."):
        try:
            module = importlib.import_module(modinfo.name)
        except Exception:
            continue
        func = getattr(module, "z_to_comoving_dist", None)
        if callable(func):
            return func
    raise ImportError(
        "Could not import VAST's z_to_comoving_dist. Confirm VAST source path "
        "and function location with: grep -R -n 'def z_to_comoving_dist' "
        "/home/pctu/VAST-v1.3.0/python/vast"
    )


def main() -> None:
    if not PANTHEON.exists():
        raise FileNotFoundError(f"Pantheon input not found: {PANTHEON}")
    if not VAST_SRC.exists():
        raise FileNotFoundError(f"VAST source directory not found: {VAST_SRC}")

    # Pantheon+SH0ES.dat is whitespace-delimited, with a header row.
    data = pd.read_csv(PANTHEON, sep=r"\s+", comment="#", low_memory=False)
    required = {"CID", "IS_CALIBRATOR", "RA", "DEC", Z_COLUMN}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required Pantheon columns: {sorted(missing)}")

    data["IS_CALIBRATOR"] = pd.to_numeric(data["IS_CALIBRATOR"], errors="coerce")
    cal = data.loc[data["IS_CALIBRATOR"] == 1].copy()
    cal["CID"] = cal["CID"].astype(str).str.strip()
    cal = cal.drop_duplicates(subset="CID", keep="first")

    if len(cal) != 43:
        raise ValueError(
            f"Expected 43 unique calibrator CIDs, found {len(cal)}. "
            "No output was written; inspect IS_CALIBRATOR and CID values."
        )

    for col in ["RA", "DEC", Z_COLUMN]:
        cal[col] = pd.to_numeric(cal[col], errors="coerce")
    if cal[["RA", "DEC", Z_COLUMN]].isna().any().any():
        bad = cal.loc[cal[["RA", "DEC", Z_COLUMN]].isna().any(axis=1), "CID"].tolist()
        raise ValueError(f"Invalid RA/DEC/{Z_COLUMN} for CIDs: {bad}")
    if not cal["RA"].between(0, 360, inclusive="left").all():
        raise ValueError("RA values must be in [0, 360) degrees.")
    if not cal["DEC"].between(-90, 90, inclusive="both").all():
        raise ValueError("DEC values must be in [-90, 90] degrees.")
    if (cal[Z_COLUMN] < 0).any():
        raise ValueError("Negative redshift encountered; refusing to write output.")

    z_to_comoving_dist = load_vast_distance_function()
    # VAST's preprocessing calls this function with float32 redshifts and
    # the same Omega_M/h settings as the reference run.
    z = cal[Z_COLUMN].to_numpy(dtype=np.float32)
    r = np.asarray(z_to_comoving_dist(z, OMEGA_M, H), dtype=float).reshape(-1)

    if len(r) != len(cal) or not np.isfinite(r).all() or (r < 0).any():
        raise ValueError("VAST returned invalid comoving distances; no output written.")

    ra_rad = np.deg2rad(cal["RA"].to_numpy(dtype=float))
    dec_rad = np.deg2rad(cal["DEC"].to_numpy(dtype=float))
    x = r * np.cos(ra_rad) * np.cos(dec_rad)
    y = r * np.sin(ra_rad) * np.cos(dec_rad)
    zz = r * np.sin(dec_rad)

    out = pd.DataFrame({
        "CID": cal["CID"].to_numpy(),
        "IS_CALIBRATOR": cal["IS_CALIBRATOR"].astype(int).to_numpy(),
        "RA_deg": cal["RA"].to_numpy(dtype=float),
        "DEC_deg": cal["DEC"].to_numpy(dtype=float),
        "redshift_column": Z_COLUMN,
        "redshift": cal[Z_COLUMN].to_numpy(dtype=float),
        "r_comoving_Mpc": r,
        "x_Mpc": x,
        "y_Mpc": y,
        "z_Mpc": zz,
        "Omega_M": OMEGA_M,
        "h": H,
        "distance_convention": "VAST z_to_comoving_dist; comoving",
    })

    # Final invariants before writing.
    if len(out) != 43 or out["CID"].nunique() != 43:
        raise AssertionError("Output must contain exactly 43 unique CIDs.")
    if not np.allclose(
        np.sqrt(out["x_Mpc"]**2 + out["y_Mpc"]**2 + out["z_Mpc"]**2),
        out["r_comoving_Mpc"],
        rtol=1e-10, atol=1e-10,
    ):
        raise AssertionError("XYZ norm does not match radial distance.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, float_format="%.10g")
    print(f"Wrote {len(out)} unique calibrators to: {OUT}")
    print(f"Redshift column: {Z_COLUMN}; Omega_M={OMEGA_M}; h={H}")
    print(out[["CID", "r_comoving_Mpc", "x_Mpc", "y_Mpc", "z_Mpc"]].head().to_string(index=False))


if __name__ == "__main__":
    main()
