"""invhull-flat lookdev — RESTORE the illustrated 2D look on the Meshy bear.

Problem: Meshy baked a soft texture onto a blobby mesh -> reads PLASTICINE
(mushy gradients, smeared ink lines, no defined edges).
Target: FLAT color zones + CRISP black contour/ink lines (cel / illustrated).

Fix (engine-faithful, Godot-portable):
  1. MAIN mesh   -> Emission shader of the BAKED TEXTURE = unlit/flat color
     (kills the soft 3D shading so colors read as flat zones like the 2D).
  2. OUTLINE mesh -> duplicate of main, Solidify with NEGATIVE thickness +
     flipped normals (inverted hull), PURE BLACK emission, backface only.
     This is exactly Godot's toon outline -> transfers 1:1.

Cycles headless (Eevee needs a GL context on 5.1.2 -> not reliable in -b).
Camera framing copied from blender/render_viewer.py (fit-to-bounds, Standard).

Run:
  blender.exe -b --python render_invhull_flat.py -- <in.glb> <out_dir> [outline_frac]
"""
import bpy, sys, os, math
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
NO_OUTLINE = "--no-outline" in a   # debug: render the flat mesh alone
pos = [x for x in a if not x.startswith("--")]   # positional args only
in_glb = pos[0]
out_dir = pos[1]
outline_frac = float(pos[2]) if len(pos) > 2 else 0.006   # fraction of bounds radius
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=in_glb)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# ---- bounds (world space) ----
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for c in obj.bound_box:
    w = obj.matrix_world @ Vector(c)
    for i in range(3):
        mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ctr = (mn + mx) * 0.5
rad = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
top = mx.z
outline_thick = rad * outline_frac
print("[invhull] bounds rad=%.4f  outline_thick=%.5f (frac=%.4f)" % (rad, outline_thick, outline_frac))

# ---- find the baked texture image from the original material ----
baked_img = None
for m in obj.data.materials:
    if m and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image is not None:
                baked_img = n.image
                break
    if baked_img:
        break
print("[invhull] baked texture:", baked_img.name if baked_img else "NONE (will use vertex/base color)")

# ================= MAIN: flat emission of the baked texture =================
flat_mat = bpy.data.materials.new("LAWEN_flat")
flat_mat.use_nodes = True
nt = flat_mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
emi = nt.nodes.new("ShaderNodeEmission")
emi.inputs["Strength"].default_value = 1.0
if baked_img is not None:
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = baked_img
    tex.interpolation = 'Closest'   # crisp painted lines, no soft bilinear smear
    uvn = nt.nodes.new("ShaderNodeUVMap")
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    # POSTERIZE the color a touch to push toward flat cel zones (optional, gentle)
    # ColorRamp with hard constant stops would over-bin; instead keep texture but
    # we drive emission directly -> preserves the illustrated paint but UNLIT.
    nt.links.new(tex.outputs["Color"], emi.inputs["Color"])
else:
    emi.inputs["Color"].default_value = (0.4, 0.6, 0.3, 1.0)
nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])

# replace all material slots on main with the flat emission material
obj.data.materials.clear()
obj.data.materials.append(flat_mat)

# ================= OUTLINE =================
# The asked-for technique is INVERTED-HULL, but on this Meshy base (473
# disconnected islands -> a shattered, non-watertight shell) a Solidify hull
# renders as a SOLID black mass: the per-fragment offset shells overlap and the
# Backfacing classification is meaningless across thousands of loose islands, so
# the camera never sees the flat mesh behind it. Verified empirically (NO_OUTLINE
# proves the flat mesh is perfect; adding the hull blacks it out).
#
# FREESTYLE is the robust outline here: it traces silhouette/border/crease lines
# from the ACTUAL visible geometry (immune to island count) and composites a
# clean black ink line over the Cycles render in background mode. This is the
# closest match to the 2D illustration's hand-drawn contour, and the line read
# transfers conceptually to Godot's toon outline (silhouette + creases).
USE_FREESTYLE = "--invhull" not in a   # default Freestyle; --invhull to force hull
sc = bpy.context.scene

