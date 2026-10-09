#!/usr/bin/env python3

"""
Read-only audit of NED position measurements against SIMBAD coordinates
for the SH0ES host reference table.

The audit deliberately keeps source_host and normalized_query_name separate:

    source_host            -> internal/source identifier
    normalized_query_name  -> name sent to SIMBAD and NED

No resolver assignments are modified by this script.
"""

import argparse
import csv
import math
import statistics
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from astroquery.simbad import Simbad


DEFAULT_INPUT = Path(
    "data/external/wp2_sh0es_host_reference.csv"
)

DEFAULT_OUTPUT = Path(
    "data/external/wp2_ned_position_audit.csv"
)

DEFAULT_RAW_DIR = Path(
    "data/external/ned_position_audit_raw"
)

NED_POSITIONS_URL = (
    "https://ned.ipac.caltech.edu/"
    "NED::API/PositionsOfObject"
)


def get_simbad_coordinate(query_name: str):
    simbad = Simbad()

    simbad.add_votable_fields(
        "main_id",
        "coo_bibcode",
    )

    result = simbad.query_object(query_name)

    if result is None or len(result) == 0:
        raise RuntimeError(
            f"SIMBAD returned no result for "
            f"normalized_query_name={query_name}"
        )

    row = result[0]

    ra = float(row["ra"])
    dec = float(row["dec"])

    main_id = str(row["main_id"])

    bibcode = row["coo_bibcode"]

    if bibcode is None:
        bibcode = ""
    else:
        bibcode = str(bibcode)

    return (
        ra,
        dec,
        main_id,
        bibcode,
    )


def fetch_ned_positions(
    query_name: str,
    raw_path: Path,
    timeout: int,
    retries: int,
):
    encoded_name = urllib.parse.quote(
        query_name,
        safe="",
    )

    url = (
        f"{NED_POSITIONS_URL}"
        f"?TARGET={encoded_name}"
    )

    raw_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    last_error = None

    for attempt in range(
        1,
        retries + 1,
    ):
        try:
            command = [
                "curl",
                "-sS",
                "--connect-timeout",
                "10",
                "--max-time",
                str(timeout),
                "-o",
                str(raw_path),
                "-w",
                "%{http_code}",
                url,
            ]

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            http_code = completed.stdout.strip()

            if (
                completed.returncode == 0
                and http_code == "200"
                and raw_path.exists()
                and raw_path.stat().st_size > 0
            ):
                return

            stderr = (
                completed.stderr.strip()
            )

            last_error = RuntimeError(
                "NED request failed: "
                f"attempt={attempt}, "
                f"http_code={http_code!r}, "
                f"returncode={completed.returncode}, "
                f"stderr={stderr!r}"
            )

        except Exception as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(5)

    raise RuntimeError(
        f"NED request failed after "
        f"{retries} attempts for "
        f"normalized_query_name={query_name}"
    ) from last_error


def parse_ned_positions(
    xml_path: Path,
):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rows = []

    for tr in root.iter():
        if not tr.tag.endswith("TR"):
            continue

        cells = [
            td.text.strip()
            if td.text is not None
            else None
            for td in tr
            if td.tag.endswith("TD")
        ]


        if len(cells) < 10:
            continue

        try:
            ra = float(cells[3])
            dec = float(cells[4])
        except (
            TypeError,
            ValueError,
        ):
            continue

        reference = cells[8]

        if reference is None:
            reference = ""

        fiducial = cells[9]

        rows.append(
            {
                "ra": ra,
                "dec": dec,
                "reference": reference,
                "fiducial": (
                    str(fiducial).lower()
                    in ("true", "1")
                ),
            }
        )

    return rows


def separation_arcsec(
    ra1_deg: float,
    dec1_deg: float,
    ra2_deg: float,
    dec2_deg: float,
):
    ra1 = math.radians(ra1_deg)
    dec1 = math.radians(dec1_deg)
    ra2 = math.radians(ra2_deg)
    dec2 = math.radians(dec2_deg)

    delta_ra = ra2 - ra1
    delta_dec = dec2 - dec1

    a = (
        math.sin(delta_dec / 2.0) ** 2
        + math.cos(dec1)
        * math.cos(dec2)
        * math.sin(delta_ra / 2.0) ** 2
    )

    a = min(
        1.0,
        max(0.0, a),
    )

    return (
        2.0
        * math.asin(math.sqrt(a))
        * 206264.80624709636
    )


