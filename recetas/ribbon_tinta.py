# RECETA: ribbon_tinta — línea de tinta paramétrica que cabalga el relieve
# QUÉ: strip de grosor constante construida por raycast sobre la superficie real (sonrisa,
#      pliegues, delineados). Crisp = GEOMETRÍA, nunca paint per-face.
# CUÁNDO: cualquier línea facial/de tinta que el 2D dibuja con pluma.
# GOTCHAS: (1) curva SIMÉTRICA en X si el rasgo lo es — el raycast sobre relieve asimétrico dio
#      smirk chueco (forzar espejado); (2) material EMISSION casi-negro (el mouth_dark viejo
#      rendía rojizo); (3) ancho 6mm lee bold a cuerpo entero, 3.4mm es tímido; (4) taper suave
#      en puntas; (5) offset proud 3.5mm por la NORMAL del hit; (6) re-trazar tras CUALQUIER
#      cambio de relieve de la zona (el color se come la línea).
# EXEMPLAR (sonrisa): build_ribbon(body, curve_fn=smile(ax, ay, az), width=0.006)
import bpy
import math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import bmesh


def surface_bvh(body):
    deps = bpy.context.evaluated_depsgraph_get()
    bev = body.evaluated_get(deps)
    bme = bev.to_mesh()
    verts = [body.matrix_world @ v.co for v in bme.vertices]
    polys = [tuple(p.vertices) for p in bme.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    bev.to_mesh_clear()
    return bvh


def smile(ax, ay, az, half_w=0.058, drop=0.108, curve=0.034):
    def fn(t):  # t in [-1,1] -> (x, z) del plano frontal; simétrica por construcción
        return ax + t * half_w, (az - drop) + curve * t * t
    return fn


def build_ribbon(body, curve_fn, width=0.006, proud=0.0035, nsamp=41,
                 name='ink_ribbon', mat_name='lip_ink', ray_dir=(0, 1, 0), ray_from_y=-0.35):
    bvh = surface_bvh(body)
    pts, nrms = [], []
    for i in range(nsamp):
        t = -1.0 + 2.0 * i / (nsamp - 1)
        xx, zz = curve_fn(t)
        hit = bvh.ray_cast(Vector((xx, ray_from_y, zz)), Vector(ray_dir), 1.0)
        if hit[0] is None:
            continue
        pts.append(hit[0] + hit[1] * proud)
        nrms.append(hit[1])
    bm = bmesh.new()
    prev = None
    for i, p in enumerate(pts):
        tang = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        wdir = nrms[i].cross(tang).normalized()
        tt = i / (len(pts) - 1)
        taper = 0.30 + 0.70 * math.sin(math.pi * tt) ** 0.35
        a = bm.verts.new(p - wdir * width * taper / 2)
        b = bm.verts.new(p + wdir * width * taper / 2)
        if prev:
            bm.faces.new((prev[0], prev[1], b, a))
        prev = (a, b)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nt = mat.node_tree
        for node in list(nt.nodes):
            nt.nodes.remove(node)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs[0].default_value = (0.055, 0.045, 0.04, 1.0)
        nt.links.new(em.outputs[0], out.inputs[0])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = Matrix.Identity(4)
    for pl in me.polygons:
        pl.use_smooth = True
    return ob
