# biome_facet.py -- planar-decomposition rock: flat faces meeting at sharp arrises.
#
# WHY THIS EXISTS (2026-08-08, Dungeon Party)
#
# Every rock in the motor until now was built by displacing vertices along their
# normal with Perlin noise (rock_pack ridge+detail, river_pack, gen_golem,
# golem_guardian -- four forks of the same idea). That operator has a hard
# structural limit: normal displacement of a closed surface produces a
# CONTINUOUSLY UNDULATING surface. It can make a lumpier potato. It can never
# make a plane, because a plane requires many vertices to share one normal and
# noise is what breaks that sharing.
#
# Joan, looking at rock_showcase.png beside Path of Exile references:
# "son rocas genericas, el estilo PoE no se nota en ellas". The style he is
# pointing at is built from FLAT FACES meeting at SHARP ARRISES, plus bedding
# strata. No amount of frequency or amplitude tuning reaches it from noise.
#
# So this is a different operator, not a tuned one: build the solid by CUTTING it
# with planes. The intersection of half-spaces is a convex polyhedron -- flat
# faces and sharp edges by construction, which is exactly the target. Concavity
# and interest then come from STACKING several cut blocks, not from noise.
#
# The two techniques are complementary, not rivals: cut for the architecture,
# then optionally let the old noise ride on top at low amplitude for grain.
import math

import bmesh
from mathutils import Matrix, Vector

from biome_stem import paint_verts_of_faces  # noqa: F401  (re-exported for callers)


# Quantified adjacency, from the M3 checklist: centres of neighbouring masses sit
# at <= 0.55-0.65 x the sum of their radii. Above that they read as separate
# stones floating near each other; below it they read as one mass. Midpoint.
ADJACENCY = 0.60

# Minimum distance of any cutting plane from the block centre, as a fraction of
# the block radius. This is a GUARANTEE, not a taste value: the intersection of
# all half-spaces always contains the ball of this radius, so no combination of
# random cuts can ever produce an empty or degenerate block.
MIN_CUT_FRAC = 0.55


def _convex_chunk(rng, radius, cuts, bedding, bedding_jitter, elongate, flatten):
    """One convex polyhedron carved out of a cube by successive plane cuts.

    Returns (coords, faces) as plain data so the caller can place and paint it
    without this function needing to know about the target bmesh.

    `bedding` adds near-horizontal cut planes with only `bedding_jitter` of tilt.
    Those are what read as sedimentary strata: parallel flat faces stacked up the
    block, the signature of the reference outcrops.

    Consumes rng draws: 2 per bedding plane + 4 per free cut.
    """
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=radius * 4.0)

    planes = []
    for i in range(bedding):
        # Alternate up/down so strata cut both the top and the underside.
        n = Vector((
            rng.uniform(-bedding_jitter, bedding_jitter),
            rng.uniform(-bedding_jitter, bedding_jitter),
            1.0 if i % 2 == 0 else -1.0,
        ))
        planes.append((n.normalized(), radius * rng.uniform(MIN_CUT_FRAC, 0.95)))
    for _ in range(cuts):
        n = Vector((rng.gauss(0.0, 1.0), rng.gauss(0.0, 1.0), rng.gauss(0.0, 1.0)))
        if n.length < 1e-6:
            n = Vector((0.0, 0.0, 1.0))
        # Free cuts sit in a NARROW band near the surface (0.80-1.0 r). The first
        # version spread them 0.55-1.0 and the result read as folded paper: a few
        # deep cuts remove so much volume that only three or four enormous facets
        # survive. Stone wants many medium facets. The ball of MIN_CUT_FRAC still
        # survives every possible combination, so the block can never degenerate.
        planes.append((n.normalized(), radius * rng.uniform(0.80, 1.0)))

    for normal, dist in planes:
        geom = tmp.verts[:] + tmp.edges[:] + tmp.faces[:]
        res = bmesh.ops.bisect_plane(
            tmp, geom=geom, dist=1e-6,
            plane_co=normal * dist, plane_no=normal,
            clear_outer=True,
        )
        # bisect_plane with clear_outer leaves the cut open; the fill is what
        # turns the opening into the flat face this whole recipe is about.
        cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if cut_edges:
            bmesh.ops.holes_fill(tmp, edges=cut_edges)

    # Normalise BEFORE the shape scaling, so `radius` means the block's real
    # bounding radius in metres. Without this the caller's radius is a lie: the
    # cuts sit at <= 1.0r along their own normals but the CORNERS between three
    # cut planes survive much further out, so a radius=0.70 block measured
    # 2.08 m across. An asset generator whose size argument does not predict the
    # size is worse than one with no argument at all.
    reach = max((v.co.length for v in tmp.verts), default=0.0)
    if reach > 1e-6:
        k = radius / reach
        for v in tmp.verts:
            v.co *= k

    for v in tmp.verts:
        v.co.x *= elongate
        v.co.z *= flatten

    tmp.verts.index_update()
    coords = [v.co.copy() for v in tmp.verts]
    faces = [[v.index for v in f.verts] for f in tmp.faces]
    tmp.free()
    return coords, faces


