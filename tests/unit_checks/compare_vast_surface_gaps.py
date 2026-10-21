from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[2]
H = 0.674

SN_FILE = ROOT / "data/external/wp2_sh0es_calibrator_xyz_om0315_h0674.csv"

RUNS = {
    "old_h0674": (
        Path.home()
        / "voidh0-linux-work/vast_sdss_dr7_output"
        / "vollim_dr7_cbp_102709_VoidFinder_Output.fits",
        1.0,
    ),
    "control_h1": (
        Path.home()
        / "voidh0-linux-work/vast_sdss_dr7_output_hinv"
        / "vollim_dr7_cbp_102709_hinv_VoidFinder_Output.fits",
        H,
    ),
}

OUT_FILE = (
    ROOT
    / "data/external/wp2_sh0es_void_surface_gaps_hinv_om0315.csv"
)


def read_spheres(hdul, extension):
    table = hdul[extension].data
    names = {name.lower(): name for name in table.names}

    required = {"x", "y", "z", "radius"}
    missing = required - set(names)
    if missing:
        raise ValueError(
            f"{extension}: fehlende FITS-Spalten: {sorted(missing)}"
        )

    xyz = np.column_stack([
        np.asarray(table[names[axis]], dtype=float)
        for axis in ("x", "y", "z")
    ])
    radii = np.asarray(table[names["radius"]], dtype=float)

    if "void" in names:
        ids = np.asarray(table[names["void"]])
    else:
        ids = np.arange(len(radii))

    valid = (
        np.isfinite(xyz).all(axis=1)
        & np.isfinite(radii)
        & (radii > 0)
    )
    return xyz[valid], radii[valid], ids[valid]


def closest_surface(point, centers, radii, ids):
    # Abstand zur Oberfläche jeder Kugel:
    # negativ = innerhalb, positiv = außerhalb.
    gaps = np.linalg.norm(centers - point, axis=1) - radii

    # Nächstgelegene Kugeloberfläche: Abstand mit kleinstem Absolutbetrag.
    # Bei mehreren Treffern nicht den tiefsten negativen Abstand wählen.
    i = int(np.argmin(np.abs(gaps)))

    # Separat den stärksten negativen Abstand für die Geometrie-Diagnostik.
    deepest_i = int(np.argmin(gaps))

    return {
        "signed_gap_native": float(gaps[i]),
        "closest_boundary_sphere_id": str(ids[i]),
        "closest_boundary_center_distance_native": float(
            np.linalg.norm(centers[i] - point)
        ),
        "closest_boundary_radius_native": float(radii[i]),
        "most_negative_gap_native": float(gaps[deepest_i]),
        "most_negative_sphere_id": str(ids[deepest_i]),
        "inside_any_sphere": bool(np.any(gaps <= 0)),
        "number_of_containing_spheres": int(np.sum(gaps <= 0)),
    }


def main():
    if not SN_FILE.exists():
        raise FileNotFoundError(f"SN-Datei nicht gefunden: {SN_FILE}")

    sn = pd.read_csv(SN_FILE)
    required = {"CID", "x_Mpc", "y_Mpc", "z_Mpc"}
    missing = required - set(sn.columns)
    if missing:
        raise ValueError(f"SN-Datei: fehlende Spalten: {sorted(missing)}")

    if sn["CID"].duplicated().any():
        raise ValueError("SN-Datei enthält doppelte CIDs.")

    results = []

    for run_name, (fits_path, sn_scale) in RUNS.items():
        if not fits_path.exists():
            raise FileNotFoundError(f"FITS-Datei nicht gefunden: {fits_path}")

        print(f"\nLese {run_name}: {fits_path}")

        with fits.open(fits_path, memmap=True) as hdul:
            for kind in ("MAXIMALS", "HOLES"):
                centers, radii, ids = read_spheres(hdul, kind)
                print(f"  {kind}: {len(radii)} Kugeln")

                for row in sn.itertuples(index=False):
                    # Alte Geometrie: SN-Koordinaten in Mpc.
                    # Kontrolllauf: SN-Koordinaten * h, passend
                    # zur numerischen Skala des h=1-Laufs.
                    point = np.array(
                        [row.x_Mpc, row.y_Mpc, row.z_Mpc],
                        dtype=float,
                    ) * sn_scale

                    nearest = closest_surface(point, centers, radii, ids)

                    # Native Längeneinheiten sind im alten Lauf
                    # nominell Mpc und im Kontrolllauf Mpc/h.
                    # Für einen größenordnungsmäßigen Vergleich
                    # rechnen wir beide Abstände in physische Mpc um.
                    native_to_mpc = 1.0 / sn_scale

                    results.append({
                        "CID": row.CID,
                        "run": run_name,
                        "sphere_type": kind,
                        "n_spheres": len(radii),
                        **nearest,
                        "signed_gap_Mpc": (
                            nearest["signed_gap_native"] * native_to_mpc
                        ),
                        "abs_gap_Mpc": (
                            abs(nearest["signed_gap_native"])
                            * native_to_mpc
                        ),
                    })

    out = pd.DataFrame(results)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False)

    print("\n=== Mitgliedschaftswechsel ===")
    membership = out.pivot(
        index=["CID", "sphere_type"],
        columns="run",
        values="inside_any_sphere",
    ).reset_index()

    changed = membership[
        membership["old_h0674"] != membership["control_h1"]
    ]
    if changed.empty:
        print("Keine Änderungen gefunden.")
    else:
        print(changed.to_string(index=False))

    print("\n=== Drei besonders wichtige CIDs ===")
    focus = {"2003du", "2005cf", "2012ht"}
    cols = [
        "CID", "run", "sphere_type", "inside_any_sphere",
        "number_of_containing_spheres", "signed_gap_Mpc",
        "closest_boundary_sphere_id",
    ]
    print(
        out[out["CID"].astype(str).isin(focus)][cols]
        .sort_values(["CID", "sphere_type", "run"])
        .to_string(index=False)
    )

    print("\n=== Kleinste Abstände zur Kugeloberfläche ===")
    print(
        out.sort_values("abs_gap_Mpc")
        .groupby(["run", "sphere_type"], as_index=False)
        .head(10)[cols]
        .to_string(index=False)
    )

    print(f"\nDatei geschrieben: {OUT_FILE}")


if __name__ == "__main__":
    main()
