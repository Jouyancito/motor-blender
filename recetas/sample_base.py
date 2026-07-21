# RECETA: sample_base — samplear la paleta REAL de la malla
# QUÉ: devuelve los colores dominantes reales del vertex-paint por zona. La malla es la verdad;
#      el doc de paleta es historia.
# CUÁNDO: SIEMPRE antes de pintar/limpiar/comparar colores. Sin excepción.
# GOTCHAS: la lección de los 1183 sellos (2026-07-13): el doc decía #9DBB4D (0.616,0.733,0.302)
#      pero la malla viva usaba (0.38,0.56,0.11) — cada "limpieza" con el valor del doc estampó
#      manchas claras. Attribute POINT 'brand'; foreach_get, nunca loop por vért (freeze 100k+).
# EXEMPLAR: base = sample_base(bpy.data.objects['body_united'])['dominante']
import bpy
import numpy as np


def sample_base(obj, attr_name='brand', zone_mask=None):
    """Colores reales del paint. zone_mask: bool (n,) opcional en índice de vértices."""
    me = obj.data
    attr = me.color_attributes.get(attr_name) or next(
        (a for a in me.color_attributes if a.domain == 'POINT'), None)
    n = len(me.vertices)
    cols = np.empty(n * 4, dtype=np.float32)
    attr.data.foreach_get('color', cols)
    c = cols.reshape(n, 4)[:, :3]
    if zone_mask is not None:
        c = c[zone_mask]
    # dominante = moda por cuantización fina (los paints por código son valores exactos)
    q = np.round(c * 200).astype(np.int32)
    uniq, counts = np.unique(q, axis=0, return_counts=True)
    order = np.argsort(-counts)
    top = [(tuple((uniq[i] / 200.0).round(3)), int(counts[i])) for i in order[:8]]
    return {'dominante': np.array(top[0][0], dtype=np.float32), 'top8': top, 'n': len(c)}
