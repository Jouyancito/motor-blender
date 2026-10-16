# scale_ref.py -- THE 1.80 m mannequin, once.
#
# WHY THIS EXISTS
#
# Joan's proportion rule (2026-07-18): every generated asset or scene is judged
# beside a visible 1.80 m human reference, not trusted from numbers. The helper
# lived as two copy-pastes -- village_gen.build_scale_ref and the clown_gen
# mannequin block -- the exact duplication CREATION_PROTOCOL anti-patterns warn
# about (build_goat vs build_sheep), and a rule that depends on someone copying
# the helper into the next generator already failed: nothing forced build_gato
# to have one.
#
# So: one definition here, and require_scale_evidence() in the use_size.py
# style -- the build FAILS when the mannequin is not in the scene or its
# renders were not produced. recetas/motor_run.py calls it for every generator.
#
# USAGE
#     from recetas import scale_ref
#     scale_ref.build_mannequin(location=(2.5, 0, 0))
#     ...render...
#     scale_ref.require_scale_evidence(render_paths, asset_objects=[body])
#
# `bpy` is imported inside the functions that need it so the pure part
# (scale_evidence_report) is fixture-testable without Blender.
import os

from recetas.verdict import Report, PASS, FAIL, NOT_TESTED

MANNEQUIN_H = 1.80          # metres: the player character
NAME_PREFIX = "ref_human"   # object names: ref_human_body*, ref_human_head*
BODY_R, BODY_H, BODY_VERTS = 0.20, 1.50, 8
HEAD_R, HEAD_Z = 0.15, 1.65
HEAD_SEG, HEAD_RINGS = 10, 8
COLOR = (0.80, 0.20, 0.18)  # red: reads against every biome palette

# The geometry must add up to the declared height. A drifting constant here
# would silently re-define "1.80 m" for every generator (lesson 8).
assert abs((HEAD_Z + HEAD_R) - MANNEQUIN_H) < 1e-9, "mannequin geometry != MANNEQUIN_H"


def default_material():
    import bpy
    m = bpy.data.materials.get("scale_ref")
    if m is None:
        m = bpy.data.materials.new("scale_ref")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*COLOR, 1.0)
        b.inputs["Roughness"].default_value = 0.5
    return m


def build_mannequin(location=(0.0, 0.0, 0.0), suffix="", material=None,
                    smooth=False):
    """
    Add the 1.80 m mannequin standing with its soles at `location` (x, y, z).

    `suffix` is appended to the object names (village_gen places several);
    `material` lets a generator pass its own cached material; `smooth` applies
    smooth shading (clown_gen's look). Returns [body, head].
    """
    import bpy

    x, y, z = location
    material = material or default_material()

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=BODY_VERTS, radius=BODY_R, depth=BODY_H,
        location=(x, y, z + BODY_H / 2.0))
    body = bpy.context.object
    body.name = "%s_body%s" % (NAME_PREFIX, suffix)
    body.data.materials.append(material)
    if smooth:
        bpy.ops.object.shade_smooth()

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=HEAD_SEG, ring_count=HEAD_RINGS, radius=HEAD_R,
        location=(x, y, z + HEAD_Z))
    head = bpy.context.object
    head.name = "%s_head%s" % (NAME_PREFIX, suffix)
    head.data.materials.append(material)
    if smooth:
        bpy.ops.object.shade_smooth()
    try:
        from recetas.motor_stamp import stamp_object, SCALE_REF_PART
    except ImportError:
        from motor_stamp import stamp_object, SCALE_REF_PART
    for _o in (body, head):
        stamp_object(_o, SCALE_REF_PART, "scale_ref")
    return [body, head]


def find_mannequin(scene=None):
    """Mannequin parts already in the scene (any generator's, by name prefix)."""
    import bpy
    scene = scene or bpy.context.scene
    return [o for o in scene.objects
            if o.type == 'MESH' and o.name.startswith(NAME_PREFIX)]


