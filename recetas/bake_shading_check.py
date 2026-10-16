# RECETA (gate): bake_shading_check -- "la luz hace la sombra": no shading baked into colour.
# QUE: Pearson correlation between per-vertex colour LUMINANCE and ray OCCLUSION over the
#      surface vertices. A painted shadow darkens exactly where occlusion is high, so the
#      correlation goes strongly negative; uneven paint driven by position noise (stains)
#      is uncorrelated. PASS when r > -0.15 (rana v10: r >= 0.06; v9, which painted the
#      crease shadow: r = -0.825). The gate carries its OWN positive control: it re-runs
#      the same instrument on a luminance array with a synthetic shadow painted in
#      (lum - 0.6 * occlusion). If that control does not read strongly negative the
#      instrument is blind and the result is NOT_TESTED, never PASS (LECCIONES 3/12;
#      probe_with_control). Degenerate inputs (flat colour, no occlusion variance, too
#      few samples) are NOT_TESTED too: r is undefined, and "undefined" is not "clean".
# CUANDO: any asset whose colour lives in a vertex-colour layer (rana, Dungeon mobs, any
#      FLOAT_COLOR bake). Run it on the FINAL .blend before a verdict. Joan, rana v9:
#      "sigues como pintando la sombra" -> fix the geometry, not the colour.
# LECCION: COSECHA_2026-10-16.md section 8 lesson e (not yet in LECCIONES.md), memory
#      feedback_la_luz_hace_la_sombra; LECCIONES.md#3 and #12 for the in-gate control.
# NO INCLUIDO: the original's second half, the heart HALO ring (front ortho Workbench
#      render, band ratio around ONE outline). It is outline-specific (needs the heart
#      implicit curve) and stays in rana/rana_bake_check.py. Its three blind-spot lessons
#      are recorded in COSECHA_2026-10-16.md section 2 (clip_start cut the front, vcol
#      attribute not the active one, band averaging diluted a thin ring).
# GOTCHAS: occlusion rays start eps above the surface along the normal and are sampled in
#      the normal's hemisphere; ray_len / eps are WORLD units (rana: 2.5 mm / 0.04 mm on a
#      31 mm figure) -> they default to 8% / 0.1% of the bbox diagonal, pass absolutes to
#      reproduce a specific measurement. Sampling is seeded (random.Random(5)) so the
#      verdict is repeatable.
# FUENTE: rana/rana_bake_check.py:28-60 (part 1 only).
# EXEMPLAR:
#   rep = bake_shading_check(body, occluders=[body, heart],
#                            vertex_filter=lambda v: v.normal.y < -0.2)   # front only
#   rep.require_complete()
import math
import random

try:
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
except ImportError:  # the pure judge stays importable without Blender
    bmesh = None
try:
    from recetas.verdict import Report, PASS, FAIL, NOT_TESTED
    from recetas.probe_with_control import ProbeSet
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from verdict import Report, PASS, FAIL, NOT_TESTED
    from probe_with_control import ProbeSet

R_MIN = -0.15            # r above this = no baked shadow (rana v10 gate)
CONTROL_SHADOW = 0.6     # strength of the synthetic painted shadow in the control
MIN_SAMPLES = 50


