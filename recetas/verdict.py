# verdict.py -- four states, because "not measured" must never read as "fine".
#
# WHY THIS EXISTS (2026-09-02, external review)
#
# Four independent models reviewed the motor's method. All four landed on the
# same structural gap: there is no definition of DONE, and every gate returns a
# binary. A binary has nowhere to put "this check did not run", so an unrun
# check silently joins the passes.
#
# The motor already paid for this. The showcase gate asked "is there a PNG
# newer than the .glb?" and four mobs shipped white for a month: the colour
# check had never run, and nothing said so. In a binary world an absent test
# and a passed test are the same value.
#
# So:
#     PASS            the property was checked and holds
#     FAIL            the property was checked and does not hold
#     NOT_TESTED      the check did not run -- MISSING EVIDENCE, not absolution
#     NOT_APPLICABLE  the property does not apply here, with a stated reason
#
# NOT_APPLICABLE requires a reason string. Without one it is indistinguishable
# from NOT_TESTED with better manners, which is exactly how an exemption list
# rots into lesson 8 (a constant nobody maintains, quietly passing builds).
#
# The aggregate is deliberately harsh: a report containing NOT_TESTED is NOT
# a pass. It is incomplete, and it says which rows are missing.
#
# USAGE
#     from recetas.verdict import Report, PASS, FAIL, NOT_TESTED, NOT_APPLICABLE
#
#     r = Report("turtle")
#     r.add("glb_has_colour", PASS, "COLOR_0 present, 1834 verts")
#     r.add("material_varies", FAIL, "detail=0.00002 < 0.00010")
#     r.add("motion_spec", NOT_TESTED, "no gait capture this run")
#     r.add("clothing_fit", NOT_APPLICABLE, reason="asset has no garments")
#     print(r.render())
#     r.require_complete()      # SystemExit unless every row is PASS/N/A

PASS = "PASS"
FAIL = "FAIL"
NOT_TESTED = "NOT_TESTED"
NOT_APPLICABLE = "NOT_APPLICABLE"

_STATES = (PASS, FAIL, NOT_TESTED, NOT_APPLICABLE)

# Fixed width so a stack of reports lines up in a terminal and a missing row is
# visible at a glance rather than needing to be read.
_MARK = {
    PASS: "  PASS ",
    FAIL: "  FAIL ",
    NOT_TESTED: " !NOEV ",       # no evidence
    NOT_APPLICABLE: "  n/a  ",
}


class Report:
    """A checklist of properties with an honest four-state verdict each."""

    def __init__(self, subject):
        self.subject = subject
        self.rows = []

    def add(self, prop, state, detail="", reason=""):
        if state not in _STATES:
            raise ValueError("unknown state %r; use one of %s" % (state, _STATES))
        if state == NOT_APPLICABLE and not reason:
            # Refusing this is the whole point: an unreasoned exemption is an
            # untested property wearing a costume.
            raise ValueError(
                "NOT_APPLICABLE on %r needs an explicit reason -- without one it "
                "is NOT_TESTED with better manners, and that is how an exemption "
                "list turns into lesson 8." % prop)
        self.rows.append({"prop": prop, "state": state,
                          "detail": detail, "reason": reason})
        return self

    # -- queries -----------------------------------------------------------

    def by_state(self, state):
        return [r for r in self.rows if r["state"] == state]

    @property
    def failed(self):
        return self.by_state(FAIL)

    @property
    def untested(self):
        return self.by_state(NOT_TESTED)

    def is_complete(self):
        """Complete = every property either holds or is reasoned inapplicable."""
        return not self.failed and not self.untested

    def verdict(self):
        if self.failed:
            return FAIL
        if self.untested:
            return NOT_TESTED     # incomplete is NOT a pass
        return PASS

    # -- output ------------------------------------------------------------

    def render(self):
        width = max([len(r["prop"]) for r in self.rows] + [12])
        lines = ["", "  %s -- %s" % (self.subject, self.verdict()),
                 "  " + "-" * (width + 40)]
        for r in self.rows:
            note = r["detail"] or r["reason"]
            lines.append("  %s %s  %s" % (_MARK[r["state"]],
                                          r["prop"].ljust(width), note))
        if self.untested:
            lines.append("")
            lines.append("  %d propiedad(es) SIN EVIDENCIA. Eso no es aprobado:"
                         % len(self.untested))
            for r in self.untested:
                lines.append("    - %s" % r["prop"])
        return "\n".join(lines) + "\n"

    def require_complete(self):
        """SystemExit unless every property is PASS or reasoned NOT_APPLICABLE."""
        if self.is_complete():
            return self
        raise SystemExit(
            self.render() + "\n"
            "El asset NO está terminado. Un FAIL es un defecto; un NOT_TESTED es\n"
            "una propiedad que nadie miró — y en un veredicto binario esas dos se\n"
            "confunden con un pase. Corré el check que falta o declaralo\n"
            "NOT_APPLICABLE con su razón.")
