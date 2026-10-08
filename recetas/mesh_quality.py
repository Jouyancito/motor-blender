# mesh_quality.py -- judge a mesh with numbers instead of by eye (canonical copy).
#
# PORTED 2026-10-08 from DungeonParty-A game/tools/blender/mesh_quality.py,
# which implemented BER / topology_score / hausdorff and had zero callers
# besides its own test. The motor is transversal, so this is the canonical home
# and it is wired into motor_run (step `mesh`); the game copy is now redundant.
#
# Metrics come from the evaluation stage of the Hunyuan3D Studio game-ready
# pipeline (arXiv 2509.12815):
#     BER  Boundary Edge Ratio  -- holes and loose borders
#     TS   Topology Score       -- OUR composition (the paper publishes no
#                                  formula); do not cite it as theirs
#     HD   Hausdorff Distance   -- did a derived mesh drift off its source
#
# NEW IN THE PORT (gate, not just measurement):
#     inconsistent_normals()  edges whose two faces disagree on winding, plus an
#                             inward-facing closed volume (negative signed volume)
#     uv_report()             missing UV layer / overlapping UV islands
#     check_mesh()            a Report per object: PASS/FAIL against per-family
#                             limits from router_knowledge (`mesh` field)
#
# `bpy`, `bmesh` and mathutils are imported inside the functions that need them
# so the pure helpers stay importable without Blender.
from recetas.verdict import Report, PASS, FAIL, NOT_TESTED, NOT_APPLICABLE

# Degenerate below this area, in square metres. A 0.1 mm triangle on a human is
# not detail, it is a vertex that failed to merge.
DEGENERATE_AREA = 1e-8

# A quad corner this far out of plane, relative to the face span, will shade as
# two visibly different halves once the engine triangulates it.
PLANARITY_TOL = 0.02

UV_GRID = 256


class masks_muted:
    """Turn off MASK modifiers for the duration of a block (they change the
    vertex count the depsgraph hands back, silently breaking 1:1 indexing)."""

    def __init__(self, *objs):
        self.objs = [o for o in objs if o is not None]
        self.states = []

    def __enter__(self):
        import bpy
        for o in self.objs:
            for m in o.modifiers:
                if m.type == "MASK":
                    self.states.append((m, m.show_viewport))
                    m.show_viewport = False
        bpy.context.view_layer.update()
        return self

    def __exit__(self, *exc):
        import bpy
        for m, was in self.states:
            m.show_viewport = was
        bpy.context.view_layer.update()
        return False


def bm_from(obj, evaluated=True):
    """World-space bmesh. evaluated=False gives the raw cage."""
    import bpy
    import bmesh
    bm = bmesh.new()
    if evaluated:
        bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
    else:
        bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    return bm


def boundary_edge_ratio(bm):
    """Fraction of edges owned by exactly one face (0.0 = closed volume)."""
    total = len(bm.edges)
    if total == 0:
        raise ValueError("mesh has no edges -- nothing to measure")
    boundary = [e for e in bm.edges if len(e.link_faces) == 1]
    return {"ber": len(boundary) / total, "boundary_edges": len(boundary),
            "total_edges": total, "border_loops": _count_border_loops(boundary)}


def _count_border_loops(boundary_edges):
    by_index = {e.index: e for e in boundary_edges}
    remaining = set(by_index)
    loops = 0
    while remaining:
        loops += 1
        stack = [remaining.pop()]
        while stack:
            e = by_index[stack.pop()]
            for v in e.verts:
                for nb in v.link_edges:
                    if nb.index in remaining:
                        remaining.discard(nb.index)
                        stack.append(nb.index)
    return loops


