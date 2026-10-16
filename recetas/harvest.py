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
#            "technique": "mpfb_human_base"}]}          # promoted: must be registered AND not predate the manifest
#
#   (b) an explicit nothing, from a CLOSED list of reasons (free text is not accepted):
#       "harvest": {"none": "reused_only:bvh_glue,paint_por_geometria"}   # each registered AND
#                                                       # called with part= by a manifest generator
#       "harvest": {"none": "asset_specific:gen.py:42"} # real code in the asset that has no reuse value
#
# Source rules: the file resolves INSIDE the asset dir or the motor's recetas/ (no ../,
# no absolute paths elsewhere, symlinks resolved), is a .py file, and the cited lines sit
# inside ONE def/class body. A promoted technique must be a registry id whose module was
# first committed AFTER the manifest was created (a technique that already existed was
# not learned from this asset). Missing/empty section, a reason outside the closed list,
# both forms at once, a one-word `why` -> FAIL. Use tools/harvest_asset.py to edit it.
#
# Honest limit: this proves the question was ANSWERED with checkable citations, not that
# the answer is complete. It makes skipping the question a visible, failing act.
import ast
import os
import re
import subprocess
import time

try:
    from recetas.technique_registry import REGISTRY, is_registered, evidence, _key
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from technique_registry import REGISTRY, is_registered, evidence, _key

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_WORDS = 3            # a `why` is a sentence, not a token
MIN_WHY = 15
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


def _check_source(src, asset_dir):
    """None when `src` ('file.py:12' / 'file.py:12-30') is a real citation: inside the asset
    dir or recetas/, a .py file, lines within ONE def/class body. Else the reason."""
    m = _SRC.match(str(src or "").strip())
    if not m:
        return "source %r is not file:line" % (src,)
    raw = os.path.expanduser(m.group("path"))
    cands = [raw] if os.path.isabs(raw) else [os.path.join(asset_dir or "", raw), os.path.join(REPO, raw)]
    real = next((os.path.realpath(c) for c in cands if os.path.isfile(c)), None)
    if not real:
        return "source file %r does not exist (relative to the asset dir or the motor)" % m.group("path")
    if not _inside(real, _roots(asset_dir)):
        return "source %r resolves outside the asset dir and recetas/ (%s)" % (m.group("path"), real)
    if not real.endswith(".py"):
        return "source %r is not a .py file: only code can be harvested" % m.group("path")
    lo = int(m.group("a"))
    hi = int(m.group("b") or lo)
    try:
        with open(real, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=real)
    except (OSError, SyntaxError, ValueError) as e:
        return "cannot parse %s (%s)" % (real, e)
    if not (1 <= lo <= hi):
        return "source %s has an invalid line range" % src
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and n.lineno <= lo and hi <= n.end_lineno:
            return None
    return "source %s:%d-%d is not inside a def/class body (module-level lines are not a technique)" % (
        m.group("path"), lo, hi)


def _module_first_commit(module):
    """Epoch of the commit that first added recetas/<module>.py, or None."""
    try:
        out = subprocess.run(
            ["git", "-C", REPO, "log", "--diff-filter=A", "--format=%ct", "--", "recetas/%s.py" % module],
            capture_output=True, text=True, timeout=30).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    return min(int(x) for x in out) if out else None


def _created_epoch(created):
    try:
        return time.mktime(time.strptime(str(created), "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None


def _check_promoted(technique, created):
    if not is_registered(technique):
        return "promoted technique %r is not in recetas/technique_registry.py" % (technique,)
    t0 = _created_epoch(created)
    if t0 is None:
        return "cannot prove %r postdates the asset: manifest has no valid `created`" % (technique,)
    module = REGISTRY[_key(technique)]["module"]
    t1 = _module_first_commit(module)
    if t1 is None:
        return "recetas/%s.py is not committed in git: cannot date the promotion" % module
    if t1 <= t0:
        return ("%r predates this asset (recetas/%s.py first committed %s, manifest created %s): "
                "it was not learned from here"
                % (technique, module, time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t1)), created))
    return None


def _check_none(none, asset_dir, generators):
    cat, _, arg = none.partition(":")
    if cat not in NONE_CATEGORIES or not arg.strip():
        return ["harvest `none` must be one of %s (closed list, no free text); got %r"
                % (" | ".join("%s:<...>" % c for c in NONE_CATEGORIES), none[:60])]
    if cat == "asset_specific":
        err = _check_source(arg.strip(), asset_dir)
        return ["asset_specific: " + err] if err else []
    techs = [t.strip() for t in arg.split(",") if t.strip()]
    if not techs:
        return ["reused_only needs a technique list"]
    gens = []
    for g in generators or []:
        g = os.path.expanduser(str(g))
        gens.append(g if os.path.isabs(g) else os.path.join(asset_dir or "", g))
    problems = []
    for t in techs:
        if not is_registered(t):
            problems.append("reused_only: %r is not a registered technique" % t)
        elif not any(os.path.isfile(g) and evidence(g, t)[0] for g in gens):
            problems.append("reused_only: no manifest generator imports AND calls %r with part=" % t)
    return problems


def validate(section, asset_dir=None, created=None, generators=None):
    """(ok, problems, summary). `section` is manifest.get("harvest"); `created` and
    `generators` come from the same manifest."""
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
    problems = []
    for i, e in enumerate(entries):
        tag = "entries[%d]" % i
        if not isinstance(e, dict):
            problems.append("%s is not an object" % tag)
            continue
        err = _check_source(e.get("source"), asset_dir)
        if err:
            problems.append("%s: %s" % (tag, err))
        why = str(e.get("why") or "").strip()
        if len(why) < MIN_WHY or len(why.split()) < MIN_WORDS:
            problems.append("%s: `why` must be a one-line sentence (>= %d words, >= %d chars)" % (tag, MIN_WORDS, MIN_WHY))
        st = e.get("status")
        if st not in STATUSES:
            problems.append("%s: status %r is not one of %s" % (tag, st, "/".join(STATUSES)))
        elif st == "promoted":
            err = _check_promoted(e.get("technique"), created)
            if err:
                problems.append("%s: %s" % (tag, err))
    if problems:
        return False, problems, ""
    return True, [], "%d entr%s (%s)" % (
        len(entries), "y" if len(entries) == 1 else "ies",
        ", ".join(str(e.get("technique") or e["source"]) for e in entries[:3]))
