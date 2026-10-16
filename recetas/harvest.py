# harvest.py -- the HARVEST gate: an asset may not pass unless it says what it taught the motor.
#
# WHY (2026-10-16, cosecha): rana, taza and rem each invented techniques that sat inside
# their project folders for weeks (decals, the bake-shading check, MPFB bodies, probes with
# controls). Nobody had to look at them again, so nobody did: LECCIONES 1 -- a rule that
# needs remembering has already failed. The harvest is therefore a precondition of the
# verdict, enforced where the verdict is written (tools/verify_asset.py).
#
# The manifest (_motor/manifest.json) must carry a `harvest` section, in ONE of two forms:
#
#   (a) techniques promoted or proposed for the motor from this asset:
#       "harvest": {"entries": [
#           {"source": "rem_v8_body_gen.py:80-110",     # file:line, INSIDE the asset dir (or motor recetas/)
#            "why": "MPFB human built headless with detailed helpers on",
#            "status": "promoted",                      # promoted | proposed
#            "technique": "mpfb_human_base"}]}          # promoted: registered now, ABSENT from manifest.registry_snapshot
#
#   (b) an explicit nothing, from a CLOSED list of reasons (free text is not accepted):
#       "harvest": {"none": "reused_only:bvh_glue,paint_por_geometria"}   # each registered AND
#                                                       # called with part= by a manifest generator
#       "harvest": {"none": "asset_specific:gen.py:42"} # real code in the asset that has no reuse value
#
# Source rules: the file resolves INSIDE the asset dir or the motor's recetas/ (no ../,
# no absolute paths elsewhere, symlinks resolved), is a .py file, and the cited lines sit
# inside ONE non-trivial def/class body (>= 3 statements, not pass/.../return None) and is
# not motor infrastructure or an already-registered recipe. A promoted technique must be
# registered now and ABSENT from the manifest's `registry_snapshot` (the sorted registry ids
# start_asset recorded at creation: a technique that already existed was not learned here),
# and must be claimed by this asset: its cited source lives in the asset dir, or a manifest
# generator imports AND calls it with part=. Duplicate entries, a `why` without 3 distinct
# 3-letter words, missing/empty section, a reason outside the closed list, both forms at
# once -> FAIL. Use tools/harvest_asset.py to edit it.
#
# Honest limit: this proves the question was ANSWERED with checkable citations, not that
# the answer is complete. It makes skipping the question a visible, failing act.
import ast
import os
import re

try:
    from recetas.technique_registry import REGISTRY, is_registered, evidence, _key
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from technique_registry import REGISTRY, is_registered, evidence, _key

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_WORDS = 3            # a `why` is a sentence: >= 3 DISTINCT words of >= 3 letters
MIN_BODY_STMTS = 3       # a cited def/class must do something
# Motor infrastructure: never an asset's own work (plus every registered recipe module, below).
INFRA = {"harvest", "technique_registry", "motor_stamp", "verdict", "preflight_router", "router_knowledge",
         "asset_spec", "rubric", "motor_assets", "mesh_quality", "physics", "gltf_check", "views",
         "scale_ref", "use_size", "material_swatch", "probe_with_control", "preflight_destructivo"}
STATUSES = ("promoted", "proposed")
NONE_CATEGORIES = ("reused_only", "asset_specific")
_SRC = re.compile(r"^(?P<path>.+):(?P<a>\d+)(?:-(?P<b>\d+))?$")


def empty_section():
    """The template start_asset.py writes: deliberately FAILS until it is filled."""
    return {"entries": [], "none": ""}


def _roots(asset_dir):
    roots = [os.path.realpath(os.path.join(REPO, "recetas"))]
    if asset_dir:
        roots.append(os.path.realpath(asset_dir))
    return roots


def _inside(real, roots):
    return any(real == r or real.startswith(r + os.sep) for r in roots)


