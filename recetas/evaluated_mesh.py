# RECETA: evaluated_mesh -- measure what the model LOOKS like, not the base cage.
# QUE: morphed_coords(obj) -> (W, N): world positions and normals of the EVALUATED mesh
#      (shape keys applied) that line up 1:1 with the BASE vertex indices.
#      masks_muted(obj): context manager that turns MASK modifiers off while measuring.
#      shapekey_drift(obj): mean base->evaluated displacement, to PROVE the morphed path
#      is needed (or that it is not).
# CUANDO: any measurement or paint-by-geometry on a mesh with shape keys or MASK modifiers.
# GOTCHAS: (1) me.vertices.foreach_get("co") is the BASE cage: with 41 shape keys it was
#      mean 102 mm, max 183 mm off a 1.80 m character, non-uniform, and it fails silently
#      (plausible numbers, paint "a bit off"). (2) a MASK still on drops 19158 verts to
#      13380, so evaluated index i is a different vertex than base index i. The function
#      REFUSES to return a mismatched result: a wrong answer here is invisible.
#      (3) also paint_por_geometria gotcha #2 -- same trap, walked into anyway.
# LECCIONES: LECCIONES.md#3 and #14 (an instrument that cannot see the defect); engram
#      Dungeon #2493. Pair the check with probe_with_control.ProbeSet so "no drift" is
#      only believed after a deliberately morphed control showed drift.
# FUENTE: Dungeon game/tools/blender/_char_common.py:36 (masks_muted), :59 (morphed_coords),
#      :89 (shapekey_drift). Copies existed in 4 + 2 places.
# EXEMPLAR:
#   W, N = morphed_coords(body)         # then mask = (W[:,2] > 1.5) & ...
import numpy as np

try:
    import bpy
except ImportError:
    bpy = None


class masks_muted:
    """Turn off MASK modifiers for the duration of a block."""

    def __init__(self, *objs):
        self.objs = [o for o in objs if o is not None]
        self.states = []

    def __enter__(self):
        for o in self.objs:
            for m in o.modifiers:
                if m.type == "MASK" and m.show_viewport:
                    self.states.append((m, m.show_viewport))
                    m.show_viewport = False
        bpy.context.view_layer.update()
        return self

    def __exit__(self, *exc):
        for m, was in self.states:
            m.show_viewport = was
        bpy.context.view_layer.update()
        return False


def morphed_coords(obj):
    """(W, N) of the evaluated mesh, masks muted, 1:1 with BASE indices."""
    with masks_muted(obj):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        no = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("normal", no)
        ev.to_mesh_clear()
    nb = len(obj.data.vertices)
    if n != nb:
        raise RuntimeError(
            "mask not muted: %d evaluated vs %d base. Without a 1:1 mapping every group "
            "index points at the wrong vertex." % (n, nb))
    M = np.array(obj.matrix_world)
    W = co.reshape(n, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    N = no.reshape(n, 3).astype(np.float64) @ np.linalg.inv(M[:3, :3])
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    return W, N


def shapekey_drift(obj):
    """Mean base-to-evaluated displacement in metres. 0.0 means no morphing."""
    W, _ = morphed_coords(obj)
    me = obj.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    M = np.array(obj.matrix_world)
    base = co.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    return float(np.mean(np.linalg.norm(W - base, axis=1)))