def topology_score(bm):
    """0.0 (broken) .. 1.0 (clean), plus the raw defect counts. Non-manifold and
    degenerate are hard errors that break export and dominate the score; valence
    and planarity are quality signals (see the game original for the rationale)."""
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < DEGENERATE_AREA)

    interior = [v for v in bm.verts
                if not v.is_boundary and not v.is_wire and v.link_faces]
    irregular = sum(1 for v in interior if len(v.link_edges) != 4)
    valence_rate = irregular / len(interior) if interior else 0.0

    quads = [f for f in bm.faces if len(f.verts) == 4]
    nonplanar = 0
    for f in quads:
        a, b, c, d = (v.co for v in f.verts)
        span = max((a - c).length, (b - d).length)
        if span > 0 and abs((d - a).dot(f.normal)) / span > PLANARITY_TOL:
            nonplanar += 1
    planar_rate = nonplanar / len(quads) if quads else 0.0

    score = 1.0
    score -= min(0.40, 40.0 * nonmanifold / max(1, len(bm.edges)))
    score -= min(0.40, 40.0 * degenerate / max(1, len(bm.faces)))
    score -= 0.12 * valence_rate
    score -= 0.08 * planar_rate
    return {"ts": max(0.0, score), "nonmanifold_edges": nonmanifold,
            "degenerate_faces": degenerate, "irregular_valence": irregular,
            "valence_rate": valence_rate, "nonplanar_quads": nonplanar,
            "planar_rate": planar_rate, "interior_verts": len(interior),
            "quads": len(quads),
            "tris": sum(1 for f in bm.faces if len(f.verts) == 3),
            "ngons": sum(1 for f in bm.faces if len(f.verts) > 4)}


def signed_volume(bm):
    """Signed volume from face fans (positive = outward-facing winding on a
    closed mesh). Meaningless on an open mesh: the caller checks boundary_edges."""
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    return vol


def inconsistent_normals(bm):
    """
    Normals defects that survive a visual glance at a flat-shaded render:

      inconsistent_edges  manifold edges whose two faces traverse the edge in the
                          SAME direction (winding disagrees: one face is flipped
                          relative to its neighbour)
      inward_closed       True when the mesh is closed and its signed volume is
                          negative (the whole shell faces inward)
    """
    bad = 0
    for e in bm.edges:
        if len(e.link_loops) == 2:
            l1, l2 = e.link_loops
            if l1.vert == l2.vert:
                bad += 1
    closed = all(len(e.link_faces) == 2 for e in bm.edges) and len(bm.edges) > 0
    vol = signed_volume(bm) if closed else 0.0
    return {"inconsistent_edges": bad, "closed": closed,
            "signed_volume": vol, "inward_closed": bool(closed and vol < 0.0)}


def _tri_cover(tris, grid=UV_GRID):
    """(sum of per-triangle covered cells, cells covered by at least one)."""
    import numpy as np
    count = np.zeros((grid, grid), dtype=np.int32)
    xs = (np.arange(grid) + 0.5) / grid
    for (ax, ay), (bx, by), (cx, cy) in tris:
        x0, x1 = int(max(0, min(ax, bx, cx) * grid - 1)), int(min(grid, max(ax, bx, cx) * grid + 2))
        y0, y1 = int(max(0, min(ay, by, cy) * grid - 1)), int(min(grid, max(ay, by, cy) * grid + 2))
        if x0 >= x1 or y0 >= y1:
            continue
        px, py = np.meshgrid(xs[x0:x1], xs[y0:y1])
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        w1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
        w2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
        inside = (w1 >= 0) & (w2 >= 0) & (1 - w1 - w2 >= 0)
        count[y0:y1, x0:x1] += inside.astype(np.int32)
    return int(count.sum()), int((count > 0).sum())


def uv_overlap_ratio(tris):
    """Share of covered UV area that is covered more than once (0 = no overlap)."""
    total, union = _tri_cover(tris)
    return 0.0 if total == 0 else (total - union) / total


def uv_report(obj):
    """{"has_uv": bool, "overlap": ratio|None} from the object's ACTIVE UV map."""
    me = obj.data
    if not me.uv_layers:
        return {"has_uv": False, "overlap": None}
    me.calc_loop_triangles()
    uv = me.uv_layers.active.data
    tris = [tuple(tuple(uv[i].uv) for i in t.loops) for t in me.loop_triangles]
    return {"has_uv": True, "overlap": uv_overlap_ratio(tris), "tris": len(tris)}


