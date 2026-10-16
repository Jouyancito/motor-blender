# RECETA: mpfb_human_base -- a rigged human from MPFB 2.0.18, headless, on Blender 5.1.2.
# QUE: mpfb_human_base(macros, race, ...) builds the MPFB basemesh with its helper cubes,
#      collapses the macro shape keys so the vertices ARE the shape, names and stamps it.
#      add_human_rig(body) fits MPFB's default rig AFTER any reproportion (the rig is
#      fitted to the joint-* cube groups, so proportions must change first).
#      strip_helpers / region_ids / group_idx: keep only the skin, label body regions by
#      bone-prefix whitelist, pick vertices by group.
# CUANDO: every human or humanoid. Replaces a Skin-modifier skeleton, which gives only
#      tubes ("tubos, muneca poligonal", Joan on rem v7); MPFB anatomy was accepted
#      ("ahora si parece anatomia de un humano").
# GOTCHAS (each cost a session):
#   1. INSTALL via install-file, not by hand and not from the online repo:
#        blender --command extension install-file -r user_default --enable <mpfb.zip>
#      Then `bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")` in every
#      --factory-startup run (ensure_mpfb() does it and fails loudly with this command).
#   2. detailed_helpers=True is NOT optional: the rig is fitted to the joint-* cubes;
#      without them the armature is built from EMPTY groups and comes out SCRAMBLED
#      WITHOUT ANY ERROR. This recipe hard-codes True and has no parameter to turn it off.
#   3. Delete the factory cube (--factory-startup ships Camera, Light and a 2 m Cube): it
#      rendered as a floor slab and was an unstamped visible mesh. clean_factory_scene()
#      removes ONLY the untouched factory objects, never anything else.
#   4. Collapse the macro targets (shape_key_remove(all=True, apply_mix=True)) or the
#      reproportion edits the basis and the mix fights it.
#   5. MPFB also keeps side/macro vertex groups (Left, Right, body, ...) that weigh 1.0 on
#      most vertices: region labelling uses a BONE-PREFIX whitelist (BONE_PREFIX) or every
#      vertex lands on "Left".
#   6. A realistic MPFB head dilated to anime proportions reads as a BOBBLEHEAD on a stock
#      neck: plan for the head to be REPLACEABLE (cut at mid-neck, swap, remesh only the
#      closed solids -- a non-watertight base voxel-remeshed gives lace). See
#      reproportion_humanoid.
# FUENTE: rem/v8/rem_v8_body_gen.py:80-110 make_human, :172 strip_helpers, :428-470
#      region_ids/BONE_PREFIX, :400-414 clean_scene; probe: rem/body/probe_mpfb.py.
# EXEMPLAR:
#   clean_factory_scene()
#   body = mpfb_human_base(dict(gender=0.0, age=0.33), dict(asian=0.7, caucasian=0.3), part="body")
#   J = reproportion_humanoid(body, k_leg=1.26)          # BEFORE the rig
#   rig = add_human_rig(body, part="body")
import numpy as np

import bpy
import bmesh

try:
    from recetas.motor_stamp import stamp_object as _motor_stamp
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from motor_stamp import stamp_object as _motor_stamp

TECHNIQUE = "mpfb_human_base"
MPFB_MODULE = "bl_ext.user_default.mpfb"
INSTALL_HINT = ("blender --command extension install-file -r user_default --enable <path>/mpfb.zip "
                "(MPFB 2.0.18; rem keeps the zip in rem/body/_dl/mpfb.zip)")

REG = dict(skin=0, torso=1, arm_up=2, arm_fore=3, hand=4, thigh=5, shin=6, foot=7, neck=8, head=9)
BONE_PREFIX = ("spine", "root", "pelvis", "breast", "clavicle", "upperarm", "shoulder", "lowerarm",
               "wrist", "finger", "metacarpal", "upperleg", "lowerleg", "foot", "toe", "neck",
               "head", "jaw", "eye", "ear", "tongue", "teeth")


def ensure_mpfb():
    """Enable MPFB for this session or SystemExit with the install-file command."""
    try:
        bpy.ops.preferences.addon_enable(module=MPFB_MODULE)
    except Exception as e:  # noqa: BLE001 -- any failure here means "not installed/usable"
        raise SystemExit("MPFB is not available (%s: %s). Install it with:\n  %s"
                         % (type(e).__name__, e, INSTALL_HINT))
    if MPFB_MODULE not in bpy.context.preferences.addons:
        raise SystemExit("MPFB did not enable. Install it with:\n  %s" % INSTALL_HINT)


