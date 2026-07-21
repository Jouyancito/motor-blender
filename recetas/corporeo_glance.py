# RECETA — GLANCE: the cheap cadence-1 look (audit 2026-07-16, loop refactor).
# ~2-4s after EVERY mutating MCP block, BEFORE the next one. Catastrophe tripwire +
# eye — it does NOT judge vs the 2D (that's the step's job, cadence 2).
#
# Use via MCP:
#   exec(open(r'C:\Users\the_j\Desktop\Lawen\corporeo-3d\_motor\recetas\corporeo_glance.py').read())
#   glance()                      # probes + front render
#   glance(views=('front','q34')) # extra angle
#
# Output: _gate/g360/glance/GLANCE_<ts>_<view>.png + glance.jsonl (probe ledger).
# Renders use bpy.ops.render.opengl(view_context=False) on a temp camera — a REAL
# offscreen render, independent of window focus / Local View (the raw-screenshot hole).
import bpy
import json
import math
import os
import time
from mathutils import Vector

_GLANCE_DIR = os.path.join(os.path.dirname(bpy.data.filepath), "..", "_gate", "g360", "glance")
_VIEW_AZ = {"front": 0, "q34": 45, "side": 90, "back": 180}


def _probes(obj_name):
    o = bpy.data.objects.get(obj_name)
    if o is None:
        return {"error": f"{obj_name} missing"}
    me = o.data
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    bm.free()
    mw = o.matrix_world
    xs, ys, zs = [], [], []
    for c in o.bound_box:
        w = mw @ Vector(c)
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
    return {"verts": len(me.vertices), "open_edges": open_edges,
            "bbox": [round(min(xs), 3), round(max(xs), 3), round(min(ys), 3),
                     round(max(ys), 3), round(min(zs), 3), round(max(zs), 3)],
            "n_objects_visible": sum(1 for x in bpy.data.objects if not x.hide_render)}


def glance(obj_name=None, views=("front",), res=700, zone=None, zone_radius=0.45):
    """zone=(x,y,z) world center -> the camera frames THAT feature, not the body.
    Regla Joan 2026-07-17: la vista sigue al trabajo (garra en mano = camara en la garra)."""
    if obj_name is None:
        cfg = os.path.join(os.path.dirname(bpy.data.filepath), "..", "motor.config.json")
        try:
            obj_name = json.load(open(cfg)).get("main_object", "base_v2")
        except Exception:
            obj_name = "base_v2"
    os.makedirs(_GLANCE_DIR, exist_ok=True)
    p = _probes(obj_name)
    ts = time.strftime("%H%M%S")
    scene = bpy.context.scene
    prev_cam, prev_x, prev_y, prev_pct = (scene.camera, scene.render.resolution_x,
                                          scene.render.resolution_y, scene.render.resolution_percentage)
    prev_path = scene.render.filepath
    cam_data = bpy.data.cameras.new("GlanceTmp")
    cam = bpy.data.objects.new("GlanceTmp", cam_data)
    scene.collection.objects.link(cam)
    try:
        o = bpy.data.objects.get(obj_name)
        bb = p.get("bbox", [-1, 1, -1, 1, 0, 2])
        if zone is not None:
            cx, cy, cz = zone
            rad = zone_radius
        else:
            cx, cy, cz = (bb[0]+bb[1])/2, (bb[2]+bb[3])/2, (bb[4]+bb[5])/2
            rad = max(bb[1]-bb[0], bb[5]-bb[4]) * 1.6 + 0.5
        outs = []
        for v in views:
            az = math.radians(_VIEW_AZ.get(v, 0))
            cam.location = (cx + rad*math.sin(az), cy - rad*math.cos(az), cz)
            look = Vector((cx, cy, cz)) - cam.location
            cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
            scene.camera = cam
            scene.render.resolution_x = scene.render.resolution_y = res
            scene.render.resolution_percentage = 100
            fp = os.path.join(_GLANCE_DIR, f"GLANCE_{ts}_{v}.png")
            scene.render.filepath = fp
            bpy.ops.render.opengl(write_still=True, view_context=False)
            outs.append(fp)
            print("[glance] render ->", fp)
    finally:
        scene.camera = prev_cam
        scene.render.resolution_x, scene.render.resolution_y = prev_x, prev_y
        scene.render.resolution_percentage = prev_pct
        scene.render.filepath = prev_path
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "object": obj_name, **p, "renders": outs}
    with open(os.path.join(_GLANCE_DIR, "glance.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("[glance] probes:", {k: v for k, v in p.items() if k != "bbox"})
    return entry
