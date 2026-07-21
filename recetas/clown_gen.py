"""clown_gen — EXPERIMENTAL: first humanoid character from primitives.

Capability probe (PO request 2026-07-19): can the motor build a character with
identity, not just architecture? Subject: classic AUGUSTE clown, grounded in a
real reference (Wikipedia Commons "Auguste clown reading a book upside-down"):
orange voluminous wig + tiny black bowler, white face, round red nose, red
plaid-ish jacket with yellow lapels/cuffs, striped shirt, baggy red trousers
with yellow cuffs, white gloves, giant blue-yellow shoes.

Proportions: ~1.75 m to scalp (wig adds more), audited against the standard
1.80 m red reference mannequin placed beside him.

Run: blender -b --python clown_gen.py -- <out_dir> [seed]
"""
import bpy, sys, os, math, random
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT_DIR = args[0]
SEED = int(args[1]) if len(args) > 1 else 7
os.makedirs(OUT_DIR, exist_ok=True)
rng = random.Random(SEED)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Palette from the auguste reference photo
RED_SUIT   = (0.62, 0.10, 0.08)
RED_DARK   = (0.45, 0.07, 0.06)   # plaid hint stripe
YELLOW     = (0.88, 0.68, 0.10)
WHITE      = (0.92, 0.90, 0.86)
SKIN_WHITE = (0.93, 0.88, 0.82)   # white face makeup
NOSE_RED   = (0.80, 0.08, 0.05)
ORANGE_WIG = (0.90, 0.38, 0.06)
BLACK      = (0.06, 0.06, 0.07)
SHOE_BLUE  = (0.12, 0.25, 0.62)
STRIPE_BG  = (0.90, 0.90, 0.90)

_mats = {}
def mat(name, color, rough=0.75):
    key = (name, color, rough)
    if key not in _mats:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1.0)
        b.inputs["Roughness"].default_value = rough
        _mats[key] = m
    return _mats[key]

