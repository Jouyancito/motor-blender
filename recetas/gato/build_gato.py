# build_gato.py — Gray cat (gata gris), motor tier M3.
# A basic gray cat build using the motor's established patterns:
# - FLOAT_COLOR vertex layer (never BYTE_COLOR, confirmed bug: ~12x darker)
# - Shape keys for expressive feline facial features
# - Idle animation with subtle movements
# - Runs headless: blender -b --python build_gato.py
#
# Run:
#   blender -b --python build_gato.py
#   blender -b --python build_gato.py -- --name Nami --color gris
#   blender -b --python build_gato.py -- --name Nami --color plateado
#
# Paletas disponibles: gris, plateado, blanco, negro

import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Matrix, noise as mnoise

from recetas import preflight_router
from recetas.verdict import Report, PASS, FAIL, NOT_TESTED, NOT_APPLICABLE

# 0b: Require the established cat technique — FLOAT_COLOR + shape keys.
_ = preflight_router.require_technique("gato", "floating_color_with_shape_keys")

# 0b: Cat structure — must have FLOAT_COLOR vertex layer.
_ = preflight_router.require_structure("gato", "float_color_layer")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
REN_DIR = os.path.join(OUT_DIR, "renders")
ANIM_DIR = os.path.join(REN_DIR, "anim")
os.makedirs(ANIM_DIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
FPS = 24
scene.render.fps = FPS

# ---------- CLI ----------
_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = "Nami"
COLOR = "gris"
for _i, _a in enumerate(_argv):
    if _a == "--name" and _i + 1 < len(_argv):
        NAME = _argv[_i + 1]
    elif _a == "--color" and _i + 1 < len(_argv):
        COLOR = _argv[_i + 1]

# Paletas de color para el gato gris
PALETTES = {
    "gris": {
        "deep": (0.080, 0.070, 0.060),
        "bright": (0.150, 0.130, 0.110),
        "bubble": (0.450, 0.430, 0.400),
    },
    "plateado": {
        "deep": (0.020, 0.025, 0.030),
        "bright": (0.100, 0.110, 0.120),
        "bubble": (0.300, 0.320, 0.350),
    },
    "blanco": {
        "deep": (0.200, 0.180, 0.160),
        "bright": (0.350, 0.320, 0.290),
        "bubble": (0.850, 0.830, 0.780),
    },
    "negro": {
        "deep": (0.002, 0.001, 0.001),
        "bright": (0.010, 0.005, 0.005),
        "bubble": (0.150, 0.120, 0.100),
    },
}
palette = PALETTES.get(COLOR, PALETTES["gris"])

def bake_vcol(palette_name):
    """Write the FLOAT_COLOR layer for a habitat palette."""
    p = PALETTES[palette_name]
    bm = bmesh.new()
    bm.from_mesh(me)
    layer = bm.loops.layers.float_color.get("Col") or bm.loops.layers.float_color.new("Col")
    for face in bm.faces:
        for loop in face.loops:
            zn = (loop.vert.co.z + 0.5) / 1.0  # normalize from -0.5 to 0.5 range
            col = (p["deep"][0] + (p["bright"][0] - p["deep"][0]) * zn ** 1.25,
                   p["deep"][1] + (p["bright"][1] - p["deep"][1]) * zn ** 1.25,
                   p["deep"][2] + (p["bright"][2] - p["deep"][2]) * zn ** 1.25)
            loop[layer] = (col[0], col[1], col[2], 1.0)
    bm.to_mesh(me)
    bm.free()

def lerp3(a, b, t):
    t = max(0.0, min(1.0, t))
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)

bake_vcol(COLOR)

# ---------- body: basic feline form ----------
# Cat body shape: characteristic feline proportions
SEGMENTS = 48
RINGS = 30
bpy.ops.mesh.primitive_uv_sphere_add(segments=SEGMENTS, ring_count=RINGS, radius=0.5)
body = bpy.context.object
body.name = NAME
me = body.data

# Flatten the sphere to make it more cat-like — wider, shorter, more feline
for v in me.vertices:
    scale = 1.3
    v.co.x *= scale
    v.co.y *= scale
    # Make it shorter in Z
    v.co.z *= 0.7

# Head: the top vertices already form a reasonable head shape
# Just refine it slightly
for v in me.vertices:
    if v.co.z > 0.1:  # upper half - head area
        # Soften the head shape
        len_xy = math.hypot(v.co.x, v.co.y)
        if len_xy > 0.01:
            # Make forehead slightly higher, jaw more defined
            v.co.z += 0.05 * (1.0 - abs(v.co.y))

# Tail: simple curve
# We'll add a simple curve object for the tail
import bpy.types as types

# Actually, let's just note the tail will be implied in animations

# ---------- vertex colour: FLOAT_COLOR (never BYTE_COLOR) ----------
# This is critical — BYTE_COLOR makes colors ~12x darker (confirmed project bug)
bake_vcol(COLOR)

# ---------- shape keys: cat facial expressions ----------
def add_key(name):
    k = body.shape_key_add(name=name, from_mix=False)
    k.value = 0.0
    return k

# Basis key
add_key("Basis")

# Shape keys for cat expressions
# Whisker pads
sk = add_key("whisker_pad_L")
for i, v in enumerate(me.vertices):
    if v.co.x < -0.1:  # left side
        v.co.x -= 0.04

sk = add_key("whisker_pad_R")
for i, v in enumerate(me.vertices):
    if v.co.x > 0.1:  # right side
        v.co.x += 0.04

# Ear tilts
sk = add_key("ear_tilt_L")
for i, v in enumerate(me.vertices):
    # Upper left area - ear
    if v.co.z > 0.2 and v.co.x < -0.1:
        v.co.z += 0.06

