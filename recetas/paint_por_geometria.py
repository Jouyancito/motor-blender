# RECETA: paint_por_geometria — pintar zonas por criterio 3D, vectorizado
# QUÉ: helper que da (W, Nw, zf, cols) listos en numpy para definir máscaras por geometría
#      (altura, normal, elipse, banda) y estampar color. Concepto #2 de la bitácora: pintar
#      por GEOMETRÍA, nunca por vista.
# CUÁNDO: cualquier zona de color/sombra sobre vertex-paint.
# GOTCHAS: (1) normales world = no @ inv(M3) — el .T faltante pintó la panza en la ESPALDA;
#      (2) shape keys: pintar colors SÍ llega al render, mover me.vertices NO;
#      (3) color destino: SAMPLEAR primero (ver sample_base.py);
#      (4) suavidad de borde: POINT domain interpola solo — no hace falta falloff manual chico.
# EXEMPLAR:
#   g = geo(bpy.data.objects['body_united'])
#   mask = (g.zf > 0.8) & (g.Nw[:,1] < -0.2) & (((g.x-ax)/0.1)**2 + ((g.z-az)/0.1)**2 < 1)
#   stamp(g, mask, (0.38, 0.56, 0.11))
import bpy
import numpy as np


class geo:
    def __init__(self, obj, attr_name='brand'):
        me = obj.data
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get('co', co)
        no = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get('normal', no)
        M = np.array(obj.matrix_world)
        self.obj, self.me, self.n = obj, me, n
        self.W = co.reshape(n, 3) @ M[:3, :3].T + M[:3, 3]
        Nw = no.reshape(n, 3) @ np.linalg.inv(M[:3, :3])
        self.Nw = Nw / np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-9)
        self.x, self.y, self.z = self.W[:, 0], self.W[:, 1], self.W[:, 2]
        self.zf = (self.z - self.z.min()) / max(self.z.max() - self.z.min(), 1e-9)
        self.attr = me.color_attributes.get(attr_name)
        cols = np.empty(n * 4, dtype=np.float32)
        self.attr.data.foreach_get('color', cols)
        self.cols = cols.reshape(n, 4)

    def apex(self, zf_min=0.80):
        """ápex del hocico = vért más frontal (-Y) de la región alta. SOLO región cabeza:
        con umbral bajo la PANZA le gana al hocico (gotcha documentado)."""
        head = self.zf > zf_min
        i = np.where(head)[0][np.argmin(self.y[head])]
        return float(self.x[i]), float(self.y[i]), float(self.z[i])


def stamp(g, mask, rgb):
    g.cols[mask, :3] = np.array(rgb, dtype=np.float32)
    g.attr.data.foreach_set('color', g.cols.reshape(-1))
    g.me.update()
    return int(mask.sum())