def add_faceted_rock(bm, vcol, center, spec, rng):
    """A rock as a STACK of plane-cut blocks, painted in place.

    spec keys:
      radius        block radius in metres (the mass is roughly 1.5-2x this)
      blocks        how many blocks are stacked (1 = a single boulder)
      cuts          free cutting planes per block -- more cuts, more facets
      bedding       near-horizontal planes per block (sedimentary strata)
      elongate      X stretch, >1 for a slab lying down
      flatten       Z squash, <1 for a slab, >1 for a column
      color_rock    base tint
      color_moss    up-facing tint, or None for a bare rock
      moss_min_z    face-normal Z above which moss can grow (0.55 ~ 57 deg)
      moss_chance   probability a qualifying face actually gets moss
      crevice_dark  how much the bottom of the mass darkens, 0..1

    Returns the list of created BMFaces. Consumes rng draws per block.
    """
    radius = spec["radius"]
    blocks = spec.get("blocks", 3)
    color_rock = spec.get("color_rock", (0.42, 0.40, 0.36))
    color_moss = spec.get("color_moss")
    moss_min_z = spec.get("moss_min_z", 0.55)
    moss_chance = spec.get("moss_chance", 0.75)
    crevice_dark = spec.get("crevice_dark", 0.45)
    scale_lo, scale_hi = spec.get("block_scale", (0.55, 1.0))

    origin = Vector(center)
    placed = []          # (centre, radius) of blocks already down
    made_faces = []
    all_verts = []

    for i in range(blocks):
        # A stack that keeps its block size all the way up reads as a spiral of
        # equal stones. Real piled rock narrows: broad base, smaller crown.
        taper = spec.get("taper", 0.0)
        shrink = 1.0 - taper * (i / max(blocks - 1, 1))
        r = radius * shrink * (1.0 if i == 0 else rng.uniform(scale_lo, scale_hi))
        if not placed:
            pos = origin.copy()
        else:
            anchor_c, anchor_r = placed[rng.randrange(len(placed))]
            ang = rng.uniform(0.0, math.tau)
            # The adjacency rule is what makes a stack read as ONE rock. Sitting
            # at exactly ADJACENCY looks glued; a little closer looks quarried.
            d = ADJACENCY * (r + anchor_r) * rng.uniform(0.72, 1.0)
            # `stack` decides whether the mass grows outward or upward. At 0 the
            # blocks spread on the ground; at 1 they pile. The first version had
            # no such control and every mass came out a puddle: stacked_mossy
            # measured 2.29 m wide by 1.03 m tall when it was meant to be a cairn.
            stack = spec.get("stack", 0.0)
            horiz = 1.0 - 0.75 * stack
            pos = anchor_c + Vector((
                math.cos(ang) * d * horiz,
                math.sin(ang) * d * horiz,
                d * stack * rng.uniform(0.60, 1.0) + rng.uniform(-0.10, 0.30) * r,
            ))
        placed.append((pos, r))

        coords, faces = _convex_chunk(
            rng, r,
            cuts=spec.get("cuts", 9),
            bedding=spec.get("bedding", 0),
            bedding_jitter=spec.get("bedding_jitter", 0.10),
            elongate=spec.get("elongate", 1.0),
            flatten=spec.get("flatten", 1.0),
        )

        verts = [bm.verts.new(pos + c) for c in coords]
        all_verts.extend(verts)
        for idx in faces:
            try:
                f = bm.faces.new([verts[k] for k in idx])
            except ValueError:
                continue          # duplicate face from a coincident cut; skip
            f.normal_update()
            made_faces.append(f)

    if not all_verts:
        return made_faces

    # ---- paint -------------------------------------------------------------
    # Two passes on purpose. Base first for every vertex, then moss only on
    # up-facing faces. Vertices shared with a mossy face get overwritten, which
    # bleeds the moss a few centimetres down the arris -- the references show a
    # hard-ish boundary, not a razor line, so the bleed is wanted.
    z_lo = min(v.co.z for v in all_verts)
    z_hi = max(v.co.z for v in all_verts)
    z_span = max(z_hi - z_lo, 1e-6)

    for v in all_verts:
        # Crevice/base darkening. The references have deep darks low in the mass
        # and clear light on top; a flat tint is what made ours read as plaster.
        t = (v.co.z - z_lo) / z_span
        k = 1.0 - crevice_dark * (1.0 - t)
        vcol[v] = tuple(c * k for c in color_rock)

    if color_moss is not None:
        # Moss is decided PER VERTEX, from the vertex's own averaged normal, not
        # per face. Painting a qualifying face paints every vertex it touches,
        # and on a coarse plane-cut block most vertices touch at least one
        # up-facing face — the first version turned the whole rock green with
        # moss_min_z=0.5. A vertex normal cannot bleed: a vertex low on a
        # vertical flank keeps the stone colour even if the face above it is flat.
        for v in all_verts:
            if not v.link_faces:
                continue
            n = Vector((0.0, 0.0, 0.0))
            for f in v.link_faces:
                n += f.normal
            if n.length < 1e-9:
                continue
            if (n / len(v.link_faces)).normalized().z < moss_min_z:
                continue
            if rng.random() > moss_chance:
                continue
            vcol[v] = color_moss

    return made_faces


def flat_shade(faces):
    """Hard-shade every face. The arris IS the style -- smooth shading would
    round exactly the edge this recipe exists to produce."""
    for f in faces:
        f.smooth = False
