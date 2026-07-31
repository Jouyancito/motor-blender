# showcase_ficha.py -- the ficha / showcase RENDER rig for the biome packs.
#
# Lives in lookdev, not recetas: none of this is geometry. Nothing here ends up
# in an exported GLB (labels are removed and transforms reset before export), so
# the oracle for this module is the rendered PNG, not the GLB bytes.
#
# Light convention is genuinely divergent across the packs (D18) and both forms
# are kept as real functions rather than normalized:
#   area_light -- flower / bush / tree / river / rock (AREA)
#   sun_light  -- grass (SUN, directional, aimed purely by rotation)
import math
import bpy


# ------------------------------------------------------------------ lighting
def area_light(scene, name, loc, energy, size, color=(1, 1, 1), aim=None):
    """AREA light. aim=None orients via location.to_track_quat('Z','Y') (the
    flower/bush/tree/river convention); aim=(x,y,z) points at that target
    instead (the rock_pack convention)."""
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    o.rotation_mode = 'QUATERNION'
    if aim is None:
        o.rotation_quaternion = o.location.to_track_quat('Z', 'Y')
    else:
        from mathutils import Vector
        o.rotation_quaternion = (Vector(aim) - o.location).to_track_quat('-Z', 'Y')
    return o


def sun_light(scene, name, energy, color, rotation_euler):
    """SUN light: a directional source with no position, aimed by rotation only."""
    d = bpy.data.lights.new(name, "SUN")
    d.energy = energy
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.rotation_euler = rotation_euler
    return o


# -------------------------------------------------------------------- camera
def track_camera(scene, name, loc, target_loc, lens, target_name="target"):
    """TRACK_TO camera rig. Returns (cam, target)."""
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    target = bpy.data.objects.new(target_name, None)
    scene.collection.objects.link(target)
    cam.constraints.new(type='TRACK_TO').target = target

    target.location = target_loc
    cam.location = loc
    return cam, target


# -------------------------------------------------------------------- labels
def add_labels(scene, entries, size, y=-0.55, z=0.02, extrude=0.006, rot_x=90,
               align_x='CENTER', align_y='BOTTOM', color=(0.92, 0.92, 0.88),
               roughness=0.55, material=None,
               name_prefix="label", mat_prefix="mat_label"):
    """One extruded FONT object per entry. `entries` is a list of (key, text, x).

    align_y is a real parameter: most packs use 'BOTTOM' with z>0 so the text
    grows UPWARD (a flat opaque ground plane fully occludes anything below its
    own z=0 surface from an elevated camera -- caught on flower_pack). grass_pack
    has no ground plane and keeps its original 'TOP' at z<0.

    material=None creates one material per label named "<mat_prefix>_<key>";
    passing a material reuses a single shared one instead.
    """
    objs = []
    for key, text, x in entries:
        curve = bpy.data.curves.new(f"{name_prefix}_{key}", type='FONT')
        curve.body = text
        curve.size = size
        curve.align_x = align_x
        curve.align_y = align_y
        curve.extrude = extrude
        obj = bpy.data.objects.new(f"{name_prefix}_{key}", curve)
        obj.location = (x, y, z)
        obj.rotation_euler = (math.radians(rot_x), 0.0, 0.0)
        scene.collection.objects.link(obj)

        mat = material
        if mat is None:
            mat = bpy.data.materials.new(f"{mat_prefix}_{key}")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
            bsdf.inputs["Roughness"].default_value = roughness
        curve.materials.append(mat)
        objs.append(obj)
    return objs


def remove_labels(objs):
    """Delete ficha-only label objects and their curve datablocks before export."""
    for lbl in objs:
        data = lbl.data
        bpy.data.objects.remove(lbl, do_unlink=True)
        bpy.data.curves.remove(data)


# ------------------------------------------------------------------- renderer
def eevee_standard(scene, samples=64, raytracing=True, resolution=(1920, 1080)):
    """EEVEE Next + Standard view transform. Standard (not Filmic/AgX) because
    these packs pick their colors in linear space and want them back unmapped."""
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = raytracing
    scene.eevee.taa_render_samples = samples
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
