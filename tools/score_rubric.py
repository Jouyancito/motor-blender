#!/usr/bin/env python3
"""score_rubric.py -- fill in the visual rubric of a motor_verdict.json.

    python3 tools/score_rubric.py <motor_verdict.json>                 interactive
    python3 tools/score_rubric.py <json> --reviewer Joan \
        --score plausibility_3d=4 --score texture_quality=2:"seams on the belly" \
        --answer q03=yes --answer q05=no:"tail floats"                  batch
    python3 tools/score_rubric.py <json> --show                         print only

Look at the files listed under `evidence` FIRST. Scores are 1-5 (below 3 needs a
note); answers are yes / no / na (no and na need a note). The overall status flips
from EVIDENCE_READY to PASS or FAIL only when every score and answer is in.
No external AI API is called.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from recetas import rubric as R  # noqa: E402


def parse_pair(text, cast=str):
    key, _, rest = text.partition("=")
    val, _, note = rest.partition(":")
    return key.strip(), (cast(val.strip()), note.strip())


def show(v):
    rub = v["rubric"]
    print("\nstatus: %s   (gates: %s; rubric: %s; reviewer: %s)"
          % (v.get("status"), v.get("verdict"), rub["status"], rub["reviewer"]))
    print("evidence:")
    for p in v.get("evidence", []):
        print("   ", p)
    print("dimensions:")
    for k, d in rub["dimensions"].items():
        print("  %-28s %s  %s" % (k, d["score"] if d["score"] else "-", d["note"]))
    print("questions:")
    for q in rub["questions"]:
        print("  %s [%s] %s\n        source: %s" % (
            q["id"], q["answer"] or "-", q["text"], q["source"]))


def interactive(v):
    rub = v["rubric"]
    scores, answers = {}, {}
    print("Look at the evidence renders first:")
    for p in v.get("evidence", []):
        print("   ", p)
    for k, d in rub["dimensions"].items():
        while True:
            raw = input("\n%s\n  %s\n  score 1-5 (note after ':'; enter = skip): "
                        % (k, d["prompt"])).strip()
            if not raw:
                break
            s, _, note = raw.partition(":")
            try:
                R.set_score(rub, k, int(s), note.strip())
                scores[k] = (int(s), note.strip())
                break
            except (ValueError, R.RubricError) as exc:
                print("  ->", exc)
    for q in rub["questions"]:
        while True:
            raw = input("\n%s  %s\n  (source %s)\n  yes/no/na (note after ':'; "
                        "enter = skip): " % (q["id"], q["text"], q["source"])).strip()
            if not raw:
                break
            a, _, note = raw.partition(":")
            try:
                R.set_answer(rub, q["id"], a.strip(), note.strip())
                answers[q["id"]] = (a.strip(), note.strip())
                break
            except R.RubricError as exc:
                print("  ->", exc)
    return scores, answers


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verdict")
    ap.add_argument("--reviewer")
    ap.add_argument("--score", action="append", default=[], help="dim=N[:note]")
    ap.add_argument("--answer", action="append", default=[], help="qid=yes|no|na[:note]")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args(argv)

    with open(args.verdict, encoding="utf-8") as fh:
        v = json.load(fh)
    if "rubric" not in v:
        raise SystemExit("this verdict has no rubric block (written by an older motor_run)")
    if args.show:
        show(v)
        return 0
    try:
        if args.score or args.answer:
            scores = dict(parse_pair(s, int) for s in args.score)
            answers = dict(parse_pair(a) for a in args.answer)
        else:
            if not args.reviewer:
                args.reviewer = input("reviewer name: ").strip()
            scores, answers = interactive(v)
        status = R.apply_review(v, args.reviewer, scores, answers)
    except (R.RubricError, ValueError) as exc:
        raise SystemExit("score_rubric: %s" % exc)
    with open(args.verdict, "w", encoding="utf-8") as fh:
        json.dump(v, fh, indent=2, default=str)
    show(v)
    print("\nWritten. Overall status: %s" % status)
    return 0 if status in ("PASS", "PASS_WITH_GAPS", "EVIDENCE_READY") else 1


if __name__ == "__main__":
    sys.exit(main())
