# RECETA: contorno_2d — extraer contorno/perfil de silueta desde una imagen 2D
# QUÉ: geometría derivada de los PÍXELES del ref, no de la imaginación (directiva trabajo-fino).
#      Da: máscara fg, contorno exterior (normalizado), perfil de anchos por fila.
# CUÁNDO: antes de construir un rasgo con silueta propia (melena) o re-proporcionar (warp);
#      como target para lofts/comparaciones.
# GOTCHAS: (1) fg por color de esquinas — en CLOSE-UPS las esquinas inferiores son cuerpo:
#      usar solo esquinas superiores (bug cazado en la vista face); (2) el ref puede estar
#      OFF-MODEL: validar refs derivadas contra el canon antes de calibrar (lección oso flaco);
#      (3) corre en WSL env critic (cv2/numpy).
# EXEMPLAR: fg, contour_norm, perfil = contorno_2d('_refs/filomeno_nude_apose.png')
import cv2
import numpy as np


def contorno_2d(path, top_corners_only=False, tol=0.10, n_rows=240):
    rgb = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    h, w = rgb.shape[:2]
    k = max(4, min(h, w) // 50)
    if top_corners_only:
        corners = np.concatenate([rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3)])
    else:
        corners = np.concatenate([rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3),
                                  rgb[-k:, :k].reshape(-1, 3), rgb[-k:, -k:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    fg = (np.linalg.norm(rgb - bg, axis=2) > tol).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    ys, xs = np.where(fg > 0)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    box = fg[y0:y1 + 1, x0:x1 + 1]
    cs, _ = cv2.findContours(box, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    cn = np.stack([(c[:, 0] - box.shape[1] / 2) / (box.shape[1] / 2),
                   c[:, 1] / box.shape[0]], axis=1)          # x:-1..1, y:0..1
    prof = cv2.resize(box, (box.shape[1], n_rows), interpolation=cv2.INTER_NEAREST)
    perfil = prof.sum(axis=1).astype(float) / n_rows
    return fg.astype(bool), cn, perfil