def hausdorff(bm_a, bm_b, symmetric=True):
    """Distance from mesh A to the SURFACE of mesh B, in mm (max, p95, mean)."""
    from mathutils.bvhtree import BVHTree
    tree_b = BVHTree.FromBMesh(bm_b)
    d_ab = _distances(bm_a, tree_b)
    if not d_ab:
        raise ValueError("mesh A has no vertices to sample")
    out = {"max_mm": max(d_ab) * 1000.0, "p95_mm": _percentile(d_ab, 0.95) * 1000.0,
           "mean_mm": sum(d_ab) / len(d_ab) * 1000.0, "samples": len(d_ab)}
    if symmetric:
        d_ba = _distances(bm_b, BVHTree.FromBMesh(bm_a))
        if d_ba:
            out["max_mm_reverse"] = max(d_ba) * 1000.0
            out["hausdorff_mm"] = max(out["max_mm"], out["max_mm_reverse"])
    return out


def _distances(bm, tree):
    out = []
    for v in bm.verts:
        hit = tree.find_nearest(v.co)
        if hit[0] is not None:
            out.append(hit[3])
    return out


def _percentile(values, q):
    s = sorted(values)
    return 0.0 if not s else s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


# ------------------------------------------------------------------ the gate

DEFAULT_LIMITS = {"max_nonmanifold": 0, "max_degenerate": 0, "max_inconsistent": 0,
                  "needs_uv": False, "uv_overlap_max": 0.02, "max_tris": None}


def judge(measures, limits, name="mesh"):
    """
    Pure core of the gate: `measures` dict -> Report. Testable without Blender.

    measures: nonmanifold_edges, degenerate_faces, inconsistent_edges,
              inward_closed, tris_total, uv {has_uv, overlap}
    """
    lim = dict(DEFAULT_LIMITS)
    lim.update(limits or {})
    r = Report("MESH %s" % name)

    def cmp(prop, value, limit, unit=""):
        r.add(prop, PASS if value <= limit else FAIL,
              "%s%s (max %s)" % (value, unit, limit))

    cmp("nonmanifold_edges", measures["nonmanifold_edges"], lim["max_nonmanifold"])
    cmp("degenerate_faces", measures["degenerate_faces"], lim["max_degenerate"])
    cmp("inconsistent_winding_edges", measures["inconsistent_edges"],
        lim["max_inconsistent"])
    r.add("normals_outward", FAIL if measures["inward_closed"] else PASS,
          "closed mesh with negative signed volume (%.4f)" % measures.get("signed_volume", 0.0)
          if measures["inward_closed"] else "not inward-facing")
    if lim["max_tris"] is not None:
        cmp("tri_budget", measures["tris_total"], lim["max_tris"])
    else:
        r.add("tri_budget", NOT_APPLICABLE,
              reason="no sourced triangle budget for this family")

    if lim["needs_uv"]:
        uv = measures["uv"]
        if not uv["has_uv"]:
            r.add("uv_present", FAIL, "family requires textures but the mesh has no UV map")
            r.add("uv_overlap", NOT_TESTED, "no UV map to measure")
        else:
            r.add("uv_present", PASS, "%s tris mapped" % uv.get("tris", "?"))
            ov = uv["overlap"]
            r.add("uv_overlap", PASS if ov <= lim["uv_overlap_max"] else FAIL,
                  "%.3f of covered UV area is covered twice (max %.3f)"
                  % (ov, lim["uv_overlap_max"]))
    else:
        r.add("uv_present", NOT_APPLICABLE,
              reason="family does not require textures (vertex-colour workflow)")
    return r


def measure_object(obj, evaluated=True):
    with masks_muted(obj):
        bm = bm_from(obj, evaluated)
        try:
            m = {}
            m.update(boundary_edge_ratio(bm))
            m.update(topology_score(bm))
            m.update(inconsistent_normals(bm))
            m["tris_total"] = sum(len(f.verts) - 2 for f in bm.faces)
            m["verts"], m["faces"] = len(bm.verts), len(bm.faces)
        finally:
            bm.free()
    m["uv"] = uv_report(obj)
    return m


def check_mesh(objs, limits, verbose=True):
    """Judge every mesh and merge into one Report (one row set per object)."""
    merged = Report("MESH QUALITY")
    measures = {}
    for o in objs:
        m = measure_object(o)
        measures[o.name] = m
        sub = judge(m, limits, o.name)
        for row in sub.rows:
            merged.add("%s: %s" % (o.name, row["prop"]), row["state"],
                       row["detail"], row["reason"])
    if verbose:
        print(merged.render())
    return merged, measures
