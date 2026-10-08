# rubric.py -- the human/visual half of the verdict, as data that cannot be skipped.
#
# WHY THIS EXISTS (2026-10-08)
#
# The gates measure properties (topology, scale, glTF validity, structure rows).
# They cannot say whether the thing LOOKS right, and "a metric is evidence only
# for the specific thing it measures" (memory: look-before-you-report). So the
# motor writes, next to every verdict, a rubric a reviewer must fill in by LOOKING
# at the evidence renders -- and the overall status cannot be PASS until they do.
#
#   gates pass, rubric PENDING   -> EVIDENCE_READY   (never PASS)
#   rubric filled, all good      -> PASS (or PASS_WITH_GAPS if gaps are open)
#   any score < 3 or any "no"    -> FAIL
#
# DIMENSIONS: the five 3D-asset quality axes of GPTEval3D / 3DGen-Bench (per
# Joan's brief 2026-10-08): 3D plausibility, geometry detail, texture quality,
# geometry-texture coherence, prompt fidelity. Scores are 1-5.
#
# QUESTIONS: yes/no understanding questions in the ShapeCraft/VQA style, derived
# from what the router already KNOWS about the subject's family (structure rows,
# discarded techniques, required views, physics, declared gaps). Each cites the
# router field it came from, so a question can always be traced to its source.
#
# NO external AI API is called anywhere here. The reviewer is Joan or Claude
# looking at the files named in `evidence`.
import datetime
import os

DIMENSIONS = {
    "plausibility_3d": "Does it hold together as a physically plausible 3D object "
                       "from every view (no impossible joins, floating or "
                       "interpenetrating parts)?",
    "geometry_detail": "Is the geometric detail adequate for the use size: "
                       "silhouette, secondary forms, no blocky or noisy surface?",
    "texture_quality": "Is the colour/texture quality adequate: resolution, "
                       "no seams, no flat or washed-out regions?",
    "geometry_texture_coherence": "Do colour/texture and geometry agree (colour "
                                  "breaks follow form; nothing painted that the "
                                  "geometry contradicts)?",
    "prompt_fidelity": "Does it read as the requested subject ({subject!r}) at "
                       "the use size, next to the 1.80 m reference?",
}

PASS_MIN_SCORE = 3          # initial, uncalibrated: below this a dimension fails
ANSWERS = ("yes", "no", "na")

# What each ungrateful/standard view is FOR (views.py comments, the 2026-08-25
# review): the question asked of that view.
VIEW_QUESTIONS = {
    "cenital": "From 'cenital', is the layout right (symmetry, limb/part "
               "directions, nothing pointing the wrong way)?",
    "perfil": "In 'perfil', does anything protrude through a surface or float "
              "away from the body?",
    "atras": "In 'atras', does any glued-on geometry separate from the body or "
             "is there an artefact only visible from behind?",
    "bajo": "In 'bajo', is the underside closed, with no open gaps or floating "
            "parts?",
    "macro_placa": "In 'macro_placa', does the surface detail read at close "
                   "range (no smeared or missing detail)?",
    "tresq_alto": "In 'tresq_alto', is the overall form what the family note "
                  "says it should be?",
    "frente": "In 'frente', does the stance/face read correctly beside the "
              "1.80 m mannequin?",
}


def _q(qs, text, source, ref=""):
    qs.append({"id": "q%02d" % (len(qs) + 1), "text": text, "source": source,
               "ref": ref, "answer": None, "note": ""})


def derive_questions(subject, rules, req, structure_rows=None):
    """
    Yes/no questions from the router's knowledge of the matched families.

    rules          list of Rules (preflight_router.route_all)
    req            preflight_router.requirements(subject)
    structure_rows {category: {part: {plano, angulo, limite}}} read from the
                   family's structure spec (asset_spec.parse_structure)
    """
    qs = []
    structure_rows = structure_rows or {}
    if not rules:
        _q(qs, "The subject %r has no registered family: is it recognisable as "
               "what was asked for?" % subject, "router:unknown")
    for r in rules:
        cat, d = r.category, r.data
        if d.get("mannequin_m"):
            sz = [x for x in d.get("size_ranges", [])]
            extra = (" Sourced size: %s." % "; ".join(
                "%s %s %.2f-%.2f m" % (x["aliases"][0], x["dim"], *x["range_m"])
                for x in sz)) if sz else ""
            _q(qs, "Is the asset in believable proportion to the 1.80 m mannequin "
                   "in 'frente' and 'perfil'?" + extra,
               "router:%s.mannequin_m" % cat,
               (sz[0]["source"] if sz else ""))
        for label in d.get("required_views", []):
            if label in VIEW_QUESTIONS:
                _q(qs, VIEW_QUESTIONS[label],
                   "router:%s.required_views[%s]" % (cat, label),
                   "recetas/views.py:VIEWS")
        for part, row in (structure_rows.get(cat) or {}).items():
            _q(qs, "Is the part '%s' %s, at %s, limited by: %s?"
                   % (row["raw"], row["plano"], row["angulo"], row["limite"]),
               "router:%s.structure_spec#%s" % (cat, part),
               "recetas/specs/%s/_structure_spec.md" % cat)
        ph = d.get("physics")
        if ph and ph.get("stands"):
            _q(qs, "Does the asset visibly rest on the ground plane in 'frente' "
                   "and 'perfil' (no floating, no sinking), with every limb or "
                   "support that should bear weight touching it?",
               "router:%s.physics.stands" % cat, ph.get("source", ""))
        elif ph and ph.get("stands") is False:
            _q(qs, "The family is declared NOT standing (%s): is it clearly "
                   "airborne/placed rather than resting wrongly on the ground?"
                   % ph.get("reason", ph.get("basis", "")),
               "router:%s.physics.stands" % cat, ph.get("source", ""))
        for key in d.get("discarded", {}):
            _q(qs, "Does the result avoid the ruled-out technique '%s' (%s)?"
                   % (key, d["discarded"][key].split(".")[0][:110]),
               "router:%s.discarded[%s]" % (cat, key),
               d.get("discarded_sources", {}).get(key, ""))
        for gap in d.get("gaps", []):
            _q(qs, "OPEN GAP: %s -- is it acceptable to ship with this hole "
                   "declared?" % gap, "router:%s.gaps" % cat)
    return qs


