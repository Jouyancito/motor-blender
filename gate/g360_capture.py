# g360_capture.py — GATE 360 capture: fixed 13-view render set + geometric audits (v1.1).
#
# One headless Blender launch does BOTH halves of "seeing":
#   1. Renders the FIXED 13-view set (12-shot standard + face close-up) of the live
#      scene into _gate/g360/views/. Same views every run — verdicts comparable.
#   2. Geometric audits without any render, written to orientation.json:
#      - paint orientation: world normals (inverse-transform — the missing .T once
#        painted the belly on the BACK) vs vertex-color class
#      - mesh islands: the main object must be ONE island (floating chunks are invisible
#        to silhouette rules when they overlap the body in projection)
#
# v1.1 (post ultracode review): 13 views (rear ¾ + worm ±60 + bird + face restore the
# 12-shot standard), PNG/res% pinned, try/finally restore, expected-paint floors FAIL
# instead of silently skipping, evaluated-mesh vert-count guard, robust ventral anchor.
#
# Run headless (the canonical way, via corporeo_step.py):
#   blender.exe -b <blend> --python-exit-code 1 --python g360_capture.py -- --out <dir> [--res 1500]
import bpy
import json
import math
import os
import sys

import numpy as np
from mathutils import Vector

# ---------------------------------------------------------------- args
def _default_object():
    """Single source of truth: motor.config.json at repo root. Hardcoding a name
    here is how the gate silently measured the retired body_united (2026-07-16)."""
    cfg_path = os.path.join(os.path.dirname(bpy.data.filepath), "..", "motor.config.json")
    try:
        with open(cfg_path) as f:
            return json.load(f).get("main_object", "base_v2")
    except Exception:
        return "base_v2"


def _parse_args():
    argv = sys.argv
    args = {"out": None, "res": 1500, "object": _default_object(), "zone": ""}
    if "--" in argv:
        rest = argv[argv.index("--") + 1:]
        i = 0
        while i < len(rest):
            k = rest[i].lstrip("-")
            if k in args:
                if i + 1 >= len(rest):
                    print(f"[g360] FATAL: flag --{k} needs a value")
                    sys.exit(2)
                args[k] = rest[i + 1]
                i += 2
            else:
                i += 1
    if args["out"] is None:
        args["out"] = os.path.join(os.path.dirname(bpy.data.filepath), "..", "_gate", "g360", "views")
    args["res"] = int(args["res"])
    return args


# The fixed view set (name, azimuth deg, elevation deg). az 0 = camera at -Y looking
# +Y (the bear faces -Y: muzzle world-normal N_y is negative — the sanity anchor).
# Matches the project's 12-shot verdict standard (skill corporeo-3d) + face close-up.
VIEWS = [
    ("front",    0,    0),
    ("back",     180,  0),
    ("side_L",   90,   0),
    ("side_R",  -90,   0),
    ("q34_L",    45,   0),
    ("q34_R",   -45,   0),
    ("rear34_L", 135,  0),
    ("rear34_R", -135, 0),
    ("worm",     0,  -30),
    ("wormL60",  60, -30),
    ("wormR60", -60, -30),
    ("bird",     0,   35),
]


def world_bbox(obj):
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for c in obj.bound_box:
        w = obj.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
    return mn, mx


