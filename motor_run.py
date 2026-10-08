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
#     technique -> structure -> GENERATOR -> mesh -> gltf -> physics -> evidence
#     -> scale -> use_size
#
#   technique   preflight_router.require_technique  (unknown subject fails closed)
#   structure   asset_spec.check_structure          (parts the generator declares)
#   GENERATOR   runpy.run_path
#   mesh        mesh_quality.check_mesh: non-manifold, degenerate, winding/normals,
#               UV (where the family needs textures), tri budget (per family)
#   gltf        gltf_check.validate: Khronos validator on any .glb the generator
#               wrote (fails loudly if the validator is not installed)
#   physics     physics.check_physics: COM inside the support polygon, rigid-body
#               drop/settle (tilt, drift), floating islands, BVH interpenetration;
#               per-family policy from router_knowledge `physics`
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
#              or {"exempt": "..."}   <- only a REQUEST: honoured solely if
#                                       recetas/approved_exemptions.json has an
#                                       entry approved by Joan for this exact
#                                       (generator, subject, type)}
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

from recetas import (asset_spec, gltf_check, mesh_quality, physics,  # noqa: E402
                     preflight_router, rubric, scale_ref, use_size, views)
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


# --------------------------------------------------------------- exemptions
# A generator must NOT be able to grant itself an exemption: its sidecar may
# only DECLARE what it wants, and motor_run honours it only if a human-approved
# entry for exactly this (generator, subject, type) exists in the registry.
REGISTRY_PATH = os.path.join(ROOT, "recetas", "approved_exemptions.json")
EXEMPTION_TYPES = ("structure_exempt", "allow_unknown")
_ENTRY_FIELDS = ("generator", "subject", "type", "reason", "approved_by", "date")


def _norm_subject(text):
    return " ".join((text or "").lower().split())


def _rel_generator(generator):
    rel = os.path.relpath(generator, ROOT)
    return generator if rel.startswith("..") else rel.replace(os.sep, "/")


def load_registry():
    """Validated list of approved exemptions ([] when the file is absent)."""
    if not os.path.isfile(REGISTRY_PATH):
        return []
    with open(REGISTRY_PATH, encoding="utf-8") as fh:
        entries = json.load(fh)
    for e in entries:
        missing = [f for f in _ENTRY_FIELDS if not str(e.get(f, "")).strip()]
        if missing or e["type"] not in EXEMPTION_TYPES or len(e["reason"]) < 20:
            raise SystemExit("motor_run: malformed entry in %s (missing %s, type "
                             "%r, reason >= 20 chars): %r"
                             % (REGISTRY_PATH, missing, e.get("type"), e))
    return entries


def approved_exemption(generator, subject, kind):
    for e in load_registry():
        if (e["type"] == kind and e["generator"] == _rel_generator(generator)
                and _norm_subject(e["subject"]) == _norm_subject(subject)):
            return e
    return None


def _refuse_unapproved(generator, subject, kind):
    raise SystemExit(
        "motor_run: %s asks for a %r exemption for subject %r, but %s has no "
        "approved entry for it.\nExemptions are not granted by the generator "
        "or the command line: ask Joan for approval, then add an entry "
        "{generator, subject, type, reason, approved_by, date}."
        % (_rel_generator(generator), kind, subject, REGISTRY_PATH))


