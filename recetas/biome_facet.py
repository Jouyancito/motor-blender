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


def _erode(tmp, radius, amount, scale, subdiv, seed):
    """Pit and pock the cut solid without dissolving its architecture.

    This is the half of the recipe that was written in the header and then not
    built: "cut for the architecture, then let noise ride on top at low
    amplitude". Joan's in-game Path of Exile reference is eroded limestone --
    irregular, pocked, full of small cavities -- not the crisp concept-art
    facets. The plane cuts give the angular masses; this gives them a surface.

    The noise is biased NEGATIVE so it carves pockets inward rather than
    inflating bumps outward: erosion removes material. Deterministic from `seed`,
    consumes no rng draws, so turning it on cannot reshuffle block placement.
    """
    if subdiv > 0:
        bmesh.ops.subdivide_edges(tmp, edges=tmp.edges[:], cuts=subdiv,
                                  use_grid_fill=True)
    tmp.normal_update()
    for v in tmp.verts:
        p = v.co * scale
        n = (math.sin(p.x * 1.7 + p.y * 2.3 + seed)
             * math.sin(p.y * 1.9 + p.z * 2.7 + seed * 0.7)
             * math.sin(p.z * 2.1 + p.x * 1.3 + seed * 1.3))
        v.co += v.normal * ((n - 0.35) * amount * radius)