def render_views(main_obj, out_dir, res):
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    mn, mx = world_bbox(main_obj)
    ctr = (mn + mx) * 0.5
    rad = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    height = mx.z - mn.z
    # face close-up target: head center (top ~14% below the crown)
    face_ctr = Vector((ctr.x, ctr.y, mn.z + 0.86 * height))

    cam = bpy.data.objects.get("GateCam")
    if not cam:
        cd = bpy.data.cameras.new("GateCamData")
        cam = bpy.data.objects.new("GateCam", cd)
        sc.collection.objects.link(cam)
    cam.data.lens = 70

    rs = sc.render
    prev = (sc.camera, rs.resolution_x, rs.resolution_y, rs.filepath,
            sc.view_settings.view_transform, rs.resolution_percentage,
            rs.image_settings.file_format)
    paths = {}
    try:
        sc.camera = cam
        rs.resolution_x = int(res * 0.82)
        rs.resolution_y = res
        rs.resolution_percentage = 100          # a saved 50% preview must not shrink the gate
        rs.image_settings.file_format = 'PNG'
        sc.view_settings.view_transform = 'Standard'  # viewer match, not AgX

        # per-view distance fit: project the 8 bbox corners through the camera and
        # grow dist until all fit with margin — a fixed multiplier clipped the figure
        # in 8 of 13 views (the frame-clip rule in gate360 proved it)
        tan_v = 18.0 / cam.data.lens                      # 36mm sensor on the tall axis
        tan_h = tan_v * (rs.resolution_x / rs.resolution_y)
        corners = [Vector((X, Y, Z)) for X in (mn.x, mx.x) for Y in (mn.y, mx.y) for Z in (mn.z, mx.z)]

        def fits(loc, tgt, margin=0.90):
            fwd = (tgt - loc).normalized()
            right = fwd.cross(Vector((0, 0, 1)))
            if right.length < 1e-6:
                right = Vector((1, 0, 0))
            right.normalize()
            up = right.cross(fwd)
            for c in corners:
                v = c - loc
                d = v.dot(fwd)
                if d <= 0.01:
                    return False
                if abs(v.dot(right)) > margin * tan_h * d or abs(v.dot(up)) > margin * tan_v * d:
                    return False
            return True

        def shot(name, az, el, tgt, dist, fit=True):
            a, e = math.radians(az), math.radians(el)
            direction = Vector((math.sin(a) * math.cos(e),
                                -math.cos(a) * math.cos(e),
                                math.sin(e)))
            if fit:
                while not fits(tgt + direction * dist, tgt) and dist < rad * 6:
                    dist *= 1.06
            cam.location = tgt + direction * dist
            d = tgt - cam.location
            cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
            fp = os.path.join(out_dir, f"v_{name}.png")
            rs.filepath = fp
            bpy.ops.render.render(write_still=True)
            paths[name] = fp
            print(f"[g360] shot {name} (dist {dist / rad:.2f}r)")

        for name, az, el in VIEWS:
            shot(name, az, el, ctr, rad * 1.7)
        shot("face", 8, 2, face_ctr, rad * 0.72, fit=False)  # deliberate close-up crop
    finally:
        (sc.camera, rs.resolution_x, rs.resolution_y, rs.filepath,
         sc.view_settings.view_transform, rs.resolution_percentage,
         rs.image_settings.file_format) = prev
    return paths


def render_zone(main_obj, out_dir, res, zone):
    """View 14 — dynamic close-up of the touched zone (from the feature's ficha).
    zone = 'cx,cy,cz,r' in world coords."""
    try:
        cx_, cy_, cz_, zr = [float(v) for v in zone.split(",")]
    except Exception:
        print(f"[g360] WARN: bad --zone '{zone}' (want cx,cy,cz,r) — skipping feature view")
        return
    sc = bpy.context.scene
    cam = bpy.data.objects.get("GateCam")
    rs = sc.render
    prev = (sc.camera, rs.resolution_x, rs.resolution_y, rs.filepath,
            sc.view_settings.view_transform, rs.resolution_percentage,
            rs.image_settings.file_format)
    try:
        sc.camera = cam
        rs.resolution_x = 900
        rs.resolution_y = 700
        rs.resolution_percentage = 100
        rs.image_settings.file_format = 'PNG'
        sc.view_settings.view_transform = 'Standard'
        tgt = Vector((cx_, cy_, cz_))
        for tag, az, el in (("feature", 20, -8), ("feature_b", -25, -20)):
            a, e = math.radians(az), math.radians(el)
            cam.location = tgt + Vector((zr * 2.4 * math.sin(a) * math.cos(e),
                                         -zr * 2.4 * math.cos(a) * math.cos(e),
                                         zr * 2.4 * math.sin(e)))
            cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
            rs.filepath = os.path.join(out_dir, f"v_{tag}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[g360] shot {tag} (zone close-up)")
    finally:
        (sc.camera, rs.resolution_x, rs.resolution_y, rs.filepath,
         sc.view_settings.view_transform, rs.resolution_percentage,
         rs.image_settings.file_format) = prev


