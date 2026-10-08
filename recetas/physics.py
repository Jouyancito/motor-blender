# physics.py -- does the asset stand, hold together, and not pass through itself?
#
# WHY THIS EXISTS
#
# Every other gate looks at the asset as an image or as topology. None asks the
# questions a person asks in two seconds with the model in hand: would it fall
# over? is that part attached to anything? are those two things inside each
# other? (CREATION_PROTOCOL 5.2: "check for floating geometry"; the golem's
# detached stones; the 1.30 m "cat".) These are measurements, so they are gates.
#
# Four measurements, all in bpy, none needing a GPU:
#
#   1. support    centre of mass (volume-weighted) inside the convex hull of the
#                 ground-contact vertices, and the asset actually TOUCHING the
#                 ground (a floating or sunken asset has no support polygon)
#   2. drop       a rigid-body drop/settle over N frames of a temporary copy:
#                 final tilt and horizontal drift. LIMITATION: collision is the
#                 convex hull of the whole asset (a concave stance such as 4
#                 separate legs is not simulated leg by leg); check 1 covers
#                 the real stance statically.
#   3. islands    connected parts that touch nothing (neither another part nor,
#                 for families that stand, the ground)
#   4. interpen.  overlapping triangles between separate objects, by BVH
#
# Per-family policy lives in router_knowledge (`physics`): which checks apply,
# and whether islands / interpenetration FAIL or only REPORT. The numbers are
# initial and uncalibrated (basis says so); the measured values are always
# written to the verdict so a limit can be calibrated later.
#
# `bpy` / numpy / mathutils are imported inside the functions that need them; the
# 2-D geometry and the judge are pure and fixture-tested without Blender.
import math

from recetas.verdict import Report, PASS, FAIL, NOT_APPLICABLE

# ------------------------------------------------------------------ pure part


def convex_hull_2d(points):
    """Andrew's monotone chain. Returns the hull as a CCW list of (x, y); fewer
    than 3 points (or all collinear) returns the 1-2 distinct extreme points."""
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def hull_area(hull):
    if len(hull) < 3:
        return 0.0
    return abs(sum(hull[i][0] * hull[(i + 1) % len(hull)][1]
                   - hull[(i + 1) % len(hull)][0] * hull[i][1]
                   for i in range(len(hull)))) / 2.0


def inside_margin(pt, hull):
    """
    Signed distance from `pt` to the hull boundary in the plane: positive when
    inside (how far the COM is from tipping over), negative when outside. A hull
    with fewer than 3 vertices has no interior: the margin is -distance to it.
    """
    x, y = pt
    if len(hull) == 0:
        return float("-inf")
    if len(hull) < 3:
        d = min(math.hypot(x - hx, y - hy) for hx, hy in hull)
        if len(hull) == 2:
            (ax, ay), (bx, by) = hull
            L2 = (bx - ax) ** 2 + (by - ay) ** 2
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * (bx - ax)
                                                       + (y - ay) * (by - ay)) / L2))
            d = math.hypot(x - (ax + t * (bx - ax)), y - (ay + t * (by - ay)))
        return -d
    inside, best = True, float("inf")
    seg = float("inf")
    for i in range(len(hull)):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % len(hull)]
        ex, ey = bx - ax, by - ay
        L = math.hypot(ex, ey)
        if L == 0:
            continue
        side = (ex * (y - ay) - ey * (x - ax)) / L      # >0 = left of CCW edge
        best = min(best, abs(side))
        if side < 0:
            inside = False
        t = max(0.0, min(1.0, ((x - ax) * ex + (y - ay) * ey) / (L * L)))
        seg = min(seg, math.hypot(x - (ax + t * ex), y - (ay + t * ey)))
    return best if inside else -seg


def angle_deg(u, v):
    """Angle between two 3-vectors, degrees."""
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(a * a for a in v))
    if nu == 0 or nv == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (nu * nv)))))


