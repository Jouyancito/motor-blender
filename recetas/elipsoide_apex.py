# RECETA: elipsoide_apex — zona facial anclada al ápex del hocico
# QUÉ: pinta una zona (pera del tan, hocico) como UN elipsoide anclado al landmark real de la
#      malla (ápex = vért más frontal de la cabeza). Auto-adapta si la geometría cambia
#      (re-correrla post-warp la re-ancla sola).
# CUÁNDO: zonas faciales que en el 2D son una forma coherente. NUNCA cortar zonas por banda de
#      altura (anti-receta: el corte por zf partió la pera en anillo).
# GOTCHAS: (1) ápex SOLO en región cabeza (zf>0.80) — con umbral bajo gana la panza; (2) limpiar
#      la zona vieja ANTES con criterio de clase (r>g), no de banda; (3) profundizar el tono
#      ~6-20% según el shader (el cel lava el color); (4) solo cara frontal (Nw_y < 0.35).
# EXEMPLAR:
#   from paint_por_geometria import geo, stamp
#   g = geo(body); ax, ay, az = g.apex()
#   pear = pear_mask(g, ax, ay, az); stamp(g, pear, TAN_DEEP)
import numpy as np


def pear_mask(g, ax, ay, az, half_w=0.095, half_h=0.072, depth=0.16,
              drop=0.050, ny_max=0.35, zf_min=0.77):
    dxe = (g.x - ax) / half_w
    dze = (g.z - (az - drop)) / half_h
    dye = (g.y - ay) / depth
    return ((dxe ** 2 + dze ** 2 + np.maximum(dye, 0) ** 2 < 1.0)
            & (g.Nw[:, 1] < ny_max) & (g.zf > zf_min))


def clean_old_warm(g, ax, base_rgb, zf_lo=0.76, zf_hi=0.93, half_w=0.20):
    r, gr = g.cols[:, 0], g.cols[:, 1]
    zone = (g.zf > zf_lo) & (g.zf < zf_hi) & (np.abs(g.x - ax) < half_w) & (g.Nw[:, 1] < 0.35)
    old = zone & (r > gr)
    g.cols[old, :3] = np.array(base_rgb, dtype=np.float32)
    return int(old.sum())
