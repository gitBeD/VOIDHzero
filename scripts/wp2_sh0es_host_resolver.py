#!/usr/bin/env python3
"""
Resolve the 37 unique SH0ES host galaxies against SIMBAD and NED.

Design:
- Read the already-validated CID -> source-host table.
- Deduplicate to one row per normalized host query name.
- Query SIMBAD and NED independently, read-only.
- Never silently choose among multiple returned objects.
- Preserve source_host and normalized_query_name separately.
- Write:
    1) one host-level table (37 unique hosts)
    2) one CID-level table (43 Pantheon+ CIDs)
- A host is only marked "resolved_consistent" when both services return
  coordinates and agree within the configurable angular tolerance.
- Any ambiguity, missing result, or disagreement is marked for review.

Requires:
    pip install astroquery

Input columns required:
    CID, source_host, normalized_query_name, status

Expected input:
    data/external/wp2_sh0es_host_reference.csv

Output:
    data/external/wp2_sh0es_host_resolved.csv
    data/external/wp2_sh0es_cid_resolved.csv
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import astropy.units as u
import pandas as pd
from astropy.coordinates import SkyCoord
from astroquery.ipac.ned import Ned
from astroquery.simbad import Simbad


DEFAULT_INPUT = Path("data/external/wp2_sh0es_host_reference.csv")
DEFAULT_HOST_OUTPUT = Path("data/external/wp2_sh0es_host_resolved.csv")
DEFAULT_CID_OUTPUT = Path("data/external/wp2_sh0es_cid_resolved.csv")

# This is deliberately a diagnostic consistency threshold, not a scientific
# host-matching threshold.
COORD_CONSISTENCY_ARCSEC = 1.0
REQUEST_PAUSE_SECONDS = 0.5


def clean_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def extract_simbad(name: str) -> dict:
    try:
        result = Simbad.query_object(name)
    except Exception as exc:
        return {
            "status": "query_error",
            "main_id": "",
            "matched_id": "",
            "ra_deg": None,
            "dec_deg": None,
            "bibcode": "",
            "note": repr(exc),
        }

    if result is None or len(result) == 0:
        return {
            "status": "not_found",
            "main_id": "",
            "matched_id": "",
            "ra_deg": None,
            "dec_deg": None,
            "bibcode": "",
            "note": "",
        }

    if len(result) != 1:
        return {
            "status": "ambiguous",
            "main_id": "; ".join(clean_value(x) for x in result["main_id"]),
            "matched_id": (
                "; ".join(clean_value(x) for x in result["matched_id"])
                if "matched_id" in result.colnames
                else ""
            ),
            "ra_deg": None,
            "dec_deg": None,
            "bibcode": "",
            "note": f"{len(result)} rows returned",
        }

    row = result[0]
    return {
        "status": "resolved",
        "main_id": clean_value(row["main_id"]),
        "matched_id": clean_value(row["matched_id"])
        if "matched_id" in result.colnames
        else "",
        "ra_deg": float(row["ra"]) if row["ra"] is not None else None,
        "dec_deg": float(row["dec"]) if row["dec"] is not None else None,
        "bibcode": clean_value(row["coo_bibcode"])
        if "coo_bibcode" in result.colnames
        else "",
        "note": "",
    }


def extract_ned(name: str) -> dict:
    try:
        result = Ned.query_object(name)
    except Exception as exc:
        return {
            "status": "query_error",
            "object_name": "",
            "ra_deg": None,
            "dec_deg": None,
            "note": repr(exc),
        }

    if result is None or len(result) == 0:
        return {
            "status": "not_found",
            "object_name": "",
            "ra_deg": None,
            "dec_deg": None,
            "note": "",
        }

    # NED's name query can return more than one source row. We do not
    # silently select one. The host is reviewed manually in that case.
    if len(result) != 1:
        names = []
        if "Object Name" in result.colnames:
            names = [clean_value(x) for x in result["Object Name"]]
        return {
            "status": "ambiguous",
            "object_name": "; ".join(names),
            "ra_deg": None,
            "dec_deg": None,
            "note": f"{len(result)} rows returned",
        }

    row = result[0]
    ra_col = next((c for c in ("RA(deg)", "RA") if c in result.colnames), None)
    dec_col = next((c for c in ("DEC(deg)", "DEC") if c in result.colnames), None)

    if ra_col is None or dec_col is None:
        return {
            "status": "no_coordinates",
            "object_name": clean_value(row["Object Name"])
            if "Object Name" in result.colnames
            else "",
            "ra_deg": None,
            "dec_deg": None,
            "note": "coordinate columns not found",
        }

    return {
        "status": "resolved",
        "object_name": clean_value(row["Object Name"])
        if "Object Name" in result.colnames
        else "",
        "ra_deg": float(row[ra_col]),
        "dec_deg": float(row[dec_col]),
        "note": "",
    }


def angular_sep_arcsec(ra1, dec1, ra2, dec2):
    if any(x is None or pd.isna(x) for x in (ra1, dec1, ra2, dec2)):
        return None
    a = SkyCoord(ra1 * u.deg, dec1 * u.deg, frame="icrs")
    b = SkyCoord(ra2 * u.deg, dec2 * u.deg, frame="icrs")
    return float(a.separation(b).arcsec)


def classify(simbad, ned):
    if simbad["status"] != "resolved" or ned["status"] != "resolved":
        return "review_required"

    sep = angular_sep_arcsec(
        simbad["ra_deg"], simbad["dec_deg"],
        ned["ra_deg"], ned["dec_deg"],
    )
    if sep is None:
        return "review_required"
    if sep <= COORD_CONSISTENCY_ARCSEC:
        return "resolved_consistent"
    return "review_required"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--host-output", type=Path, default=DEFAULT_HOST_OUTPUT)
    parser.add_argument("--cid-output", type=Path, default=DEFAULT_CID_OUTPUT)
    parser.add_argument(
        "--pause",
        type=float,
        default=REQUEST_PAUSE_SECONDS,
        help="pause between remote service requests in seconds",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    required = {
        "CID",
        "source_host",
        "normalized_query_name",
        "status",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required input columns: {sorted(missing)}")

    # Only the closed source table is allowed into the resolver.
    ELIGIBLE_STATUSES = ["exact", "alias/normalization", "source_not_in_Riess_Table6"]

    bad_status = df.loc[
    ~df["status"].isin(ELIGIBLE_STATUSES),
    ["CID", "source_host", "status"],
    ]

    if not bad_status.empty:
        raise ValueError(
            "Input contains CIDs that are not eligible for automatic resolution:\n"
            + bad_status.to_string(index=False)
        )

    hosts = (
        df[
            ["source_host", "normalized_query_name"]
        ]
        .drop_duplicates()
        .sort_values(["normalized_query_name", "source_host"])
        .reset_index(drop=True)
    )

    print(f"CID rows: {len(df)}")
    print(f"Unique hosts to resolve: {len(hosts)}")

    simbad = Simbad()
    simbad.add_votable_fields("main_id", "coo_bibcode")

    rows = []

    for i, host in hosts.iterrows():
        source_host = host["source_host"]
        query_name = host["normalized_query_name"]

        print(f"[{i + 1:02d}/{len(hosts):02d}] {source_host} -> {query_name}")

        sim = extract_simbad(query_name)
        time.sleep(args.pause)
        ned = extract_ned(query_name)
        time.sleep(args.pause)

        sep = angular_sep_arcsec(
            sim["ra_deg"], sim["dec_deg"],
            ned["ra_deg"], ned["dec_deg"],
        )

        rows.append(
            {
                "source_host": source_host,
                "normalized_query_name": query_name,
                "SIMBAD_status": sim["status"],
                "SIMBAD_main_id": sim["main_id"],
                "SIMBAD_matched_id": sim["matched_id"],
                "SIMBAD_RA_deg": sim["ra_deg"],
                "SIMBAD_DEC_deg": sim["dec_deg"],
                "SIMBAD_coordinate_bibcode": sim["bibcode"],
                "SIMBAD_note": sim["note"],
                "NED_status": ned["status"],
                "NED_object_name": ned["object_name"],
                "NED_RA_deg": ned["ra_deg"],
                "NED_DEC_deg": ned["dec_deg"],
                "NED_note": ned["note"],
                "SIMBAD_NED_separation_arcsec": sep,
                "resolver_status": classify(sim, ned),
            }
        )

    host_out = pd.DataFrame(rows)

    # SIMBAD coordinates are retained as the machine-readable reference.
    # They are provisional unless SIMBAD and NED agree within tolerance.
    host_out["reference_RA_deg"] = host_out["SIMBAD_RA_deg"]
    host_out["reference_DEC_deg"] = host_out["SIMBAD_DEC_deg"]

    def determine_reference_status(row):
        if row["resolver_status"] == "resolved_consistent":
            return "cross_checked"

        if (
                pd.notna(row["SIMBAD_RA_deg"])
                and pd.notna(row["SIMBAD_DEC_deg"])
        ):
            return "provisional_simbad_only"

        return "unavailable"

    host_out["reference_status"] = host_out.apply(
        determine_reference_status, axis=1
    )

    host_out["reference_source"] = host_out["reference_status"].map(
        {
            "cross_checked": "SIMBAD+NED",
            "provisional_simbad_only": "SIMBAD",
            "unavailable": "",
        }
    )

    args.host_output.parent.mkdir(parents=True, exist_ok=True)
    host_out.to_csv(args.host_output, index=False)

    cid_out = df.merge(
        host_out[
            [
                "source_host",
                "normalized_query_name",
                "SIMBAD_status",
                "SIMBAD_main_id",
                "NED_status",
                "NED_object_name",
                "SIMBAD_RA_deg",
                "SIMBAD_DEC_deg",
                "NED_RA_deg",
                "NED_DEC_deg",
                "SIMBAD_NED_separation_arcsec",
                "resolver_status",
                "reference_RA_deg",
                "reference_DEC_deg",
                "reference_source",
                "reference_status",
            ]
        ],
        on=["source_host", "normalized_query_name"],
        how="left",
        validate="many_to_one",
    )

    cid_out.to_csv(args.cid_output, index=False)

    print("\n=== Summary ===")
    print(host_out["resolver_status"].value_counts(dropna=False).to_string())
    print(f"\nHost output: {args.host_output}")
    print(f"CID output:  {args.cid_output}")


if __name__ == "__main__":
    main()