def judge(m, cfg):
    """
    Pure core: measurements `m` + policy `cfg` -> Report.

    m keys (any may be None when not measured):
      ground_gap_m, support_margin_m, support_contacts, com,
      drop {tilt_deg, drift_m, rest_min_z}, islands {count, details,
      skipped_reason}, interpenetration {pairs, triangle_pairs}
    """
    r = Report("PHYSICS")
    tol = cfg["ground_tol_m"]

    if cfg["stands"]:
        gap = m.get("ground_gap_m")
        if gap is None:
            r.add("ground_contact", FAIL, "ground gap not measured")
        elif abs(gap) > tol:
            r.add("ground_contact", FAIL,
                  "lowest point is %+.3f m from the ground plane (|gap| > %.3f): "
                  "%s" % (gap, tol, "floating" if gap > 0 else "sunk below it"))
        else:
            r.add("ground_contact", PASS, "lowest point %+.3f m from ground" % gap)
        marg = m.get("support_margin_m")
        if marg is None:
            r.add("com_in_support", FAIL, "support polygon not measured")
        elif marg < 0:
            r.add("com_in_support", FAIL,
                  "centre of mass is %.3f m OUTSIDE the support polygon "
                  "(%s contact vertices): it tips over"
                  % (-marg, m.get("support_contacts")))
        else:
            r.add("com_in_support", PASS,
                  "COM %.3f m inside the support polygon (%s contact vertices)"
                  % (marg, m.get("support_contacts")))
    else:
        r.add("ground_contact", NOT_APPLICABLE,
              reason="family does not stand (%s)" % (cfg.get("reason")
                                                     or cfg.get("basis")))
        r.add("com_in_support", NOT_APPLICABLE,
              reason="family does not stand (%s)" % (cfg.get("reason")
                                                     or cfg.get("basis")))

    if cfg["drop_test"]:
        d = m.get("drop")
        if not d:
            r.add("drop_settle", FAIL, "drop test did not run")
        else:
            bad = []
            if d["tilt_deg"] > cfg["max_tilt_deg"]:
                bad.append("tilt %.1f deg > %.1f" % (d["tilt_deg"], cfg["max_tilt_deg"]))
            if d["drift_m"] > cfg["max_drift_m"]:
                bad.append("drift %.2f m > %.2f" % (d["drift_m"], cfg["max_drift_m"]))
            detail = ("tilt %.1f deg, drift %.3f m, rests at z=%.3f over %d frames"
                      % (d["tilt_deg"], d["drift_m"], d["rest_min_z"], d["frames"]))
            r.add("drop_settle", FAIL if bad else PASS,
                  detail + ((" -- " + "; ".join(bad)) if bad else ""))
    else:
        r.add("drop_settle", NOT_APPLICABLE,
              reason="family is not drop-tested (%s)" % (cfg.get("reason")
                                                         or cfg.get("basis")))

    _policy(r, "floating_islands", cfg["islands"], m.get("islands"),
            lambda v: v["count"], lambda v: "%d floating part(s): %s" % (
                v["count"], "; ".join(v.get("details", [])[:3])))
    _policy(r, "interpenetration", cfg["interpenetration"], m.get("interpenetration"),
            lambda v: v["pairs"], lambda v: "%d object pair(s) overlap "
            "(%d triangle pairs)" % (v["pairs"], v["triangle_pairs"]))
    return r


def _policy(r, prop, mode, value, count, text):
    if mode == "skip":
        r.add(prop, NOT_APPLICABLE, reason="family policy: skip (see router physics)")
        return
    if value is None:
        r.add(prop, FAIL, "not measured")
        return
    if value.get("skipped_reason"):
        r.add(prop, NOT_APPLICABLE, reason=value["skipped_reason"])
        return
    n = count(value)
    detail = text(value) if n else "none"
    if mode == "fail":
        r.add(prop, FAIL if n else PASS, detail)
    else:   # report: always PASS, the number is in the detail and the verdict
        r.add(prop, PASS, "report-only: " + detail)


# ------------------------------------------------------------- Blender part

PERTURB_DEG = (2.0, 1.0)   # initial disturbance of the drop test (rotation X, Y)


def _world_geometry(objs, evaluated=True):
    """(verts Nx3 float array, tris Mx3 int array, per-object (start, end) vert
    ranges) for all objects in world space."""
    import bpy
    import bmesh
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    verts, tris, ranges = [], [], []
    base = 0
    for o in objs:
        bm = bmesh.new()
        bm.from_object(o, dg) if evaluated else bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.verts.ensure_lookup_table()
        vs = [tuple(v.co) for v in bm.verts]
        ts = [tuple(base + v.index for v in f.verts) for f in bm.faces]
        verts.extend(vs)
        tris.extend(ts)
        ranges.append((base, base + len(vs)))
        base += len(vs)
        bm.free()
    return (np.array(verts, dtype=float).reshape(-1, 3),
            np.array(tris, dtype=int).reshape(-1, 3), ranges)


def center_of_mass(verts, tris):
    """Volume-weighted centroid (tetrahedra from the origin). Falls back to the
    area-weighted surface centroid when the signed volume is ~0 (open meshes)."""
    import numpy as np
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    total = vol.sum()
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0
    if abs(total) > 1e-9 * max(1.0, area.sum()):
        cent = (a + b + c) / 4.0
        return (cent * vol[:, None]).sum(axis=0) / total, "volume"
    cent = (a + b + c) / 3.0
    return (cent * area[:, None]).sum(axis=0) / area.sum(), "surface"