def pearson(xs, ys):
    """Pearson r, or None when either side has no variance (r undefined)."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    if vx < 1e-12 or vy < 1e-12:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(vx * vy + 1e-30)


def judge(xs, ys, report=None, r_min=R_MIN, name="no_baked_shading"):
    """PURE decision from occlusion `xs` and vertex luma `ys` (parallel lists); `report` is
    an optional ProbeSet. Returns (ProbeSet, r, r_control). Adds a row whose control is the same luma with a synthetic shadow painted in."""
    ps = ProbeSet("bake_shading") if report is None else report
    if len(xs) < MIN_SAMPLES:
        ps.report.add(name, NOT_TESTED, "only %d surface samples (< %d): r is meaningless"
                      % (len(xs), MIN_SAMPLES))
        return ps, None, None
    r = pearson(xs, ys)
    base = sum(ys) / len(ys)
    r_ctrl = pearson(xs, [base - CONTROL_SHADOW * x for x in xs])
    if r is None or r_ctrl is None:
        ps.report.add(name, NOT_TESTED,
                      "r undefined (flat colour or no occlusion variance): the instrument cannot "
                      "see shading here, so 'clean' would be a blind zero")
        return ps, r, r_ctrl
    ps.row(name, r > r_min, "r(luma, occlusion) = %.3f over %d vertices (gate: r > %.2f)"
        % (r, len(xs), r_min),
        control_fired=r_ctrl <= r_min,
        control_detail="synthetic painted shadow reads r = %.3f (must be <= %.2f)" % (r_ctrl, r_min))
    return ps, r, r_ctrl


def vertex_luma(obj, attr_name="Col"):
    """Per-vertex mean Rec.709 luma of colour attribute `attr_name` (corner or point)."""
    me = obj.data
    ca = me.color_attributes.get(attr_name)
    if ca is None:
        return None
    lum = [0.0] * len(me.vertices)
    cnt = [0] * len(me.vertices)
    if ca.domain == "CORNER":
        for li, loop in enumerate(me.loops):
            c = ca.data[li].color
            lum[loop.vertex_index] += 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
            cnt[loop.vertex_index] += 1
    else:
        for vi, d in enumerate(ca.data):
            c = d.color
            lum[vi] = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
            cnt[vi] = 1
    return [l / max(1, n) for l, n in zip(lum, cnt)]


def occlusion_samples(obj, occluders=None, vertex_filter=None, n_dirs=24, ray_len=None,
                      eps=None, max_samples=4000, seed=5):
    """([vertex indices], [occlusion fraction 0..1]) for a seeded sample of obj's vertices."""
    me = obj.data
    occluders = occluders or [obj]
    bm = bmesh.new()
    for o in occluders:
        bm.from_mesh(o.data)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    diag = Vector(obj.dimensions).length or 1.0
    ray_len = diag * 0.08 if ray_len is None else ray_len
    eps = diag * 0.001 if eps is None else eps
    rnd = random.Random(seed)
    dirs = []
    for i in range(n_dirs):
        r1, r2 = (i + 0.5) / n_dirs, rnd.random()
        rr, ph = math.sqrt(r1), 2 * math.pi * r2
        dirs.append(Vector((rr * math.cos(ph), rr * math.sin(ph), math.sqrt(1 - r1))))
    cand = [v for v in me.vertices if vertex_filter is None or vertex_filter(v)]
    sample = rnd.sample(cand, min(max_samples, len(cand)))
    idx, occ = [], []
    for v in sample:
        n = v.normal
        rot = n.to_track_quat("Z", "Y").to_matrix()
        hits = sum(tree.ray_cast(v.co + n * eps, rot @ d, ray_len)[0] is not None for d in dirs)
        idx.append(v.index)
        occ.append(hits / len(dirs))
    return idx, occ


def bake_shading_check(obj, attr_name="Col", occluders=None, vertex_filter=None,
                       r_min=R_MIN, **occ_kw):
    """Run the gate on `obj`. Returns a verdict.Report (PASS / FAIL / NOT_TESTED)."""
    ps = ProbeSet("BAKE_SHADING %s" % obj.name)
    lum = vertex_luma(obj, attr_name)
    if lum is None:
        ps.report.add("no_baked_shading", NOT_TESTED,
                      "%s has no colour attribute %r: nothing to measure" % (obj.name, attr_name))
        return ps.report
    idx, occ = occlusion_samples(obj, occluders, vertex_filter, **occ_kw)
    judge(occ, [lum[i] for i in idx], report=ps, r_min=r_min)
    return ps.report