# ---------------------------------------------------------------- geometric audits
def _vertex_colors(me):
    """Return (n,4) float colors from the paint attribute (POINT domain), or None."""
    attr = me.color_attributes.get("brand")
    if attr is None or attr.domain != 'POINT':
        attr = next((a for a in me.color_attributes if a.domain == 'POINT'), None)
    if attr is None:
        return None, None
    n = len(me.vertices)
    cols = np.empty(n * 4, dtype=np.float32)
    attr.data.foreach_get("color", cols)
    return cols.reshape(n, 4)[:, :3], attr.name


def _island_check(me, min_verts=500):
    """The main object must be ONE watertight skin — a detached chunk overlapping the
    body in projection is invisible to every silhouette rule, so check it in 3D."""
    n = len(me.vertices)
    parent = np.arange(n, dtype=np.int64)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    ne = len(me.edges)
    ev = np.empty(ne * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(ne, 2)
    for a, b in ev:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    roots, counts = np.unique(np.fromiter((find(i) for i in range(n)), dtype=np.int64, count=n),
                              return_counts=True)
    big = int((counts >= min_verts).sum())
    return {"n_islands_total": int(len(roots)), "n_islands_big": big,
            "verdict": "PASS" if big <= 1 else "FAIL",
            "rule": f"more than one mesh island >= {min_verts} verts = detached chunk"}


def orientation_audit(main_obj, out_path):
    """Paint class vs world normal — catches paint landing on the wrong side of the
    body (the normals-transform bug class) with zero renders."""
    deps = bpy.context.evaluated_depsgraph_get()
    ob = main_obj.evaluated_get(deps)
    me = ob.to_mesh()
    base_n = len(main_obj.data.vertices)
    used_base = False
    if len(me.vertices) != base_n:
        # GN realized fur (or similar) polluted the evaluated mesh — the paint
        # attribute defaults would flood the class masks. Audit the base mesh.
        print(f"[g360] WARN: evaluated verts {len(me.vertices)} != base {base_n} — auditing base mesh")
        ob.to_mesh_clear()
        me = main_obj.data
        used_base = True
    n = len(me.vertices)

    co = np.empty(n * 3, dtype=np.float32)
    no = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    me.vertices.foreach_get("normal", no)
    co = co.reshape(n, 3)
    no = no.reshape(n, 3)

    M = np.array(main_obj.matrix_world)
    # correct normal transform is the inverse (row-vector form of (M^-1)^T);
    # for pure rotation it equals M.T — the missing .T was THE front/back-flip bug
    Nw = no @ np.linalg.inv(M[:3, :3])
    Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-9)
    Cw = co @ M[:3, :3].T + M[:3, 3]

    cols, attr_name = _vertex_colors(me)
    report = {"attr": attr_name, "n_verts": int(n), "audited_base_mesh": used_base,
              "checks": {}, "verdict": "PASS"}

    z = Cw[:, 2]
    z_frac = (z - z.min()) / max(z.max() - z.min(), 1e-9)

    checks = {}
    checks["mesh_islands"] = _island_check(main_obj.data)

    # SANITY DE ESCENA (Joan 2026-07-14: "si veo algo, lo veo del centro, frente a mí —
    # ¿está bien así?"). Las expectativas de un espectador son chequeos del motor:
    ctr_x = float((Cw[:, 0].min() + Cw[:, 0].max()) / 2)
    feet = float(Cw[:, 2].min())
    checks["escena_sujeto_en_origen"] = {
        "centro_x": round(ctr_x, 3), "pies_z": round(feet, 3),
        "verdict": "PASS" if (abs(ctr_x) < 0.05 and abs(feet) < 0.05) else "FAIL",
        "rule": "sujeto centrado en x=0 y pies en z=0 — coordenadas heredadas por accidente NO son convención",
    }

    if cols is None:
        checks["paint_attribute"] = {"verdict": "FAIL",
                                     "rule": "no POINT-domain color attribute found — paint audit impossible"}
    else:
        v = cols.max(axis=1)
        mn_c = cols.min(axis=1)
        s = (v - mn_c) / np.maximum(v, 1e-9)
        green_dom = (cols[:, 1] > cols[:, 0]) & (cols[:, 1] > cols[:, 2])
        # ventral = green NOTABLY LIGHTER than the body green. Anchor on a low
        # percentile so a large light belly can't drag the reference up (median trap).
        v_green_anchor = float(np.percentile(v[green_dom], 35)) if green_dom.any() else 0.7
        ventral = green_dom & (v > v_green_anchor + 0.06) & (z_frac > 0.25) & (z_frac < 0.75)
        tan = (cols[:, 0] > cols[:, 1]) & (cols[:, 1] > cols[:, 2]) & (s > 0.15) & (v > 0.35) & (z_frac > 0.70)
        dark = (v < 0.22)

        # expected-paint floors: a missing anchor class is a FAIL, not a silent skip
        if tan.sum() < 50:
            checks["muzzle_paint_missing"] = {"n": int(tan.sum()), "verdict": "FAIL",
                                              "rule": "expected tan muzzle paint (>=50 verts) not found"}
        else:
            mean_ny = float(Nw[tan, 1].mean())
            checks["muzzle_faces_front"] = {
                "mean_Ny": round(mean_ny, 3), "n": int(tan.sum()),
                "verdict": "PASS" if mean_ny < -0.05 else "FAIL",
                "rule": "tan muzzle paint mean N_y must be negative (bear faces -Y)",
            }
        if ventral.sum() < 50:
            checks["ventral_paint_missing"] = {"n": int(ventral.sum()), "verdict": "FAIL",
                                               "rule": "expected light-green ventral paint (>=50 verts) not found"}
        else:
            fb = float((Nw[ventral, 1] > 0.30).sum() / ventral.sum())
            checks["ventral_not_on_back"] = {
                "frac_backfacing": round(fb, 4), "n": int(ventral.sum()),
                "verdict": "PASS" if fb < 0.08 else "FAIL",
                "rule": "light-green ventral paint on N_y>0.3 verts < 8%",
            }
        if dark.sum() >= 50:
            fb_dark = float((Nw[dark, 1] > 0.30).sum() / dark.sum())
            checks["dark_back_share"] = {
                "frac_backfacing": round(fb_dark, 4), "n": int(dark.sum()),
                "verdict": "PASS" if fb_dark < 0.45 else "FAIL",
                "rule": "dark paint mostly on back-facing skin = misplaced shadow/stain",
            }

    report["checks"] = checks
    verdicts = [c.get("verdict") for c in checks.values() if isinstance(c, dict)]
    if not verdicts:
        report["verdict"] = "FAIL"  # zero checks ran = the audit saw nothing; never a free pass
    elif "FAIL" in verdicts:
        report["verdict"] = "FAIL"

    if not used_base:
        ob.to_mesh_clear()
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[g360] geometric audit: {report['verdict']} -> {out_path}")
    return report