def clean_factory_scene():
    """Remove the untouched --factory-startup objects (Cube 2 m, Camera, Light) and nothing
    else. Returns the names removed."""
    gone = []
    for o in list(bpy.data.objects):
        factory_cube = (o.type == "MESH" and o.name == "Cube" and len(o.data.vertices) == 8
                        and all(abs(d - 2.0) < 1e-6 for d in o.dimensions))
        if factory_cube or (o.type == "CAMERA" and o.name == "Camera") or (o.type == "LIGHT" and o.name == "Light"):
            gone.append(o.name)
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data is not None and data.users == 0:
                (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else
                 bpy.data.cameras if isinstance(data, bpy.types.Camera) else bpy.data.lights).remove(data)
    return gone


def mpfb_human_base(macros, race, name="human_body", part=None, scale=0.1):
    """Create the MPFB human (helpers kept, rig NOT yet), collapse macro keys, name, stamp.
    `macros`: dict merged over MPFB's default macro dict (gender, age, muscle, weight,
    proportions, height, cupsize, firmness). `race`: dict asian/caucasian/african."""
    ensure_mpfb()
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    macro = TargetService.get_default_macro_info_dict()
    macro.update(macros)
    macro["race"] = dict(race)
    # detailed_helpers=True is hard-coded on purpose (gotcha 2): no way to turn it off.
    body = HumanService.create_human(mask_helpers=False, detailed_helpers=True,
                                     extra_vertex_groups=True, feet_on_ground=True,
                                     scale=scale, macro_detail_dict=macro)
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    if body.data.shape_keys:   # collapse the macro targets so the vertices ARE the shape
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    body.name = body.data.name = name
    _motor_stamp(body, part, TECHNIQUE)
    return body


def add_human_rig(body, name="human_rig", part=None):
    """Fit MPFB's default rig. Call AFTER reproportion_humanoid, never before."""
    ensure_mpfb()
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    rig = HumanService.add_builtin_rig(body, "default", import_weights=True)
    rig.name = rig.data.name = name
    _motor_stamp(rig, part, TECHNIQUE)
    return rig


def strip_helpers(body):
    """Keep only the skin: every helper/joint cube (and the helper eyeballs) goes."""
    vg = body.vertex_groups["body"]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    dl = bm.verts.layers.deform.verify()
    kill = [v for v in bm.verts if vg.index not in v[dl]]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    for g in [g for g in body.vertex_groups if g.name.startswith(("helper-", "joint-"))]:
        body.vertex_groups.remove(g)
    return len(body.data.vertices)


def group_idx(body, names, thr=0.5, prefixes=()):
    """Indices of vertices whose group `names`/`prefixes` weighs more than `thr`."""
    gi = {vg.index: vg.name for vg in body.vertex_groups}
    out = []
    for v in body.data.vertices:
        for g in v.groups:
            nm = gi[g.group]
            if g.weight > thr and (nm in names or nm.startswith(prefixes)):
                out.append(v.index)
                break
    return np.array(out, dtype=int)


def region_ids(body):
    """Dominant BONE group per vertex -> region id (REG). Run before any geometry is
    touched so it keeps the basemesh vertex order. Non-bone groups are ignored
    (gotcha 5)."""
    gi = {vg.index: vg.name for vg in body.vertex_groups}
    out = np.zeros(len(body.data.vertices))
    for v in body.data.vertices:
        best, wb = None, 0.0
        for g in v.groups:
            nm = gi[g.group]
            if not nm.startswith(BONE_PREFIX):
                continue
            if g.weight > wb:
                best, wb = nm, g.weight
        k = "skin"
        if best:
            if best.startswith(("spine", "root", "pelvis", "breast", "clavicle")):
                k = "torso"
            elif best.startswith(("upperarm", "shoulder")):
                k = "arm_up"
            elif best.startswith("lowerarm"):
                k = "arm_fore"
            elif best.startswith(("wrist", "finger", "metacarpal")):
                k = "hand"
            elif best.startswith("upperleg"):
                k = "thigh"
            elif best.startswith("lowerleg"):
                k = "shin"
            elif best.startswith(("foot", "toe")):
                k = "foot"
            elif best.startswith("neck"):
                k = "neck"
            elif best.startswith(("head", "jaw", "eye", "ear", "tongue", "teeth")):
                k = "head"
        out[v.index] = REG[k]
    return out
