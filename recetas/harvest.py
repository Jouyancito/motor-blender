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
#           {"source": "rana/rana_gen.py:403-442",      # file:line (or file:line-line)
#            "why": "decal projected on the final surface keeps the body's smooth normals",
#            "status": "promoted",                      # promoted | proposed
#            "technique": "surface_decal"}]}            # required when promoted: must be registered
#
#   (b) an explicit nothing, with a written reason:
#       "harvest": {"none": "built entirely from existing recipes; no new technique appeared"}
#
# Missing section, empty section, empty entries, blank/trivial reason, both forms at once,
# a source that does not resolve to a real file and line, a one-word `why`, or a "promoted"
# technique the registry does not know -> FAIL. Use tools/harvest_asset.py to edit it.
#
# Honest limit: this proves the question was ANSWERED with checkable citations, not that
# the answer is complete. It makes skipping the question a visible, failing act.
import os
import re

try:
    from recetas.technique_registry import is_registered
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from technique_registry import is_registered

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_REASON = 15          # characters of a written reason / why
STATUSES = ("promoted", "proposed")
TRIVIAL = {"none", "n/a", "na", "nada", "nothing", "no", "-", "--", "ninguna", "ninguno",
           "no aplica", "not applicable", "tbd", "todo", "later", "x", "ok"}
_SRC = re.compile(r"^(?P<path>.+):(?P<a>\d+)(?:-(?P<b>\d+))?$")


def empty_section():
    """The template start_asset.py writes: deliberately FAILS until it is filled."""
    return {"entries": [], "none": ""}


def _resolve(path, asset_dir):
    p = os.path.expanduser(path)
    cands = [p] if os.path.isabs(p) else [os.path.join(asset_dir or "", p), os.path.join(REPO, p),
                                          os.path.join(os.path.expanduser("~/proyectos"), p)]
    return next((c for c in cands if os.path.isfile(c)), None)


def _check_source(src, asset_dir):
    m = _SRC.match(str(src or "").strip())
    if not m:
        return "source %r is not file:line" % (src,)
    real = _resolve(m.group("path"), asset_dir)
    if not real:
        return "source file %r does not exist (looked relative to the asset, the motor and ~/proyectos)" % m.group("path")
    lo = int(m.group("a"))
    hi = int(m.group("b") or lo)
    try:
        with open(real, encoding="utf-8", errors="replace") as fh:
            n = sum(1 for _ in fh)
    except OSError as e:
        return "cannot read %s (%s)" % (real, e)
    if not (1 <= lo <= hi <= n):
        return "source %s:%d-%d is outside the file (%d lines)" % (m.group("path"), lo, hi, n)
    return None


def validate(section, asset_dir=None):
    """(ok, problems, summary). `section` is manifest.get("harvest")."""
    if section is None:
        return False, ["manifest has NO `harvest` section (run tools/harvest_asset.py)"], ""
    if not isinstance(section, dict):
        return False, ["`harvest` must be an object, got %s" % type(section).__name__], ""
    entries = section.get("entries") or []
    none = section.get("none")
    none_s = none.strip() if isinstance(none, str) else ""
    problems = []
    if not entries and not none_s:
        if none is True:
            problems.append("`none: true` carries no reason: write WHY nothing was harvested")
        else:
            problems.append("harvest section is EMPTY: list the techniques promoted/proposed, "
                            "or declare `none` with a reason")
        return False, problems, ""
    if entries and none_s:
        return False, ["harvest has both `entries` and `none`: pick one"], ""
    if none_s:
        if none_s.lower() in TRIVIAL or len(none_s) < MIN_REASON:
            return False, ["harvest `none` reason %r is trivial (< %d chars or a placeholder)"
                           % (none_s, MIN_REASON)], ""
        return True, [], "none: " + none_s[:70]
    if not isinstance(entries, list):
        return False, ["`entries` must be a list"], ""
    for i, e in enumerate(entries):
        tag = "entries[%d]" % i
        if not isinstance(e, dict):
            problems.append("%s is not an object" % tag)
            continue
        err = _check_source(e.get("source"), asset_dir)
        if err:
            problems.append("%s: %s" % (tag, err))
        why = str(e.get("why") or "").strip()
        if len(why) < MIN_REASON or why.lower() in TRIVIAL:
            problems.append("%s: `why` must be a real one-line reason (>= %d chars)" % (tag, MIN_REASON))
        st = e.get("status")
        if st not in STATUSES:
            problems.append("%s: status %r is not one of %s" % (tag, st, "/".join(STATUSES)))
        elif st == "promoted" and not is_registered(e.get("technique")):
            problems.append("%s: promoted technique %r is not in recetas/technique_registry.py"
                            % (tag, e.get("technique")))
    if problems:
        return False, problems, ""
    return True, [], "%d entr%s (%s)" % (
        len(entries), "y" if len(entries) == 1 else "ies",
        ", ".join(str(e.get("technique") or e["source"]) for e in entries[:3]))