def _convex_chunk(rng, radius, cuts, bedding, bedding_jitter, elongate, flatten,
                  erode=0.0, erode_scale=9.0, erode_subdiv=0, erode_seed=0.0):
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

    # Erosion runs AFTER normalisation (so its amplitude is a true fraction of
    # the block radius) and BEFORE the shape scaling (so a flattened slab gets
    # its pitting flattened with it, like real bedded stone).
    if erode > 0.0:
        _erode(tmp, radius, erode, erode_scale, erode_subdiv, erode_seed)

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
            off = Vector((math.cos(ang), math.sin(ang), 0.0)) * d * horiz
            rise = d * stack * rng.uniform(0.60, 1.0) + rng.uniform(-0.10, 0.30) * r
            if rise > 0.0:
                # SUPPORT POLYGON. A block resting on another has to keep its
                # centre of mass over the one below, or the pile is a thing that
                # cannot stand. Joan, looking at the first render beside a Path of
                # Exile screenshot: "hay uno de los modelados que dejaste que esta
                # apilado y eso con fisicas se caeria, no estaria bien".
                # Capped at HALF the supporting block's radius: enough lean to
                # look quarried, never enough to topple.
                limit = anchor_r * 0.5
                if off.length > limit:
                    off *= limit / off.length
            pos = anchor_c + Vector((off.x, off.y, rise))
        placed.append((pos, r))

        coords, faces = _convex_chunk(
            rng, r,
            cuts=spec.get("cuts", 9),
            bedding=spec.get("bedding", 0),
            bedding_jitter=spec.get("bedding_jitter", 0.10),
            elongate=spec.get("elongate", 1.0),
            flatten=spec.get("flatten", 1.0),
            erode=spec.get("erode", 0.0),
            erode_scale=spec.get("erode_scale", 9.0),
            erode_subdiv=spec.get("erode_subdiv", 1),
            erode_seed=float(i) * 3.7,
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

    pit_depth = spec.get("pit_depth", 0.0)
    pit_scale = spec.get("pit_scale", 14.0)

    for v in all_verts:
        # Crevice/base darkening. The references have deep darks low in the mass
        # and clear light on top; a flat tint is what made ours read as plaster.
        t = (v.co.z - z_lo) / z_span
        k = 1.0 - crevice_dark * (1.0 - t)
        if pit_depth > 0.0:
            # PITTING LIVES IN VALUE, NOT IN SILHOUETTE. The first attempt carved
            # the pocks as geometry, displacing along vertex normals after a
            # subdivision fan; at any amplitude big enough to see, it tore the
            # block into thin blades instead of pitting it. Canon _art_canon.md
            # §17 already says it: silhouette = geometry, surface = texture. At
            # gameplay distance the eroded limestone in the reference reads as
            # dark speckle, and dark speckle is what this is.
            p = v.co * pit_scale
            n = (math.sin(p.x * 1.7 + p.y * 2.3)
                 * math.sin(p.y * 1.9 + p.z * 2.7)
                 * math.sin(p.z * 2.1 + p.x * 1.3))
            k *= 1.0 - pit_depth * max(0.0, n)
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


def _envelope_radius(t, profile):
    """Half-width of the formation at height fraction t (0 base, 1 crown)."""
    if profile == "peak":
        return max(1.0 - t, 0.04) ** 0.85
    if profile == "ridge":
        return max(1.0 - t * 0.55, 0.04)
    if profile == "split":
        # Two shoulders with a notch: the silhouette dips in the middle band.
        return max((1.0 - t) * (1.0 + 0.35 * math.cos(t * math.pi * 2.0)), 0.04)
    return max(1.0 - t * t, 0.04) ** 0.5      # dome


def add_stone_aggregate(bm, vcol, center, spec, rng):
    """A rock FORMATION as many small stones packed into a silhouette.

    This is what the reference sheets actually are. Counted on
    `_references/rock_poe/rock_poe_mossy_stacked_set.png`: every formation is an
    aggregate of roughly 15-40 individual stones, not one faceted mass. That one
    fact answers three separate problems at once:

      * SURFACE — the "texture" of the formation IS the boundaries between
        stones. A single mass with big facets reads bare no matter how it is
        shaded, because the detail frequency lives in the packing, not in the
        material. This is why adding erosion noise to a 4-block mass failed
        twice: it was solving at the wrong scale.
      * MOSS EDGE — a stone is mossy or it is not. Painting WHOLE stones gives
        the hard boundary the references show, for free. Trying to get that edge
        inside one big face is what vertex colour cannot do.
      * PHYSICS — packed small stones rest on each other. Nothing balances.

    Cost is unchanged: ~30 stones at ~20 tris each is the same budget a handful
    of heavily-cut blocks already spent.

    spec keys:
      radius / height   formation half-width and height in metres
      profile           dome | peak | ridge | split
      stones            how many stones fill the envelope
      elongate          X stretch of the whole formation
      outliers          loose stones dropped around the foot
      stone_frac        stone radius as a fraction of formation radius
      color_rock / color_moss / moss_top_frac / moss_chance / tint_drift
      crevice_dark      darkening toward the base of the formation
    """
    R = spec["radius"]
    H = spec.get("height", R * 1.1)
    profile = spec.get("profile", "dome")
    n = spec.get("stones", 26)
    elongate = spec.get("elongate", 1.0)
    outliers = spec.get("outliers", 5)
    stone_frac = spec.get("stone_frac", 0.30)
    color_rock = spec.get("color_rock", (0.13, 0.12, 0.09))
    color_moss = spec.get("color_moss")
    moss_top_frac = spec.get("moss_top_frac", 0.55)
    moss_chance = spec.get("moss_chance", 0.7)
    tint_drift = spec.get("tint_drift", 0.16)
    crevice_dark = spec.get("crevice_dark", 0.55)
    cuts = spec.get("cuts", 7)

    origin = Vector(center)
    made_faces = []

    def place_stone(pos, stone_r, height_t, allow_moss):
        coords, faces = _convex_chunk(
            rng, stone_r, cuts=cuts, bedding=spec.get("bedding", 0),
            bedding_jitter=spec.get("bedding_jitter", 0.10),
            elongate=rng.uniform(0.85, 1.25), flatten=rng.uniform(0.72, 1.10),
        )
        verts = [bm.verts.new(pos + c) for c in coords]
        for idx in faces:
            try:
                f = bm.faces.new([verts[k] for k in idx])
            except ValueError:
                continue
            f.normal_update()
            made_faces.append(f)
        # ONE colour per stone. Per-stone tint drift is what gives the reference
        # sheets their liveliness -- neighbouring stones differ in value, and
        # that reads as surface without a single texel.
        mossy = (allow_moss and color_moss is not None
                 and height_t >= moss_top_frac and rng.random() < moss_chance)
        base = color_moss if mossy else color_rock
        drift = 1.0 + rng.uniform(-tint_drift, tint_drift)
        depth = 1.0 - crevice_dark * (1.0 - height_t)
        col = tuple(max(0.0, min(1.0, c * drift * depth)) for c in base)
        for v in verts:
            vcol[v] = col

    # ---- settle pass: decide every stone's resting height BEFORE building ----
    # The envelope only chooses WHERE in plan a stone goes. Its height is not
    # sampled, it is DERIVED: each stone drops until it rests on the ground or on
    # stones already placed. The first version sampled z from the envelope too and
    # produced stones hanging in mid air with nothing beneath them -- a hard fail
    # on the Naturalness Audit's floating-geometry item, and the same class of
    # error Joan caught on the block stack ("eso con fisicas se caeria").
    #
    # Resting height uses the same quantified adjacency as everything else: two
    # stones read as one mass when their centres sit at ADJACENCY x the sum of
    # their radii. Given the horizontal gap, that fixes the vertical drop exactly,
    # so stones interlock instead of leaving the gaps the loose version had.
    seats = []          # (Vector centre, radius, height_fraction)
    for _i in range(n):
        t = rng.random() ** 1.45
        env = _envelope_radius(t, profile)
        ang = rng.uniform(0.0, math.tau)
        rad = R * env * math.sqrt(rng.random())
        stone_r = R * stone_frac * (1.0 - 0.40 * t) * rng.uniform(0.78, 1.25)
        x = math.cos(ang) * rad * elongate
        y = math.sin(ang) * rad
        z = stone_r * 0.55          # resting on the ground, part-buried
        for pc, pr, _pt in seats:
            reach = ADJACENCY * (stone_r + pr)
            d = math.hypot(x - pc.x, y - pc.y)
            if d < reach:
                z = max(z, pc.z + math.sqrt(reach * reach - d * d))
        seats.append((Vector((x, y, z)), stone_r, t))

    # Height is an OUTCOME of the packing, so the formation is rescaled to honour
    # the spec — but UNIFORMLY, positions and stone radii together.
    #
    # Scaling Z alone was a bug with teeth: the settle above guarantees every
    # stone touches its supporter, and stretching only the vertical axis pulls
    # each stone off the one holding it up. Floating stones came back on the very
    # pass that was meant to have fixed them. A uniform scale preserves every
    # distance ratio, so contact survives by construction.
    top = max((c.z + r for c, r, _t in seats), default=1.0)
    k = min(1.6, max(0.6, H / max(top, 1e-6)))

    for c, stone_r, _t in seats:
        pos = origin + c * k
        # Moss follows where the stone ENDED UP, not where it was drawn.
        place_stone(pos, stone_r * k, min(1.0, (c.z * k) / max(H, 1e-6)),
                    allow_moss=True)

    for _i in range(outliers):
        # Loose stones at the foot. In the references these are what stop the
        # formation from having a hard contact line with the ground.
        ang = rng.uniform(0.0, math.tau)
        rad = R * rng.uniform(1.0, 1.55)
        pos = origin + Vector((
            math.cos(ang) * rad * elongate,
            math.sin(ang) * rad,
            R * stone_frac * rng.uniform(-0.25, 0.10),
        ))
        place_stone(pos, R * stone_frac * rng.uniform(0.35, 0.70), 0.0,
                    allow_moss=False)

    return made_faces


def flat_shade(faces):
    """Hard-shade every face. The arris IS the style -- smooth shading would
    round exactly the edge this recipe exists to produce."""
    for f in faces:
        f.smooth = False