def audit_host(
    source_host: str,
    query_name: str,
    raw_path: Path,
    timeout: int,
    retries: int,
):
    (
        simbad_ra,
        simbad_dec,
        simbad_main_id,
        simbad_bibcode,
    ) = get_simbad_coordinate(
        query_name
    )

    fetch_ned_positions(
        query_name=query_name,
        raw_path=raw_path,
        timeout=timeout,
        retries=retries,
    )

    positions = parse_ned_positions(
        raw_path
    )

    if not positions:
        raise RuntimeError(
            "NED response contained no usable "
            "position records"
        )

    for position in positions:
        position["separation_arcsec"] = (
            separation_arcsec(
                simbad_ra,
                simbad_dec,
                position["ra"],
                position["dec"],
            )
        )

    separations = [
        position["separation_arcsec"]
        for position in positions
    ]

    fiducial_positions = [
        position
        for position in positions
        if position["fiducial"]
    ]

    if len(fiducial_positions) == 1:
        fiducial = fiducial_positions[0]

        fiducial_separation = (
            fiducial["separation_arcsec"]
        )

        fiducial_reference = (
            fiducial["reference"]
        )

    elif len(fiducial_positions) > 1:
        fiducial_separation = min(
            position["separation_arcsec"]
            for position in fiducial_positions
        )

        references = sorted(
            {
                position["reference"]
                for position in fiducial_positions
            }
        )

        fiducial_reference = (
            "MULTIPLE: "
            + "; ".join(references)
        )

    else:
        fiducial_separation = ""
        fiducial_reference = ""

    return {
        "source_host": source_host,
        "normalized_query_name": query_name,
        "SIMBAD_main_id": simbad_main_id,
        "SIMBAD_RA_deg": simbad_ra,
        "SIMBAD_DEC_deg": simbad_dec,
        "SIMBAD_coordinate_bibcode": simbad_bibcode,
        "NED_position_count": len(
            positions
        ),
        "NED_min_separation_arcsec": min(
            separations
        ),
        "NED_median_separation_arcsec": (
            statistics.median(separations)
        ),
        "NED_max_separation_arcsec": max(
            separations
        ),
        "NED_count_le_0.1_arcsec": sum(
            value <= 0.1
            for value in separations
        ),
        "NED_count_le_0.5_arcsec": sum(
            value <= 0.5
            for value in separations
        ),
        "NED_count_le_1.0_arcsec": sum(
            value <= 1.0
            for value in separations
        ),
        "NED_count_le_2.0_arcsec": sum(
            value <= 2.0
            for value in separations
        ),
        "NED_fiducial_count": len(
            fiducial_positions
        ),
        "NED_fiducial_separation_arcsec": (
            fiducial_separation
        ),
        "NED_fiducial_reference": (
            fiducial_reference
        ),
        "audit_status": "resolved",
        "audit_note": "",
    }


def load_hosts(input_path: Path):
    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        required = {
            "source_host",
            "normalized_query_name",
        }

        missing = required - set(
            reader.fieldnames or []
        )

        if missing:
            raise ValueError(
                "Input is missing required columns: "
                + ", ".join(sorted(missing))
            )

        hosts = []

        for row in reader:
            source_host = (
                row["source_host"].strip()
            )

            query_name = (
                row["normalized_query_name"]
                .strip()
            )

            if not source_host:
                continue

            if not query_name:
                raise ValueError(
                    "Empty normalized_query_name "
                    f"for source_host={source_host}"
                )

            hosts.append(
                (
                    source_host,
                    query_name,
                )
            )

    unique_hosts = []

    seen = set()

    for source_host, query_name in hosts:
        if source_host in seen:
            continue

        seen.add(source_host)

        unique_hosts.append(
            (
                source_host,
                query_name,
            )
        )

    return unique_hosts


