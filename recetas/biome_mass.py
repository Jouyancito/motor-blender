# biome_mass.py -- lobe-mass recipe: blobs, dabs and accents that build volume.
#
# Phase 1 of the biome consolidation only lands what grass_pack needs
# (add_accent_blob). The dab/core/canopy/lobe helpers used by flower, bush and
# tree land with their own packs, each behind its own byte-compare.
import bmesh
from mathutils import Matrix

from biome_stem import paint_verts_of_faces


def add_accent_blob(bm, vcol, pos, radius, color, squash_z=1.6):
    """Tiny icosphere (flower bud) -- subdivisions=1 keeps it ~20 tris.

    `squash_z` scales the blob about its own center along Z (>1 stretches it
    into a bud, <1 flattens it into a cushion). Consumes no rng draws.
    """
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=radius,
                                     matrix=Matrix.Translation(pos))
    new_verts = res["verts"]
    for v in new_verts:
        v.co.z = pos.z + (v.co.z - pos.z) * squash_z
    paint_verts_of_faces(new_verts, vcol, color)
