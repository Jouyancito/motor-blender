# RECETA: nails_asentados — cuñas de queratina asentadas en puntas (uñas/garras)
# QUÉ: rasgo nítido chico = GEOMETRÍA (anti-receta: paint de uñas → 0.001 pale_frac).
#      Cuña aplanada, raíz hundida en el dedo, material mate (NUNCA emission → "velas brillantes").
# CUÁNDO: uñas, garras, dientes, cuernos chicos — cualquier placa/queratina en punta.
# GOTCHAS: (1) el ancla es el DEDO — si no hay dedos (mitones), construir el ancla primero
#      (garras para dedos inexistentes = causa raíz del fallo 2026-07-12); (2) verificar con
#      CLOSE-UP obligatorio antes de ✅; (3) material Diffuse crema ILUMINADO (muy oscuro
#      desaparece del pale-metric, muy claro = vela); (4) curva de garra: UNA cuña angulada,
#      no 2 segmentos (dio zigzag).
# EXEMPLAR: add_nail(bm, pos, Vector((0,-1,-0.55)), length=0.030, rad=0.010)
import bpy
from mathutils import Vector, Matrix
import bmesh


def add_nail(bm, pos, direction, length, rad, flatten=0.45, sink=0.8, segments=10):
    d = direction.normalized()
    mt = (Matrix.Translation(pos - d * rad * sink) @
          d.to_track_quat('Z', 'Y').to_matrix().to_4x4() @
          Matrix.Diagonal(Vector((1.0, flatten, 1.0, 1.0))))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments,
                          radius1=rad, radius2=rad * 0.25, depth=length,
                          matrix=mt @ Matrix.Translation(Vector((0, 0, length / 2))))


def keratin_material(name='claw_keratin', rgb=(0.90, 0.88, 0.72)):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        for node in list(nt.nodes):
            nt.nodes.remove(node)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bsdf = nt.nodes.new('ShaderNodeBsdfDiffuse')
        bsdf.inputs[0].default_value = (*rgb, 1.0)
        nt.links.new(bsdf.outputs[0], out.inputs[0])
    return mat
