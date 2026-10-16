# RECETA: probe_with_control -- a probe may only report "clean" if its control fired.
# QUE: every measurement is paired with a CONTROL: the same instrument pointed at an
#      input that is known to be bad (the skirt shrunk 15%, the cuff lifted 1.2 cm, the
#      strap moved 0.15 cm off the back). The control MUST register the INTENDED defect. If the
#      measured input reads clean and the control did NOT fire, the instrument is blind
#      and the row is NOT_TESTED -- never PASS. A zero from a blind probe and a zero from
#      a working probe look identical and neither raises an error.
# CUANDO: any "is there a defect?" measurement whose answer you would otherwise trust
#      when it comes back empty: clearances, penetrations, floating islands, distances,
#      counts, a grep that returned 0.
# LECCIONES: LECCIONES.md#3 (metricas ciegas: correr un control positivo), #12 (el banco
#      de pruebas tambien necesita su control positivo: la geometria de prueba tiene que
#      poder expresar el defecto), #14 (NOT_TESTED no es aprobado). rana_bake_check's halo
#      probe was blind THREE times (clip_start, inactive vcol layer, diluted band) and
#      each one returned a confident clean number.
# FUENTE: rem/v8/rem_v8_measure.py:28 `row(name, ok, detail, control)` + its 21 checks,
#      each with a shrunken/moved control that must fail. This module ENFORCES the pairing
#      instead of printing it.
# EXEMPLAR:
#   ps = ProbeSet("rem v8")
#   ps.probe("skirt_clear_of_body",
#            measure=lambda cloth: count_inside(cloth),   # same instrument on both inputs
#            ok=lambda n: n == 0,                         # True = clean
#            subject=skirt, control=skirt_shrunk_15pct,
#            intended=lambda n: n > 0,                    # the control must fail FOR THIS reason
#            detail=lambda n: "%d verts inside" % n)
#   ps.zero("legs_clear_of_cloth", touches, skirt, skirt_shrunk)    # count==0 sugar
#   print(ps.report.render()); ps.report.require_complete()
# There is deliberately NO way to write "the control fired" by hand: the verdict is derived
# from running `measure` on the control here (cosecha-1 review: a self-declared flag made the
# whole pairing decorative). stdlib only: usable inside Blender, a hook, or plain python3.
import json

try:
    from recetas.verdict import Report, PASS, FAIL, NOT_TESTED
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from verdict import Report, PASS, FAIL, NOT_TESTED

BLIND = "instrument blind: the control did not fire"
WRONG_REASON = "control failed, but not for the intended defect"


def judge(ok_subject, control_fired):
    """The whole rule in one place. Returns the verdict state.

    subject defective            -> FAIL (a defect is a defect, control or not)
    subject clean, control fired -> PASS
    subject clean, control quiet -> NOT_TESTED (a clean reading from a blind probe)
    """
    if not ok_subject:
        return FAIL
    return PASS if control_fired else NOT_TESTED


class ProbeSet:
    """A Report whose rows are control-paired probes."""

    def __init__(self, subject):
        self.report = Report(subject)
        self.rows = []     # machine-readable twin of report.rows (for json)

    def _record(self, name, state, detail, ok, control_fired, control_detail):
        self.report.add(name, state, detail)
        self.rows.append({"name": name, "state": state, "ok": ok,
                          "control_fired": control_fired,
                          "detail": detail, "control_detail": control_detail})
        return state

    def probe(self, name, measure, ok, subject, control, intended, detail=None):
        """Run `measure` on the subject AND on the control with the SAME instrument.
        `ok(value)` is True for a clean reading. For the control to count as FIRED it must
        (1) make ok() False AND (2) satisfy `intended(value)`, the predicate naming the
        defect the control was built to expose; failing for any other reason is reported
        as WRONG_REASON and the clean subject stays NOT_TESTED."""
        if not callable(intended):
            raise TypeError("probe(): `intended` is required -- say WHICH defect the control exposes")
        try:
            value = measure(subject)
            ctrl_value = measure(control)
            clean = bool(ok(value))
            fails = not ok(ctrl_value)
            fired = fails and bool(intended(ctrl_value))
            vacuous = clean and bool(intended(value))
        except Exception as e:  # noqa: BLE001 -- a crash ANYWHERE (measure, ok, intended) is not a clean probe
            return self._record(name, NOT_TESTED, "probe crashed: %s: %s" % (type(e).__name__, e),
                                None, None, "")
        fmt = detail or (lambda v: repr(v))
        if vacuous:
            # `intended` is True on the CLEAN subject: it cannot tell the defect from a good
            # reading (lambda v: True would make every control "fire"), so it proves nothing.
            return self._record(name, NOT_TESTED,
                                "%s   [control: %s]   <-- intended predicate is vacuous: it is also true on the clean subject"
                                % (fmt(value), fmt(ctrl_value)), clean, False, fmt(ctrl_value))
        text = fmt(value)
        text += "   [control: %s]" % fmt(ctrl_value)
        if clean and not fired:
            text += "   <-- %s" % (BLIND if not fails else WRONG_REASON)
        if not clean and not fired:
            text += "   (defect found; note the control ALSO slipped through)"
        return self._record(name, judge(clean, fired), text, clean, fired, fmt(ctrl_value))

    def zero(self, name, count, subject, control, unit="hit(s)"):
        """Sugar for the commonest case: 'count(subject) must be 0'; the control must make
        it > 0. `count` is a callable run on both inputs."""
        return self.probe(name, count, lambda n: n == 0, subject, control,
                          intended=lambda n: n > 0,
                          detail=lambda n: "%s %s" % (n, unit))

    def to_json(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"subject": self.report.subject, "verdict": self.report.verdict(),
                       "rows": self.rows}, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        return path