sk = add_key("ear_tilt_R")
for i, v in enumerate(me.vertices):
    # Upper right area - ear
    if v.co.z > 0.2 and v.co.x > 0.1:
        v.co.z += 0.06

# Mouth expressions
sk = add_key("mouth_open")
for i, v in enumerate(me.vertices):
    # Lower jaw area
    if v.co.z < -0.35:
        v.co.z += 0.03

# Eye expressions
sk = add_key("eye_wide_L")
for i, v in enumerate(me.vertices):
    # Approximate eye area (left)
    if v.co.z > 0.1 and v.co.x < -0.08 and v.co.y > -0.25 and v.co.y < 0.25:
        v.co.z += 0.04

sk = add_key("eye_wide_R")
for i, v in enumerate(me.vertices):
    # Approximate eye area (right)
    if v.co.z > 0.1 and v.co.x > 0.08 and v.co.y > -0.25 and v.co.y < 0.25:
        v.co.z += 0.04

# Animate the shape keys
kb = me.shape_keys.key_blocks
FPS = 24
scene.render.fps = FPS

# Idle animation: subtle facial movements
def anim_idle(t):
    return {
        "whisker_pad_L": 0.08 * math.sin(2 * math.pi * t * 0.5),
        "whisker_pad_R": 0.08 * math.sin(2 * math.pi * t * 0.5 + math.pi),
        "ear_tilt_L": 0.04 * math.sin(2 * math.pi * t * 0.3),
        "ear_tilt_R": 0.04 * math.sin(2 * math.pi * t * 0.3 + math.pi),
        "mouth_open": 0.015 * math.sin(2 * math.pi * t * 1.0),
        "eye_wide_L": 0.02 * math.sin(2 * math.pi * t * 1.5),
        "eye_wide_R": 0.02 * math.sin(2 * math.pi * t * 1.5 + math.pi),
    }

# ---------- materials ----------
def mat_gel(alpha=0.8, color_palette="gris"):
    m = bpy.data.materials.new("gata_gel")
    m.use_nodes = True
    nt = m.node_tree
    n = nt.nodes["Principled BSDF"]
    n.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    n.inputs["Roughness"].default_value = 0.4
    n.inputs["IOR"].default_value = 1.33
    n.inputs["Alpha"].default_value = alpha
    # Drive Base Color from the exported vertex layer
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "Col"
    nt.links.new(attr.outputs["Color"], n.inputs["Base Color"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = 'BLENDED'
    if hasattr(m, "blend_method"):
        m.blend_method = 'BLEND'
    m.use_backface_culling = True
    return m

gel = mat_gel(0.8, COLOR)
me.materials.append(gel)

# ---------- lights ----------
world = bpy.data.worlds.new("world")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.25, 0.22, 0.50, 1.0)

# Key light (soft, from front-left)
light_data = bpy.data.lights.new("key_light", 'POINT')
light_data.energy = 150
light_data.color = (1.0, 0.95, 0.9)
light_obj = bpy.data.objects.new("key_light_obj", light_data)
light_obj.location = (-1.5, -1.5, 2.0)
light_obj.scale = (1.0, 1.0, 1.0)
scene.collection.objects.link(light_obj)

# Fill light (soft, from front-right)
light_data2 = bpy.data.lights.new("fill_light", 'POINT')
light_data2.energy = 60
light_data2.color = (0.9, 0.92, 0.95)
light_obj2 = bpy.data.objects.new("fill_light_obj", light_data2)
light_obj2.location = (1.5, -1.5, 2.0)
scene.collection.objects.link(light_obj2)

# ---------- renders ----------
scene.render.resolution_x = 512
scene.render.resolution_y = 640

# Still render - front view
scene.render.filepath = os.path.join(REN_DIR, f"{NAME}.png")
bpy.ops.render.render(write_still=True)
print(f"[gata] still render done: {NAME}")

# Animation: render some frames per shape key
for label, sampler in [("idle", anim_idle)]:
    sk_ad = body.animation_data_create()
    obj_ad = body.animation_data_create()
    act_sk = bpy.data.actions.new(f"{label}_sk")
    sk_ad.action = act_sk
    act_obj = bpy.data.actions.new(f"{label}_obj")
    obj_ad.action = act_obj
    
    for f in range(1, 25, 2):  # 12 frames
        t = (f - 1) / 24.0
        vals = sampler(t)
        for k in ["whisker_pad_L", "whisker_pad_R", "ear_tilt_L", "ear_tilt_R",
                  "mouth_open", "eye_wide_L", "eye_wide_R"]:
            if k in kb:
                kb[k].value = vals.get(k, 0.0)
                kb[k].keyframe_insert("value", frame=f)
    
    # Object location can animate subtle breathing
    if "z" in vals:
        body.location.z = 0.02 * math.sin(2 * math.pi * t)
        body.keyframe_insert("location", frame=f)
    
    sk_ad.action = None
    obj_ad.action = None
    
    print(f"[gata] frames: {label}")

# Reset values
for k in ["whisker_pad_L", "whisker_pad_R", "ear_tilt_L", "ear_tilt_R",
          "mouth_open", "eye_wide_L", "eye_wide_R"]:
    if k in kb:
        kb[k].value = 0.0

body.location = (0, 0, 0)
for k in kb.keys():
    if k.value != 0.0:
        kb[k].value = 0.0

# Save
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, f"{NAME}_wip.blend"))
print(f"[gata] DONE — {NAME} built with FLOAT_COLOR + shape keys ({COLOR})")
print(f"[gata] Saved to {OUT_DIR}/{NAME}_wip.blend")
print(f"[gata] Color palette: {COLOR}")