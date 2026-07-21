#!/usr/bin/env python3
"""gate_regions.py — semantic-region render-vs-2D gate for Filomeno (v1, 2026-07-09).

THE canonical verdict tool (replaces measure_harness as gate; see _MANIFEST.md §2).
Design rules (earned the hard way):
  - NO whitelist: every region is scored AGAINST THE 2D, never against a hardcoded
    "expected" (measure_harness whitelisted the mouth and passed a wound-gash 7/7).
  - Named verdicts: output says "mouth: FAIL (reads as wound)" in words, per region.
  - Change tripwire: if the render hash is identical to the previous run, SCREAM —
    "identical" after an edit means the edit did not reach the render, not "no regression".
  - Crops board: emits target|render crop pairs per region so the eye can verify the
    landmark detection landed on the right pixels (anti measuring-the-wrong-box).

Run (WSL conda env `critic`):
  python gate_regions.py --render gate_front.png --target ../../_refs/filomeno_nude_apose.png \
      --out ./out [--expect-change]
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
import numpy as np
import cv2
from skimage.color import rgb2lab, deltaE_ciede2000


# ---------------------------------------------------------------- segmentation
def load_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def fg_mask(rgb, tol=0.10):
    h, w = rgb.shape[:2]
    k = max(4, min(h, w) // 50)
    corners = np.concatenate([rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3),
                              rgb[-k:, :k].reshape(-1, 3), rgb[-k:, -k:].reshape(-1, 3)])
    bg_col = np.median(corners, axis=0)
    mask = (np.linalg.norm(rgb - bg_col, axis=2) > tol).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask.astype(bool)


def hsv_of(rgb):
    hsv = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    return hsv[:, :, 0] * 2.0, hsv[:, :, 1] / 255.0, hsv[:, :, 2] / 255.0  # H in deg


def segment(rgb, fg):
    H, S, V = hsv_of(rgb)
    ink = fg & (V < 0.35)
    green = fg & ~ink & (H >= 55) & (H <= 105) & (S > 0.12)
    tan = fg & ~ink & ~green & (H >= 10) & (H < 55) & (S > 0.10)
    red = fg & (((H < 15) | (H > 340)) & (S > 0.30) & (V > 0.20) & (V < 0.85))
    return {"ink": ink, "green": green, "tan": tan, "red": red, "H": H, "S": S, "V": V}


def bbox_of(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def largest_component(mask, min_size=30):
    m = mask.astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    best, area = None, min_size
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= area:
            area = stats[i, cv2.CC_STAT_AREA]; best = i
    if best is None:
        return None, None
    return lab == best, stats[best]


# ---------------------------------------------------------------- landmarks
def landmarks(rgb):
    """Detect the semantic region boxes in ONE image (its own frame)."""
    fg = fg_mask(rgb)
    seg = segment(rgb, fg)
    fx0, fy0, fx1, fy1 = bbox_of(fg)
    FH, FW = fy1 - fy0, fx1 - fx0

    # muzzle = largest tan component in the top 35% of the figure
    top_band = np.zeros_like(fg); top_band[fy0:fy0 + int(FH * 0.35), :] = True
    muz_mask, muz_stats = largest_component(seg["tan"] & top_band, min_size=int(FH * FW * 0.0008))
    if muz_mask is None:  # fallback: center of top band
        mx0, my0 = fx0 + int(FW * 0.42), fy0 + int(FH * 0.08)
        mx1, my1 = fx0 + int(FW * 0.58), fy0 + int(FH * 0.22)
    else:
        mx0, my0, mx1, my1 = bbox_of(muz_mask)
    muz_w, muz_h = mx1 - mx0, my1 - my0
    head_cx = (mx0 + mx1) // 2

    # head box: from figure top to just below the muzzle
    hy0, hy1 = fy0, min(fy1, my1 + int(muz_h * 0.25))
    row = min(hy1 - 1, (my0 + my1) // 2)
    cols = np.where(fg[row])[0]
    hx0, hx1 = (int(cols.min()), int(cols.max()) + 1) if len(cols) else (fx0, fx1)
    head_w = hx1 - hx0

    def clampbox(x0, y0, x1, y1):
        h, w = fg.shape
        return [max(0, int(x0)), max(0, int(y0)), min(w, int(x1)), min(h, int(y1))]

    # ears: PEAKS of the top-of-figure profile left/right of head center
    # (fixed v1.1: corner boxes landed on empty background in the 2D — mane is wider than the ears)
    ear_h = int((hy1 - hy0) * 0.26); ear_w = int(head_w * 0.22)
    strip_rows = fy0 + max(2, int(FH * 0.10))
    top_row = np.full(fg.shape[1], 10**9)
    ys, xs = np.where(fg[:strip_rows + int(FH * 0.05), :])
    np.minimum.at(top_row, xs, ys)
    valid = np.where(top_row < 10**9)[0]

    def ear_peak(side_cols):
        if len(side_cols) == 0:
            return None
        return int(side_cols[np.argmin(top_row[side_cols])])

    # restrict the peak search to the central head band — mane spikes wider than the
    # ears were hijacking the left peak (2D crop landed on background)
    inner = valid[(valid > head_cx - head_w * 0.42) & (valid < head_cx + head_w * 0.42)]
    pkL = ear_peak(inner[inner < head_cx])
    pkR = ear_peak(inner[inner >= head_cx])
    R = {
        "head":  clampbox(hx0, hy0, hx1, hy1),
        "muzzle": clampbox(mx0, my0, mx1, my1),
        "mouth": clampbox(mx0, my0 + int(muz_h * 0.45), mx1, my1),          # bottom 55% of muzzle
        "nose":  clampbox(mx0 + muz_w * 0.2, my0, mx1 - muz_w * 0.2, my0 + muz_h * 0.5),
        "ear_L": clampbox(pkL - ear_w // 2, top_row[pkL], pkL + ear_w // 2, top_row[pkL] + ear_h) if pkL is not None else None,
        "ear_R": clampbox(pkR - ear_w // 2, top_row[pkR], pkR + ear_w // 2, top_row[pkR] + ear_h) if pkR is not None else None,
        "mane":  clampbox(hx0, hy0 + ear_h, hx1, hy1),                       # face-framing band (minus ear strip)
        "belly": clampbox(fx0 + FW * 0.32, fy0 + FH * 0.38, fx1 - FW * 0.32, fy0 + FH * 0.68),
        "torso_fur_L": clampbox(fx0 + FW * 0.10, fy0 + FH * 0.30, fx0 + FW * 0.30, fy0 + FH * 0.62),
        "torso_fur_R": clampbox(fx1 - FW * 0.30, fy0 + FH * 0.30, fx1 - FW * 0.10, fy0 + FH * 0.62),
        "hand_L": None, "hand_R": None,
        "feet":  clampbox(fx0 + FW * 0.15, fy1 - FH * 0.10, fx1 - FW * 0.15, fy1),
        "figure": [fx0, fy0, fx1, fy1],
    }
    # hands: extreme fg pixels in the 35-62% height band
    band = np.zeros_like(fg); band[fy0 + int(FH * 0.35):fy0 + int(FH * 0.62), :] = True
    bfg = fg & band
    ys, xs = np.where(bfg)
    if len(xs):
        hw = int(head_w * 0.35)
        lx, ly = xs.min(), int(np.mean(ys[xs < xs.min() + 5]))
        rx, ry = xs.max(), int(np.mean(ys[xs > xs.max() - 5]))
        R["hand_L"] = clampbox(lx, ly - hw, lx + 2 * hw, ly + hw)
        R["hand_R"] = clampbox(rx - 2 * hw, ry - hw, rx, ry + hw)
    return fg, seg, R


# ---------------------------------------------------------------- metrics
def crop(mask_or_img, box):
    x0, y0, x1, y1 = box
    return mask_or_img[y0:y1, x0:x1]


def mean_lab(rgb, mask):
    if mask.sum() < 10:
        return None
    px = rgb[mask].reshape(-1, 1, 3)
    return rgb2lab(px).reshape(-1, 3).mean(axis=0)


def delta_e(lab_a, lab_b):
    if lab_a is None or lab_b is None:
        return None
    return float(deltaE_ciede2000(lab_a.reshape(1, 1, 3), lab_b.reshape(1, 1, 3))[0, 0])


def stroke_stats(ink_crop):
    """Ink stroke shape stats — the confetti-vs-flick discriminator.
    v1.1: components touching the crop border are EXCLUDED (the figure outline runs
    through fur regions and inflated aspect to 7000+); median instead of mean; aspect capped."""
    m = ink_crop.astype(np.uint8)
    H, W = m.shape
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    areas, aspects = [], []
    region_area = float(m.size)
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        if a < 4:
            continue
        x0, y0 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        x1 = x0 + stats[i, cv2.CC_STAT_WIDTH]; y1 = y0 + stats[i, cv2.CC_STAT_HEIGHT]
        if x0 <= 1 or y0 <= 1 or x1 >= W - 1 or y1 >= H - 1:
            continue  # outline / border-crossing component, not a fur stroke
        ys, xs = np.where(lab == i)
        pts = np.stack([xs, ys], 1).astype(np.float32)
        if len(pts) > 2:
            pts_c = pts - pts.mean(0)
            cov = np.cov(pts_c.T)
            ev = np.sort(np.linalg.eigvalsh(cov))[::-1]
            aspects.append(min(50.0, float(np.sqrt(max(ev[0], 1e-9) / max(ev[1], 1e-9)))))
        areas.append(a)
    if not areas:
        return {"n": 0, "density": 0.0, "mean_area_frac": 0.0, "mean_aspect": None}
    return {"n": len(areas),
            "density": round(sum(areas) / region_area, 4),
            "mean_area_frac": round(float(np.median(areas)) / region_area, 5),
            "mean_aspect": round(float(np.median(aspects)), 2) if aspects else None}


def region_metrics(rgb, fg, seg, box, exclude_box=None):
    if box is None:
        return None
    if exclude_box is not None:  # e.g. mane = head WITHOUT the face (else face ink dilutes it)
        fg = fg.copy()
        ex0, ey0, ex1, ey1 = exclude_box
        fg[ey0:ey1, ex0:ex1] = False
    f = crop(fg, box)
    if f.sum() < 20:
        return None
    r = crop(rgb, box)
    pale = (crop(seg["V"], box) > 0.80) & (crop(seg["S"], box) < 0.18) & f  # claw/tooth nubs
    out = {
        "lab": mean_lab(r, f),
        "dark_frac": round(float((crop(seg["ink"], box) & f).sum() / f.sum()), 4),
        "red_frac": round(float((crop(seg["red"], box) & f).sum() / f.sum()), 4),
        "pale_frac": round(float(pale.sum() / f.sum()), 4),
        "strokes": stroke_stats(crop(seg["ink"], box) & f),
    }
    # contour roughness (claw scallops raise it; mitten lowers it)
    cs, _ = cv2.findContours(f.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if cs:
        c = max(cs, key=cv2.contourArea)
        a = cv2.contourArea(c)
        p = cv2.arcLength(c, True)
        out["roughness"] = round(float(p * p / max(a, 1.0)), 1)
    return out


# ---------------------------------------------------------------- verdicts (target-relative — NO whitelist)
def judge(region, t, r):
    """Compare render metrics r against target metrics t. Returns (PASS/FAIL, reasons)."""
    if t is None or r is None:
        return "SKIP", ["region not detected in one image"]
    fails = []
    de = delta_e(t["lab"], r["lab"])
    if de is not None and de > 12:
        fails.append(f"color dE={de:.1f} (>12)")
    # wound detector — generic: red where the 2D has none
    if r["red_frac"] > max(0.05, t["red_frac"] * 3 + 0.02):
        fails.append(f"red_frac {r['red_frac']:.3f} vs 2D {t['red_frac']:.3f} — reads as wound/raw")
    # stain detector — dark where the 2D is clean
    if r["dark_frac"] > t["dark_frac"] * 2.5 + 0.06:
        fails.append(f"dark_frac {r['dark_frac']:.3f} vs 2D {t['dark_frac']:.3f} — stain/blotch")
    # missing ink — 2D has linework the render lacks (e.g. toes, claws, mouth line)
    if t["dark_frac"] > 0.04 and r["dark_frac"] < t["dark_frac"] * 0.35:
        fails.append(f"ink missing: dark_frac {r['dark_frac']:.3f} vs 2D {t['dark_frac']:.3f}")
    # stroke style — confetti (big compact blobs) vs flicks (small elongated)
    ts, rs = t["strokes"], r["strokes"]
    if region.startswith(("torso_fur", "mane")) and ts["n"] >= 5 and rs["n"] >= 1:
        if rs["mean_area_frac"] > ts["mean_area_frac"] * 2.2:
            fails.append(f"strokes too BIG: area_frac {rs['mean_area_frac']:.5f} vs 2D {ts['mean_area_frac']:.5f} (confetti, not flicks)")
        if ts["mean_aspect"] and rs["mean_aspect"] and rs["mean_aspect"] < ts["mean_aspect"] * 0.6:
            fails.append(f"strokes too COMPACT: aspect {rs['mean_aspect']} vs 2D {ts['mean_aspect']} (blob vs flick)")
        if rs["density"] < ts["density"] * 0.4:
            fails.append(f"fur too sparse: density {rs['density']} vs 2D {ts['density']}")
    # extremity shape — claws/toes scallop the contour
    if region.startswith(("hand", "feet")) and "roughness" in t and "roughness" in r:
        if r["roughness"] < t["roughness"] * 0.55:
            fails.append(f"contour too smooth: {r['roughness']} vs 2D {t['roughness']} (mitten — no claws/toes)")
    # claw/nail detail — the 2D has pale claw nubs at the extremity tips
    if region.startswith(("hand", "feet")):
        if t["pale_frac"] > 0.008 and r["pale_frac"] < t["pale_frac"] * 0.25:
            fails.append(f"claws/toes MISSING: pale_frac {r['pale_frac']:.3f} vs 2D {t['pale_frac']:.3f}")
    return ("FAIL" if fails else "PASS"), fails


# ---------------------------------------------------------------- crops board
def board(t_rgb, r_rgb, t_R, r_R, order, out_path, cell=170):
    rows = []
    for name in order:
        pair = []
        for rgb, R in ((t_rgb, t_R), (r_rgb, r_R)):
            box = R.get(name)
            if box is None:
                pair.append(np.full((cell, cell, 3), 0.35, np.float32)); continue
            c = crop(rgb, box)
            s = cell / max(c.shape[:2])
            c = cv2.resize(c, (max(1, int(c.shape[1] * s)), max(1, int(c.shape[0] * s))))
            pad = np.full((cell, cell, 3), 0.92, np.float32)
            pad[:c.shape[0], :c.shape[1]] = c
            pair.append(pad)
        row = np.hstack(pair)
        row = cv2.copyMakeBorder((row * 255).astype(np.uint8), 18, 2, 2, 2, cv2.BORDER_CONSTANT, value=(30, 30, 30))
        cv2.putText(row, f"{name}  (2D | render)", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        rows.append(row)
    half = (len(rows) + 1) // 2
    col1, col2 = rows[:half], rows[half:]
    while len(col2) < len(col1):
        col2.append(np.zeros_like(col1[0]))
    sheet = np.hstack([np.vstack(col1), np.vstack(col2)])
    cv2.imwrite(out_path, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--out", default="./out")
    ap.add_argument("--expect-change", action="store_true",
                    help="fail loudly if the render is byte-identical to the previous run")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # ---- change tripwire
    state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
    h = hashlib.sha256(open(args.render, "rb").read()).hexdigest()
    prev = {}
    if os.path.exists(state_path):
        prev = json.load(open(state_path))
    tripwire = None
    if prev.get("render_hash") == h:
        tripwire = "RENDER IDENTICAL TO PREVIOUS RUN — your edit did NOT reach the render. 'Identical' is NOT 'no regression'."
        if args.expect_change:
            print("!!!! CHANGE TRIPWIRE:", tripwire)
    json.dump({"render_hash": h, "render": args.render}, open(state_path, "w"))

    t_rgb = load_rgb(args.target)
    r_rgb = load_rgb(args.render)
    t_fg, t_seg, t_R = landmarks(t_rgb)
    r_fg, r_seg, r_R = landmarks(r_rgb)

    order = ["head", "mane", "ear_L", "ear_R", "muzzle", "nose", "mouth",
             "belly", "torso_fur_L", "torso_fur_R", "hand_L", "hand_R", "feet"]
    def tip_box(R, name):
        """Extremities are judged at the TIP (claws/toes live there, not on the arm)."""
        box = R.get(name)
        if box is None:
            return None
        x0, y0, x1, y1 = box
        if name == "hand_L":
            return [x0, y0, x0 + int((x1 - x0) * 0.5), y1]
        if name == "hand_R":
            return [x1 - int((x1 - x0) * 0.5), y0, x1, y1]
        if name == "feet":
            return [x0, y0 + int((y1 - y0) * 0.35), x1, y1]
        return box

    metrics = {}
    for name in order:
        t_box = tip_box(t_R, name) if name.startswith(("hand", "feet")) else t_R.get(name)
        r_box = tip_box(r_R, name) if name.startswith(("hand", "feet")) else r_R.get(name)
        t_ex = t_R.get("muzzle") if name == "mane" else None
        r_ex = r_R.get("muzzle") if name == "mane" else None
        metrics[name] = (region_metrics(t_rgb, t_fg, t_seg, t_box, exclude_box=t_ex),
                         region_metrics(r_rgb, r_fg, r_seg, r_box, exclude_box=r_ex))

    # POOL the fur-style target across both torso sides: the 2D's inking varies 1.8x
    # side-to-side (noise, not style) — the fur STYLE target is one, not two.
    tL, tR2 = metrics.get("torso_fur_L", (None,))[0], metrics.get("torso_fur_R", (None,))[0]
    if tL and tR2:
        pooled = dict(tL)
        pooled["dark_frac"] = round((tL["dark_frac"] + tR2["dark_frac"]) / 2, 4)
        pooled["strokes"] = {k: (round((tL["strokes"][k] + tR2["strokes"][k]) / 2, 6)
                                 if isinstance(tL["strokes"][k], (int, float)) and isinstance(tR2["strokes"][k], (int, float))
                                 else tL["strokes"][k])
                             for k in tL["strokes"]}
        metrics["torso_fur_L"] = (pooled, metrics["torso_fur_L"][1])
        metrics["torso_fur_R"] = (pooled, metrics["torso_fur_R"][1])

    report, n_fail = {}, 0
    for name in order:
        tm, rm = metrics[name]
        verdict, reasons = judge(name, tm, rm)
        if verdict == "FAIL":
            n_fail += 1
        de = delta_e(tm["lab"], rm["lab"]) if (tm and rm) else None
        report[name] = {"verdict": verdict, "reasons": reasons, "delta_e": round(de, 1) if de else None,
                        "target": {k: v for k, v in (tm or {}).items() if k != "lab"},
                        "render": {k: v for k, v in (rm or {}).items() if k != "lab"}}

    board(t_rgb, r_rgb, t_R, r_R, order, os.path.join(args.out, "regions_board.png"))

    # v1.4: expose figure-normalized box centers so callers can detect a feature
    # painted in the WRONG PLACE (each image's landmarks are self-referential —
    # without this, a relocated muzzle gets judged against itself and passes)
    def _norm_centers(R):
        fx0, fy0, fx1, fy1 = R["figure"]
        FW, FH = max(fx1 - fx0, 1), max(fy1 - fy0, 1)
        cc = {}
        for k, b in R.items():
            if k == "figure" or b is None:
                continue
            cc[k] = [round(((b[0] + b[2]) / 2 - fx0) / FW, 4),
                     round(((b[1] + b[3]) / 2 - fy0) / FH, 4)]
        return cc

    out = {"render": args.render, "target": args.target, "tripwire": tripwire,
           "n_fail": n_fail, "regions": report,
           "box_centers": {"target": _norm_centers(t_R), "render": _norm_centers(r_R)}}
    json.dump(out, open(os.path.join(args.out, "gate_report.json"), "w"), indent=2, default=str)

    print("=" * 72)
    print(f"REGION GATE — {n_fail} FAIL / {sum(1 for r in report.values() if r['verdict']=='PASS')} PASS"
          + (f"   [TRIPWIRE: {tripwire}]" if tripwire else ""))
    print("=" * 72)
    for name in order:
        r = report[name]
        mark = {"PASS": "  ok ", "FAIL": " FAIL", "SKIP": " skip"}[r["verdict"]]
        line = f"{mark}  {name:12s} dE={str(r['delta_e']):>5s}"
        print(line + ("   " + " | ".join(r["reasons"]) if r["reasons"] else ""))
    print(f"\nboard  -> {os.path.join(args.out, 'regions_board.png')}")
    print(f"report -> {os.path.join(args.out, 'gate_report.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