def support_measure(verts, tris, ground_z=0.0, tol=0.02):
    """Ground gap, support-polygon margin and COM for a world-space mesh."""
    com, kind = center_of_mass(verts, tris)
    min_z = float(verts[:, 2].min())
    contacts = verts[verts[:, 2] <= min_z + tol]
    hull = convex_hull_2d([(float(x), float(y)) for x, y, _z in contacts])
    margin = inside_margin((float(com[0]), float(com[1])), hull)
    return {"ground_gap_m": min_z - ground_z, "support_margin_m": margin,
            "support_contacts": int(len(contacts)),
            "support_hull_area_m2": hull_area(hull),
            "com": [round(float(v), 4) for v in com], "com_kind": kind}


def islands_measure(objs, ground_z=0.0, stands=True, touch_tol=0.005,
                    ground_tol=0.02, cap=300):
    """
    Group loose parts into connected clusters (touching = BVH overlap or
    vertex-to-surface distance <= touch_tol). Every cluster except the largest
    is an island; for standing families an island resting on the ground does
    not count as floating.
    """
    import bpy
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    comps, trees, boxes, cverts = [], [], [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        vs = [mw @ v.co for v in me.vertices]
        parent = list(range(len(vs)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for e in me.edges:
            ra, rb = find(e.vertices[0]), find(e.vertices[1])
            if ra != rb:
                parent[ra] = rb
        groups = {}
        for i in range(len(vs)):
            groups.setdefault(find(i), []).append(i)
        polys_by_root = {}
        for pl in me.polygons:
            polys_by_root.setdefault(find(pl.vertices[0]), []).append(tuple(pl.vertices))
        for root, idx in groups.items():
            arr = np.array([tuple(vs[i]) for i in idx])
            comps.append((o, idx))
            cverts.append(arr)
            boxes.append((arr.min(axis=0) - touch_tol, arr.max(axis=0) + touch_tol))
            polys = polys_by_root.get(root, [])
            trees.append(BVHTree.FromPolygons(vs, polys, all_triangles=False,
                                              epsilon=0.0) if polys else None)
        ev.to_mesh_clear()
        if len(comps) > cap:
            return {"count": 0, "components": len(comps), "details": [],
                    "skipped_reason": "more than %d loose parts: island analysis "
                                      "skipped (declared gap)" % cap}
    n = len(comps)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            lo = np.maximum(boxes[i][0], boxes[j][0])
            hi = np.minimum(boxes[i][1], boxes[j][1])
            if (lo > hi).any():
                continue
            touching = False
            if trees[i] is not None and trees[j] is not None:
                touching = bool(trees[i].overlap(trees[j]))
                if not touching:
                    for p in cverts[i]:
                        hit = trees[j].find_nearest(Vector(p))
                        if hit[0] is not None and hit[3] <= touch_tol:
                            touching = True
                            break
            if touching:
                parent[find(i)] = find(j)
    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    sizes = {k: sum(len(cverts[i]) for i in v) for k, v in clusters.items()}
    main = max(sizes, key=sizes.get)
    details = []
    for k, members in clusters.items():
        if k == main:
            continue
        zmin = min(float(cverts[i][:, 2].min()) for i in members)
        on_ground = stands and abs(zmin - ground_z) <= ground_tol
        if on_ground:
            continue
        o = comps[members[0]][0]
        details.append("%s (%d verts, lowest z=%.3f)" % (o.name, sizes[k], zmin))
    return {"count": len(details), "components": n, "clusters": len(clusters),
            "details": details}


def interpenetration_measure(objs, cap_objects=60):
    """BVH triangle overlap between every pair of SEPARATE objects."""
    import bpy
    from mathutils.bvhtree import BVHTree
    if len(objs) < 2:
        return {"pairs": 0, "triangle_pairs": 0, "details": [],
                "skipped_reason": "single object: nothing to interpenetrate"}
    if len(objs) > cap_objects:
        return {"pairs": 0, "triangle_pairs": 0, "details": [],
                "skipped_reason": "%d objects > cap %d: pairwise analysis "
                                  "skipped (declared gap)" % (len(objs), cap_objects)}
    dg = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, dg) for o in objs]
    pairs, tri, details = 0, 0, []
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            hit = trees[i].overlap(trees[j])
            if hit:
                pairs += 1
                tri += len(hit)
                details.append("%s x %s: %d triangle pairs"
                               % (objs[i].name, objs[j].name, len(hit)))
    return {"pairs": pairs, "triangle_pairs": tri, "details": details[:10]}


def drop_measure(objs, ground_z=0.0, drop_height=0.05, frames=60):
    """
    Rigid-body drop of ONE temporary mesh (all objects merged, origin at the
    centre of mass, convex-hull collision) onto a passive ground plane. The scene
    is restored afterwards. Returns tilt (angle of the up axis), horizontal drift
    of the COM and the lowest point at rest.
    """
    import bpy
    import bmesh
    from mathutils import Vector
    scene = bpy.context.scene
    verts, tris, _r = _world_geometry(objs)
    com, _kind = center_of_mass(verts, tris)

    me = bpy.data.meshes.new("__phys_probe")
    bm = bmesh.new()
    vmap = [bm.verts.new(tuple(v - com)) for v in verts]
    for t in tris:
        try:
            bm.faces.new([vmap[i] for i in t])
        except ValueError:
            pass                                # duplicate face: harmless here
    bm.to_mesh(me)
    bm.free()
    probe = bpy.data.objects.new("__phys_probe", me)
    scene.collection.objects.link(probe)
    probe.location = (float(com[0]), float(com[1]), float(com[2]) + drop_height)
    # A deterministic 2/1 degree disturbance: a perfectly symmetric body balanced
    # on an unstable equilibrium (a cone on its tip) never topples in an ideal
    # simulation, so without it the test would pass shapes that fall over in life.
    probe.rotation_euler = (math.radians(PERTURB_DEG[0]), math.radians(PERTURB_DEG[1]), 0.0)

    gme = bpy.data.meshes.new("__phys_ground")
    gbm = bmesh.new()
    bmesh.ops.create_cube(gbm, size=1.0)
    gbm.to_mesh(gme)
    gbm.free()
    ground = bpy.data.objects.new("__phys_ground", gme)
    ground.scale = (200.0, 200.0, 1.0)
    ground.location = (0.0, 0.0, ground_z - 0.5)         # top face at ground_z
    scene.collection.objects.link(ground)

    had_world = scene.rigidbody_world is not None
    saved = (scene.frame_start, scene.frame_end, scene.frame_current)
    result = None
    try:
        bpy.context.view_layer.update()
        if not had_world:
            bpy.ops.rigidbody.world_add()
        rbw = scene.rigidbody_world
        rbw.point_cache.frame_start, rbw.point_cache.frame_end = 1, frames
        scene.frame_start, scene.frame_end = 1, frames
        for ob, kind in ((ground, 'PASSIVE'), (probe, 'ACTIVE')):
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.rigidbody.object_add(type=kind)
        ground.rigid_body.collision_shape = 'BOX'
        probe.rigid_body.collision_shape = 'CONVEX_HULL'
        probe.rigid_body.mass = 1.0
        scene.frame_set(1)
        for f in range(1, frames + 1):
            scene.frame_set(f)
        bpy.context.view_layer.update()
        mw = probe.matrix_world
        up = mw.to_3x3() @ Vector((0.0, 0.0, 1.0))
        fin = mw.translation
        rest_min = min((mw @ Vector(c)).z for c in probe.bound_box)
        result = {"tilt_deg": angle_deg(tuple(up), (0.0, 0.0, 1.0)),
                  "drift_m": math.hypot(fin.x - float(com[0]), fin.y - float(com[1])),
                  "rest_min_z": float(rest_min), "frames": frames,
                  "drop_height_m": drop_height,
                  "collision": "convex hull of the whole asset"}
    finally:
        scene.frame_set(saved[2])
        scene.frame_start, scene.frame_end = saved[0], saved[1]
        if not had_world and scene.rigidbody_world is not None:
            bpy.ops.rigidbody.world_remove()
        for ob in (probe, ground):
            data = ob.data
            bpy.data.objects.remove(ob)
            bpy.data.meshes.remove(data)
    return result


def measure(objs, cfg, ground_z=0.0):
    """Run every measurement the family's policy asks for."""
    verts, tris, _ranges = _world_geometry(objs)
    m = {}
    if cfg["stands"]:
        m.update(support_measure(verts, tris, ground_z, cfg["ground_tol_m"]))
    else:
        com, kind = center_of_mass(verts, tris)
        m["com"] = [round(float(v), 4) for v in com]
        m["lowest_z_m"] = float(verts[:, 2].min())
    if cfg["drop_test"]:
        m["drop"] = drop_measure(objs, ground_z, cfg["drop_height_m"], cfg["frames"])
    if cfg["islands"] != "skip":
        m["islands"] = islands_measure(objs, ground_z, cfg["stands"],
                                       ground_tol=cfg["ground_tol_m"])
    if cfg["interpenetration"] != "skip":
        m["interpenetration"] = interpenetration_measure(objs)
    return m


def check_physics(objs, cfg, ground_z=0.0, verbose=True):
    m = measure(objs, cfg, ground_z)
    rep = judge(m, cfg)
    if verbose:
        print(rep.render())
    return rep, m
