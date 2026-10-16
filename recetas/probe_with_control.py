# RECETA: probe_with_control -- a probe may only report "clean" if its control fired.
# QUE: every measurement is paired with a CONTROL: the same instrument pointed at an
#      input that is known to be bad (the skirt shrunk 15%, the cuff lifted 1.2 cm, the
#      strap moved 0.15 cm off the back). The control MUST register the defect. If the
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
#            measure=lambda cloth: count_inside(cloth),   # value for one input
#            ok=lambda n: n == 0,                         # True = clean
#            subject=skirt, control=skirt_shrunk_15pct,   # control must make ok() False
#            detail=lambda n: "%d verts inside" % n)
#   ps.zero("legs_clear_of_cloth", touches, control_touches)   # count==0 sugar
#   print(ps.report.render()); ps.report.require_complete()
# stdlib only: usable inside Blender, a hook, or plain python3.
import json

try:
    from recetas.verdict import Report, PASS, FAIL, NOT_TESTED
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from verdict import Report, PASS, FAIL, NOT_TESTED

BLIND = "instrument blind: the control did not fire"


def judge(ok_subject, control_fired):
    """The whole rule in one place. Returns the verdict state.

    subject defective            -> FAIL (a defect is a defect, control or not)
    subject clean, control fired -> PASS
    subject clean, control quiet -> NOT_TESTED (a clean reading from a blind probe)
    subject clean, no control    -> NOT_TESTED
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

    def row(self, name, ok, detail="", control_fired=None, control_detail=""):
        """Value-based API: you already measured. `control_fired` is True when the
        control input was caught by the same instrument, False when it slipped
        through, None when no control exists."""
        ok = bool(ok)
        if control_fired is None:
            state = judge(ok, False)
            why = "no control supplied" if ok else ""
        else:
            state = judge(ok, bool(control_fired))
            why = "" if (control_fired or not ok) else BLIND
        text = detail
        if control_detail:
            text += "   [control: %s]" % control_detail
        if why:
            text += "   <-- %s" % why
        if not ok and control_fired is False:
            text += "   (defect found; note the control ALSO slipped through)"
        return self._record(name, state, text, ok, control_fired, control_detail)

    def probe(self, name, measure, ok, subject, control, detail=None):
        """Callable API: run `measure` on the subject AND on the control with the
        SAME instrument. The control is expected to make ok() False."""
        try:
            value = measure(subject)
            ctrl_value = measure(control)
        except Exception as e:  # noqa: BLE001 -- a crashed probe is not a clean probe
            return self._record(name, NOT_TESTED, "probe crashed: %s: %s" % (type(e).__name__, e),
                                None, None, "")
        fmt = detail or (lambda v: repr(v))
        return self.row(name, ok(value), fmt(value),
                        control_fired=not ok(ctrl_value), control_detail=fmt(ctrl_value))

    def zero(self, name, count, control_count, unit="hit(s)"):
        """Sugar for the commonest case: 'count must be 0', control must be > 0."""
        return self.row(name, count == 0, "%s %s" % (count, unit),
                        control_fired=control_count > 0,
                        control_detail="%s %s (must be > 0)" % (control_count, unit))

    def to_json(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"subject": self.report.subject, "verdict": self.report.verdict(),
                       "rows": self.rows}, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        return path