def make_ctx(argv):
    generator, subject, opts, gen_args = parse_args(argv)
    if not os.path.isfile(generator):
        raise SystemExit("no such generator: %s" % generator)
    side = load_sidecar(generator)
    if "asset_objects" in side:
        raise SystemExit("motor_run: sidecar asset_objects is no longer "
                         "supported: a generator cannot choose which of its "
                         "meshes get judged. Every mesh is framed.")
    asked_struct = bool(side.get("structure", {}).get("exempt"))
    asked_unknown = bool(opts["allow_unknown"] or side.get("allow_unknown"))
    struct_entry = approved_exemption(generator, subject, "structure_exempt")
    unknown_entry = approved_exemption(generator, subject, "allow_unknown")
    if asked_struct and not struct_entry:
        _refuse_unapproved(generator, subject, "structure_exempt")
    if asked_unknown and not unknown_entry:
        _refuse_unapproved(generator, subject, "allow_unknown")
    stem = os.path.splitext(os.path.basename(generator))[0]
    out = os.path.abspath(opts["out"] or os.path.join(ROOT, "_out", stem))
    return {
        "generator": generator, "stem": stem, "subject": subject,
        "gen_args": gen_args, "sidecar": side, "out": out,
        "technique": opts["technique"] or side.get("technique") or "",
        # Only the registry's reason is ever used, never the requester's text.
        "allow_unknown": unknown_entry["reason"] if unknown_entry else "",
        "structure_exempt": struct_entry["reason"] if struct_entry else "",
        "report": Report("MOTOR_RUN %s :: %s" % (stem, subject)),
        "rules": None, "rules_all": [], "req": None, "gaps": [], "measures": {}, "evidence": [], "asset_objects": [],
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
    ctx["rules_all"] = preflight_router.route_all(ctx["subject"])
    ctx["req"] = preflight_router.requirements(ctx["subject"])
    cats = ctx["req"]["categories"] or ["UNKNOWN (allowed: %s)" % ctx["allow_unknown"]]
    ctx["report"].add("technique", PASS, "%r ok for %s"
                      % (ctx["technique"], ", ".join(cats)))
    for gap in ctx["req"]["gaps"]:
        ctx["gaps"].append(gap)
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
    exempt = ctx["structure_exempt"]
    if exempt:
        sub.add("moving_parts", NOT_APPLICABLE, reason=exempt)
    elif not checked:
        raise SystemExit(
            "motor_run: the generator declares no moving parts and no "
            "exemption. A part without a STRUCTURE row is researched first "
            "(preflight 4d); a build with none must say so with a reason: "
            "an APPROVED entry in recetas/approved_exemptions.json (ask Joan)")
    print(sub.render())
    if not sub.is_complete():
        raise SystemExit(sub.render() + "\nPREFLIGHT 4d SIN CUMPLIR (motor_run).\n")
    if exempt and not checked:
        ctx["gaps"].append("structure exempt (approved): %s" % exempt)
        ctx["report"].add("structure", NOT_APPLICABLE, reason=exempt)
    else:
        ctx["report"].add("structure", PASS, "%d part rows researched" % checked)


def step_generator(ctx):
    os.makedirs(ctx["out"], exist_ok=True)
    os.environ["MOTOR_OUT_DIR"] = ctx["out"]
    sys.argv = [ctx["generator"], "--"] + ctx["gen_args"]
    t0 = time.time()
    ctx["glb_before"] = _glb_snapshot(ctx)
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


def step_mesh(ctx):
    assets = _asset_objects(ctx)
    ctx["asset_objects"] = assets
    lim = ctx["req"]["mesh"]
    rep, measures = mesh_quality.check_mesh(assets, lim)
    ctx["measures"]["mesh"] = measures
    n_na = len([r for r in rep.rows if r["state"] == NOT_APPLICABLE])
    if not rep.is_complete():
        raise SystemExit(rep.render() + "\nMESH GATE FAILED (motor_run).\n")
    ctx["report"].add("mesh", PASS, "%d objects, %d checks pass, %d n/a"
                      % (len(assets), len(rep.rows) - n_na, n_na))


def _glb_snapshot(ctx):
    """{path: mtime_ns} of every .glb in the out dir and next to the generator."""
    snap = {}
    for d in {ctx["out"], os.path.dirname(ctx["generator"])}:
        if os.path.isdir(d):
            for name in os.listdir(d):
                path = os.path.join(d, name)
                if name.lower().endswith(".glb") and os.path.isfile(path):
                    snap[path] = os.stat(path).st_mtime_ns
    return snap


def _find_glbs(ctx):
    """GLBs the generator created or rewrote: a snapshot diff, not a clock
    comparison (file mtimes use a coarse clock and can lag time.time())."""
    before = ctx.get("glb_before", {})
    return sorted(p for p, m in _glb_snapshot(ctx).items() if before.get(p) != m)


def step_gltf(ctx):
    glbs = _find_glbs(ctx)
    if not glbs:
        ctx["report"].add("gltf", NOT_APPLICABLE,
                          reason="the generator wrote no .glb during this run")
        return
    results = {}
    bad = []
    for path in glbs:
        res = gltf_check.validate(path)
        state, detail = gltf_check.judge(res)
        results[os.path.basename(path)] = res
        print("  [gltf] %s %s" % (state, detail))
        if state != PASS:
            bad.append(detail)
    ctx["measures"]["gltf"] = results
    if bad:
        raise SystemExit("motor_run: glTF validation failed:\n  " + "\n  ".join(bad))
    ctx["report"].add("gltf", PASS, "%d .glb validated, 0 errors" % len(glbs))


def step_physics(ctx):
    assets = _asset_objects(ctx)
    ctx["asset_objects"] = assets
    cfg = ctx["req"]["physics"]
    rep, measures = physics.check_physics(assets, cfg)
    ctx["measures"]["physics"] = {"config": cfg, "measured": measures,
                                  "notes": ctx["req"]["physics_notes"]}
    for key in ("islands", "interpenetration"):
        why = (measures.get(key) or {}).get("skipped_reason")
        if why and "declared gap" in why:
            ctx["gaps"].append("physics %s: %s" % (key, why))
    if not rep.is_complete():
        raise SystemExit(rep.render() + "\nPHYSICS GATE FAILED (motor_run).\n")
    na = len([r for r in rep.rows if r["state"] == NOT_APPLICABLE])
    ctx["report"].add("physics", PASS, "%d checks pass, %d n/a" %
                      (len(rep.rows) - na, na))


def _asset_objects(ctx):
    """Every mesh except the mannequin: a generator cannot pick what is judged."""
    import bpy
    objs = [o for o in bpy.context.scene.objects
            if o.type == 'MESH' and not o.name.startswith(scale_ref.NAME_PREFIX)]
    if not objs:
        raise SystemExit("motor_run: the generator left no mesh to judge")
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
    sz = req["size_range"] or {}
    rep = scale_ref.require_scale_evidence(
        ctx["evidence"], asset_objects=ctx["asset_objects"],
        expected_height_m=sz.get("range_m") if sz.get("dim") == "height" else None,
        expected_span_m=sz.get("range_m") if sz.get("dim") == "span" else None)
    if not any(r["prop"] in ("asset_height_vs_source", "asset_span_vs_source")
               and r["state"] == PASS for r in rep.rows):
        gap = ("asset height was NOT checked against a sourced size range "
               "(none for this family)")
        ctx["gaps"].append(gap)
        print("  [motor_run] OPEN GAP  %s" % gap)
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
    ("mesh", step_mesh),
    ("gltf", step_gltf),
    ("physics", step_physics),
    ("evidence", step_evidence),
    ("scale", step_scale),
    ("use_size", step_use_size),
]