def sphere(name, r, loc, material, seg=16, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    ob.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return ob

def cyl(name, r, h, loc, material, rot=(0, 0, 0), verts=14):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return ob

def torus(name, r, minor, loc, material, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=minor, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.scale = scale
    ob.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return ob

# ── Proportions (m). Reference human 1.80; clown slightly shorter + wig. ──────
HIP = 0.86          # hip height
CHEST = 1.28
SHOULDER = 1.42
NECK = 1.50
HEAD_C = 1.62       # head center
HEAD_R = 0.145

X = 0.0  # clown stands at origin

# Legs: baggy red trousers (two fat cylinders) + yellow cuffs
for s in (-1, 1):
    lx = X + s * 0.11
    cyl("leg_%d" % s, 0.085, HIP - 0.12, (lx, 0, (HIP - 0.12) / 2 + 0.10), mat("suit", RED_SUIT))
    torus("cuff_%d" % s, 0.095, 0.030, (lx, 0, 0.16), mat("yellow", YELLOW), scale=(1, 1, 0.8))
    # Giant shoe: elongated ellipsoid, toe forward (-Y), yellow toe cap
    sphere("shoe_%d" % s, 0.105, (lx, -0.10, 0.055), mat("shoe", SHOE_BLUE, rough=0.35),
           scale=(1.0, 2.3, 0.55))
    sphere("toecap_%d" % s, 0.085, (lx, -0.27, 0.055), mat("yellow", YELLOW, rough=0.35),
           scale=(1.0, 1.15, 0.52))

# Torso: barrel jacket + yellow lapel + buttons
sphere("torso", 0.24, (X, 0, (HIP + SHOULDER) / 2), mat("suit", RED_SUIT),
       scale=(1.0, 0.78, 1.30))
cyl("lapel", 0.055, 0.44, (X, -0.175, (HIP + SHOULDER) / 2 + 0.04), mat("yellow", YELLOW),
    rot=(math.radians(6), 0, 0))
# two buttons only, both ON the lapel (round-1's third button floated at the crotch)
for i in range(2):
    sphere("button_%d" % i, 0.032, (X, -0.225, CHEST - 0.06 - i * 0.13), mat("yellow", YELLOW, rough=0.3))
# striped shirt hint at the chest V
sphere("shirt", 0.10, (X, -0.13, SHOULDER - 0.06), mat("stripe", STRIPE_BG), scale=(1.2, 0.5, 0.8))
# small bowtie at the neck (round-1's blue torus read as a giant pacifier)
BOW_BLUE = (0.10, 0.22, 0.60)
for s in (-1, 1):
    sphere("bow_wing_%d" % s, 0.042, (X + s * 0.045, -0.15, NECK - 0.015), mat("bow", BOW_BLUE),
           scale=(1.25, 0.5, 0.75))
sphere("bow_knot", 0.020, (X, -0.16, NECK - 0.015), mat("bow", BOW_BLUE))

# Arms: joint-to-hand segments so cuffs/gloves land ON the limb axis
# (round 1 placed them by eyeballed offsets and they floated mid-air).
def limb(name, p1, p2, r, material):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    ob = cyl(name, r, d.length, tuple((p1 + p2) / 2), material)
    ob.rotation_euler = d.normalized().to_track_quat('Z', 'Y').to_euler()
    return ob

for s in (-1, 1):
    joint = Vector((X + s * 0.19, 0, SHOULDER - 0.03))    # buried in torso
    hand = Vector((X + s * 0.50, -0.05, HIP + 0.16))       # down-and-out
    d = (hand - joint).normalized()
    limb("arm_%d" % s, tuple(joint), tuple(hand), 0.062, mat("suit", RED_SUIT))
    sphere("shoulder_%d" % s, 0.075, tuple(joint), mat("suit", RED_SUIT))
    cuff_c = joint + d * ((hand - joint).length - 0.075)
    c = torus("arm_cuff_%d" % s, 0.068, 0.024, tuple(cuff_c), mat("yellow", YELLOW))
    c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    sphere("glove_%d" % s, 0.075, tuple(hand + d * 0.05), mat("glove", WHITE))

# Head: white-makeup face
sphere("head", HEAD_R, (X, 0, HEAD_C), mat("face", SKIN_WHITE), seg=20)
sphere("nose", 0.045, (X, -HEAD_R + 0.012, HEAD_C + 0.005), mat("nose", NOSE_RED, rough=0.3))
# Eyes: white ovals + black pupils, high-contrast auguste style
for s in (-1, 1):
    sphere("eye_%d" % s, 0.032, (X + s * 0.055, -HEAD_R + 0.030, HEAD_C + 0.058),
           mat("glove", WHITE), scale=(1.0, 0.55, 1.25))
    sphere("pupil_%d" % s, 0.013, (X + s * 0.055, -HEAD_R + 0.012, HEAD_C + 0.058), mat("black", BLACK))
    # black brow arc
    torus("brow_%d" % s, 0.030, 0.007, (X + s * 0.055, -HEAD_R + 0.030, HEAD_C + 0.105),
          mat("black", BLACK), rot=(math.radians(80), 0, 0), scale=(1, 1, 0.6))
# Big red smile: half-sunk thin torus tilted into the lower face
torus("smile", 0.062, 0.014, (X, -HEAD_R + 0.035, HEAD_C - 0.065), mat("nose", NOSE_RED),
      rot=(math.radians(72), 0, 0), scale=(1.1, 1.0, 0.75))

# Wig: cluster of orange puffs around sides + top, bald front (auguste)
puffs = [(-0.12, 0.02, 0.10), (0.12, 0.02, 0.10), (-0.10, 0.10, 0.05), (0.10, 0.10, 0.05),
         (0.0, 0.11, 0.11), (-0.14, 0.05, -0.02), (0.14, 0.05, -0.02)]
for i, (px, py, pz) in enumerate(puffs):
    r = 0.075 + rng.uniform(-0.012, 0.015)
    sphere("wig_%d" % i, r, (X + px, py, HEAD_C + pz + 0.04), mat("wig", ORANGE_WIG, rough=0.95), seg=12)

# Tiny bowler hat perched on top of the wig
cyl("hat_crown", 0.055, 0.075, (X, 0.02, HEAD_C + 0.235), mat("black", BLACK, rough=0.4))
cyl("hat_brim", 0.085, 0.014, (X, 0.02, HEAD_C + 0.20), mat("black", BLACK, rough=0.4))

# ── 1.80 m reference mannequin (standard, PO proportion rule) ─────────────────
mx = 0.85
mman = mat("scale_ref", (0.80, 0.20, 0.18), rough=0.5)
cyl("ref_human_body", 0.20, 1.50, (mx, 0, 0.75), mman, verts=8)
sphere("ref_human_head", 0.15, (mx, 0, 1.65), mman, seg=10)

# ── Stage: floor + lights + camera ────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
floor = bpy.context.object
floor.data.materials.append(mat("floor", (0.72, 0.66, 0.58), rough=0.9))

sun = bpy.data.lights.new("sun", 'SUN')
sun.energy = 3.0
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
so.rotation_euler = (math.radians(50), 0, math.radians(-30))
bpy.context.collection.objects.link(so)
fill = bpy.data.lights.new("fill", 'AREA')
fill.energy = 400.0
fill.size = 6.0
fo = bpy.data.objects.new("fill", fill)
fo.location = (2.5, -3.5, 2.2)
fo.rotation_euler = (math.radians(65), 0, math.radians(35))
bpy.context.collection.objects.link(fo)

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.84, 1.0)

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 900
scene.render.resolution_y = 1100
scene.view_settings.view_transform = 'Standard'

cam_d = bpy.data.cameras.new("C")
cam_d.lens = 55
cam = bpy.data.objects.new("C", cam_d)
bpy.context.collection.objects.link(cam)
scene.camera = cam

def shot(label, pos, target):
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).normalized().to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT_DIR, "clown_%s.png" % label)
    bpy.ops.render.render(write_still=True)
    print("[clown_gen] shot", label)

shot("front", (0.35, -3.4, 1.25), (0.2, 0, 1.0))
shot("face", (0.15, -1.3, 1.62), (0.0, 0, 1.58))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "clown.blend"))
print("[clown_gen] DONE seed=%d" % SEED)
