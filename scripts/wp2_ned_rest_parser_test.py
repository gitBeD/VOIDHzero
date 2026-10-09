#!/usr/bin/env python3

from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


NED_API = (
    "https://ned.ipac.caltech.edu/"
    "NED::API/PositionsOfObject"
)


def query_ned(host: str) -> bytes:
    params = urllib.parse.urlencode({"TARGET": host})
    url = f"{NED_API}?{params}"

    print(f"NED URL: {url}")
    print("Requesting ...")

    with urllib.request.urlopen(url, timeout=20) as response:
        print(f"HTTP status: {response.status}")
        return response.read()


def inspect_votable(xml_bytes: bytes) -> None:
    root = ET.fromstring(xml_bytes)

    print(f"Root tag: {root.tag}")

    # VOTable namespace may vary slightly between versions.
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"

    fields = root.findall(f".//{namespace}FIELD")

    print()
    print(f"FIELD count: {len(fields)}")
    print("Columns:")

    for field in fields:
        name = field.attrib.get("name", "")
        datatype = field.attrib.get("datatype", "")
        unit = field.attrib.get("unit", "")
        print(
            f"  name={name!r} datatype={datatype!r} unit={unit!r}"
        )

    rows = root.findall(f".//{namespace}TABLEDATA/{namespace}TR")

    print()
    print(f"TABLEDATA rows: {len(rows)}")

    if rows:
        print()
        print("First row:")

        cells = rows[0].findall(f"{namespace}TD")

        for index, cell in enumerate(cells):
            value = cell.text.strip() if cell.text else ""
            print(f"  [{index}] {value!r}")


def main() -> int:
    host = "NGC 1365"

    print(f"=== NED REST parser test: {host} ===")
    print()

    try:
        xml_bytes = query_ned(host)
        print(f"Downloaded: {len(xml_bytes)} bytes")
        print()

        inspect_votable(xml_bytes)

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
