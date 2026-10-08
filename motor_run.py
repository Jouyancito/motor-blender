# motor_run.py -- the single entry point. No generator runs without its gates.
#
# WHY THIS EXISTS (2026-10-08)
#
# Every gate in recetas/ was written, fixture-tested, and had ZERO call sites:
# the router, asset_spec and use_size were reachable only by a generator that
# remembered to import them, and LECCIONES 1 already said what that is worth
# ("si una regla necesita que yo me acuerde de ir a buscarla, ya fallo").
# So the order is fixed HERE, not in each generator:
#
#     technique -> structure -> GENERATOR -> evidence -> scale -> use_size
#
#   technique   preflight_router.require_technique  (unknown subject fails closed)
#   structure   asset_spec.check_structure          (parts the generator declares)
#   GENERATOR   runpy.run_path
#   evidence    mannequin (scale_ref) + orbit of the ungrateful angles (views)
#   scale       scale_ref.require_scale_evidence
#   use_size    use_size.require_use_size
#
# A generator cannot skip one: it is not the one calling them. And
# tools/test_gates.py fails if a step stops calling its gate, so unwiring is
# never silent.
#
# USAGE
#   blender -b --factory-startup --python-exit-code 1 --python motor_run.py -- \
#       <generator.py> "<subject>" [--motor-out DIR] [--motor-technique KEY] \
#       [--motor-allow-unknown "reason"] [generator args...]
#
# The generator declares what only it knows in a sidecar `<generator>.motor.json`
# read BEFORE anything runs:
#   {"technique": "key",
#    "structure": {"ref_dir": "rel/or/abs", "moving_parts": ["a", "b"]}
#              or {"exempt": "reason this build has no moving parts to research"},
#    "asset_objects": ["Name", "Prefix*"]}
#
# The output is NOT a visual verdict. It is a list of files to open and look at.
import json
import os
import runpy
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from recetas import asset_spec, preflight_router, scale_ref, use_size, views  # noqa: E402
from recetas.verdict import Report, PASS, FAIL, NOT_APPLICABLE  # noqa: E402


# --------------------------------------------------------------------- parsing

def parse_args(argv):
    """argv is everything after Blender's `--`."""
    if len(argv) < 2:
        raise SystemExit("usage: motor_run.py -- <generator.py> \"<subject>\" "
                         "[--motor-out DIR] [--motor-technique KEY] "
                         "[--motor-allow-unknown REASON] [generator args...]")
    opts = {"out": None, "technique": None, "allow_unknown": ""}
    gen_args = []
    rest = argv[2:]
    i = 0
    while i < len(rest):
        a = rest[i]
        key = {"--motor-out": "out", "--motor-technique": "technique",
               "--motor-allow-unknown": "allow_unknown"}.get(a)
        if key:
            if i + 1 >= len(rest):
                raise SystemExit("%s needs a value" % a)
            opts[key] = rest[i + 1]
            i += 2
        else:
            gen_args.append(a)
            i += 1
    return os.path.abspath(argv[0]), argv[1], opts, gen_args


def load_sidecar(generator):
    path = os.path.splitext(generator)[0] + ".motor.json"
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def make_ctx(argv):
    generator, subject, opts, gen_args = parse_args(argv)
    if not os.path.isfile(generator):
        raise SystemExit("no such generator: %s" % generator)
    side = load_sidecar(generator)
    stem = os.path.splitext(os.path.basename(generator))[0]
    out = os.path.abspath(opts["out"] or os.path.join(ROOT, "_out", stem))
    return {
        "generator": generator, "stem": stem, "subject": subject,
        "gen_args": gen_args, "sidecar": side, "out": out,
        "technique": opts["technique"] or side.get("technique") or "",
        "allow_unknown": opts["allow_unknown"] or side.get("allow_unknown", ""),
        "report": Report("MOTOR_RUN %s :: %s" % (stem, subject)),
        "rules": None, "req": None, "evidence": [], "asset_objects": [],
    }


# ----------------------------------------------------------------------- steps
# One function per step; each calls its gate and nothing else decides pass/fail.
# tools/test_gates.py parses THIS file and fails if a call below disappears.

def step_technique(ctx):
    if not ctx["technique"]:
        raise SystemExit("motor_run: no technique declared. Pass "
                         "--motor-technique KEY or set \"technique\" in the "
                         "generator's .motor.json: 0b CON QUE TRUCO is not optional.")
    rules = preflight_router.require_technique(
        ctx["subject"], ctx["technique"],
        allow_unknown=bool(ctx["allow_unknown"]), reason=ctx["allow_unknown"])
    ctx["rules"] = rules
    ctx["req"] = preflight_router.requirements(ctx["subject"])
    cats = ctx["req"]["categories"] or ["UNKNOWN (allowed: %s)" % ctx["allow_unknown"]]
    ctx["report"].add("technique", PASS, "%r ok for %s"
                      % (ctx["technique"], ", ".join(cats)))
    for gap in ctx["req"]["gaps"]:
        print("  [motor_run] OPEN GAP  %s" % gap)


