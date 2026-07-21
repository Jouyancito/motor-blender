"""Cel-banded look-dev for the Lawen bear.

Approach:
  - EEVEE (BLENDER_EEVEE, renders headless on this 5.1.2 build).
  - CEL color: keep the baked texture as albedo, but route lighting through a
    Diffuse BSDF -> Shader-to-RGB -> ColorRamp (CONSTANT interp, 3 bands) and
    MULTIPLY the banded light into the texture, then Emission. This flattens the
    soft 3D shading into hard cel zones while preserving the painted identity.
  - OUTLINE: inverted-hull. Duplicate the mesh, Solidify (negative thickness,
    flip normals) so only backfaces show, pure-black emission, unlit. Gives a
    crisp black contour on silhouette + creases, engine-portable.

Camera/lights framing reuse render_viewer.py (fit-to-bounds, Standard transform,
front + 3/4 + face). White-ish world to match the 2D's white background.

Run:
  blender.exe -b --python cel_banded.py -- <in.glb> <out_dir>
"""
import bpy, sys, os, math
from mathutils import Vector

a = sys.argv[sys.argv.index("--")+1:]
in_glb, out_dir = a[0], a[1]
NO_HULL = "--nohull" in a   # debug: render cel material only
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=in_glb)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# ---- grab the baked texture image from the imported material ----
base_img = None
src_mat = obj.data.materials[0] if obj.data.materials else None
if src_mat and src_mat.use_nodes:
    for n in src_mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image is not None:
            base_img = n.image
            break
print("[cel] baked image:", base_img.name if base_img else None)

# ---- build the CEL material ----
cel = bpy.data.materials.new("CEL")
cel.use_nodes = True
nt = cel.node_tree
nt.nodes.clear()
out_n = nt.nodes.new("ShaderNodeOutputMaterial")
emit = nt.nodes.new("ShaderNodeEmission")

# albedo: baked texture (or a neutral green fallback)
if base_img is not None:
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = base_img
    tex.interpolation = 'Linear'
    albedo_out = tex.outputs['Color']
else:
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = (0.45, 0.6, 0.25, 1)
    albedo_out = rgb.outputs[0]

# lighting -> banded factor
diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = 'CONSTANT'
cr = ramp.color_ramp
# 3 cel bands: shadow / mid / light. Brightened so albedo stays readable & flat.
cr.elements[0].position = 0.0;  cr.elements[0].color = (0.62, 0.62, 0.62, 1)  # shadow band
cr.elements[1].position = 0.5;  cr.elements[1].color = (0.84, 0.84, 0.84, 1)  # mid band
e2 = cr.elements.new(0.78);     e2.color = (1.0, 1.0, 1.0, 1)                  # lit band
nt.links.new(diff.outputs[0], s2rgb.inputs[0])
nt.links.new(s2rgb.outputs[0], ramp.inputs[0])

# multiply albedo * banded light
mul = nt.nodes.new("ShaderNodeMixRGB")
mul.blend_type = 'MULTIPLY'
mul.inputs['Fac'].default_value = 1.0
nt.links.new(albedo_out, mul.inputs['Color1'])
nt.links.new(ramp.outputs['Color'], mul.inputs['Color2'])

nt.links.new(mul.outputs['Color'], emit.inputs['Color'])
emit.inputs['Strength'].default_value = 1.0
nt.links.new(emit.outputs[0], out_n.inputs[0])

# replace material slots on the bear
obj.data.materials.clear()
obj.data.materials.append(cel)

# ---- OUTLINE via FREESTYLE ----
# Inverted-hull failed on this 473-island shattered Meshy mesh: backface culling
# can't carve a rim from non-manifold soup, so the shell renders solid black.
# Freestyle draws true contour ink lines (silhouette + border + crease) and is
# topology-independent + works headless in EEVEE. This is the right tool here.
def setup_freestyle():
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.mode = 'EDITOR'
    fs.use_smoothness = True
    # remove default lineset(s), add a clean black one
    while fs.linesets:
        fs.linesets.remove(fs.linesets[0])
    ls = fs.linesets.new("ink")
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_contour = True
    ls.select_edge_mark = False
    lst = ls.linestyle
    lst.color = (0, 0, 0)
    lst.thickness = 2.2          # crisp ink, not chunky (at 720x900)
    lst.thickness_position = 'CENTER'
    lst.use_chaining = True
    sc.render.line_thickness_mode = 'ABSOLUTE'
    # crease angle: lines on sharper folds only, keeps it clean
    try: vl.freestyle_settings.crease_angle = math.radians(130)
    except Exception: pass

if not NO_HULL:
    setup_freestyle()

# ---- bounds for framing (from the real bear, not the hull) ----
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for c in obj.bound_box:
    w = obj.matrix_world @ Vector(c)
    for i in range(3): mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ctr = (mn+mx)*0.5; rad = max((mx-mn).x, (mx-mn).y, (mx-mn).z); top = mx.z

# ---- world: white background (match 2D), low-energy so cel bands stay flat ----
world = bpy.data.worlds.new("W"); bpy.context.scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 1.0

# ---- a single key sun so the cel banding has a clear light direction ----
sun = bpy.data.lights.new("S", 'SUN'); sun.energy = 3.0
so = bpy.data.objects.new("S", sun); bpy.context.collection.objects.link(so)
so.rotation_euler = (math.radians(55), math.radians(8), math.radians(35))

# ---- camera + EEVEE ----
cd = bpy.data.cameras.new("C"); cd.lens = 75
cam = bpy.data.objects.new("C", cd); bpy.context.collection.objects.link(cam)
sc = bpy.context.scene; sc.camera = cam
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 720; sc.render.resolution_y = 900
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
# EEVEE quality knobs (guarded — names vary across builds)
try: sc.eevee.taa_render_samples = 64
except Exception: pass

def shot(lbl, ang, el, tgt, dist):
    aa = math.radians(ang); e = math.radians(el)
    cam.location = tgt+Vector((math.sin(aa)*math.cos(e), -math.cos(aa)*math.cos(e), math.sin(e)))*dist
    cam.rotation_euler = (tgt-cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(out_dir, "view_%s.png" % lbl)
    bpy.ops.render.render(write_still=True)
    print("[cel] shot", lbl, "->", sc.render.filepath)

shot("front", 0, 6, ctr, rad*2.6)
shot("34", 20, 6, ctr, rad*2.5)
shot("face", 16, 2, Vector((ctr.x, ctr.y, top-rad*0.18)), rad*0.9)
print("[cel] DONE")