def main():
    args = _parse_args()
    obj = bpy.data.objects.get(args["object"])
    if obj is None:
        # FAIL CLOSED — no silent fallback. A gate that measures "whatever mesh is
        # biggest" produces confident PASSes on the wrong object (2026-07-16 audit).
        print(f"[g360] FATAL: main object '{args['object']}' not found in the scene. "
              "Fix motor.config.json or the scene — refusing to measure a substitute.")
        sys.exit(2)
    # vert-count drift guard: the named object must still be the mesh we think it is
    cfg_path = os.path.join(os.path.dirname(bpy.data.filepath), "..", "motor.config.json")
    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
        expected = int(cfg.get("expected_verts", 0))
        tol = float(cfg.get("vert_tolerance", 0.10))
    except Exception:
        expected, tol = 0, 0.10
    if expected:
        actual = len(obj.data.vertices)
        if abs(actual - expected) > expected * tol:
            print(f"[g360] FATAL: '{obj.name}' has {actual} verts, expected {expected} "
                  f"(±{int(tol*100)}%). The scene changed under the gate — update "
                  "motor.config.json deliberately if this is intentional.")
            sys.exit(2)
    out_dir = os.path.abspath(args["out"])
    render_views(obj, out_dir, args["res"])
    if args["zone"]:
        render_zone(obj, out_dir, args["res"], args["zone"])
    else:
        # stale feature views from a previous --feature run must not be judged as fresh
        for tag in ("feature", "feature_b"):
            p = os.path.join(out_dir, f"v_{tag}.png")
            if os.path.exists(p):
                os.remove(p)
    orientation_audit(obj, os.path.join(out_dir, "orientation.json"))
    print("[g360] DONE")


if __name__ == "__main__":
    main()
