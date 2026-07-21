# RECETA: bvh_glue — conformar/pegar un objeto a la superficie con offset proud
# QUÉ: cada vért del accesorio va al punto más cercano de la piel + offset por la normal del
#      hit. El fix "boca despegada" (124 verts flotaban >4mm).
# CUÁNDO: ribbons/liners/accesorios que deben cabalgar la piel y quedaron flotando o hundidos
#      tras editar el relieve.
# GOTCHAS: (1) BVH sobre la malla EVALUADA (relieve real con modifiers); (2) NUNCA vacuum-form
#      per-vért en piezas con estructura (arruga — para eso proyección monoaxial del anillo
#      trasero); esto es para strips/liners chatos; (3) offset 2-3.5mm; si tras pegar sigue
#      invisible, el problema NO es burial — reconstruir paramétrico (lección solidify).
# EXEMPLAR: glue_to_surface(bpy.data.objects['mouth_lip'], body, proud=0.0035)
import bpy
from mathutils.bvhtree import BVHTree


def glue_to_surface(obj, body, proud=0.0030):
    deps = bpy.context.evaluated_depsgraph_get()
    bev = body.evaluated_get(deps)
    bme = bev.to_mesh()
    verts = [body.matrix_world @ v.co for v in bme.vertices]
    polys = [tuple(p.vertices) for p in bme.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    bev.to_mesh_clear()
    mw = obj.matrix_world
    mwi = mw.inverted()
    moved = 0
    for v in obj.data.vertices:
        loc, nrm, idx, dist = bvh.find_nearest(mw @ v.co)
        if loc is None:
            continue
        v.co = mwi @ (loc + nrm * proud)
        moved += 1
    obj.data.update()
    return moved