def world_z_extent(objs):
    """(min_z, max_z) of the objects' world-space bounding boxes."""
    from mathutils import Vector
    zs = []
    for o in objs:
        zs.extend((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    return (min(zs), max(zs)) if zs else (0.0, 0.0)


def scale_evidence_report(mannequin_height, render_paths, asset_height=None,
                          expected_height_m=None, tol=0.02, exists=os.path.isfile,
                          size_of=os.path.getsize, asset_span=None,
                          expected_span_m=None, weak_source=False):
    """
    Pure core of the gate (no bpy): one row per property.

    mannequin_height   measured height of the mannequin in the scene, or None
    render_paths       renders that are supposed to show asset + mannequin
    asset_height       measured asset height, if known
    expected_height_m  (lo, hi) sourced range for the asset, or None
    """
    r = Report("SCALE EVIDENCE")
    if mannequin_height is None:
        r.add("mannequin_in_scene", FAIL,
              "no object named %s_* in the scene" % NAME_PREFIX)
    elif abs(mannequin_height - MANNEQUIN_H) > tol:
        r.add("mannequin_in_scene", FAIL,
              "mannequin is %.3f m, must be %.2f m +-%.2f (it was rescaled)"
              % (mannequin_height, MANNEQUIN_H, tol))
    else:
        r.add("mannequin_in_scene", PASS, "%.3f m" % mannequin_height)

    if not render_paths:
        r.add("renders_written", NOT_TESTED, "no render paths were given")
    else:
        missing = [p for p in render_paths
                   if not (exists(p) and size_of(p) > 0)]
        if missing:
            r.add("renders_written", FAIL, "%d/%d missing or empty: %s"
                  % (len(missing), len(render_paths),
                     ", ".join(os.path.basename(m) for m in missing[:3])))
        else:
            r.add("renders_written", PASS, "%d files" % len(render_paths))

    if expected_height_m is None:
        r.add("asset_height_vs_source", NOT_TESTED,
              "no sourced size range for this family")
    elif asset_height is None:
        r.add("asset_height_vs_source", NOT_TESTED, "asset height not measured")
    else:
        lo, hi = expected_height_m
        inside = lo <= asset_height <= hi
        # A WEAK source (size mentioned in passing, not a spec) can only warn.
        state = PASS if inside else (NOT_TESTED if weak_source else FAIL)
        r.add("asset_height_vs_source", state,
              ("WARN (weak source) " if weak_source and not inside else "")
              + "%.3f m vs sourced %.2f-%.2f m (%.0f %% of the mannequin)"
              % (asset_height, lo, hi, 100.0 * asset_height / MANNEQUIN_H))
    if expected_span_m is not None:
        # Wingspan / nose-to-tail length: the sourced size of flyers and
        # animals is a HORIZONTAL extent, not a height.
        if asset_span is None:
            r.add("asset_span_vs_source", NOT_TESTED, "asset span not measured")
        else:
            lo, hi = expected_span_m
            inside = lo <= asset_span <= hi
            r.add("asset_span_vs_source",
                  PASS if inside else (NOT_TESTED if weak_source else FAIL),
                  ("WARN (weak source) " if weak_source and not inside else "")
                  + "%.3f m vs sourced %.2f-%.2f m" % (asset_span, lo, hi))
    return r


def world_xy_span(objs):
    """Widest horizontal extent (max of the X and Y world extents)."""
    from mathutils import Vector
    xs, ys = [], []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x)
            ys.append(w.y)
    return max(max(xs) - min(xs), max(ys) - min(ys)) if xs else 0.0


def require_scale_evidence(render_paths, scene=None, asset_objects=None,
                           expected_height_m=None, verbose=True,
                           expected_span_m=None, weak_source=False):
    """
    Fail the build unless the mannequin is in the scene at 1.80 m AND the
    renders that show it exist. Same contract as use_size.require_use_size:
    called last, so an asset cannot finish without seeing itself at human scale.

    `asset_height_vs_source` stays NOT_TESTED (and the gate does not fail on it)
    unless `expected_height_m` -- a SOURCED (lo, hi) range -- is passed.
    """
    parts = find_mannequin(scene)
    mh = None
    if parts:
        lo, hi = world_z_extent(parts)
        mh = hi - lo
    ah = None
    if asset_objects:
        lo, hi = world_z_extent(asset_objects)
        ah = hi - lo
    aspan = world_xy_span(asset_objects) if asset_objects else None
    rep = scale_evidence_report(mh, list(render_paths or []), ah,
                                expected_height_m, asset_span=aspan,
                                expected_span_m=expected_span_m,
                                weak_source=weak_source)
    if verbose:
        print(rep.render())
    hard = [row for row in rep.rows
            if row["state"] == FAIL or
            (row["state"] == NOT_TESTED and row["prop"] not in
             ("asset_height_vs_source", "asset_span_vs_source"))]
    if hard:
        raise SystemExit(
            rep.render() + "\nSIN EVIDENCIA DE ESCALA. El asset se juzga al lado "
            "del maniqui de 1.80 m (recetas/scale_ref.py), no de memoria.\n")
    return rep
