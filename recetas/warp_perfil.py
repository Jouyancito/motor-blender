# RECETA: warp_perfil — re-proporcionar el cuerpo entero contra un perfil 2D
# QUÉ: UN warp analítico: remapeo-z por masa acumulada + curva de anchos por fila, derivado de
#      los dos perfiles de silueta. Reemplaza escalados por bandas (anti-receta: 3 pases fallidos
#      contra métrica auto-normalizante).
# CUÁNDO: proporciones globales no calzan con el ref y las bandas dicen dónde.
# GOTCHAS: (1) suavizado con np.convolve 'same' SIN padding aplasta bordes (xscale 0.43 fantasma —
#      pad mode='edge'); (2) clamp dv [0.75,1.3] y ratio [0.8,1.22]; (3) aplicar a SHAPE KEYS
#      (Basis+MouthOpen), no a me.vertices; (4) objetos de rasgos: transformarlos con el mismo
#      warp per-vért; (5) la pintura viaja con los verts pero recetas ancladas (pera) conviene
#      RE-CORRERLAS post-warp; (6) VALIDAR el ref primero (lección oso-flaco: ref off-model =
#      warp fiel a un target equivocado); (7) VERIFICAR con ojo + overlay, el IoU global es
#      insensible a mejoras locales.
# EXEMPLAR: tablas = derivar_tablas(perfil_2d, perfil_render); aplicar_warp(body, tablas)
import numpy as np


def derivar_tablas(w2d, wrn, clamp_dv=(0.75, 1.30), clamp_r=(0.80, 1.22), smooth_pad=12):
    """w2d/wrn: perfiles de ancho por fila (misma N, normalizados por su altura)."""
    v = np.linspace(0, 1, len(w2d))
    c2d = np.cumsum(w2d); c2d /= c2d[-1]
    crn = np.cumsum(wrn); crn /= crn[-1]
    v2d_of_vrn = np.interp(crn, c2d, v)
    dv = np.clip(np.gradient(v2d_of_vrn, v), *clamp_dv)
    remap = np.cumsum(dv)
    remap = (remap - remap[0]) / (remap[-1] - remap[0])   # pineado corona/pies
    w2d_at = np.interp(remap, v, w2d)
    ratio = np.clip(np.where(wrn > 1e-4, w2d_at / np.maximum(wrn, 1e-4), 1.0), *clamp_r)
    rp = np.pad(ratio, smooth_pad, mode='edge')
    k = np.ones(2 * smooth_pad + 1) / (2 * smooth_pad + 1)
    ratio_s = np.convolve(rp, k, mode='same')[smooth_pad:-smooth_pad]
    return {'v': v, 'remap': remap, 'xscale': ratio_s}


def make_warp_world(tab, ztop, zbot, cx, cy, y_effect=0.5):
    H = ztop - zbot
    def warp(Wp):
        v = np.clip((ztop - Wp[:, 2]) / H, 0, 1)
        s = np.interp(v, tab['v'], tab['xscale'])
        out = Wp.copy()
        out[:, 2] = ztop - np.interp(v, tab['v'], tab['remap']) * H
        out[:, 0] = cx + (Wp[:, 0] - cx) * s
        out[:, 1] = cy + (Wp[:, 1] - cy) * (s ** y_effect)
        return out
    return warp
