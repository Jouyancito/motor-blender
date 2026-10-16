#!/usr/bin/env python3
"""start_asset.py -- the front door of every Blender modeling job.

    python3 tools/start_asset.py <asset_dir> "<subject description>" \
        [--technique part=tech ...] [--allow-unknown "<reason>"]

What it does:
  1. Runs preflight_router.route_all() on the subject and PRINTS the rules:
     established technique, discarded techniques, sources to cite, views.
  2. Lists the recipe library (recetas/RECETAS.md plus any recetas/*.py not
     indexed there) so nobody re-writes bpy that already exists.
  3. Calls preflight_router.require_technique() for every declared part. A
     discarded technique, or a subject with no registered knowledge and no
     --allow-unknown reason, aborts with SystemExit and writes NOTHING.
  4. Writes <asset_dir>/_motor/manifest.json. The PreToolUse hook
     ~/.claude/hooks/motor-modeling-gate.py refuses any `blender --python` run
     (direct or hidden inside a .sh) for an asset dir without a valid manifest.

Why a manifest and not a reminder (LECCIONES.md section 1): a rule that needs
me to remember to go fetch it has already failed. Rem v1-v7 never touched the
motor; the gate makes the motor the only road to a Blender run.

The manifest proves the declaration was made, not that the generator obeys it.
motor_run.py / the gates still judge the output.
"""
import argparse
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from recetas.preflight_router import route_all, require_technique  # noqa: E402

SCHEMA = 1
MANIFEST_REL = os.path.join("_motor", "manifest.json")


def recipe_index():
    """(name, one-liner) from RECETAS.md's table, then un-indexed recetas/*.py."""
    rec_dir = os.path.join(REPO, "recetas")
    rows, seen = [], set()
    try:
        with open(os.path.join(rec_dir, "RECETAS.md"), encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"\|\s*`([^`|]+)`\s*\|\s*([^|]*)\|", line)
                if m:
                    name = os.path.basename(m.group(1))
                    rows.append((name, m.group(2).strip()))
                    seen.add(name)
    except OSError:
        pass
    for fn in sorted(os.listdir(rec_dir)):
        if fn.endswith(".py") and not fn.startswith("_") and fn not in seen:
            rows.append((fn, "(not indexed in RECETAS.md -- read its header)"))
    return rows


def parse_techniques(items):
    parts = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit("--technique wants part=technique, got %r" % item)
        part, tech = (s.strip() for s in item.split("=", 1))
        if not part or not tech:
            raise SystemExit("--technique wants part=technique, got %r" % item)
        parts[part] = tech
    return parts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("asset_dir")
    ap.add_argument("subject", help="what is being built, e.g. 'gato', 'pelo largo'")
    ap.add_argument("--technique", action="append", default=[], metavar="PART=TECH",
                    help="technique chosen for one part; repeat per part")
    ap.add_argument("--allow-unknown", default="", metavar="REASON",
                    help="subject has no router entry: why is it safe anyway?")
    args = ap.parse_args(argv)

    asset_dir = os.path.abspath(os.path.expanduser(args.asset_dir))
    subject = args.subject.strip()
    if not subject:
        raise SystemExit("subject description is empty")
    parts = parse_techniques(args.technique)
    if not parts:
        raise SystemExit(
            "declare at least one part: --technique <part>=<technique> "
            "(e.g. --technique pelo=cards_alpha). The technique is chosen BEFORE "
            "the build, not discovered after it.")

    # 1. rules
    matches = route_all(subject)
    unknown = not matches
    print("=" * 70)
    print("MOTOR START -- %s" % subject)
    print("=" * 70)
    if matches:
        for rules in matches:
            print(rules.render())
    else:
        print("  Router has no entry for %r (unknown subject)." % subject)
        if args.allow_unknown.strip():
            print("  Proceeding UNKNOWN, reason: %s" % args.allow_unknown.strip())

    # 2. recipes
    print("  RECIPE LIBRARY (read recetas/RECETAS.md before writing new bpy):")
    for name, desc in recipe_index():
        print("    - %-26s %s" % (name, desc[:90]))

    # 3. validate every declared part
    checked = {}
    for part, tech in parts.items():
        # A part may have its own family (pelo); otherwise it is judged against
        # the whole subject's rules plus the universal discards.
        scope = part if route_all(part) else subject
        require_technique(scope, tech, verbose=False,
                          allow_unknown=bool(args.allow_unknown.strip()),
                          reason=args.allow_unknown)
        checked[part] = {"technique": tech, "validated_against": scope}
        print("  OK  %s = %s  (checked against %r)" % (part, tech, scope))

    # 4. manifest
    manifest = {
        "schema": SCHEMA,
        "subject": subject,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "routed_categories": [r.category for r in matches],
        "unknown_subject": unknown,
        "allow_unknown_reason": args.allow_unknown.strip() if unknown else "",
        "rules": [
            {"category": r.category,
             "established": r.data.get("established"),
             "discarded": sorted(r.data.get("discarded", {})),
             "must_read": r.data.get("must_read", [])}
            for r in matches],
        "parts": checked,
    }
    out_dir = os.path.join(asset_dir, "_motor")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(asset_dir, MANIFEST_REL)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("\n  MANIFEST written: %s" % path)
    print("  Blender runs for this asset are now unblocked. Build THROUGH the "
          "motor (motor_run.py + gates); the manifest only proves the declaration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
