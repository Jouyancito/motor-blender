# RECETA: surface_decal -- paint IN the surface, not a sticker on it.
# QUE: a dense disc (centre + `rings` x `segs` quad grid), EVERY vertex ray-projected onto
#      the final target surface, and its custom split normals copied from the target's
#      smooth (vertex-interpolated) normals at those points. The decal then shades exactly
#      like the wood/skin/cloth under it.
# CUANDO: eyes, logos, labels, stripes, spots, nose/mouth dots on any organic or curved
#      surface that is already in its FINAL shape (project last, after every deformation).
# GOTCHAS: (1) v6/v7 recomputed normals from the tiny decal faces and lifted 0.18 mm: the
#      eyes read as pasted-on buttons (Joan, rana v7). Copy the target's smooth normals and
#      keep the lift ~0.06 mm. (2) a miss RAISES (SystemExit) instead of silently dropping
#      the decal. (3) the original seeded its wobble with Python's hash(name): hash(str) is
#      randomised per process, so the same decal came out different every run. Here the
#      seed is crc32(name) (stable) unless you pass seed=. (4) the ray is parameterised
#      (origin + direction, world space) instead of the original's hard-coded
#      y=-0.05 / +Y front view. (5) the BVH is built from the target's mesh DATA (final
#      sculpted mesh, no modifiers); pass tree= to reuse one across many decals.
# FUENTE: rana/rana_gen.py:392-442 (smooth_normal, decal), approved by Joan at v10
#      ("Esta si que si, ya si es muy similar", engram #2950). Replaces paint_por_geometria
#      where the graphic needs real geometry of its own (per-vertex paint cannot draw an
#      eye smaller than the mesh edge).
# EXEMPLAR:
#   tree = BVHTree.FromBMesh(bm_of(body))
#   surface_decal("eye_0", body, origin=(-0.0074, -0.05, 0.0180), direction=(0, 1, 0),
#                 rx=0.0030, rz=0.0026, material=BLACK, wobble=0.04, tree=tree, part="decals")
import math
import random
import zlib

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

try:
    from recetas.motor_stamp import stamp_object as _motor_stamp
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from motor_stamp import stamp_object as _motor_stamp

TECHNIQUE = "surface_decal"


def build_tree(obj):
    """BVH of obj's mesh data in OBJECT space."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def smooth_normal(obj, idx, co):
    """Target's interpolated SMOOTH normal at point `co` of polygon `idx` (the BVH hands
    back the flat face normal)."""
    me = obj.data
    poly = me.polygons[idx]
    cos = [me.vertices[i].co for i in poly.vertices]
    w = poly_3d_calc(cos, co)
    n = Vector((0, 0, 0))
    for wi, i in zip(w, poly.vertices):
        n += me.vertices[i].normal * wi
    return n.normalized()


def surface_decal(name, target, origin, direction, rx, rz, material, lift=0.00006,
                  wobble=0.0, seed=None, tree=None, collection=None, rings=14, segs=48,
                  part=None):
    """Project an elliptical (rx, rz) decal onto `target` along `direction` from `origin`
    (both WORLD space). Returns (hit_point, face_normal) in target OBJECT space. The
    decal object takes the target's matrix_world, so it sits exactly on it."""
    mwi = target.matrix_world.inverted()
    o = mwi @ Vector(origin)
    d = (mwi.to_3x3() @ Vector(direction)).normalized()
    tree = tree or build_tree(target)
    hit, n, idx, _ = tree.ray_cast(o, d)
    if hit is None:
        raise SystemExit("surface_decal %s missed the %s surface from %s along %s"
                         % (name, target.name, tuple(origin), tuple(direction)))
    rot = n.to_track_quat("Z", "Y").to_matrix()
    wr = random.Random((zlib.crc32(name.encode()) & 0xffff) if seed is None else seed)
    jit = [1 + wobble * wr.uniform(-1, 1) for _ in range(6)]
    bm = bmesh.new()
    pts, nrm = [hit], [smooth_normal(target, idx, hit)]
    for i in range(1, rings + 1):
        for j in range(segs):
            a = 2 * math.pi * j / segs
            k = (jit[int(j * 6 / segs)] * (1 - (j * 6 / segs) % 1)
                 + jit[(int(j * 6 / segs) + 1) % 6] * ((j * 6 / segs) % 1))
            local = Vector((rx * k * i / rings * math.cos(a), rz * k * i / rings * math.sin(a), 0))
            p = hit + rot @ local
            h, hn, fi, dist = tree.ray_cast(p + n * 0.004, -n, 0.008)
            if h is None or abs(dist - 0.004) > 0.0012:
                h, hn, fi, _ = tree.find_nearest(p)
            pts.append(h)
            nrm.append(smooth_normal(target, fi, h))
    vs = [bm.verts.new(p + q * lift) for p, q in zip(pts, nrm)]
    c, grid = vs[0], [vs[1 + i * segs:1 + (i + 1) * segs] for i in range(rings)]
    for j in range(segs):
        bm.faces.new((c, grid[0][j], grid[0][(j + 1) % segs]))
    for i in range(rings - 1):
        for j in range(segs):
            k = (j + 1) % segs
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    me.normals_split_custom_set_from_vertices(nrm)
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = target.matrix_world.copy()
    (collection or bpy.context.scene.collection).objects.link(ob)
    me.materials.append(material)
    _motor_stamp(ob, part, TECHNIQUE)
    return hit, n
