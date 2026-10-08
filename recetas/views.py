# views.py -- the judgement view set and an orbit capture that writes it to disk.
#
# WHY THIS EXISTS
#
# "Orbit the asset before reporting" (memory: orbitar siempre antes de reportar,
# Joan 2026-08-19 -- "es 2da vez hoy y demasiadas veces durante estas semanas")
# lived in the game repo as preview_zone.py / _canonical_views.py. A tool that
# exists but is not called is the failure the rule was written about, and the
# motor could not call it: it lives in another repo and is tied to the warrior's
# vertex groups. This is the asset-level port: same angles, same reasons, the
# same guard that fails when an ungrateful angle goes missing -- plus the
# verification that every shot exists on disk (a run that printed six labels and
# wrote zero files happened before, on a relative render.filepath).
#
# Source of the view set: DungeonParty-A game/tools/blender/_canonical_views.py
# (VIEWS, _REQUIRED, _REQUIRED_ANY) and preview_zone.py (shot verification).
#
# USAGE
#     from recetas import views
#     paths = views.orbit_capture("_out/gato/evidence", "gato", objects)
#
# `bpy` is imported inside the functions that need it.
import math
import os

# label, azimuth (0 = front, +90 = the model's left), elevation, framing mult.
VIEWS = [
    ("cenital", 0, 89, 1.00),       # layout errors: symmetry, leg directions
    ("tresq_alto", 40, 45, 1.00),   # the flattering view -- and the baseline
    ("perfil", 90, 8, 1.00),        # where anything protruding shows
    ("frente", 0, 12, 1.00),        # face and stance
    ("atras", 180, 25, 1.00),       # where glued-on geometry separates
    ("macro_placa", 35, 55, 0.34),  # one surface region, close: does detail read?
    ("bajo", 25, -55, 1.00),        # THE UNGRATEFUL ANGLE: undersides, gaps,
                                    # floating parts. Dropped once; a blank
                                    # underside shipped.
]

# Angles a custom set may NOT lose.
_REQUIRED = ("perfil", "bajo")
_REQUIRED_ANY = (("cenital", "alto"),      # at least one top-ish view
                 ("tresq", "tresq_alto"))  # at least one three-quarter


def require_views(views):
    """SystemExit if a judgement set lost an ungrateful angle."""
    labels = {v[0] for v in views}
    missing = [r for r in _REQUIRED if r not in labels]
    for group in _REQUIRED_ANY:
        if not any(any(lbl == g or lbl.startswith(g) for lbl in labels)
                   for g in group):
            missing.append(" o ".join(group))
    if missing:
        raise SystemExit(
            "views: judgement set is missing ungrateful angle(s): %s. A set that "
            "cannot see them approves what they would show." % ", ".join(missing))


def resolve_views(labels):
    """Map required view labels (from a router entry) to VIEWS tuples; an
    unknown label is an error, not a skipped view."""
    by_label = {v[0]: v for v in VIEWS}
    unknown = [l for l in labels if l not in by_label]
    if unknown:
        raise SystemExit("views: unknown view label(s) %s; known: %s"
                         % (unknown, sorted(by_label)))
    chosen = [by_label[l] for l in labels]
    require_views(chosen)
    return chosen


require_views(VIEWS)


def _bounds(objects):
    """(centre, radius) of the bounding sphere of the objects' world boxes."""
    from mathutils import Vector
    pts = []
    for o in objects:
        pts.extend(o.matrix_world @ Vector(c) for c in o.bound_box)
    if not pts:
        raise SystemExit("views: nothing to frame")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre = (lo + hi) / 2.0
    radius = max((hi - lo).length / 2.0, 0.05)
    return centre, radius


def _ensure_light(scene):
    import bpy
    if any(o.type == 'LIGHT' for o in scene.objects):
        return []
    made = []
    for name, kind, energy, rot in (("orbit_sun", 'SUN', 3.0, (50, 0, -30)),
                                    ("orbit_fill", 'SUN', 1.2, (60, 0, 150))):
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = tuple(math.radians(a) for a in rot)
        scene.collection.objects.link(lo)
        made.append(lo)
    return made


def clear_stale(out_dir, prefix):
    """Delete `<prefix>_*.png` left by an earlier run: a view that fails to
    render this time must not be 'satisfied' by last run's file. Returns the
    number removed."""
    n = 0
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            if name.startswith(prefix + "_") and name.endswith(".png"):
                os.remove(os.path.join(out_dir, name))
                n += 1
    return n


def orbit_capture(out_dir, prefix, objects, views=None, res=640):
    """
    Render `objects` from every view in `views` (default: all of VIEWS), framed
    on their bounding sphere, and verify each file exists. Returns the paths.

    Include the mannequin in `objects` to get it in frame. The scene's camera,
    resolution and filepath are restored afterwards; lights are added only when
    the scene has none (and removed again).
    """
    import bpy
    from mathutils import Vector

    views = views or VIEWS
    require_views(views)
    scene = bpy.context.scene
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    clear_stale(out_dir, prefix)

    centre, radius = _bounds(objects)
    saved = (scene.camera, scene.render.resolution_x, scene.render.resolution_y,
             scene.render.resolution_percentage, scene.render.filepath)
    lights = _ensure_light(scene)
    cd = bpy.data.cameras.new("orbit_cam")
    cd.lens = 50
    cam = bpy.data.objects.new("orbit_cam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    half_fov = math.atan(cd.sensor_width / 2.0 / cd.lens)

    written = []
    try:
        for label, az, el, mult in views:
            a, e = math.radians(az), math.radians(el)
            d = radius * mult / math.sin(half_fov) * 1.1
            cam.location = (centre.x + d * math.sin(a) * math.cos(e),
                            centre.y - d * math.cos(a) * math.cos(e),
                            centre.z + d * math.sin(e))
            cam.rotation_euler = ((centre - cam.location).to_track_quat('-Z', 'Y')
                                  .to_euler())
            path = os.path.join(out_dir, "%s_%s.png" % (prefix, label))
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                raise SystemExit("view %r was not written to %s" % (label, path))
            written.append(path)
            print("  [views] %-12s az %+4d el %+3d -> %s"
                  % (label, az, el, os.path.basename(path)))
    finally:
        scene.camera, scene.render.resolution_x, scene.render.resolution_y, \
            scene.render.resolution_percentage, scene.render.filepath = saved
        for o in [cam] + lights:
            data, kind = o.data, o.type
            bpy.data.objects.remove(o)
            (bpy.data.cameras if kind == 'CAMERA' else bpy.data.lights).remove(data)
    if len(written) != len(views):
        raise SystemExit("incomplete orbit -- do not judge from a partial set")
    return written
