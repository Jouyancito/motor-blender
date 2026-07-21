"""FLAT EMISSION + FREESTYLE INK lookdev for the Lawen bear.

Goal: restore the 2D illustrated look (flat color zones + crisp black ink lines)
on the Meshy base, WITHOUT touching geometry. Pure shading pass.

Approach:
  - Every material -> unlit Emission of its OWN base-color texture (kills 3D shading mush).
  - Freestyle (render.use_freestyle) black LineSet: silhouette + border + crease.
  - Cycles, headless-safe. Standard view transform. White world (matches 2D bg).

Run:
  blender.exe -b --python render_flat_freestyle.py -- <in.glb> <out_dir>
"""
import bpy, sys, os, math
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
in_glb, out_dir = a[0], a[1]
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=in_glb)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# ---------------------------------------------------------------------------
# 1. FLAT / UNLIT: rebuild each material as Emission of its base-color texture.
#    Grab whatever image the GLB's Principled used for Base Color, feed it
#    straight into an Emission shader -> no diffuse/specular shading at all.
# ---------------------------------------------------------------------------
def find_base_image(mat):
    """Return the image plugged (directly or via mix) into Base Color, else None."""
    if not mat.use_nodes:
        return None
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bc = bsdf.inputs.get('Base Color')
        if bc and bc.is_linked:
            node = bc.links[0].from_node
            # walk back through simple passthrough nodes to an image
            seen = set()
            stack = [node]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                if n.type == 'TEX_IMAGE' and n.image:
                    return n.image
                for inp in n.inputs:
                    for ln in inp.links:
                        stack.append(ln.from_node)
    # fallback: any image node in the tree
    for n in nt.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            return n.image
    return None

def find_base_color(mat):
    """Flat RGBA from a Principled base color when there is no texture."""
    if mat.use_nodes:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            return tuple(bsdf.inputs['Base Color'].default_value)
    return (0.8, 0.8, 0.8, 1.0)

mats = list(obj.data.materials)
print("[flat] materials on mesh:", [m.name if m else None for m in mats])

for mat in mats:
    if mat is None:
        continue
    img = find_base_image(mat)
    base_col = find_base_color(mat)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emis = nt.nodes.new('ShaderNodeEmission')
    emis.inputs['Strength'].default_value = 1.0
    if img is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = img
        tex.interpolation = 'Linear'
        # GLB base color is sRGB data; keep it sRGB so colors match the texture
        try:
            img.colorspace_settings.name = 'sRGB'
        except Exception:
            pass
        nt.links.new(tex.outputs['Color'], emis.inputs['Color'])
        print("[flat] %-14s <- texture %s" % (mat.name, img.name))
    else:
        emis.inputs['Color'].default_value = base_col
        print("[flat] %-14s <- flat color %s" % (mat.name, tuple(round(c,2) for c in base_col)))
    nt.links.new(emis.outputs['Emission'], out.inputs['Surface'])
    # mark for a freestyle face/edge mark pass if needed (not required for SILHOUETTE)
    mat.use_backface_culling = False

# ---------------------------------------------------------------------------
# 2. Bounds for camera fit (same math as render_viewer.py)
# ---------------------------------------------------------------------------
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for c in obj.bound_box:
    w = obj.matrix_world @ Vector(c)
    for i in range(3):
        mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ctr = (mn + mx) * 0.5
rad = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
top = mx.z

# ---------------------------------------------------------------------------
# 3. White world (matches the 2D illustration's plain white background).
#    Unlit emission means lights don't matter, but a bright world keeps the
#    background pure white and gives Freestyle a clean field.
# ---------------------------------------------------------------------------
world = bpy.data.worlds.new("W"); bpy.context.scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1)
bg.inputs[1].default_value = 1.0

# ---------------------------------------------------------------------------
# 4. Render settings: Cycles (headless-safe), Standard transform, white bg.
# ---------------------------------------------------------------------------
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.resolution_x = 720
sc.render.resolution_y = 900
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'

# ---------------------------------------------------------------------------
# 5. FREESTYLE ink lines: black, ~1.8px, silhouette + border + crease.
# ---------------------------------------------------------------------------
sc.render.use_freestyle = True
sc.render.line_thickness_mode = 'ABSOLUTE'
sc.render.line_thickness = 1.8  # px baseline

vl = sc.view_layers[0]
vl.use_freestyle = True
fs = vl.freestyle_settings
fs.use_culling = True
fs.crease_angle = math.radians(134.0)  # creases sharper than this get a line

# clear default linesets, make our own
while fs.linesets:
    fs.linesets.remove(fs.linesets[0])
ls = fs.linesets.new("ink")
ls.select_silhouette = True   # outer contour
ls.select_border = True       # open-mesh borders
ls.select_crease = True       # sharp folds (fur tufts, overall seams, glasses)
ls.select_edge_mark = False
ls.select_contour = True
ls.select_external_contour = True

lst = ls.linestyle
lst.color = (0.0, 0.0, 0.0)
lst.thickness = 1.8
lst.alpha = 1.0
lst.caps = 'ROUND'
# slight thickness variation off — keep it clean/even like ink pen
lst.thickness_position = 'CENTER'

# ---------------------------------------------------------------------------
# 6. Camera + shots (front, 3/4, face) — render_viewer.py framing.
# ---------------------------------------------------------------------------
cd = bpy.data.cameras.new("C"); cd.lens = 75
cam = bpy.data.objects.new("C", cd)
bpy.context.collection.objects.link(cam); sc.camera = cam

def shot(lbl, ang, el, tgt, dist):
    aa = math.radians(ang); e = math.radians(el)
    cam.location = tgt + Vector((math.sin(aa) * math.cos(e),
                                 -math.cos(aa) * math.cos(e),
                                 math.sin(e))) * dist
    cam.rotation_euler = (tgt - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(out_dir, "view_%s.png" % lbl)
    bpy.ops.render.render(write_still=True)
    print("[flat] shot", lbl, "->", sc.render.filepath)

shot("front", 0, 6, ctr, rad * 2.6)
shot("34", 20, 6, ctr, rad * 2.5)
shot("face", 16, 2, Vector((ctr.x, ctr.y, top - rad * 0.18)), rad * 0.9)
print("[flat] DONE")