def write_output(
    output_path: Path,
    rows,
):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "source_host",
        "normalized_query_name",
        "SIMBAD_main_id",
        "SIMBAD_RA_deg",
        "SIMBAD_DEC_deg",
        "SIMBAD_coordinate_bibcode",
        "NED_position_count",
        "NED_min_separation_arcsec",
        "NED_median_separation_arcsec",
        "NED_max_separation_arcsec",
        "NED_count_le_0.1_arcsec",
        "NED_count_le_0.5_arcsec",
        "NED_count_le_1.0_arcsec",
        "NED_count_le_2.0_arcsec",
        "NED_fiducial_count",
        "NED_fiducial_separation_arcsec",
        "NED_fiducial_reference",
        "audit_status",
        "audit_note",
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit of NED position "
            "measurements against SIMBAD coordinates."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            "SH0ES host reference CSV "
            f"(default: {DEFAULT_INPUT})"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Audit output CSV "
            f"(default: {DEFAULT_OUTPUT})"
        ),
    )

    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=(
            "Directory for raw NED XML "
            f"(default: {DEFAULT_RAW_DIR})"
        ),
    )

    parser.add_argument(
        "--pause",
        type=float,
        default=2.0,
        help=(
            "Pause between hosts in seconds "
            "(default: 2.0)"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help=(
            "NED request timeout in seconds "
            "(default: 60)"
        ),
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help=(
            "NED request attempts per host "
            "(default: 3)"
        ),
    )

    args = parser.parse_args()

    hosts = load_hosts(
        args.input
    )

    print(
        f"Unique hosts to audit: {len(hosts)}"
    )

    rows = []

    for index, (
        source_host,
        query_name,
    ) in enumerate(
        hosts,
        start=1,
    ):
        print(
            f"[{index:02d}/{len(hosts):02d}] "
            f"{source_host} "
            f"-> {query_name}"
        )

        safe_name = (
            source_host.replace(" ", "_")
            .replace("/", "_")
        )

        raw_path = (
            args.raw_dir
            / f"{safe_name}.xml"
        )

        try:
            row = audit_host(
                source_host=source_host,
                query_name=query_name,
                raw_path=raw_path,
                timeout=args.timeout,
                retries=args.retries,
            )

            print(
                "  resolved:"
                f" {row['NED_position_count']} "
                "NED positions"
            )

        except Exception as exc:
            row = {
                "source_host": source_host,
                "normalized_query_name": query_name,
                "SIMBAD_main_id": "",
                "SIMBAD_RA_deg": "",
                "SIMBAD_DEC_deg": "",
                "SIMBAD_coordinate_bibcode": "",
                "NED_position_count": "",
                "NED_min_separation_arcsec": "",
                "NED_median_separation_arcsec": "",
                "NED_max_separation_arcsec": "",
                "NED_count_le_0.1_arcsec": "",
                "NED_count_le_0.5_arcsec": "",
                "NED_count_le_1.0_arcsec": "",
                "NED_count_le_2.0_arcsec": "",
                "NED_fiducial_count": "",
                "NED_fiducial_separation_arcsec": "",
                "NED_fiducial_reference": "",
                "audit_status": "pending",
                "audit_note": (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            }

            print(
                "  pending: "
                f"{type(exc).__name__}: {exc}"
            )

        rows.append(row)

        if (
            index < len(hosts)
            and args.pause > 0
        ):
            time.sleep(args.pause)

    write_output(
        args.output,
        rows,
    )

    resolved = sum(
        row["audit_status"] == "resolved"
        for row in rows
    )

    pending = sum(
        row["audit_status"] == "pending"
        for row in rows
    )

    print()
    print("=== Summary ===")
    print(f"resolved: {resolved}")
    print(f"pending: {pending}")
    print(f"total: {len(rows)}")
    print(
        f"Output: {args.output}"
    )
    print(
        f"Raw XML: {args.raw_dir}"
    )


if __name__ == "__main__":
    main()