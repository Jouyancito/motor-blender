#!/usr/bin/env python3
"""gate360.py — GATE 360 verdicts over the fixed 13-view capture (v1.1, 2026-07-12).

Extends the semantic-region gate to all angles (design from the 2026-07-09 research:
fixed cameras; front/back judged against the 2D refs; laterals by L/R symmetry;
the rest by cheap per-view rules; VLM only as a manual escalator, not wired here).

Per view:
  front / back  -> full region gate (subprocess gate_regions.py) + box-center drift
  side_L/side_R -> mirror symmetry: silhouette IoU (FAIL) + hue-class cells (WARN —
                   the key light is not symmetric, raw color diff would false-fail)
  ALL views     -> cheap rules: red (wound), enclosed holes (see-through), floating
                   fragments, dark stain blob, off-palette paint, frame clipping
  ALL views     -> change tripwire (state committed only AFTER verdicts succeed)
Plus: orientation.json (geometric audits from capture) folded into the verdict —
a SKIP there counts as FAIL (the audit is a mandatory input, not optional).

v1.1 (post ultracode review): cheap rules no longer skipped on front/back, stale
subprocess reports impossible, SKIP-region and SKIP-audit accounting, box-center
drift check, off-palette + frame-clip rules, per-view tripwire state fixed.

Run (WSL conda env `critic`):
  python gate360.py --views ./views --out ./out [--expect-change]
Exit code = number of FAILs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "region_gate"))
from gate_regions import load_rgb, fg_mask, segment  # noqa: E402

REFS = os.path.abspath(os.path.join(HERE, "..", "..", "_refs"))
GATE_REGIONS = os.path.abspath(os.path.join(HERE, "..", "region_gate", "gate_regions.py"))
VIEW_NAMES = ["front", "back", "side_L", "side_R", "q34_L", "q34_R",
              "rear34_L", "rear34_R", "worm", "wormL60", "wormR60", "bird", "face",
              "feature", "feature_b"]  # feature views exist only on --feature runs
# close-ups: the body exits the frame, so silhouette-level rules
# (clipping / holes / floaters) do not apply there
CLOSEUP_VIEWS = {"face", "feature", "feature_b"}
FULL_FIGURE_VIEWS = [v for v in VIEW_NAMES if v not in CLOSEUP_VIEWS]


# ---------------------------------------------------------------- helpers
def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def bbox_crop(rgb, fg):
    ys, xs = np.where(fg)
    if len(xs) == 0:
        return rgb, fg
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return rgb[y0:y1, x0:x1], fg[y0:y1, x0:x1]


# ---------------------------------------------------------------- cheap rules
def cheap_rules(rgb, fg, seg, full_figure=True):
    """View-agnostic defect detectors. Returns list of (severity, reason)."""
    out = []
    fga = float(fg.sum())
    if fga < 500:
        return [("FAIL", "figure not found in view")]

    # frame clipping: the figure touching the image border means the camera cropped
    # the bear — every downstream metric then judges a partial silhouette
    if full_figure:
        border = np.zeros_like(fg)
        border[0, :] = border[-1, :] = True
        border[:, 0] = border[:, -1] = True
        clip = float((fg & border).sum())
        if clip > 8:
            out.append(("FAIL", f"figure CLIPPED by frame ({int(clip)} border px) — reframe before judging"))

    # wound: red where a nude green bear has none
    red_frac = float((seg["red"] & fg).sum() / fga)
    if red_frac > 0.03:
        out.append(("FAIL", f"red_frac {red_frac:.3f} — reads as wound/raw"))

    # off-palette: paint that is none of the brand classes (green/tan/ink/red/pale)
    pale = (seg["V"] > 0.80) & (seg["S"] < 0.18) & fg
    known = seg["green"] | seg["tan"] | seg["ink"] | seg["red"] | pale
    off = float((fg & ~known).sum() / fga)
    if off > 0.06:
        out.append(("FAIL", f"off-palette paint {off:.3f} of figure — non-brand color present"))
    elif off > 0.03:
        out.append(("WARN", f"off-palette paint {off:.3f} — check for stray colors"))

    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg.astype(np.uint8), 8)
    if full_figure and n > 1:
        main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        main_dil = cv2.dilate((lab == main).astype(np.uint8), np.ones((17, 17), np.uint8))
        for i in range(1, n):
            if i == main or stats[i, cv2.CC_STAT_AREA] < 40:
                continue
            if not (main_dil.astype(bool) & (lab == i)).any():
                out.append(("FAIL", f"floating fragment: {int(stats[i, cv2.CC_STAT_AREA])}px detached from body"))
                break  # one is enough to fail; don't spam

    # see-through: background-colored holes enclosed inside the silhouette
    if full_figure:
        main_mask = (lab == (1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])))) if n > 1 else fg
        filled = main_mask.astype(np.uint8).copy()
        cs, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        solid = np.zeros_like(filled)
        cv2.drawContours(solid, cs, -1, 1, thickness=-1)
        holes_frac = float((solid.astype(bool) & ~main_mask).sum() / fga)
        if holes_frac > 0.015:
            out.append(("FAIL", f"enclosed holes {holes_frac:.3f} of figure — see-through geometry"))
        elif holes_frac > 0.004:
            out.append(("WARN", f"enclosed holes {holes_frac:.3f} — check for see-through"))

    # stain: one big compact dark blob (fur strokes are thin; eyes/nose are small)
    ink = (seg["ink"] & fg).astype(np.uint8)
    ni, labi, statsi, _ = cv2.connectedComponentsWithStats(ink, 8)
    for i in range(1, ni):
        a = statsi[i, cv2.CC_STAT_AREA]
        if a / fga > 0.025:
            w, h = statsi[i, cv2.CC_STAT_WIDTH], statsi[i, cv2.CC_STAT_HEIGHT]
            fill = a / max(w * h, 1)
            if fill > 0.35:  # compact blob, not an outline/stroke network
                out.append(("FAIL", f"dark stain blob {a / fga:.3f} of figure (fill {fill:.2f})"))
                break
    return out


# ---------------------------------------------------------------- symmetry
def symmetry_check(rgb_L, rgb_R):
    """side_L vs mirrored side_R. Silhouette IoU gates; hue-class cells warn only
    (key light is asymmetric — raw color diff would false-fail the shadow side)."""
    out = []
    fgL = fg_mask(rgb_L)
    fgR = fg_mask(rgb_R)
    cL, mL = bbox_crop(rgb_L, fgL)
    cR, mR = bbox_crop(rgb_R[:, ::-1], fgR[:, ::-1])  # mirror R
    # proportion guard BEFORE normalization: independent resize would hide it
    arL = mL.shape[1] / max(mL.shape[0], 1)
    arR = mR.shape[1] / max(mR.shape[0], 1)
    if abs(arL - arR) / max(arL, arR) > 0.06:
        out.append(("FAIL", f"L/R bbox aspect mismatch {arL:.3f} vs {arR:.3f} — one side wider/taller"))
    Hs, Ws = 480, 380
    mLr = cv2.resize(mL.astype(np.uint8), (Ws, Hs), interpolation=cv2.INTER_NEAREST).astype(bool)
    mRr = cv2.resize(mR.astype(np.uint8), (Ws, Hs), interpolation=cv2.INTER_NEAREST).astype(bool)
    iou = float((mLr & mRr).sum() / max((mLr | mRr).sum(), 1))
    if iou < 0.86:
        out.append(("FAIL", f"silhouette asymmetry: L/R IoU {iou:.3f} (<0.86)"))

    # hue-class fractions per cell (6x8 grid) — lighting-robust-ish
    cLr = cv2.resize(cL, (Ws, Hs))
    cRr = cv2.resize(cR, (Ws, Hs))
    segL = segment(cLr, mLr)
    segR = segment(cRr, mRr)
    worst = 0.0
    worst_cell = None
    gy, gx = 8, 6
    for iy in range(gy):
        for ix in range(gx):
            sl = np.s_[iy * Hs // gy:(iy + 1) * Hs // gy, ix * Ws // gx:(ix + 1) * Ws // gx]
            nL = float(mLr[sl].sum())
            nR = float(mRr[sl].sum())
            if nL < 80 or nR < 80:
                continue
            d = 0.0
            for cls in ("green", "tan", "ink"):
                fL = float((segL[cls][sl] & mLr[sl]).sum() / nL)
                fR = float((segR[cls][sl] & mRr[sl]).sum() / nR)
                d = max(d, abs(fL - fR))
            if d > worst:
                worst, worst_cell = d, (iy, ix)
    if worst > 0.45:
        out.append(("WARN", f"color-class asymmetry {worst:.2f} at cell row{worst_cell[0]}/col{worst_cell[1]} (grid 8x6, top-left origin)"))
    return out, iou


# ---------------------------------------------------------------- blocking (stage-0)
def blocking_check(ref_rgb, ren_rgb, out_dir):
    """Stage-0 artist gate: SILHOUETTE first, then the squint value read.
    While this FAILs, only silhouette/mass rounds are legitimate — no surface work.
    (Artist-lens upgrade 2026-07-13: weeks went into nails while the mane didn't exist.)"""
    out = []
    fgT = fg_mask(ref_rgb)
    fgR = fg_mask(ren_rgb)
    cT, mT = bbox_crop(ref_rgb, fgT)
    cR, mR = bbox_crop(ren_rgb, fgR)
    # common scale: fit both to the same height, pad widths (preserves proportion signal)
    H = 480
    def scale_mask(m):
        w = max(1, int(m.shape[1] * H / m.shape[0]))
        return cv2.resize(m.astype(np.uint8), (w, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    sT, sR = scale_mask(mT), scale_mask(mR)
    W = max(sT.shape[1], sR.shape[1])
    def pad(m):
        d = W - m.shape[1]
        return np.pad(m, ((0, 0), (d // 2, d - d // 2)))
    sT, sR = pad(sT), pad(sR)
    iou = float((sT & sR).sum() / max((sT | sR).sum(), 1))
    if iou < 0.90:
        out.append(("FAIL", f"SILHOUETTE not locked: IoU {iou:.3f} vs 2D (<0.90) — only silhouette/mass rounds are legitimate now"))

    # squint: both images tiny + blurred; value hierarchy must match (face wins, not belly)
    def squint(rgb, fgm):
        c, m = bbox_crop(rgb, fgm)
        g = cv2.cvtColor((c * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        w = max(1, int(g.shape[1] * 48 / g.shape[0]))
        gs = cv2.resize(g, (w, 48))
        ms = cv2.resize(m.astype(np.uint8), (w, 48), interpolation=cv2.INTER_NEAREST).astype(bool)
        gs = cv2.GaussianBlur(gs, (5, 5), 1.2)
        return gs, ms
    gT, mT2 = squint(ref_rgb, fgT)
    gR, mR2 = squint(ren_rgb, fgR)
    def hierarchy(g2, m2):
        h2 = g2.shape[0]
        head = m2[:int(h2 * 0.28)]
        belly = m2[int(h2 * 0.38):int(h2 * 0.70)]
        lum_head = float(g2[:int(h2 * 0.28)][head].mean()) if head.sum() > 10 else 0.5
        lum_belly = float(g2[int(h2 * 0.38):int(h2 * 0.70)][belly].mean()) if belly.sum() > 10 else 0.5
        return lum_belly - lum_head
    drift = hierarchy(gR, mR2) - hierarchy(gT, mT2)
    if abs(drift) > 0.12:
        out.append(("WARN", f"squint value-hierarchy drift {drift:+.2f} (belly-vs-head luminance vs 2D) — check who wins the read"))

    # squint board (for the eye — the metric above is only a tripwire)
    def up(g2):
        return cv2.resize((np.clip(g2, 0, 1) * 255).astype(np.uint8),
                          (g2.shape[1] * 6, g2.shape[0] * 6), interpolation=cv2.INTER_NEAREST)
    a, b = up(gT), up(gR)
    hh = max(a.shape[0], b.shape[0])
    a = cv2.copyMakeBorder(a, 0, hh - a.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=20)
    b = cv2.copyMakeBorder(b, 0, hh - b.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=20)
    cv2.imwrite(os.path.join(out_dir, "SQUINT.png"), np.hstack([a, b]))
    return out, iou


# ---------------------------------------------------------------- region gate wrapper
def run_region_gate(render, target, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rep_path = os.path.join(out_dir, "gate_report.json")
    if os.path.exists(rep_path):
        os.remove(rep_path)  # a crash must never resurface yesterday's verdicts
    r = subprocess.run([sys.executable, GATE_REGIONS, "--render", render,
                        "--target", target, "--out", out_dir],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(rep_path):
        return {"n_fail": 1, "error": (r.stderr or r.stdout)[-800:] or f"exit {r.returncode}"}
    return json.load(open(rep_path))


def load_acks():
    """Acknowledged FAILs: method/decision already taken — report as ACK, don't count.
    (Motor upgrade 2026-07-13: the escalation tripwire kept re-flagging decided items.)"""
    p = os.path.join(HERE, "acknowledged.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def judge_region_view(name, rep, out_dir, acks=None):
    """Fold a gate_regions report into one view verdict (SKIP-aware, box-drift-aware)."""
    acks = acks or {}
    # back ref (filomeno_apose_back.png) is the DRESSED bear — only regions that are
    # nude in that ref (head/mane/hands) are comparable; belly/feet/torso are overalls
    # and boots there (caught 2026-07-12: belly dE 24 was fur-vs-fabric, not a defect).
    # TODO: swap to a nude back ref when one exists, then re-enable the body regions.
    skip_regions = ({"muzzle", "nose", "mouth", "ear_L", "ear_R",
                     "belly", "feet", "torso_fur_L", "torso_fur_R"}
                    if name == "back" else set())
    nf, reasons = 0, []
    for rn, rr in rep.get("regions", {}).items():
        if rn in skip_regions:
            continue
        if rr.get("verdict") == "FAIL":
            if rn in acks:
                reasons.append(f"{rn}: ACK ({acks[rn][:70]}…)")
                continue
            nf += 1
            reasons.append(f"{rn}: " + "; ".join(rr.get("reasons", [])))
        elif rr.get("verdict") == "SKIP":
            # target sees the region but the render doesn't (or vice versa):
            # a disappeared feature must not read as an improvement
            nf += 1
            reasons.append(f"{rn}: SKIP — region not detected in one image (feature missing/undetectable)")
    # box-center drift: a feature painted in the WRONG PLACE drags its own box and
    # would otherwise be judged against itself at both locations
    bc = rep.get("box_centers", {})
    t_c, r_c = bc.get("target", {}), bc.get("render", {})
    if name == "front":
        for rn in ("muzzle", "nose", "mouth"):
            if rn in t_c and rn in r_c:
                dx = abs(t_c[rn][0] - r_c[rn][0])
                dy = abs(t_c[rn][1] - r_c[rn][1])
                if dx > 0.10 or dy > 0.10:
                    nf += 1
                    reasons.append(f"{rn}: box center drifted (dx={dx:.2f}, dy={dy:.2f} of figure) — feature misplaced or zone bleeding")
    if "error" in rep and not rep.get("regions"):
        nf = max(nf, 1)
        reasons.append("gate_regions error: " + str(rep["error"]))
    return nf, reasons


# ---------------------------------------------------------------- board
def build_board(views_dir, results, out_path, cell_h=300):
    tiles = []
    for name in VIEW_NAMES:
        p = os.path.join(views_dir, f"v_{name}.png")
        if not os.path.exists(p) or name not in results:
            continue
        img = cv2.imread(p, cv2.IMREAD_COLOR)
        s = cell_h / img.shape[0]
        img = cv2.resize(img, (int(img.shape[1] * s), cell_h))
        v = results[name]["verdict"]
        color = {"PASS": (60, 170, 60), "WARN": (40, 170, 220), "FAIL": (50, 50, 230)}[v]
        img = cv2.copyMakeBorder(img, 26, 4, 4, 4, cv2.BORDER_CONSTANT, value=color)
        cv2.putText(img, f"{name}: {v}", (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(img)
    if not tiles:
        return
    per_row = 5
    rows = []
    for i in range(0, len(tiles), per_row):
        chunk = tiles[i:i + per_row]
        h = max(t.shape[0] for t in chunk)
        chunk = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(20, 20, 20)) for t in chunk]
        rows.append(np.hstack(chunk))
    w = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 0, 0, w - r.shape[1], cv2.BORDER_CONSTANT, value=(20, 20, 20)) for r in rows]
    cv2.imwrite(out_path, np.vstack(rows))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", default=os.path.join(HERE, "views"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--expect-change", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    views = os.path.abspath(args.views)

    # ---- per-view change detection (state is COMMITTED only after verdicts succeed)
    state_path = os.path.join(HERE, "state_g360.json")
    prev = json.load(open(state_path)) if os.path.exists(state_path) else {}
    prev_hashes = prev.get("hashes", prev if isinstance(prev, dict) else {})
    same_dir = prev.get("views_dir", views) == views
    hashes, tripped = {}, []
    for name in VIEW_NAMES:
        p = os.path.join(views, f"v_{name}.png")
        if os.path.exists(p):
            hashes[name] = sha(p)
            if same_dir and prev_hashes.get(name) == hashes[name]:
                tripped.append(name)

    results = {}
    total_fail = 0
    ACKS = load_acks()

    # ---- front / back: full region gate vs 2D refs
    region_reports = {}
    for name, ref in (("front", "filomeno_nude_apose.png"), ("back", "filomeno_apose_back.png")):
        p = os.path.join(views, f"v_{name}.png")
        if not os.path.exists(p):
            results[name] = {"verdict": "FAIL", "reasons": ["view render missing"]}
            total_fail += 1
            continue
        rep = run_region_gate(p, os.path.join(REFS, ref), os.path.join(args.out, f"regions_{name}"))
        region_reports[name] = rep
        nf, reasons = judge_region_view(name, rep, args.out, acks=ACKS)
        results[name] = {"verdict": "FAIL" if nf else "PASS", "n_fail_regions": nf,
                         "reasons": reasons,
                         "board": os.path.join(args.out, f"regions_{name}", "regions_board.png")}
        total_fail += 1 if nf else 0

    # ---- ALL views: cheap rules (front/back included — the region gate only covers
    # its 13 boxes; holes/floaters/red/clipping need the whole silhouette)
    imgs = {}
    for name in VIEW_NAMES:
        p = os.path.join(views, f"v_{name}.png")
        if not os.path.exists(p):
            if name in ("feature", "feature_b"):
                continue  # zone close-ups only exist on --feature runs
            if name not in results:
                results[name] = {"verdict": "FAIL", "reasons": ["view render missing"]}
                total_fail += 1
            continue
        rgb = load_rgb(p)
        imgs[name] = rgb
        if name == "face":
            # close-up: the body fills the bottom corners, so estimate the background
            # color from the TOP corners only (fg_mask's 4-corner median would blend
            # body green into the bg color and count background as figure)
            h, w = rgb.shape[:2]
            k = max(4, min(h, w) // 50)
            bg_col = np.median(np.concatenate([rgb[:k, :k].reshape(-1, 3),
                                               rgb[:k, -k:].reshape(-1, 3)]), axis=0)
            fg = np.linalg.norm(rgb - bg_col, axis=2) > 0.10
        else:
            fg = fg_mask(rgb)
        seg = segment(rgb, fg)
        findings = cheap_rules(rgb, fg, seg, full_figure=(name in FULL_FIGURE_VIEWS))
        fails = [r for s, r in findings if s == "FAIL"]
        warns = [r for s, r in findings if s == "WARN"]
        if name in results:  # front/back: merge with region verdict
            results[name]["reasons"].extend(fails + warns)
            if fails:
                if results[name]["verdict"] != "FAIL":
                    results[name]["verdict"] = "FAIL"
                    total_fail += 1
            elif warns and results[name]["verdict"] == "PASS":
                results[name]["verdict"] = "WARN"
        else:
            results[name] = {"verdict": "FAIL" if fails else ("WARN" if warns else "PASS"),
                             "reasons": fails + warns}
            total_fail += 1 if fails else 0

    # ---- BLOCKING (stage-0): silhouette lock + squint, front vs 2D
    if "front" in imgs:
        ref_rgb = load_rgb(os.path.join(REFS, "filomeno_nude_apose.png"))
        bfind, iou = blocking_check(ref_rgb, imgs["front"], args.out)
        bfails = [r for s, r in bfind if s == "FAIL"]
        bwarns = [r for s, r in bfind if s == "WARN"]
        if bfails and "blocking" in ACKS:
            results["blocking"] = {"verdict": "WARN",
                                   "reasons": [f"ACK ({ACKS['blocking'][:70]}…)"] + bfails + bwarns,
                                   "silhouette_iou": round(iou, 3)}
        else:
            results["blocking"] = {"verdict": "FAIL" if bfails else ("WARN" if bwarns else "PASS"),
                                   "reasons": bfails + bwarns, "silhouette_iou": round(iou, 3)}
            total_fail += 1 if bfails else 0

    # ---- laterals: mirror symmetry
    if "side_L" in imgs and "side_R" in imgs:
        sym, iou = symmetry_check(imgs["side_L"], imgs["side_R"])
        flipped = 0
        for sev, reason in sym:
            for side in ("side_L", "side_R"):
                results[side]["reasons"].append(f"[sym] {reason}")
                if sev == "FAIL" and results[side]["verdict"] != "FAIL":
                    results[side]["verdict"] = "FAIL"
                    flipped += 1
                elif sev == "WARN" and results[side]["verdict"] == "PASS":
                    results[side]["verdict"] = "WARN"
        total_fail += flipped  # n_fail stays consistent with FAIL-view count
        for side in ("side_L", "side_R"):
            results[side]["sym_iou"] = round(iou, 3)

    # ---- geometric audits (from capture) — mandatory input, SKIP is not a pass
    ori_path = os.path.join(views, "orientation.json")
    orientation = None
    if os.path.exists(ori_path):
        orientation = json.load(open(ori_path))
        if orientation.get("verdict") != "PASS":
            total_fail += 1
    else:
        orientation = {"verdict": "FAIL", "checks": {"error": "orientation.json missing — audit never ran"}}
        total_fail += 1

    # ---- tripwire verdict
    tripwire = None
    if hashes and len(tripped) == len(hashes):
        tripwire = ("ALL views identical to previous run — the edit did NOT reach the render. "
                    "'Identical' is NOT 'no regression'.")
        if args.expect_change:
            total_fail += 1

    board_path = os.path.join(args.out, "G360_BOARD.png")
    build_board(views, results, board_path)

    report = {"views_dir": views, "tripwire": tripwire, "tripped_views": tripped,
              "n_fail": total_fail, "views": results, "orientation": orientation}
    json.dump(report, open(os.path.join(args.out, "g360_report.json"), "w"), indent=2, default=str)
    # verdicts succeeded — only NOW commit the tripwire state
    json.dump({"views_dir": views, "hashes": hashes}, open(state_path, "w"))
    # ---- history ledger (escalation tripwire input: N rounds same-region FAIL = method review)
    import datetime
    with open(os.path.join(HERE, "history.jsonl"), "a") as hf:
        hf.write(json.dumps({
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "n_fail": total_fail,
            "verdicts": {k: v["verdict"] for k, v in results.items()},
            "fail_reasons": {k: v["reasons"] for k, v in results.items() if v["verdict"] == "FAIL"},
        }) + "\n")

    # ---- console
    print("=" * 72)
    print(f"GATE 360 — {total_fail} FAIL" + (f"   [TRIPWIRE: {tripwire}]" if tripwire else ""))
    print("=" * 72)
    for name in ["blocking"] + VIEW_NAMES:
        r = results.get(name)
        if not r:
            continue
        mark = {"PASS": "  ok ", "WARN": " warn", "FAIL": " FAIL"}[r["verdict"]]
        print(f"{mark}  {name:9s}" + ("   " + " | ".join(r["reasons"]) if r.get("reasons") else ""))
    if orientation:
        mark = {"PASS": "  ok ", "FAIL": " FAIL", "SKIP": " FAIL"}.get(orientation["verdict"], " FAIL")
        det = "; ".join(f"{k}={v['verdict']}" for k, v in orientation.get("checks", {}).items()
                        if isinstance(v, dict) and "verdict" in v)
        print(f"{mark}  geometric audit   {det}")
    if args.expect_change and tripped and not tripwire:
        print(f" info  unchanged views (expected if the edit was local): {', '.join(tripped)}")
    print(f"\nboard  -> {board_path}")
    print(f"report -> {os.path.join(args.out, 'g360_report.json')}")
    return total_fail


if __name__ == "__main__":
    sys.exit(main())
