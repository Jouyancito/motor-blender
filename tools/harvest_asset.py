#!/usr/bin/env python3
"""harvest_asset.py -- fill the manifest's `harvest` section (the gate verify_asset.py enforces).

    python3 tools/harvest_asset.py <asset_dir>/_motor/manifest.json --add "<file:line>" "<one-line why>" \
        [--status promoted|proposed] [--technique <registry id>]
    python3 tools/harvest_asset.py <manifest> --none "reused_only:<technique,...>" | "asset_specific:<file:line>"
    python3 tools/harvest_asset.py <manifest> --show

Every write is validated by recetas/harvest.py before it is saved; an invalid entry is
refused and the manifest is left untouched. --none takes a CLOSED category: reused_only:<registered techniques the generators call with part=> or asset_specific:<file:line of real asset code>. --add after --none (or the reverse) replaces
the other form: a section is entries OR an explicit none, never both.
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from recetas import harvest  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("manifest")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--add", nargs=2, metavar=("FILE:LINE", "WHY"))
    g.add_argument("--none", metavar="REASON")
    g.add_argument("--show", action="store_true")
    ap.add_argument("--status", default="proposed", choices=harvest.STATUSES)
    ap.add_argument("--technique", default="")
    args = ap.parse_args(argv)

    path = os.path.abspath(args.manifest)
    asset_dir = os.path.dirname(os.path.dirname(path))
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    section = manifest.get("harvest")
    if args.show:
        ok, problems, summary = harvest.validate(section, asset_dir, manifest.get("created"), manifest.get("generators"))
        print(json.dumps(section, indent=2, ensure_ascii=False))
        print("VALID: %s" % summary if ok else "INVALID:\n  - " + "\n  - ".join(problems))
        return 0 if ok else 1
    if args.none is not None:
        new = {"entries": [], "none": args.none}
    else:
        src, why = args.add
        entry = {"source": src, "why": why, "status": args.status}
        if args.technique:
            entry["technique"] = args.technique
        entries = list((section or {}).get("entries") or [])
        new = {"entries": entries + [entry], "none": ""}
    ok, problems, summary = harvest.validate(new, asset_dir, manifest.get("created"), manifest.get("generators"))
    if not ok:
        print("REFUSED (manifest untouched):\n  - " + "\n  - ".join(problems))
        return 1
    manifest["harvest"] = new
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    print("harvest saved: %s" % summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