def build_rubric(subject, rules, req, structure_rows=None):
    return {
        "status": "PENDING",
        "reviewer": None,
        "date": None,
        "pass_rule": ("every dimension >= %d and every answer yes/na "
                      "(initial, uncalibrated)" % PASS_MIN_SCORE),
        "dimensions": {
            name: {"prompt": text.format(subject=subject), "score": None,
                   "note": ""}
            for name, text in DIMENSIONS.items()},
        "questions": derive_questions(subject, rules, req, structure_rows),
    }


def rubric_status(rubric):
    """PENDING until every score and answer is in; then PASS or FAIL."""
    dims = rubric["dimensions"].values()
    if any(d["score"] is None for d in dims):
        return "PENDING"
    if any(q["answer"] is None for q in rubric["questions"]):
        return "PENDING"
    if any(d["score"] < PASS_MIN_SCORE for d in dims):
        return "FAIL"
    if any(q["answer"] == "no" for q in rubric["questions"]):
        return "FAIL"
    return "PASS"


def overall_status(verdict):
    """
    The one word a human reads. Never PASS while the rubric is PENDING.

        FAIL            a gate failed, or the rubric failed
        EVIDENCE_READY  gates passed; waiting for a reviewer to look
        PASS            gates + rubric passed
        PASS_WITH_GAPS  same, with declared gaps still open
    """
    if verdict.get("verdict") == "FAIL":
        return "FAIL"
    rub = verdict.get("rubric")
    if not rub:
        return "EVIDENCE_READY"          # no rubric at all is not a pass either
    st = rubric_status(rub)
    if st == "PENDING":
        return "EVIDENCE_READY"
    if st == "FAIL":
        return "FAIL"
    return "PASS_WITH_GAPS" if verdict.get("gaps") else "PASS"


class RubricError(ValueError):
    pass


def set_score(rubric, dim, score, note=""):
    if dim not in rubric["dimensions"]:
        raise RubricError("unknown dimension %r; known: %s"
                          % (dim, ", ".join(rubric["dimensions"])))
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
        raise RubricError("score for %s must be an integer 1-5, got %r" % (dim, score))
    if score < PASS_MIN_SCORE and not note.strip():
        raise RubricError("a score of %d on %s needs a note saying what is wrong"
                          % (score, dim))
    rubric["dimensions"][dim].update(score=score, note=note)


def set_answer(rubric, qid, answer, note=""):
    q = next((x for x in rubric["questions"] if x["id"] == qid), None)
    if q is None:
        raise RubricError("unknown question %r" % qid)
    if answer not in ANSWERS:
        raise RubricError("answer must be one of %s, got %r" % (ANSWERS, answer))
    if answer in ("no", "na") and not note.strip():
        raise RubricError("answer %r on %s needs a note" % (answer, qid))
    q.update(answer=answer, note=note)


def apply_review(verdict, reviewer, scores=None, answers=None, today=None):
    """
    Apply {dim: (score, note)} and {qid: (answer, note)} to a verdict dict, refuse
    if the evidence files it names are gone, recompute statuses. Returns the
    overall status.
    """
    if not reviewer or not reviewer.strip():
        raise RubricError("a reviewer name is required (who looked?)")
    missing = [p for p in verdict.get("evidence", []) if not os.path.isfile(p)]
    if missing:
        raise RubricError("the evidence this rubric judges is gone: %s"
                          % ", ".join(os.path.basename(m) for m in missing[:4]))
    if not verdict.get("evidence"):
        raise RubricError("this verdict names no evidence renders to judge")
    rub = verdict["rubric"]
    for dim, (score, note) in (scores or {}).items():
        set_score(rub, dim, score, note)
    for qid, (ans, note) in (answers or {}).items():
        set_answer(rub, qid, ans, note)
    rub["reviewer"] = reviewer
    rub["date"] = (today or datetime.date.today()).isoformat()
    rub["status"] = rubric_status(rub)
    verdict["status"] = overall_status(verdict)
    return verdict["status"]