def step_structure(ctx):
    side = ctx["sidecar"].get("structure", {})
    sub = Report("STRUCTURE")
    checked = 0
    for ref_dir, parts in ctx["req"]["structure"]:
        for row in asset_spec.check_structure(ref_dir, parts).rows:
            sub.add(row["prop"], row["state"], row["detail"], row["reason"])
            checked += 1
    if side.get("moving_parts"):
        ref_dir = side.get("ref_dir")
        if not ref_dir:
            raise SystemExit("motor_run: sidecar structure declares moving_parts "
                             "but no ref_dir to find their STRUCTURE table in")
        ref_dir = ref_dir if os.path.isabs(ref_dir) else os.path.join(
            os.path.dirname(ctx["generator"]), ref_dir)
        for row in asset_spec.check_structure(ref_dir, side["moving_parts"]).rows:
            sub.add(row["prop"], row["state"], row["detail"], row["reason"])
            checked += 1
    declared = ctx["req"]["declared_parts"]
    for part in declared:
        sub.add(part, FAIL, "family declares this moving part but has no "
                "structure_spec to research it in")
        checked += 1
    if side.get("exempt"):
        sub.add("moving_parts", NOT_APPLICABLE, reason=side["exempt"])
    elif not checked:
        raise SystemExit(
            "motor_run: the generator declares no moving parts and no "
            "exemption. A part without a STRUCTURE row is researched first "
            "(preflight 4d); a build with none must say so with a reason: "
            "{\"structure\": {\"exempt\": \"...\"}} in %s.motor.json"
            % ctx["stem"])
    print(sub.render())
    if not sub.is_complete():
        raise SystemExit(sub.render() + "\nPREFLIGHT 4d SIN CUMPLIR (motor_run).\n")
    state = NOT_APPLICABLE if side.get("exempt") and not checked else PASS
    if state == NOT_APPLICABLE:
        ctx["report"].add("structure", NOT_APPLICABLE, reason=side["exempt"])
    else:
        ctx["report"].add("structure", PASS, "%d part rows researched" % checked)


def step_generator(ctx):
    os.makedirs(ctx["out"], exist_ok=True)
    os.environ["MOTOR_OUT_DIR"] = ctx["out"]
    sys.argv = [ctx["generator"], "--"] + ctx["gen_args"]
    t0 = time.time()
    try:
        runpy.run_path(ctx["generator"], run_name="__main__")
    except SystemExit as exc:
        # A generator that calls sys.exit(0) used to end the whole process with
        # rc=0 before evidence, scale, use_size or the verdict ran: a clean-looking
        # exit that skipped every later gate. Any self-exit is a failed build.
        raise SystemExit("motor_run: the generator exited by itself (code %r) "
                         "before the gates after it could run" % (exc.code,))
    ctx["report"].add("generator", PASS, "%s ran in %.1fs"
                      % (os.path.basename(ctx["generator"]), time.time() - t0))


def _asset_objects(ctx):
    import bpy
    names = ctx["sidecar"].get("asset_objects")
    objs = []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH' or o.name.startswith(scale_ref.NAME_PREFIX):
            continue
        if names is None or any(o.name == n or (n.endswith("*") and
                                                o.name.startswith(n[:-1]))
                                for n in names):
            objs.append(o)
    if not objs:
        raise SystemExit("motor_run: the generator left no mesh to judge "
                         "(asset_objects=%r)" % names)
    return objs


def _place_mannequin(assets):
    """Diagonal front-right of the asset: beside it in the frente view AND beside
    it in the perfil view (straight +X would hide the asset behind the mannequin
    in the profile shot). Reuses a mannequin the generator already built."""
    from mathutils import Vector
    parts = scale_ref.find_mannequin()
    if parts:
        return parts
    pts = [o.matrix_world @ Vector(c) for o in assets for c in o.bound_box]
    return scale_ref.build_mannequin(
        location=(max(p.x for p in pts) + 0.7 + scale_ref.BODY_R,
                  min(p.y for p in pts) - 0.7 - scale_ref.BODY_R,
                  min(p.z for p in pts)))


def _save_blend(path):
    import bpy
    bpy.ops.wm.save_as_mainfile(filepath=path)


