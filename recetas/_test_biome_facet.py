# _test_biome_facet.py -- proof that the plane-cut operator produces what noise cannot.
#
# Renders the five rock families the Path of Exile reference set is made of, at
# real metres, beside a 1.8 m player post, from a hero angle and from player eye
# height. The eye-height frame is the one that decides: a rock that only reads
# from a hero angle is the failure mode this whole exercise came from.
#
# Run: blender --background --factory-startup --python-exit-code 1 --python _test_biome_facet.py
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import biome_facet  # noqa: E402
import biome_vcol  # noqa: E402

REN_DIR = os.path.join(HERE, "renders_facet")
os.makedirs(REN_DIR, exist_ok=True)

SEED = 20260808

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Palettes. Deliberately NOT the pale cream the old pack shipped: the references
# sit in warm grey-brown and cool slate, with real darks available underneath.
# FLOAT_COLOR is LINEAR. The first pass specified sRGB-looking numbers
# (0.40, 0.36, 0.30) and rendered near-white, because 0.40 linear is about 0.66
# once displayed. These are linear values chosen so the DISPLAYED stone lands
# around sRGB 0.35-0.45 — mid grey, with real room to darken underneath.
STONE_WARM = (0.130, 0.115, 0.088)   # displays ~ (0.40, 0.38, 0.33)
STONE_COOL = (0.085, 0.095, 0.118)   # displays ~ (0.33, 0.35, 0.38)
STONE_DARK = (0.048, 0.050, 0.044)   # displays ~ (0.25, 0.26, 0.24)
MOSS = (0.022, 0.055, 0.014)         # displays ~ (0.17, 0.26, 0.13)

VARIANTS = [
    dict(key="stacked_mossy", label="Stacked / mossy",
         radius=0.45, blocks=5, cuts=22, bedding=2, stack=0.80, taper=0.45,
         color_rock=STONE_WARM, color_moss=MOSS, moss_min_z=0.72, moss_chance=0.7,
         crevice_dark=0.78),
    dict(key="column", label="Column",
         radius=0.34, blocks=2, cuts=20, bedding=4, flatten=2.2, stack=0.90,
         color_rock=STONE_COOL, color_moss=MOSS, moss_min_z=0.80, moss_chance=0.30,
         crevice_dark=0.72),
    dict(key="wedge_slab", label="Wedge slab",
         radius=0.70, blocks=2, cuts=18, bedding=1, flatten=0.40, elongate=1.6,
         stack=0.10,
         color_rock=STONE_COOL, color_moss=None, crevice_dark=0.62),
    dict(key="strata_outcrop", label="Strata outcrop",
         radius=0.55, blocks=3, cuts=16, bedding=6, bedding_jitter=0.05, flatten=0.90,
         stack=0.45, taper=0.30,
         color_rock=STONE_WARM, color_moss=MOSS, moss_min_z=0.76, moss_chance=0.55,
         crevice_dark=0.80),
    dict(key="boulder", label="Boulder",
         radius=0.60, blocks=1, cuts=26,
         color_rock=STONE_DARK, color_moss=MOSS, moss_min_z=0.78, moss_chance=0.45,
         crevice_dark=0.70),
]

SPACING = 2.2
objs = []
for i, spec in enumerate(VARIANTS):
    rng = random.Random(SEED + i * 17)
    bm = bmesh.new()
    vcol = {}
    faces = biome_facet.add_faceted_rock(bm, vcol, Vector((0.0, 0.0, 0.0)), spec, rng)
    biome_facet.flat_shade(faces)
    obj = biome_vcol.finalize_vcol_mesh(
        f"rock_{spec['key']}", bm, vcol,
        scene=scene,
        mesh_name=f"rock_{spec['key']}_mesh",
        flat=True,
    )
    obj.location = (i * SPACING, 0.0, 0.0)
    objs.append(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"[facet] {spec['key']:16s} verts={len(obj.data.vertices):4d} tris={tris:4d} "
          f"height={obj.dimensions.z:.2f}m width={obj.dimensions.x:.2f}m")

mat = biome_vcol.vcol_material("mat_rock_facet", roughness=0.85, specular=0.15)
for obj in objs:
    obj.data.materials.append(mat)

# ---- ground, post, light -------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
ground = bpy.context.active_object
mat_ground = bpy.data.materials.new("mat_ground")
mat_ground.use_nodes = True
mat_ground.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.13, 0.15, 0.10, 1.0)
ground.data.materials.append(mat_ground)

# 1.8 m player reference post -- mandatory, and the reason this test exists.
bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=1.8,
                                    location=(len(VARIANTS) * SPACING - 0.6, 0.6, 0.9))
post = bpy.context.active_object
mat_post = bpy.data.materials.new("mat_post")
mat_post.use_nodes = True
mat_post.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.92, 0.20, 0.16, 1.0)
post.data.materials.append(mat_post)


def sun(name, energy, color, rot):
    data = bpy.data.lights.new(name, type='SUN')
    data.energy = energy
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.rotation_euler = rot
    scene.collection.objects.link(obj)
    return obj


# Energy cut from 3.4/1.0. With view_transform='Standard' there is no filmic
# curve pulling highlights back, so the previous key blew every up-facing plane
# to white and the moss to emerald. Standard is still the right transform here —
# it is what the glTF viewer and Godot do — so the LIGHT has to be honest instead.
sun("key", 2.1, (1.0, 0.92, 0.78), (math.radians(52), 0, math.radians(38)))
sun("fill", 0.55, (0.55, 0.66, 0.88), (math.radians(64), 0, math.radians(-128)))

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.11, 0.13, 1.0)

# Blender 5.x renamed the next-gen EEVEE back to plain BLENDER_EEVEE. Pick
# whichever name this build actually offers instead of hardcoding one.
engines = scene.render.bl_rna.properties["engine"].enum_items.keys()
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 64
scene.view_settings.view_transform = 'Standard'


def render_to(path, loc, target, lens=40, res=(1800, 900)):
    tgt = bpy.data.objects.new("t_" + path, None)
    tgt.location = target
    scene.collection.objects.link(tgt)
    cam_data = bpy.data.cameras.new("c_" + path)
    cam_data.lens = lens
    cam = bpy.data.objects.new("c_" + path, cam_data)
    cam.location = loc
    scene.collection.objects.link(cam)
    cam.constraints.new(type='TRACK_TO').target = tgt
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = os.path.join(REN_DIR, path)
    bpy.ops.render.render(write_still=True)
    print(f"[facet] RENDERED -> renders_facet/{path}")


mid_x = (len(VARIANTS) - 1) * SPACING * 0.5
render_to("facet_hero.png", (mid_x, -7.5, 3.0), (mid_x, 0.0, 0.5))
render_to("facet_playereye.png", (mid_x - 1.2, -6.4, 1.65), (mid_x, 0.3, 0.45), lens=35)
render_to("facet_closeup.png", (0.7, -2.4, 1.05), (0.0, 0.0, 0.42), lens=55, res=(1400, 1000))
print("[facet] DONE")
