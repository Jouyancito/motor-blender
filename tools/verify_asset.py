#!/usr/bin/env python3
"""verify_asset.py -- POST-RUN check: does the .blend carry the motor's stamps?

    python3 tools/verify_asset.py <file.blend> <asset_dir>/_motor/manifest.json

Runs itself inside headless Blender (re-execs when bpy is not importable) and
writes <asset_dir>/_motor/verdict.json. Per declared part:

    part:<p>:exists     PASS when >=1 object carries motor_part == <p>
    part:<p>:technique  PASS when those objects' motor_technique contains the
                        declared technique
    unstamped_meshes    PASS when every visible mesh has a motor_part
                        (an unstamped visible mesh was built outside the motor)

States come from recetas/verdict.py. FAIL = checked and wrong; NOT_TESTED =
the check could not run (unreadable .blend / manifest). The Stop hook
~/.claude/hooks/motor-verify-gate.py refuses to close a turn while the newest
.blend is newer than the verdict or the verdict is not all PASS.

Objects whose motor_part starts with "_" (e.g. the 1.80 m scale reference) are
infrastructure: they count as stamped but are not parts.

Honest limit: stamps are custom properties; a generator can set them by hand.
The static gate (import+call, AST) and the `custom` reason rule are what make
that a visible, reviewable act rather than an accident.
"""
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
BLENDER = os.environ.get("BLENDER_BIN", "/home/jouyan/.local/bin/blender")

from recetas.verdict import Report, PASS, FAIL, NOT_TESTED  # noqa: E402


def write_verdict(manifest_path, blend, report, extra=None):
    out_dir = os.path.dirname(os.path.abspath(manifest_path))
    doc = {
        "schema": 1,
        "blend": os.path.abspath(blend),
        "blend_mtime": os.path.getmtime(blend) if os.path.isfile(blend) else None,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "verdict": report.verdict(),
        "rows": report.rows,
    }
    doc.update(extra or {})
    path = os.path.join(out_dir, "verdict.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def check(blend, manifest_path):
    report = Report("VERIFY %s" % os.path.basename(blend))
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        parts = manifest["parts"]
        assert isinstance(parts, dict) and parts
    except Exception as e:  # noqa: BLE001
        report.add("manifest_readable", NOT_TESTED, "cannot read manifest: %s" % e)
        return report
    if not os.path.isfile(blend):
        report.add("blend_exists", NOT_TESTED, "no such file: %s" % blend)
        return report
    try:
        import bpy
        bpy.ops.wm.open_mainfile(filepath=blend)
    except Exception as e:  # noqa: BLE001
        report.add("blend_opens", NOT_TESTED, "cannot open .blend: %s" % e)
        return report

    from recetas.motor_stamp import PART_PROP, TECH_PROP
    by_part, unstamped = {}, []
    for ob in bpy.data.objects:
        part = ob.get(PART_PROP)
        if part:
            by_part.setdefault(str(part), []).append(ob)
        elif ob.type == "MESH" and not ob.hide_render and not ob.hide_get():
            unstamped.append(ob.name)

    for part, spec in parts.items():
        objs = by_part.get(part, [])
        if not objs:
            report.add("part:%s:exists" % part, FAIL,
                       "no object carries motor_part=%r (built outside the motor, "
                       "or the recipe was not passed part=%r)" % (part, part))
            report.add("part:%s:technique" % part, FAIL, "no stamped object to read")
            continue
        report.add("part:%s:exists" % part, PASS, "%d object(s)" % len(objs))
        want = spec.get("technique")
        bad = [o.name for o in objs
               if want not in str(o.get(TECH_PROP, "")).split(",")]
        if bad:
            report.add("part:%s:technique" % part, FAIL,
                       "declared %r but %s carry motor_technique=%s"
                       % (want, bad[:4], [o.get(TECH_PROP) for o in objs][:4]))
        else:
            report.add("part:%s:technique" % part, PASS, want)

    if unstamped:
        report.add("unstamped_meshes", FAIL,
                   "%d visible mesh(es) without motor_part (built outside the motor): %s"
                   % (len(unstamped), ", ".join(sorted(unstamped)[:8])))
    else:
        report.add("unstamped_meshes", PASS, "every visible mesh is stamped")
    return report


def main(argv):
    try:
        import bpy  # noqa: F401
        in_blender = True
    except ImportError:
        in_blender = False

    if in_blender:
        args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    else:
        args = argv[1:]
    if len(args) != 2:
        raise SystemExit("usage: verify_asset.py <file.blend> <manifest.json>")
    blend, manifest = (os.path.abspath(a) for a in args)

    if not in_blender:
        p = subprocess.run(
            [BLENDER, "-b", "--factory-startup", "--python-exit-code", "1",
             "--python", os.path.abspath(__file__), "--", blend, manifest],
            capture_output=True, text=True)
        sys.stdout.write("\n".join(l for l in p.stdout.splitlines()
                                   if not l.startswith(("Blender ", "Read ", "Info:"))) + "\n")
        sys.stderr.write(p.stderr)
        return p.returncode

    report = check(blend, manifest)
    path = write_verdict(manifest, blend, report)
    print(report.render())
    print("  verdict written: %s" % path)
    return 0 if report.verdict() == PASS else 1


if __name__ == "__main__":
    code = main(sys.argv)
    sys.stdout.flush()
    os._exit(code) if "bpy" in sys.modules else sys.exit(code)