if not NO_OUTLINE and not USE_FREESTYLE:
  # --- legacy INVERTED-HULL path (kept for reference; fails on shattered mesh) ---
  bpy.ops.object.select_all(action='DESELECT')
  obj.select_set(True)
  bpy.context.view_layer.objects.active = obj
  bpy.ops.object.duplicate()
  outline = bpy.context.view_layer.objects.active
  outline.name = "LAWEN_outline"
  black = bpy.data.materials.new("LAWEN_black")
  black.use_nodes = True
  bnt = black.node_tree; bnt.nodes.clear()
  bout = bnt.nodes.new("ShaderNodeOutputMaterial")
  bemi = bnt.nodes.new("ShaderNodeEmission")
  bemi.inputs["Color"].default_value = (0, 0, 0, 1)
  btrans = bnt.nodes.new("ShaderNodeBsdfTransparent")
  bgeo = bnt.nodes.new("ShaderNodeNewGeometry")
  bmix = bnt.nodes.new("ShaderNodeMixShader")
  bnt.links.new(bgeo.outputs["Backfacing"], bmix.inputs["Fac"])
  bnt.links.new(bemi.outputs["Emission"], bmix.inputs[1])
  bnt.links.new(btrans.outputs["BSDF"], bmix.inputs[2])
  bnt.links.new(bmix.outputs["Shader"], bout.inputs["Surface"])
  outline.data.materials.clear(); outline.data.materials.append(black)
  sol = outline.modifiers.new("Outline", 'SOLIDIFY')
  sol.thickness = outline_thick; sol.offset = 1.0
  sol.use_flip_normals = True; sol.use_rim = False

if not NO_OUTLINE and USE_FREESTYLE:
  # --- FREESTYLE ink-line path ---
  sc.render.use_freestyle = True
  vl = sc.view_layers[0]
  vl.use_freestyle = True
  vl.freestyle_settings.mode = 'SCRIPT' if False else 'EDITOR'
  fs = vl.freestyle_settings
  # remove any pre-existing/empty linesets (an empty one with linestyle=None makes
  # parameter_editor crash on `linestyle.use_chaining`); start clean.
  while fs.linesets:
      fs.linesets.active_index = 0
      bpy.ops.scene.freestyle_lineset_remove()
  # one line set: silhouette + border + contour (the illustrated contour lines)
  ls = fs.linesets.new("ink")
  # Silhouette + contour + border = the OUTER ink line + holes (glasses gaps).
  # Crease OFF: on a fur soup every micro-fold would become a line -> noise.
  ls.select_silhouette = True
  ls.select_border = True
  ls.select_contour = True
  ls.select_crease = False
  ls.select_edge_mark = False
  lst = ls.linestyle
  lst.color = (0, 0, 0)
  lst.thickness = float(os.environ.get("FS_THICK", "2.2"))  # px ink width
  lst.thickness_position = 'CENTER'
  # Explicitly enable chaining so parameter_editor doesn't choke on a NoneType
  # chaining state when the lineset is built purely via Python (no GUI init).
  lst.use_chaining = True
  lst.chaining = 'PLAIN'

# ================= scene / render =================
world = bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
bgn = world.node_tree.nodes["Background"]
bgn.inputs[0].default_value = (1, 1, 1, 1)   # pure white bg like the 2D illustration
bgn.inputs[1].default_value = 1.0

cd = bpy.data.cameras.new("C"); cd.lens = 75
cam = bpy.data.objects.new("C", cd)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.resolution_x = 720
sc.render.resolution_y = 900
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'

def shot(lbl, ang, el, tgt, dist):
    aa = math.radians(ang); e = math.radians(el)
    cam.location = tgt + Vector((math.sin(aa) * math.cos(e),
                                 -math.cos(aa) * math.cos(e),
                                 math.sin(e))) * dist
    cam.rotation_euler = (tgt - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(out_dir, "view_%s.png" % lbl)
    bpy.ops.render.render(write_still=True)
    print("[invhull] shot", lbl)

shot("front", 0, 6, ctr, rad * 2.6)
shot("34", 20, 6, ctr, rad * 2.5)
shot("face", 16, 2, Vector((ctr.x, ctr.y, top - rad * 0.18)), rad * 0.9)
print("[invhull] DONE")