def _trivial(node):
    """Why a def/class body is not worth harvesting, or None."""
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]                                       # docstring
    def inert(st):
        if isinstance(st, ast.Pass):
            return True
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and st.value.value is Ellipsis:
            return True
        return isinstance(st, ast.Return) and (st.value is None or (
            isinstance(st.value, ast.Constant) and st.value.value is None))
    if all(inert(st) for st in body):
        return "body is only pass/.../return None"
    n = sum(isinstance(x, ast.stmt) for st in body for x in ast.walk(st))
    if n < MIN_BODY_STMTS:
        return "body has %d statement(s) (< %d)" % (n, MIN_BODY_STMTS)
    return None


def _check_source(src, asset_dir):
    """(error or None, real path or None). `src` ('file.py:12' / 'file.py:12-30') must be a
    real citation: inside the asset dir or recetas/, a .py file, lines inside ONE def/class
    with a non-trivial body, and not motor infrastructure."""
    m = _SRC.match(str(src or "").strip())
    if not m:
        return "source %r is not file:line" % (src,), None
    raw = os.path.expanduser(m.group("path"))
    cands = [raw] if os.path.isabs(raw) else [os.path.join(asset_dir or "", raw), os.path.join(REPO, raw)]
    real = next((os.path.realpath(c) for c in cands if os.path.isfile(c)), None)
    if not real:
        return "source file %r does not exist (relative to the asset dir or the motor)" % m.group("path"), None
    if not _inside(real, _roots(asset_dir)):
        return "source %r resolves outside the asset dir and recetas/ (%s)" % (m.group("path"), real), None
    if not real.endswith(".py"):
        return "source %r is not a .py file: only code can be harvested" % m.group("path"), None
    stem = os.path.splitext(os.path.basename(real))[0]
    in_recetas = real.startswith(os.path.realpath(os.path.join(REPO, "recetas")) + os.sep)
    recipe_mods = {v["module"] for v in REGISTRY.values()}
    if in_recetas and (stem in INFRA or stem in recipe_mods):
        return ("source %s is motor infrastructure / an already-registered recipe: not this asset's own work"
                % m.group("path")), None
    lo = int(m.group("a"))
    hi = int(m.group("b") or lo)
    try:
        with open(real, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=real)
    except (OSError, SyntaxError, ValueError) as e:
        return "cannot parse %s (%s)" % (real, e), None
    if not (1 <= lo <= hi):
        return "source %s has an invalid line range" % src, None
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and n.lineno <= lo and hi <= n.end_lineno:
            if best is None or n.lineno >= best.lineno:        # innermost
                best = n
    if best is None:
        return "source %s:%d-%d is not inside a def/class body (module-level lines are not a technique)" % (
            m.group("path"), lo, hi), None
    why = _trivial(best)
    if why:
        return "source %s:%d-%d cites `%s` whose %s" % (m.group("path"), lo, hi, best.name, why), None
    return None, real


def _gen_paths(asset_dir, generators):
    out = []
    for g in generators or []:
        g = os.path.expanduser(str(g))
        out.append(g if os.path.isabs(g) else os.path.join(asset_dir or "", g))
    return out


def _check_promoted(technique, real, snapshot, asset_dir, generators):
    if not is_registered(technique):
        return "promoted technique %r is not in recetas/technique_registry.py" % (technique,)
    if not isinstance(snapshot, list):
        return ("cannot prove %r is new: the manifest has no `registry_snapshot` (re-run start_asset or "
                "record one explicitly)" % (technique,))
    if _key(technique) in {_key(x) for x in snapshot}:
        return "%r was already registered when this asset started (registry_snapshot): not learned here" % (technique,)
    in_asset = bool(real and asset_dir and (real == os.path.realpath(asset_dir)
                                            or real.startswith(os.path.realpath(asset_dir) + os.sep)))
    if not in_asset and not any(os.path.isfile(g) and evidence(g, technique)[0]
                                for g in _gen_paths(asset_dir, generators)):
        return ("this asset does not own %r: its source is not in the asset dir and no manifest generator "
                "imports AND calls it with part=" % (technique,))
    return None