def step_evidence(ctx):
    req = ctx["req"]
    assets = _asset_objects(ctx)
    ctx["asset_objects"] = assets
    frame = list(assets)
    # Scale evidence is never skipped for an unknown subject: no family means
    # "unregistered", not "exempt from being seen next to a person".
    if req["mannequin"] or not req["categories"]:
        req["mannequin"] = True
        req["use_size"] = req["use_size"] or {"sizes": [512, 256, 128]}
        frame += _place_mannequin(assets)
    labels = req["views"] or [v[0] for v in views.VIEWS]
    chosen = views.resolve_views(labels)
    ev_dir = os.path.join(ctx["out"], "evidence")
    ctx["evidence"] = views.orbit_capture(ev_dir, ctx["stem"], frame, chosen)
    _save_blend(os.path.join(ctx["out"], "%s_motor.blend" % ctx["stem"]))
    ctx["report"].add("views", PASS, "%d orbit shots in %s"
                      % (len(ctx["evidence"]), ev_dir))


def step_scale(ctx):
    req = ctx["req"]
    if not req["mannequin"]:
        ctx["report"].add("scale", NOT_APPLICABLE,
                          reason="; ".join(req["mannequin_exempt"])
                          or "no matched family requires a mannequin")
        return
    rep = scale_ref.require_scale_evidence(
        ctx["evidence"], asset_objects=ctx["asset_objects"],
        expected_height_m=req["height_range"])
    if any(r["prop"] == "asset_height_vs_source" and r["state"] != PASS
           for r in rep.rows):
        print("  [motor_run] OPEN GAP  asset height was NOT checked against a "
              "sourced size range (none for this family)")
    ctx["report"].add("scale", PASS, "mannequin 1.80 m + %d renders"
                      % len(ctx["evidence"]))


def step_use_size(ctx):
    spec = ctx["req"]["use_size"]
    if not spec:
        ctx["report"].add("use_size", NOT_APPLICABLE,
                          reason="; ".join(ctx["req"]["use_size_exempt"])
                          or "no matched family declares a use size")
        return
    front = [p for p in ctx["evidence"] if p.endswith("_frente.png")]
    if not front:
        raise SystemExit("motor_run: use_size needs the 'frente' render and the "
                         "family's required_views do not include it")
    out = os.path.join(ctx["out"], "evidence", "%s_use_size.png" % ctx["stem"])
    path = use_size.require_use_size(front[0], spec["sizes"], out)
    ctx["report"].add("use_size", PASS, "%s at %s px" % (os.path.basename(path),
                                                         spec["sizes"]))


# Order is the contract. Do not reorder without changing the fixtures.
STEPS = [
    ("technique", step_technique),
    ("structure", step_structure),
    ("generator", step_generator),
    ("evidence", step_evidence),
    ("scale", step_scale),
    ("use_size", step_use_size),
]


# The report row each default step must leave behind: a step that returns
# without recording a result did not run its gate.
ROW_FOR = {"technique": "technique", "structure": "structure",
           "generator": "generator", "evidence": "views", "scale": "scale",
           "use_size": "use_size"}


def run(argv, steps=None):
    ctx = make_ctx(argv)
    ctx["completed"] = []
    for name, fn in (steps or STEPS):
        print("\n[motor_run] step: %s" % name)
        fn(ctx)
        row = ROW_FOR.get(name)
        if row and not any(r["prop"] == row for r in ctx["report"].rows):
            raise SystemExit("motor_run: step %r returned without recording %r"
                             % (name, row))
        ctx["completed"].append(name)
    report = ctx["report"]
    print(report.render())
    os.makedirs(ctx["out"], exist_ok=True)
    with open(os.path.join(ctx["out"], "motor_verdict.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"subject": ctx["subject"], "generator": ctx["generator"],
                   "verdict": report.verdict(), "rows": report.rows,
                   "evidence": ctx["evidence"]}, fh, indent=2)
    report.require_complete()
    print("[motor_run] gates %s. This is NOT a visual verdict -- open:" %
          report.verdict())
    for p in ctx["evidence"]:
        print("    %s" % p)
    return ctx


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    try:
        ctx = run(argv)
        if ctx["completed"] != [n for n, _ in STEPS]:
            raise SystemExit("motor_run: not every step ran: %r" % ctx["completed"])
    except SystemExit as exc:
        # Blender's --python-exit-code only fires on exceptions; make a failed
        # gate exit non-zero explicitly.
        # Never exit 0 from here: reaching this handler means a gate or the
        # generator ended the run early.
        print(exc.code if isinstance(exc.code, str) else
              "motor_run: exit %r" % (exc.code,), file=sys.stderr)
        sys.stderr.flush()
        os._exit(1)


if __name__ == "__main__":
    main()