# The report row each default step must leave behind: a step that returns
# without recording a result did not run its gate.
ROW_FOR = {"technique": "technique", "structure": "structure",
           "generator": "generator", "mesh": "mesh", "gltf": "gltf", "physics": "physics",
           "evidence": "views", "scale": "scale",
           "use_size": "use_size"}


def _structure_rows(rules_all):
    """{category: {part: row}} for the rubric's structure questions."""
    out = {}
    for r in rules_all:
        spec = r.data.get("structure_spec")
        if not spec:
            continue
        table = asset_spec.parse_structure(
            asset_spec.find_spec(os.path.join(ROOT, spec)))
        wanted = {p.lower() for p in r.data.get("moving_parts", [])}
        out[r.category] = {k: v for k, v in table.items()
                           if k in wanted or not wanted}
    return out


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
    # A plain PASS means nothing was left open. Declared gaps (exemptions, no
    # sourced size range, research holes) make it visibly PASS_WITH_GAPS.
    label = "PASS_WITH_GAPS" if report.verdict() == PASS and ctx["gaps"] \
        else report.verdict()
    ctx["verdict_label"] = label
    os.makedirs(ctx["out"], exist_ok=True)
    # The visual half of the verdict: derived from the router, filled in by a
    # reviewer who LOOKS at the evidence. Until then the status cannot be PASS.
    rub = rubric.build_rubric(ctx["subject"], ctx["rules_all"], ctx["req"],
                              _structure_rows(ctx["rules_all"]))
    doc = {"subject": ctx["subject"], "generator": ctx["generator"],
           "verdict": label, "gaps": ctx["gaps"], "measures": ctx["measures"],
           "rows": report.rows, "evidence": ctx["evidence"], "rubric": rub,
           # sha256 of every file a reviewer will judge; score_rubric re-hashes
           # and refuses on mismatch. Only a run whose gates passed is scoreable.
           "evidence_sha256": rubric.hash_evidence(ctx["evidence"]),
           "scoreable": report.verdict() == PASS}
    doc["status"] = rubric.overall_status(doc)
    ctx["status"] = doc["status"]
    ctx["verdict_path"] = os.path.join(ctx["out"], "motor_verdict.json")
    with open(ctx["verdict_path"], "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, default=str)
    report.require_complete()
    print("[motor_run] gates %s (%d open gaps); STATUS %s: this is NOT a visual "
          "verdict. Open the evidence, then score it:" % (label, len(ctx["gaps"]),
                                                          ctx["status"]))
    for p in ctx["evidence"]:
        print("    %s" % p)
    print("    python3 %s %s" % (os.path.join(ROOT, "tools", "score_rubric.py"),
                                ctx["verdict_path"]))
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