def _check_none(none, asset_dir, generators):
    cat, _, arg = none.partition(":")
    if cat not in NONE_CATEGORIES or not arg.strip():
        return ["harvest `none` must be one of %s (closed list, no free text); got %r"
                % (" | ".join("%s:<...>" % c for c in NONE_CATEGORIES), none[:60])]
    if cat == "asset_specific":
        err, _real = _check_source(arg.strip(), asset_dir)
        return ["asset_specific: " + err] if err else []
    techs = [t.strip() for t in arg.split(",") if t.strip()]
    if not techs:
        return ["reused_only needs a technique list"]
    gens = _gen_paths(asset_dir, generators)
    problems = []
    for t in techs:
        if not is_registered(t):
            problems.append("reused_only: %r is not a registered technique" % t)
        elif not any(os.path.isfile(g) and evidence(g, t)[0] for g in gens):
            problems.append("reused_only: no manifest generator imports AND calls %r with part=" % t)
    return problems


def validate(section, asset_dir=None, snapshot=None, generators=None):
    """(ok, problems, summary). `section` is manifest.get("harvest"); `snapshot`
    (manifest.registry_snapshot) and `generators` come from the same manifest."""
    if section is None:
        return False, ["manifest has NO `harvest` section (run tools/harvest_asset.py)"], ""
    if not isinstance(section, dict):
        return False, ["`harvest` must be an object, got %s" % type(section).__name__], ""
    entries = section.get("entries") or []
    none = section.get("none")
    none_s = none.strip() if isinstance(none, str) else ""
    if not entries and not none_s:
        if none is True:
            return False, ["`none: true` carries no reason: use reused_only:<techniques> or asset_specific:<file:line>"], ""
        return False, ["harvest section is EMPTY: list the techniques promoted/proposed, or declare "
                       "`none` as reused_only:<techniques> / asset_specific:<file:line>"], ""
    if entries and none_s:
        return False, ["harvest has both `entries` and `none`: pick one"], ""
    if none_s:
        problems = _check_none(none_s, asset_dir, generators)
        return (False, problems, "") if problems else (True, [], "none: " + none_s[:70])
    if not isinstance(entries, list):
        return False, ["`entries` must be a list"], ""
    problems, seen_src, seen_tech = [], set(), set()
    for i, e in enumerate(entries):
        tag = "entries[%d]" % i
        if not isinstance(e, dict):
            problems.append("%s is not an object" % tag)
            continue
        err, real = _check_source(e.get("source"), asset_dir)
        if err:
            problems.append("%s: %s" % (tag, err))
        key = re.sub(r"\s+", "", str(e.get("source") or ""))
        if key in seen_src:
            problems.append("%s: duplicate source %s" % (tag, e.get("source")))
        seen_src.add(key)
        tech = _key(e.get("technique")) if e.get("technique") else None
        if tech:
            if tech in seen_tech:
                problems.append("%s: technique %r listed twice" % (tag, e.get("technique")))
            seen_tech.add(tech)
        why = str(e.get("why") or "")
        words = {w.lower() for w in re.findall(r"[^\W\d_]{3,}", why)}
        if len(words) < MIN_WORDS:
            problems.append("%s: `why` needs >= %d distinct words of >= 3 letters" % (tag, MIN_WORDS))
        st = e.get("status")
        if st not in STATUSES:
            problems.append("%s: status %r is not one of %s" % (tag, st, "/".join(STATUSES)))
        elif st == "promoted":
            err = _check_promoted(e.get("technique"), real, snapshot, asset_dir, generators)
            if err:
                problems.append("%s: %s" % (tag, err))
    if problems:
        return False, problems, ""
    return True, [], "%d entr%s (%s)" % (
        len(entries), "y" if len(entries) == 1 else "ies",
        ", ".join(str(e.get("technique") or e["source"]) for e in entries[:3]))
