# biome_ao.py -- ambient occlusion baked straight into the vertex colour.
#
# WHY VERTEX AND NOT TEXTURE (2026-08-08)
#
# Joan asked whether the motor was running at maximum "con gpu". The honest
# answer for this job is that the GPU is not the lever: baking AO to a TEXTURE
# needs UVs, an image, and a render engine, and none of these packs have UVs --
# all their colour lives in FLOAT_COLOR vertex layers. Baking to VERTICES needs
# only a BVH and some rays, runs on the CPU in milliseconds, and the result
# travels inside the GLB where Godot draws it. A prettier Blender render would
# not have improved a single asset; this does.
#
# What it buys, concretely: the dark contact zones between packed stones. The
# reference rock sheets have deep darkness where stones meet, and a per-vertex
# height gradient cannot produce it -- darkness in a pile is about ENCLOSURE,
# not about height.
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _hemisphere_dirs(n):
    """`n` cosine-weighted directions on the +Z hemisphere.

    Deterministic (golden-ratio sequence, no rng draws) so a bake never
    reshuffles anything else in a build, and two runs are byte-identical.
    Cosine weighting is the physically right distribution for diffuse
    occlusion: samples cluster where the surface actually gathers light.
    """
    dirs = []
    for i in range(n):
        u = (i + 0.5) / n
        v = (i * 0.618033988749895) % 1.0
        r = math.sqrt(u)
        theta = math.tau * v
        dirs.append(Vector((r * math.cos(theta), r * math.sin(theta),
                            math.sqrt(max(0.0, 1.0 - u)))))
    return dirs


def _basis_from_normal(n):
    """Orthonormal basis with `n` as +Z, avoiding the degenerate axis."""
    helper = Vector((0.0, 0.0, 1.0)) if abs(n.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    t = n.cross(helper)
    if t.length < 1e-9:
        t = Vector((1.0, 0.0, 0.0))
    t.normalize()
    b = n.cross(t)
    return t, b


def bake_vertex_ao(bm, vcol, samples=20, max_dist=0.6, strength=0.85,
                   min_factor=0.18, default_color=(1.0, 1.0, 1.0)):
    """Multiply every entry of `vcol` by its vertex's ambient occlusion.

    bm          the FINISHED bmesh -- every mass already placed. Baking a stone
                before its neighbours exist measures nothing.
    samples     rays per vertex. 20 is plenty for low-poly: the result is a
                per-vertex value that gets interpolated across big faces anyway.
    max_dist    metres. AO must be LOCAL or the whole formation goes uniformly
                grey; roughly half a formation radius is the useful range.
    strength    1.0 = fully dark where fully enclosed.
    min_factor  floor, so a buried vertex still carries some hue instead of
                collapsing to black. Godot has no ambient term to rescue it.

    Returns (mean_factor, min_factor_seen) so the caller can print a number
    instead of asserting that the bake "worked".
    """
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    dirs = _hemisphere_dirs(samples)

    # Offset ray origins off the surface, or every ray instantly hits the face
    # it started on and the whole mesh bakes black. Scaled to the model so this
    # works on a 0.2 m pebble and a 6 m boulder alike.
    span = max((v.co.length for v in bm.verts), default=1.0)
    eps = max(span * 1e-4, 1e-6)

    total = 0.0
    lowest = 1.0
    for v in bm.verts:
        n = v.normal
        if n.length < 1e-9:
            continue
        t, b = _basis_from_normal(n)
        origin = v.co + n * eps
        hits = 0
        for d in dirs:
            world_d = t * d.x + b * d.y + n * d.z
            if tree.ray_cast(origin, world_d, max_dist)[0] is not None:
                hits += 1
        ao = 1.0 - strength * (hits / float(samples))
        ao = max(min_factor, ao)
        total += ao
        lowest = min(lowest, ao)
        base = vcol.get(v, default_color)
        vcol[v] = tuple(c * ao for c in base)

    n_verts = max(len(bm.verts), 1)
    return total / n_verts, lowest
