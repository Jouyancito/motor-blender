# biome_vcol.py -- FLOAT_COLOR vertex-color pipeline for the biome packs.
#
# This module is the ONLY sanctioned way to create a per-vertex color layer in
# this motor. BYTE_COLOR is structurally unreachable from here: `new_float_color_layer`
# is the single layer factory and it always calls `bm.loops.layers.float_color.new`.
#
# WHY that matters (2026-07-20, golem_guardian): a BYTE_COLOR corner attribute
# applies an implicit sRGB DECODE on read while bmesh's loop-color WRITE applies
# no matching encode, so hand-picked linear tones come back ~12x darker. The bug
# is invisible in code review and reads as "lighting" in a render.
#
# Colors are carried as a dict keyed by the BMVert OBJECT, never by BMVert.index:
# `.index` is stale immediately after `bm.verts.new()` and silently maps colors
# onto the wrong vertices (this rendered the whole flower_pack white once).
import bpy
import bmesh


# ---------------------------------------------------------------- scalar utils
def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else (hi if x > hi else x)


def clamp01(x):
    return clamp(x, 0.0, 1.0)


def lerp3(a, b, t):
    """Per-channel linear interpolation over the first 3 channels."""
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def jitter3(c, rng, amt):
    """ADDITIVE per-channel jitter, clamped to [0,1]. Consumes 3 rng draws (r,g,b).

    NOT the same recipe as `tint3` (multiplicative, scales each channel by
    uniform(1-amt, 1+amt)). Both exist on purpose and must keep distinct names --
    collapsing them under one name would silently give one pack the other's
    color math, the same trap that forced add_blade_strip/add_blade_card apart.
    """
    return tuple(clamp01(ch + rng.uniform(-amt, amt)) for ch in c)


# ------------------------------------------------------------- color layer I/O
def new_float_color_layer(bm, name="Col"):
    """The ONLY layer factory in this motor. Always FLOAT_COLOR, never BYTE_COLOR."""
    return bm.loops.layers.float_color.new(name)


def apply_vcol(bm, layer, vcol, default=(0.3, 0.3, 0.3)):
    """Write the BMVert-keyed color dict into every loop of every face.

    Alpha is appended here as a constant 1.0, so callers store plain RGB triples.
    """
    for f in bm.faces:
        for loop in f.loops:
            c = vcol.get(loop.vert, default)
            loop[layer] = (c[0], c[1], c[2], 1.0)


def count_tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ------------------------------------------------------------------- finalize
def finalize_vcol_mesh(name, bm, vcol, scene=None, collection=None,
                       mesh_name=None, weld_dist=0.0006, flat=True,
                       default_color=(0.3, 0.3, 0.3), validate=True,
                       normal_update=True, set_render_color_index=False):
    """Weld -> recalc normals -> paint loops -> to_mesh -> shade -> link.

    Parameters that are load-bearing for at least one shipped pack, so none of
    them may be normalized away:

    weld_dist   -- distance for bmesh.ops.remove_doubles. **None SKIPS the weld
                   entirely**; 0.0 is NOT equivalent (it still merges coincident
                   verts). flower_pack and grass_pack both depend on skipping it.
    flat        -- True sets polygon.use_smooth=False (the DP_ToonGrounded family
                   signature). grass_pack is the only pack that passes flat=False:
                   its blades are curved strips that must read as brush strokes.
    validate    -- me.validate() can DELETE degenerate/duplicate faces, so it is
                   a real behavioural switch, not a no-op safety net.
    mesh_name   -- glTF exports the MESH datablock name, which is not always the
                   object name (grass_pack uses "<obj>_mesh"). Defaults to `name`.
    """
    if weld_dist is not None:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld_dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if normal_update:
        bm.normal_update()

    layer = new_float_color_layer(bm)
    apply_vcol(bm, layer, vcol, default=default_color)

    me = bpy.data.meshes.new(mesh_name if mesh_name is not None else name)
    bm.to_mesh(me)
    bm.free()
    if validate:
        me.validate(verbose=False)
    for p in me.polygons:
        p.use_smooth = not flat

    obj = bpy.data.objects.new(name, me)
    target = collection
    if target is None:
        target = scene.collection if scene is not None else bpy.context.collection
    target.objects.link(obj)

    if set_render_color_index:
        idx = me.color_attributes.find("Col")
        if idx != -1:
            me.color_attributes.render_color_index = idx
    return obj


# ------------------------------------------------------------------- materials
def vcol_material(name, roughness=0.94, specular=0.05, double_sided=True,
                  attr="Col", subsurface=None, show_transparent_back=None):
    """Principled BSDF driven by an Attribute node -- no texture, no UVs.

    double_sided=None means "do not touch use_backface_culling" (river_pack and
    rock_pack never set it, and their exported material must stay untouched).
    subsurface=(weight, radius_tuple) is currently a grass_pack-only need.
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    n = nt.nodes["Principled BSDF"]

    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = attr
    nt.links.new(a.outputs["Color"], n.inputs["Base Color"])

    n.inputs["Roughness"].default_value = roughness

    if subsurface is not None:
        sw = n.inputs.get("Subsurface Weight")
        if sw is not None:
            sw.default_value = subsurface[0]
            n.inputs["Subsurface Radius"].default_value = subsurface[1]

    spec_in = n.inputs.get("Specular IOR Level")
    if spec_in is not None:
        spec_in.default_value = specular

    if double_sided is not None:
        m.use_backface_culling = not double_sided
    if show_transparent_back is not None and hasattr(m, "show_transparent_back"):
        m.show_transparent_back = show_transparent_back
    return m
