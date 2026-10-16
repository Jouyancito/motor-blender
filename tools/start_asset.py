#!/usr/bin/env python3
"""start_asset.py -- the front door of every Blender modeling job.

    python3 tools/start_asset.py <asset_dir> "<subject description>" \
        --generator <gen.py>[:part1,part2] --output <file.blend> [--helper <script.py>] [--technique part=tech ...] [--custom part=reason] [--allow-unknown "<reason>"]

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
from recetas.technique_registry import REGISTRY, is_registered  # noqa: E402
from recetas import harvest as harvest_mod  # noqa: E402

SCHEMA = 2
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
    ap.add_argument("--generator", action="append", default=[], metavar="GEN.PY[:PARTS]",
                    help="a script that BUILDS the asset (path, absolute or relative to "
                         "asset_dir). Optional ':part1,part2' binds it to those parts; the "
                         "gate then proves it imports+calls (with part=) the motor "
                         "implementation of just those parts' techniques. Without it, "
                         "every non-custom part is checked against it.")
    ap.add_argument("--helper", action="append", default=[], metavar="SCRIPT.PY",
                    help="a script that only inspects/renders/measures (never builds). "
                         "Any script in the asset dir that is neither generator nor helper "
                         "is denied by the gate.")
    ap.add_argument("--output", action="append", default=[], metavar="FILE.BLEND",
                    help="the .blend the build produces; verify_asset.py and the Stop gate "
                         "judge exactly these, not whatever .blend is newest")
    ap.add_argument("--custom", action="append", default=[], metavar="PART=REASON",
                    help="part whose technique is NOT in the registry: why it is "
                         "built by hand. The post-run verifier must still pass.")
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

    if not args.generator:
        raise SystemExit("declare the generator: --generator <gen.py>. The gate "
                         "reads it to prove each technique is really called.")
    if not args.output:
        raise SystemExit("declare the output: --output <file.blend> (the file verify_asset.py judges)")

    def absp(p):
        return os.path.normpath(p if os.path.isabs(p) else os.path.join(asset_dir, p))

    generators, generator_parts = [], {}
    for g in args.generator:
        path, _, plist = g.partition(":")
        generators.append(absp(path))
        if plist.strip():
            generator_parts[absp(path)] = [x.strip() for x in plist.split(",") if x.strip()]
    for g, plist in generator_parts.items():
        for pt in plist:
            if pt not in parts:
                raise SystemExit("--generator %s binds unknown part %r (declared: %s)"
                                 % (g, pt, ", ".join(parts)))
    helpers = [absp(h) for h in args.helper]
    outputs = [absp(o) for o in args.output]
    customs = {}
    for item in args.custom:
        if "=" not in item or not item.split("=", 1)[1].strip():
            raise SystemExit("--custom wants part=reason (a written reason), got %r" % item)
        part, why = item.split("=", 1)
        customs[part.strip()] = why.strip()
    for part in customs:
        if part not in parts:
            raise SystemExit("--custom %r has no matching --technique" % part)
    for part, tech in parts.items():
        if part in customs and is_registered(tech):
            raise SystemExit("%r is a registered technique; drop --custom %s" % (tech, part))
        if part not in customs and not is_registered(tech):
            raise SystemExit(
                "technique %r (part %r) has no implementation in the motor registry "
                "(recetas/technique_registry.py). Registered: %s.\nIf you build it "
                "by hand: --custom %s=\"<why>\"; its output must still carry the "
                "stamps (recetas/motor_stamp.stamp_object) and pass verify_asset.py."
                % (tech, part, ", ".join(sorted(REGISTRY)), part))

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
        if part in customs:
            checked[part].update(custom=True, custom_reason=customs[part])
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
        "generators": generators,
        "generator_parts": generator_parts,
        "helpers": helpers,
        "outputs": outputs,
        "parts": checked,
        # registry ids that existed when this asset started: harvest `promoted` entries must
        # be ABSENT from it (a technique that was already there was not learned here).
        "registry_snapshot": sorted(REGISTRY),
    }
    out_dir = os.path.join(asset_dir, "_motor")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(asset_dir, MANIFEST_REL)
    # HARVEST gate: the template starts EMPTY (which verify_asset.py fails) and a re-run of
    # start_asset must not wipe what was already recorded.
    manifest["harvest"] = harvest_mod.empty_section()
    try:
        with open(path, encoding="utf-8") as fh:
            prev_doc = json.load(fh)
        prev = prev_doc.get("harvest")
        if isinstance(prev, dict) and (prev.get("entries") or prev.get("none")):
            manifest["harvest"] = prev
        if isinstance(prev_doc.get("registry_snapshot"), list):   # never refreshed: the snapshot is the
            manifest["registry_snapshot"] = prev_doc["registry_snapshot"]   # registry AT CREATION
    except (OSError, ValueError, AttributeError):
        pass
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    # Register the asset dir so the Stop gate (motor-verify-gate.py) knows it.
    try:
        from recetas import motor_assets
        motor_assets.register(asset_dir, os.environ.get("CLAUDE_SESSION_ID") or None)
    except Exception as e:  # noqa: BLE001
        print("  WARNING: could not register asset dir for the Stop gate: %s" % e)
    print("\n  MANIFEST written: %s" % path)
    print("  AFTER building, run: python3 %s/tools/verify_asset.py <file.blend> %s"
          % (REPO, path))
    print("  (every recipe call needs part=<declared part> so its output is stamped)")
    print("  HARVEST (required for a PASS): before the verdict, record what this asset taught the motor:")
    print("    python3 %s/tools/harvest_asset.py %s --add <file:line> \"<why>\" [--status promoted --technique <id>]"
          % (REPO, path))
    print("    python3 %s/tools/harvest_asset.py %s --none \"reused_only:<techs>|asset_specific:<file:line>\"" % (REPO, path))
    print("  Blender runs for this asset are now unblocked. Build THROUGH the "
          "motor (motor_run.py + gates); the manifest only proves the declaration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
