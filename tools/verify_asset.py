#!/usr/bin/env python3
"""verify_asset.py -- POST-RUN check: does the .blend carry the motor's stamps?

    python3 tools/verify_asset.py <file.blend> <asset_dir>/_motor/manifest.json

Runs itself inside headless Blender (re-execs when bpy is not importable) and
writes <asset_dir>/_motor/verdict.json. Per declared part:

    part:<p>:exists     PASS when >=1 object carries motor_part == <p>
    part:<p>:technique  PASS when those objects' motor_technique contains the
                        declared technique
    unstamped_renderables PASS when every renderable object in the scene (mesh, curve,
                        surface, meta, font, collection instance...) has a motor_part
    harvest             PASS only when the manifest's `harvest` section lists the techniques
                        promoted/proposed from this asset (file:line + why) or declares
                        `none` with a reason; missing/empty -> FAIL (see recetas/harvest.py,
                        edit with tools/harvest_asset.py)

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
from recetas import harvest  # noqa: E402


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


# Object types that can render (or instance renderables). A stamped EMPTY does
# not make a part: it has no geometry. ARMATURE counts as a part (rigs are parts)
# but is never "unstamped geometry" because it does not render.
RENDERABLE = {"MESH", "CURVE", "SURFACE", "META", "FONT", "CURVES", "POINTCLOUD",
              "VOLUME", "GREASEPENCIL", "GPENCIL"}
PART_TYPES = RENDERABLE | {"ARMATURE"}


def _renders(ob):
    """True when `ob` can put pixels in a render: renderable type, or an empty
    instancing a collection."""
    if ob.type in RENDERABLE:
        return True
    return ob.type == "EMPTY" and ob.instance_type == "COLLECTION" and ob.instance_collection is not None


def _in_play(ob, view_layer_objs, scene_objs):
    """Judge only objects that are really in the scene: in the active view layer
    (an excluded collection is out), linked to a scene (an orphan from
    bpy.data.objects.new is out), and visible in the viewport or renderable."""
    if ob.name not in view_layer_objs or not ob.users_scene:
        return False
    try:
        visible = ob.visible_get()
    except Exception:  # noqa: BLE001 -- no view layer context
        visible = not ob.hide_get()
    return visible or not ob.hide_render


def _declared_outputs(manifest, manifest_path):
    asset_dir = os.path.dirname(os.path.dirname(os.path.abspath(manifest_path)))
    outs = manifest.get("outputs")
    if not outs:
        return None   # legacy manifest: any .blend is accepted
    return {os.path.realpath(o if os.path.isabs(o) else os.path.join(asset_dir, o)) for o in outs}


def check(blend, manifest_path):
    report = Report("VERIFY %s" % os.path.basename(blend))
    try:
        return _check(report, blend, manifest_path)
    except Exception:  # noqa: BLE001 -- a crash must never read as a pass or vanish
        import traceback
        report.add("verifier_crashed", NOT_TESTED,
                   "verify_asset crashed: " + traceback.format_exc().strip().splitlines()[-1])
        return report


def _check(report, blend, manifest_path):
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        parts = manifest["parts"]
        assert isinstance(parts, dict) and parts
    except Exception as e:  # noqa: BLE001
        report.add("manifest_readable", NOT_TESTED, "cannot read manifest: %s" % e)
        return report
    # HARVEST gate (cosecha 2026-10-16): pure manifest check, so it runs even when the
    # blend later cannot be judged. No `harvest` section / empty section -> FAIL.
    ok, problems, summary = harvest.validate(
        manifest.get("harvest"), os.path.dirname(os.path.dirname(os.path.abspath(manifest_path))))
    if ok:
        report.add("harvest", PASS, summary)
    else:
        report.add("harvest", FAIL, "; ".join(problems[:3]) + (
            " [%d more]" % (len(problems) - 3) if len(problems) > 3 else "")
            + " -- fill it with: python3 tools/harvest_asset.py %s --add <file:line> <why> | --none <reason>"
            % manifest_path)
    declared = _declared_outputs(manifest, manifest_path)
    if declared is not None and os.path.realpath(blend) not in declared:
        report.add("blend_declared", FAIL,
                   "%s is not one of the manifest's declared outputs (%s): re-run start_asset.py "
                   "with --output, or verify the declared file"
                   % (blend, ", ".join(sorted(declared))))
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
    view_layer_objs = {o.name for o in bpy.context.view_layer.objects}
    scene_objs = None
    by_part, unstamped, ignored = {}, [], 0
    for ob in bpy.data.objects:
        if not _in_play(ob, view_layer_objs, scene_objs):
            ignored += 1
            continue
        part = ob.get(PART_PROP)
        if part:
            by_part.setdefault(str(part), []).append(ob)
        elif _renders(ob):
            unstamped.append("%s(%s)" % (ob.name, ob.type))

    for part, spec in parts.items():
        objs = [o for o in by_part.get(part, []) if o.type in PART_TYPES]
        empties = [o.name for o in by_part.get(part, []) if o.type not in PART_TYPES]
        if not objs:
            why = ("only non-geometry objects carry motor_part=%r (%s): an Empty is not a part"
                   % (part, ", ".join(empties[:3]))) if empties else (
                   "no object carries motor_part=%r (built outside the motor, or the recipe "
                   "was not passed part=%r)" % (part, part))
            report.add("part:%s:exists" % part, FAIL, why)
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
        report.add("unstamped_renderables", FAIL,
                   "%d renderable object(s) without motor_part (built outside the motor): %s"
                   % (len(unstamped), ", ".join(sorted(unstamped)[:8])))
    else:
        report.add("unstamped_renderables", PASS,
                   "every renderable in the scene is stamped (%d out-of-scene/orphan object(s) ignored)" % ignored)
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
    try:
        path = write_verdict(manifest, blend, report)
    except Exception as e:  # noqa: BLE001
        print("  verdict NOT written: %s" % e)
        return 2
    print(report.render())
    print("  verdict written: %s" % path)
    return 0 if report.verdict() == PASS else 1


if __name__ == "__main__":
    code = main(sys.argv)
    sys.stdout.flush()
    os._exit(code) if "bpy" in sys.modules else sys.exit(code)
