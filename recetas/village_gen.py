"""village_gen — biome x threat x scale living-village generator (v5).

v4 PASSED the wall ("realmente una muralla") but Joan's verdict was blunt:
"no es una aldea, es una barrera con cuatro bloques" — no doors, no windows,
no stairs, no internal elevation, houses interchangeable, zero settlement
LOGIC (layout was radius-random, not organized). This pass fixes all of that.

STRUCTURE is shared by all biomes (the algorithm below). STYLE is a dict per
biome (colors, stake density/jitter, roof pitch, tower material, vegetation,
+ NEW climate params: window size, porch frequency — see "climate reasoning"
below). Generator inputs are now THREE axes:

    BIOME (pradera|bosque|hielo)  x  THREAT (ground_beasts|flyers|night_predators)  x  SCALE (aldea|destacamento)

Reference canon: DungeonParty-A/game/docs/art/_references/
  bandit_camp/_synthesis.md      (pradera — Rivira x Axlin fusion; Axlin threat
                                   principle + concentric-defense source)
  village_bosque/_synthesis.md   (bosque — Irontown: dense spiked palisade, terraces)
  village_hielo/_synthesis.md    (hielo — Dawnstar structure + Irithyll mood)
  village_palisade/_synthesis.md, village_watchtower/_synthesis.md, rocks/_synthesis.md
  village_settlement_logic/_synthesis.md  (why commons cluster to the
                                   center and residential sits farther out;
                                   cross-checked medieval-European +
                                   West-African + American-Southeast sources;
                                   2026-07-20 addendum: market logic +
                                   foundation-by-wealth rule, see v10)
  village_lotr/_synthesis.md     (NEW 2026-07-20 — Old Mill Hobbiton
                                   stone/timber/thatch massing + market
                                   hanging-goods logic, see v10)
  village_casona/_synthesis.md   (NEW 2026-07-18 — the ONE central anchor
                                   building: Jorrvaskr/Dragonsreach massing,
                                   stone plinth + monumental stair + composite
                                   wing, see build_casona())
  village_roofs/_synthesis.md    (NEW 2026-07-18 — thatch/tile/snow-shingle
                                   roof identity + the "roof never floats"
                                   support-bracket rule, see build_roof())

## Casona + roofs-with-life pass (PO principle, 2026-07-18 v5 feedback)

Joan's v5 verdict: roofs were "uniform lifeless single-color prisms" and the
central building was just `house(dominant=True)` — a scaled-up copy of every
other hut. Fixed via `build_casona()` (composite stone-plinth+wood hall +
attached wing, replaces the old dominant-house path entirely) and
`build_roof()` (dispatches to `thatch_roof()`/`banded_roof()` per a per-biome
weighted `roof_kinds` pool instead of one flat `gable_roof()` call — see
village_roofs/_synthesis.md for the thatch/tile/shingle geometry techniques
and the mandatory support-bracket rule: an overhanging roof edge always gets
a visible corner brace, nothing floats).

## Module-internal coherence rule (PO addendum, 2026-07-18, live)

Every module must self-agree with real-world logic at its OWN scale — a
large module implies MORE of its contents, a small one fewer; a vocation
prop (forge, drying rack) never appears alone without its supporting detail
(an anvil needs visible fuel/ingots next to it, not just the anvil). This
rule governs any module touched in a given pass; it does not retroactively
force a rewrite of untouched modules. Applied this pass to `build_crafts_area`
(the herreria economy variant adds an ingot/fuel pile next to the anvil, see
ECONOMY_PROFILES below) — `build_livestock_pen`/`build_garden` already satisfy
it (pen size already implies a small animal count range, garden bed count
already matches its fixed row/col grid) and were left untouched.

## Economy/vocation axis (PO principle 5, 2026-07-18, live — 5th generator axis)

    BIOME x THREAT x SCALE x SEED (module rolls) x ECONOMY (vocation)

A village's livelihood shapes its structures/props/permanence independently
of biome or threat. `ECONOMY_PROFILES` is the schema (below, near
THREAT_PROFILES): `agricola` (default, current behavior, farming/mixed
village — zero visual change) is the only economy WIRED to affect generation
this pass beyond the schema itself; `herreria` (iron-working) is the one
extra economy IMPLEMENTED this pass (boosts `crafts_area` presence weight +
adds a fuel/ingot prop next to the anvil, per the coherence rule above) since
it was the cheapest real hook available without derailing the casona/roof
focus. `pieles` (hide/pelt), `nomada` (temporary hunting camp — NOTE: implies
LIMITED LIFETIME/relocation, relevant to the future WorldState canon in
`_village_expansion_canon.md` §4), and `costera` (fishing) are documented in
the schema but NOT implemented — future passes wire their prop_tag into the
relevant module builders the same way `herreria` does here. Full schema +
rationale duplicated in `game/docs/_village_expansion_canon.md` §11.

## Threat INTENSITY (PO addendum, 2026-07-18, live — threat axis extension)

A wall must be proportional to how dangerous the biome actually is, not
maximal by default — `THREAT_PROFILES` already answers WHAT is defended
against; `INTENSITY_PROFILES` (new) answers HOW MUCH. Three levels (calm /
wary / dangerous) scale wall height, stake density, ring coverage (a `calm`
village fences only part of its perimeter — "partial boundary marker," not a
full stockade), and gate heaviness (calm skips the reinforced double-gate
airlock for a single simple gate). `DEFAULT_INTENSITY_BY_BIOME` keeps every
biome at `wary` (today's existing behavior, zero default-render regression);
`calm` is CLI-reachable (5th... 7th positional arg, see Run below) and was
smoke-tested this pass but is not part of the 3-biome audit loop. Full
schema in `game/docs/_village_expansion_canon.md` §8.

## Climate-conditioned architecture (PO principle 2, 2026-07-18)

Sourced from vernacular-architecture research (warm-climate porches/overhangs
vs cold-climate compact insulated forms — see canon doc
`game/docs/_village_expansion_canon.md` §Research for the full citation list).
Baked into STYLES as `window_scale` (bigger openings read as an airier, less
insulated building) and `porch_chance` (open, semi-outdoor structures are a
warm-climate tell — verandas/porches let residents live half-outdoors; cold
climates protect every opening instead). Pradera also gets a `drying_rack`
prop (open-air food/hide preservation only makes sense without hard freezes).

## Axlin threat axis (PO principle 3 — Joan's favorite, "El bestiario de Axlin")

A village's defenses are conditioned by what actually hunts it, not just its
biome. `THREAT_PROFILES` is the schema (documented inline below); each biome
picks a sensible DEFAULT so the existing exact CLI invocation
(`village_gen.py -- <biome> <out> <seed>`) exercises a distinct profile per
biome for free, but any profile may be forced via CLI arg 4.

## Scale/role axis (PO principle 4)

`aldea` = the main settlement (bigger footprint, full functional zoning:
commons, residential, garden, livestock, crafts, well). `destacamento` = a
small outpost for scattering (2-3 structures + a wall fragment + a tower, no
functional zoning). Every `aldea` run ALSO builds one bonus `destacamento`
nearby (`DEST_OFFSET`) purely so a destacamento render is always produced for
audit — pass `scale=destacamento` explicitly to generate ONLY a standalone
outpost (the shape used for floor-scatter).

## Weighted module pools (PO live addendum, Joan — Minecraft-village-style)

Village CONTENT is no longer hardcoded always-on/off — it is a catalog of
optional modules, each with a spawn probability, rolled ONCE per village from
the seeded `rng` in a fixed order (deterministic per seed: same seed always
rolls the same module combo, different seeds/villages diverge). Rolling
answers "what exists"; the settlement-logic bands (commons/residential/wall)
answer "where it goes" — the two are decoupled on purpose, exactly like
Minecraft's structure-piece weighting vs. its terrain placement rules.

`MODULE_POOL[scale]` is a list of `{"name", "weight"}` (a plain probability,
`rng.random() < weight`) or `{"name", "count_weights"}` (a discrete weighted
distribution over how MANY instances to spawn, via `roll_weighted`). Schema:

    MODULE_POOL = {
      "aldea": [
        {"name": "well",           "weight": 0.90},
        {"name": "garden",         "weight": 0.60, "count_weights": {1: 0.6, 2: 0.4}},
        {"name": "livestock_pen",  "weight": 0.45},
        {"name": "crafts_area",    "weight": 0.30},
        {"name": "granary",        "weight": 0.25},
        {"name": "extra_house",    "count_weights": {0: 0.05, 1: 0.35, 2: 0.45, 3: 0.15}},
      ],
      "destacamento": [
        {"name": "bunk_hut",         "weight": 0.70},
        {"name": "third_structure",  "weight": 0.35},
      ],
    }

`central`/`hut_storage`/`hut_kitchen`/`hut_outhouse` (aldea) and
`dest_tent` (destacamento) stay OUTSIDE the pool — Joan mandated those
functional zones as non-negotiable identity in the 2026-07-18 round-1
feedback (`dungeon-party/village-gen-feedback`), before this pool existed.
The pool governs the NEW, genuinely-optional content this pass adds. Full
schema + rationale duplicated in `game/docs/_village_expansion_canon.md`
§Module pools so it survives outside this file's comments too.

## v8 — occlusion/discovery pass (PO verdict, 2026-07-19: "1-minute village")
v7 passed density/life-signal review but failed on a NEW axis: from the
gate, one fast glance revealed ~80% of the village (casona door visible
straight down the entry corridor, all huts readable in one pass — "podria
recorrerla en 1 min"). v8 fixes the missing axis, OCCLUSION/DISCOVERY, and
one real bug:
  1. STAIRS BUG — build_stairs() had its tread-height formula inverted
     (tallest step farthest from the door, not nearest); fixed.
  2. OCCLUSION LAYOUT — (a) build_double_gate() now bends: the interior
     gate jogs sideways off the exterior gate's straight radial line, with
     a baffle wall blocking the old sightline (see its docstring); (b)
     houses bias toward 2-3 angular "blocks" via find_clustered_spot() /
     make_cluster_centers(), some rotated 30-60 deg (house(facing_deg=...));
     (c) build_yard_fence() subdivides yards. A permanent "fastview" camera
     shot (just inside the exterior gate, mannequin eye height) audits this
     every render — see the Run section near the bottom of this file.
  3. EXTERIOR LIFE ACCESSORIES — build_loom/build_hide_rack/
     build_outdoor_kitchen/build_outdoor_seat/build_hanging_line, pool-rolled
     and scattered along the residential band (see MODULE_POOL) so walking
     the paths reveals them one at a time.
  4. ROOF SILHOUETTE — build_roof() now auto-rolls a small asymmetric ridge
     offset on every call (never a perfectly symmetric gable) and gains a
     'hip' kind (pyramid-ended, see gable_roof's ridge_inset); thatch ridges
     sag slightly; rafter tails poke past every eave; extra-house height
     jitter widened for a less uniform skyline.
  5. CASONA INTERIOR — wall shelves + jars, pots hanging over the hearth, a
     rug patch, stools, sacks/a barrel (build_casona()'s "RICHER INTERIOR"
     block) on top of the v7 table/hearth/beds.
  6. POSE VARIETY — build_sheep()/build_chicken() roll a per-animal pose
     (graze/alert/lying; normal/pecking). Real MOTION (walking, chewing,
     pecking animation) is GAME-SIDE (Godot) — this generator only varies
     the STATIC pose so a still render isn't N copies of one frozen animal.
  7. DENSITY + OVERLAP REJECTION — MODULE_POOL weights nudged up (~12-14
     structures target); PLACED_FOOTPRINTS/register_footprint()/
     spot_clear() reject a new structure too close to an existing one.

## v8.1 — calibration + "mood_valheim" lookdev layer (PO feedback, 2026-07-19)
Joan's v8 playtest: occlusion overcorrected (fastview went from "sees too
much" to a blank wall filling ~70% of frame), hanging lines read as power
cables (single taut strut, one fixed height, spread the whole village), and
the campfire/hearth were still a white placeholder cone. Fixed WITHOUT
touching any v5-v8 feature:
  1. ALLEY, NOT A WALL — build_double_gate()'s baffle now carries a lit
     torch + accent banner on its camera-facing side (see its docstring),
     and the fastview camera moved from 0.8m to 0.3m past the exterior
     threshold so more corridor depth reads before the baffle. Casona door
     stays hidden; the corridor now channels toward a warm focal point
     instead of blinding the viewer.
  2. HANGING LINES — build_hanging_line() now skips spans over 8m (item 2a),
     droops a catenary-approximating polyline (item 2b), varies attach
     height per span (item 2c), and clusters items near the sag point
     (item 2d) instead of one taut same-height line spanning the village.
  3. REAL CAMPFIRE — build_campfire_logs()/build_campfire_flames() (crossed
     firewood + orange-outer/yellow-inner flame wedges) replace the old
     single white cone at ALL THREE fires: the plaza campfire, the
     destacamento campfire (which also gained its first ember light), and
     the casona interior hearth (build_hearth()).
  4. LOOKDEV LAYER — a new, separate, importable module
     `lookdev/mood_valheim.py` (`apply_mood(scene, biome_style)`) adds a
     warm-key/cool-fill light hierarchy, procedural bump detail on the
     shared wood/stone/thatch materials, very-low-density atmosphere, and a
     compositor pass (glare/bloom + vignette + biome-derived color grade).
     Applied right before rendering, ON by default — pass a `mood` arg of
     "off"/"0"/"false"/"none" (8th positional CLI arg) to disable it. This
     module is intentionally generator-agnostic (it only reads a STYLES-
     shaped dict) so it can apply to any Blender scene, not just villages.

## v9 — texture / desire-paths / non-circular perimeter / decoration logic
## (PO feedback, 2026-07-19, from his own rendered-viewport screenshot)
Four items, none touching any prior feature:
  1. TEXTURE (the big one) — materials read as flat colored blocks with
     shadow-only shading. Fixed AT THE ALBEDO LEVEL (not just relief) via
     `lookdev/mood_valheim.py`'s new `_inject_albedo_variation()`: a
     no-UV Object-space Noise->ColorRamp chain mixes 2-3 tones into every
     wood/stone/thatch/tile-shingle/ground material's Base Color (thatch
     streaked directionally, wood plank-striped, stone/ground mottled/
     blotched — see that function's own docstring for the per-family
     tuning). Plus micro-dressing GEOMETRY in village_gen.py: stray leaf
     flecks scattered across every roof (build_roof), small alpha cobweb
     fans in the concave wall/eave corners (build_cobweb, ~28% chance per
     corner), and overlapping thatch bunch rows along the eave edge
     (thatch_roof's new "EAVE BUNCH ROWS" block).
  2. DESIRE PATHS — build_path() was a dead-straight lerp; real wear paths
     curve organically and route around obstacles. Now samples a
     Catmull-Rom spline through 1-2 seeded-noise-offset control points
     (`_desire_path_curve`) that also get pushed clear of any already-
     placed structure footprint (reusing PLACED_FOOTPRINTS) — see
     `_catmull_rom`/`_desire_path_curve`.
  3. NON-CIRCULAR PERIMETER — the wall was always a perfect circle. A new
     `ring_radius(angle)` (2 seeded harmonics, ANCHORED so it returns
     exactly RING_R at GATE_ANG — see the "Build" section comment for why
     that anchor matters) deforms the palisade into an elongated/irregular
     silhouette per seed; `build_palisade`/`build_torches`/
     `build_vegetation` all follow it. ~55% of seeds also roll a CLIFF ARC
     (`HAS_CLIFF`/`CLIFF_ARC`): a jagged stacked-boulder rock face
     (`build_cliff_wall`) stands in for the palisade along that stretch —
     Rivira-style, the outcrop itself IS the wall there.
  4. DECORATION PLACEMENT LOGIC — hanging lines could cross a path at
     head height. `build_interior` now builds PATHS BEFORE hanging
     decorations (order swap) so `hangline_path_conflict()` can test each
     candidate span's straight-line crossing against every path polyline;
     a span whose sagged height at the crossing point would dip below
     ~2.05m clearance is skipped in favor of the next-nearest neighbor.

## v10 — foundation-by-wealth / multi-break roofs / market / goats / light
## density (Joan's 5-reference drop, 2026-07-20 — village_settlement_logic
## addendum + village_lotr synthesis, both freshly researched this pass)
Five items, none touching prior features:
  1. FOUNDATION BY WEALTH — Joan's critique ("es medio raro encontrar
     cimiento de cemento en una aldea tan chica") on the OLD `stone_base`
     block in house(): a monolithic stone slab read as poured cement even
     on the smallest hut. `build_poor_footing()` replaces it with a ring of
     loose uncut fieldstones (make_rock()'s per-rock bmesh/noise variation,
     already proven on hearth-stones/cliff-wall) at every site that used to
     get the old slab — the casona's own `stone_casona` cut-stone plinth
     (build_casona) is UNTOUCHED, it's the one building that's SUPPOSED to
     read as wealth.
  2. MULTI-BREAK ROOFS — `build_house_annex()` (new) attaches a smaller
     volume with its OWN lower-ridge roof on the -X side of a hut, auto-
     rolled (~45%) for footprints big enough to justify it, mirroring
     build_casona()'s existing wing at hut scale. Skipped on raised/
     terrace variants (their elevated base_z doesn't support an unsupported
     annex box without a new floating-geometry bug).
  3. MARKET MODULE — `build_market()`/`build_market_stall()` (new): 2-3
     stalls near the commons hub, each a 4-post frame + DISTINCT-colored
     cloth awning + a barrel/basket/sack goods cluster. Pool-rolled
     (MODULE_POOL "market"), re-weighted UP for economy agricola/costera,
     forced to ZERO for intensity=dangerous (Axlin: high threat = no
     standing commerce, only rare peddlers) — same re-roll pattern
     crafts_area already uses for its economy hook.
  4. GOAT COHERENCE — `build_goat()` (new) reuses build_sheep()'s exact
     silhouette grammar (wool/hide mass + head + legs + tail) with
     goat-specific cues (small horns, straighter/leaner body, no wool
     poof). build_livestock_pen rolls goat vs sheep per-animal: 65% goat
     for economy=pieles (Axlin's bestiary text names goat wool
     specifically), a modest 15% sprinkle otherwise — sheep stays the
     default, this is an alternate roll, not a replacement.
  5. LIGHT DENSITY — window_glass_material()'s warm-window probability
     raised 0.7->0.85 (DanMachi 18F reference: population reads through
     window-glow DENSITY, independent of structure count). One constant,
     no new geometry.

## v10 PO live addendum (cheap extras, 2026-07-20, don't derail items 1-5)
  6. CEMETERY MODULE — `build_cemetery()`/`build_grave_marker()` (new): a
     small fenced-off graveyard corner near the wall (same unbiased-search
     placement as the outhouse), 3-6 wood-cross or stone-slab markers with
     palisade-stake-style lean/height jitter. LOW MODULE_POOL weight
     (0.22) — this is atmosphere, not a functional zone.
  7. ERA/TECH COHERENCE RULE (general principle, applies going forward):
     decoration/props must match the settlement's implied tech level —
     nothing modern/21st-century on medieval-reading huts. See the rule
     block right before "Market" above — confirmed no drift introduced by
     any v10 item (market stalls stay wood/cloth/rope, no metal-modern
     look).

Run (headless):
  blender -b --python village_gen.py -- <pradera|bosque|hielo> <out_dir> [seed] [threat] [scale] [economy] [intensity] [mood]
  (mood defaults to "on"; pass "off" as the 8th arg to render without the
  lookdev layer, e.g. for a fast geometry-only iteration pass)
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, noise

args = sys.argv[sys.argv.index("--") + 1:]
BIOME = args[0]
OUT_DIR = args[1]
SEED = int(args[2]) if len(args) > 2 else 7
os.makedirs(OUT_DIR, exist_ok=True)
rng = random.Random(SEED)

MOOD_ARG = args[7] if len(args) > 7 else "on"
MOOD_ON = MOOD_ARG.strip().lower() not in ("off", "0", "false", "none")
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lookdev"))

MANNEQUIN_H = 1.80  # proportion ground truth — every door/window is checked against this

# ── STYLE layer (BIOME) ─────────────────────────────────────────────────────
# wood_dark retuned 2026-07-18 from real references (Fort Harrod / Castrum
# Vechtense — see village_palisade/_synthesis.md). window_scale/porch_chance
# NEW this pass — climate-conditioned architecture, see module docstring.
STYLES = {
    "pradera": {  # bandit camp — Rivira x Axlin: uneven logs, high jitter, warm day
        "ground": (0.22, 0.31, 0.17), "ground_var": (0.31, 0.39, 0.23),
        "wood": (0.36, 0.26, 0.16), "wood_dark": (0.40, 0.29, 0.17),
        "roof": (0.30, 0.22, 0.13), "accent": (0.55, 0.12, 0.10),  # tattered banner red
        "stake_count": 44, "stake_r": 0.28, "stake_h": 3.2, "jitter": 1.0,
        "palisade_touching": True,
        "ring_coverage": 1.0, "roof_pitch": 0.8, "snow": False,
        "tower_stone": False, "trees": "rocks", "terraces": 1,
        "sun_energy": 2.6, "sun_color": (1.0, 0.93, 0.78), "sun_elev": 48,
        "sky": (0.55, 0.65, 0.75), "fog": None,
        # climate (warm, open-air lifestyle): big windows, most houses porched,
        # drying racks for hide/food preservation in open air.
        "window_scale": 1.15, "porch_chance": 0.55, "drying_rack": True,
        "stone_base_chance": 0.15,
        # roof material variety (village_roofs/_synthesis.md) — thatch is the
        # common hut roof, tile is the "civilized" roof reserved for casona.
        # "hip" added v8 item 4 (roof silhouette variety) — small share so
        # thatch/tile stay the dominant reads, hip just breaks monotony.
        "roof_kinds": {"thatch": 0.55, "tile": 0.30, "hip": 0.18}, "casona_roof_kind": "tile",
    },
    "bosque": {  # Irontown: DENSE thin spiked stakes, dark wood, mist, terraces
        "ground": (0.13, 0.19, 0.11), "ground_var": (0.20, 0.27, 0.15),
        "wood": (0.22, 0.16, 0.11), "wood_dark": (0.22, 0.18, 0.14),
        "roof": (0.16, 0.12, 0.09), "accent": (0.29, 0.48, 0.24),
        "stake_count": 90, "stake_r": 0.15, "stake_h": 3.6, "jitter": 0.35,
        "palisade_touching": True,
        "ring_coverage": 1.0, "roof_pitch": 1.0, "snow": False,
        "tower_stone": False, "trees": "pines", "terraces": 2,
        "sun_energy": 1.6, "sun_color": (0.85, 0.95, 0.82), "sun_elev": 35,
        "sky": (0.35, 0.45, 0.38), "fog": (0.55, 0.62, 0.55),
        # climate (cool humid forest, mid-range): moderate windows, some porches.
        "window_scale": 0.95, "porch_chance": 0.30, "drying_rack": False,
        "stone_base_chance": 0.30,
        # mostly dark shingle (Irontown wood roofs); occasional thatch hut.
        "roof_kinds": {"shingle": 0.68, "thatch": 0.18, "hip": 0.15}, "casona_roof_kind": "tile",
    },
    "hielo": {  # Dawnstar structure + Irithyll mood: longhouses, stone tower, night
        "ground": (0.82, 0.86, 0.92), "ground_var": (0.68, 0.74, 0.84),
        "wood": (0.20, 0.16, 0.13), "wood_dark": (0.17, 0.15, 0.14),
        "roof": (0.24, 0.19, 0.15), "accent": (0.55, 0.75, 0.95),
        "stake_count": 22, "stake_r": 0.14, "stake_h": 2.6, "jitter": 0.5,
        "ring_coverage": 0.55, "roof_pitch": 1.6, "snow": True,
        "tower_stone": True, "trees": "pines_snow", "terraces": 1,
        "sun_energy": 0.9, "sun_color": (0.62, 0.72, 0.95), "sun_elev": 22,
        "sky": (0.10, 0.13, 0.22), "fog": (0.16, 0.20, 0.30),
        # climate (cold, insulated, protected openings): SMALL windows, no
        # porches (nobody lounges half-outdoors in the cold), stone base common.
        # v11 item 27 (2026-07-20, OPEN QUESTION per Joan, not a firm
        # decision): nudged 0.65->0.70 as a MODEST signal toward more
        # stone/less exposed wood on hielo's common huts — do not push this
        # further without Joan explicitly confirming a bigger wood-vs-stone
        # swing for the snow biome first.
        "window_scale": 0.65, "porch_chance": 0.0, "drying_rack": False,
        "stone_base_chance": 0.70,
        # shingle base ALWAYS layered under the snow cap (never bare snow —
        # PO principle 4: visible plank/shingle understructure).
        "roof_kinds": {"shingle": 0.85, "hip": 0.15}, "casona_roof_kind": "shingle",
    },
}
S = STYLES[BIOME]
ROCK_TONES = [(0.52, 0.51, 0.46), (0.47, 0.47, 0.42), (0.58, 0.57, 0.50), (0.50, 0.53, 0.47)]

# ── THREAT axis (Axlin principle) — schema for future profiles ─────────────
# Each profile: wall_h_mult (defense height response), gate_reinforced (extra
# flanking spikes + thicker gateposts at the airlock), torch_ring (lit posts
# around the inner wall — night vigilance), covered_plaza (roofed commons —
# overhead threat cover). Add a new key here + branch in the 4 build sites
# below (build_double_gate, build_torches, build_interior's plaza) to extend.
THREAT_PROFILES = {
    "ground_beasts": {  # wolves/golems/slimes on foot — reinforce the gate + raise the wall
        "wall_h_mult": 1.15, "gate_reinforced": True, "torch_ring": False, "covered_plaza": False,
    },
    "flyers": {  # birds/hawks descending — cover the commons, wall height less relevant
        "wall_h_mult": 1.0, "gate_reinforced": False, "torch_ring": False, "covered_plaza": True,
    },
    "night_predators": {  # nocturnal hunters — light the perimeter, raise the wall a touch
        "wall_h_mult": 1.10, "gate_reinforced": False, "torch_ring": True, "covered_plaza": False,
    },
}
DEFAULT_THREAT_BY_BIOME = {"pradera": "ground_beasts", "bosque": "flyers", "hielo": "night_predators"}
THREAT_NAME = args[3] if len(args) > 3 else DEFAULT_THREAT_BY_BIOME[BIOME]
T = THREAT_PROFILES[THREAT_NAME]

# ── THREAT INTENSITY (PO addendum 2026-07-18) — HOW MUCH, on top of WHAT ───
# A calm prairie does not justify a 10m fortress wall. Scales wall height,
# stake density, ring coverage (calm fences only PART of the perimeter — a
# low boundary marker, not a stockade) and gate heaviness (calm = single
# simple gate, no reinforced double-gate airlock). `wary` reproduces today's
# existing numbers exactly (mult=1.0 everywhere) so default 3-arg runs are
# byte-identical to before this pass — see build section for the wiring.
INTENSITY_PROFILES = {
    "calm":      {"wall_h_mult": 0.50, "stake_count_mult": 0.40, "ring_coverage_mult": 0.55, "gate_heavy": False},
    "wary":      {"wall_h_mult": 1.00, "stake_count_mult": 1.00, "ring_coverage_mult": 1.00, "gate_heavy": True},
    "dangerous": {"wall_h_mult": 1.30, "stake_count_mult": 1.25, "ring_coverage_mult": 1.00, "gate_heavy": True},
}
DEFAULT_INTENSITY_BY_BIOME = {"pradera": "wary", "bosque": "wary", "hielo": "wary"}
INTENSITY_NAME = args[6] if len(args) > 6 else DEFAULT_INTENSITY_BY_BIOME[BIOME]
IN = INTENSITY_PROFILES[INTENSITY_NAME]

# ── ECONOMY / VOCATION axis (PO principle 5, 2026-07-18) — 5th generator
# input: BIOME x THREAT x SCALE x SEED x ECONOMY. Shapes structures/props/
# permanence by livelihood, independent of biome/threat. `agricola` is the
# implemented default (zero-op — matches all prior behavior). `herreria` is
# the one extra economy WIRED this pass (crafts_area presence weight boost +
# a fuel/ingot prop next to the anvil — module-internal coherence rule, see
# module docstring). `pieles`/`nomada`/`costera` are schema-only stubs for a
# future pass to wire the same way. `nomada`'s "temporary" permanence flag is
# a forward-looking note for the WorldState canon (a nomad camp should be
# able to relocate/vanish, unlike a permanent aldea) — NOT implemented here.
ECONOMY_PROFILES = {
    "agricola": {"crafts_weight_mult": 1.0, "prop_tag": None,         "permanence": "permanent"},
    "herreria": {"crafts_weight_mult": 1.8, "prop_tag": "metal",      "permanence": "permanent"},
    "pieles":   {"crafts_weight_mult": 1.0, "prop_tag": "hide",       "permanence": "permanent"},
    "nomada":   {"crafts_weight_mult": 0.6, "prop_tag": "hide_tent",  "permanence": "temporary"},
    "costera":  {"crafts_weight_mult": 1.0, "prop_tag": "nets_boats", "permanence": "permanent"},
}
DEFAULT_ECONOMY_BY_BIOME = {"pradera": "agricola", "bosque": "agricola", "hielo": "agricola"}
ECONOMY_NAME = args[5] if len(args) > 5 else DEFAULT_ECONOMY_BY_BIOME[BIOME]
EC = ECONOMY_PROFILES[ECONOMY_NAME]

# ── SCALE axis ───────────────────────────────────────────────────────────────
SCALE_PRESETS = {
    "aldea": {"ring_r": 26.0},
    "destacamento": {"ring_r": 9.0},
}
SCALE_NAME = args[4] if len(args) > 4 else "aldea"

# ── Weighted module pool (Minecraft-village-style) — see module docstring ──
## DENSITY BUMP (PO v7 item 2, 2026-07-19): ~12 structures target, up from
## ~5 — more houses in the residential band + the functional buildings,
## tighter clustering per settlement logic. `garden`/`livestock_pen` are now
## presence-only gates (weight, no count_weights) — their actual COUNT/SIZE
## is computed in build_interior() from the rolled house population
## (population coherence rule: more houses = more crop rows = more animals,
## not an independent dice roll). `coop` and `storage_shed` are new pool
## entries filling out the ~12-structure target with background population.
# DENSITY BUMP v8 (PO v8 item 7, 2026-07-19): the v7 pool averaged ~9-10
# structures (short of its own 12-14 target) — extra_house weights + the
# functional-building weights are nudged up here so the average lands in
# range. Also NEW: 5 exterior-life accessory entries (loom/hide_rack/
# outdoor_kitchen/extra_seating, "hanging_decor" is unconditional — see
# build_interior) for item 3 — distributed along paths, not clumped.
MODULE_POOL = {
    "aldea": [
        {"name": "well", "weight": 0.92},
        {"name": "garden", "weight": 0.75},
        {"name": "livestock_pen", "weight": 0.65},
        {"name": "coop", "weight": 0.60},
        {"name": "crafts_area", "weight": 0.45},
        {"name": "granary", "weight": 0.50},
        {"name": "storage_shed", "weight": 0.45},
        {"name": "extra_house", "count_weights": {2: 0.10, 3: 0.30, 4: 0.35, 5: 0.25}},
        {"name": "loom", "weight": 0.55},
        {"name": "hide_rack", "weight": 0.45},
        {"name": "outdoor_kitchen", "weight": 0.55},
        {"name": "extra_seating", "count_weights": {0: 0.15, 1: 0.35, 2: 0.35, 3: 0.15}},
        # MARKET (PO v10 item 3, 2026-07-20) — schema-only baseline here;
        # build_interior() re-weights this per ECONOMY/INTENSITY right
        # after the roll (see its own comment), same re-roll pattern
        # crafts_area already uses for its economy hook. Baseline favors
        # "no market" so a village without the economy/intensity boost
        # stays sparse-commerce by default.
        {"name": "market", "count_weights": {0: 0.60, 2: 0.28, 3: 0.12}},
        # CEMETERY (PO live addendum, 2026-07-20) — pure atmosphere, LOW
        # weight on purpose (this is mood dressing, not a functional zone
        # like well/garden/livestock).
        {"name": "cemetery", "weight": 0.22},
    ],
    "destacamento": [
        {"name": "bunk_hut", "weight": 0.70},
        {"name": "third_structure", "weight": 0.35},
    ],
}

def roll_bool(rng, weight):
    return rng.random() < weight

def roll_weighted(rng, count_weights):
    """Pick one key from a {value: probability} table via a single seeded
    roll. Probabilities need not be pre-normalized (divided by their sum)."""
    items = list(count_weights.items())
    total = sum(w for _, w in items)
    r = rng.random() * total
    acc = 0.0
    for key, w in items:
        acc += w
        if r <= acc:
            return key
    return items[-1][0]

def roll_module_pool(rng, scale_name):
    """Roll the full pool once, in FIXED catalog order (determinism per
    seed). Returns {module_name: True/False} or {module_name: count}.

    Entries with BOTH `weight` and `count_weights` (e.g. garden: 90% chance
    to exist AT ALL, then 1-2 count if it does) are TWO-STAGE: the presence
    gate rolls first, and the count only rolls if presence passed — round-2
    self-review caught a bug where `count_weights` silently pre-empted
    `weight`, making garden spawn 100% of the time instead of 60%. Entries
    with ONLY `count_weights` (extra_house) fold "doesn't exist" into the
    distribution itself via an explicit 0 bucket instead.
    """
    rolled = {}
    for entry in MODULE_POOL[scale_name]:
        name = entry["name"]
        if "weight" in entry and "count_weights" in entry:
            rolled[name] = roll_weighted(rng, entry["count_weights"]) if roll_bool(rng, entry["weight"]) else 0
        elif "count_weights" in entry:
            rolled[name] = roll_weighted(rng, entry["count_weights"])
        else:
            rolled[name] = roll_bool(rng, entry["weight"])
    return rolled

RING_R = SCALE_PRESETS[SCALE_NAME]["ring_r"]
DEST_RING_R = SCALE_PRESETS["destacamento"]["ring_r"]
DEST_ACTIVE = (SCALE_NAME == "aldea")  # bonus destacamento built alongside the main aldea
# SCENE SEPARATION (v11 item 28, 2026-07-20): the bonus destacamento used
# to sit only ~48m from the main aldea (RING_R + DEST_RING_R + 13.0) on the
# SAME shared terrain patch — close enough to read as an unexplained
# second settlement stapled onto the first, not a distinct location. Pushed
# out to a fixed ~170m offset (well inside Joan's 150-200m ask) with its
# OWN small separate terrain patch (see build_terrain's cx/cy/half params
# below) instead of extending the main terrain grid all the way out there
# — extending one shared 60x60 grid to cover a 170m gap would coarsen the
# main village's own terrain resolution as a side effect (the cheapest
# correct fix per the item's own framing: two small independent patches,
# not one giant coarse one).
DEST_CX, DEST_CY = (170.0, 0.0) if DEST_ACTIVE else (10_000.0, 10_000.0)
## Widened 1.0x -> 1.4x (PO v9 item 3, 2026-07-19): the non-circular
## perimeter's ring_radius() can bulge the wall out to ~1.35x RING_R on its
## widest side, and the cliff-wall rock stacks jitter a bit further out
## still — the terrain patch must cover the whole irregular silhouette, not
## just the old flat-circle radius, or the wall/cliff would hang off the
## edge of the flattened ground. No longer needs to reach DEST_CX (v11 item
## 28 — the destacamento gets its own separate patch now).
TERRAIN_HALF = RING_R * 1.4 + 4.0 + 8.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ── v12 pivot: REAL CC0 image textures (PolyHaven) ─────────────────────────
# Root cause (dungeon-party/village-gen-summary, 2026-07-20, Joan's verdict:
# "todo esta con colores solidos... son solo colores solidos"): 11 rounds of
# mood_valheim.py's procedural noise-based color/bump variation CANNOT
# reproduce real material structure — directional wood grain, stone joint
# lines, woven/laid straw — because generic noise has no knowledge of those
# patterns. Real materials need real photographed IMAGE textures. This adds
# that path alongside the existing procedural mat(): mat() now transparently
# ROUTES a handful of canonical material names — the ones used for the
# largest, most visually-dominant surfaces (ground, walls, dark structural
# wood/stakes/posts, thatch) — to a cached textured material instead of a
# flat color, with ZERO changes needed at any of the ~40 call sites already
# scattered across this file (mat("wood", ...) / mat("wood_dark", ...) /
# mat("ground", ...) / mat("roof_thatch", ...)) — the cheapest-correct fix
# per this file's own convention (see build_poor_footing's docstring for the
# same reasoning applied elsewhere). mood_valheim.py's procedural albedo/bump
# injection already no-ops on any material whose Base Color/Normal input is
# already linked (see its own idempotency checks in _add_bump/
# _add_albedo_noise) so it automatically backs off these textured materials
# with zero extra guard code here — textured and procedural layers coexist
# by construction on the SAME shared mat() cache, never double-applied.
TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_textures")

def _tex_path(slug, kind):
    """kind in {'diff', 'nor', 'rough'}. Returns None (safe no-op — NEVER a
    crash) if the file wasn't downloaded; mat_textured() falls back to a
    flat Base Color in that case so a missing texture degrades to the OLD
    flat-color look instead of an ugly grey/pink default-material placeholder."""
    for ext in (".jpg", ".png"):
        p = os.path.join(TEX_DIR, "%s_%s%s" % (slug, kind, ext))
        if os.path.exists(p):
            return p
    return None

_tex_img_cache = {}
def _load_tex_image(path, non_color=False):
    if path is None:
        return None
    key = (path, non_color)
    if key not in _tex_img_cache:
        img = bpy.data.images.load(path, check_existing=True)
        if non_color:
            try:
                img.colorspace_settings.name = 'Non-Color'
            except Exception:
                pass
        _tex_img_cache[key] = img
    return _tex_img_cache[key]

_tex_mats = {}
def mat_textured(key, slug, scale=2.0, projection='top', fallback_color=(0.45, 0.40, 0.32), rough_mult=1.0, tint=None):
    """Real image-texture Principled BSDF material (PolyHaven CC0 photo
    textures) — Geometry(Position, WORLD-space — same choice mood_valheim.py
    already proved for its own noise nodes, see _add_bump's docstring, so a
    shared material reads the same real-world grain size on a huge wall AND
    a tiny picket) -> Mapping (scale = tile size in meters) -> Image Texture
    -> Base Color (+ a Normal Map chain from the nor_gl map, + the Rough map
    on Roughness when present, both Non-Color). `projection`: 'top'
    (ground/roof-top: raw world X/Y drives U/V — correct for anything read
    mostly from above) or 'side' (walls/posts/stakes: the Mapping node's
    Rotation rotates world Z into the V slot so vertical grain/coursing
    reads correctly on upright surfaces — an Image Texture node only ever
    samples 2 of the 3 input vector components, so which 2 axes matters).
    Cached by (key, projection, scale, tint) — every call site sharing all
    four reuses one material, exactly like mat()'s own cache.

    `tint` (Judgment Day SUSPECT #2 fix, 2026-07-21): an (r,g,b) color —
    normally the caller's own jittered biome color (jitter_tone()'s output)
    — multiplied into the Base Color via a ColorMix node (MULTIPLY, subtle
    0.45 factor so the photo texture's own detail stays dominant) so that
    jitter_tone()'s per-house +/- tone jitter, which used to be dead code
    for any material routed here (the cache never varied by color, so every
    house shared one identical material), now has a real, if subtle, visual
    effect. Including `tint` in the cache key means two different jittered
    colors — or a deliberately darker/warmer tint like the thatch ridge
    cap's — genuinely produce two distinct materials instead of collapsing
    to one shared instance."""
    cache_key = (key, projection, scale, tint)
    if cache_key in _tex_mats:
        return _tex_mats[cache_key]
    m = bpy.data.materials.new("tex_%s_%s" % (key, projection))
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*fallback_color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9

    mapping = nt.nodes.new("ShaderNodeMapping")
    inv = 1.0 / max(0.001, scale)
    mapping.inputs["Scale"].default_value = (inv, inv, inv)
    if projection in ('side', 'side_local'):
        mapping.inputs["Rotation"].default_value = (math.radians(90.0), 0.0, 0.0)
    if projection == 'side_local':
        # DIAGONAL-STRUT FIX (v12 round-1 self-eyeball, destacamento render):
        # world-space Position badly SHEARS the texture on anything that
        # isn't roughly vertical (tower cross-braces, any strut()/oriented
        # cone rotated off-axis) — sampling raw world X/Z along a diagonal
        # member stretches the image unevenly across its length, since the
        # mapping has no idea the object itself is tilted. TexCoord.Object
        # (the object's OWN local space, unaffected by its world rotation)
        # fixes this for any UNSCALED primitive — cylinder()/strut()/
        # oriented_cone() bake their real-world size into the primitive call
        # itself (radius=r, depth=h) rather than via object.scale, so local
        # Z already IS the object's true-length axis regardless of which
        # way it's rotated in world space. Reserved for "wood_dark" (posts/
        # stakes/beams/braces — mat()'s routing below); "wood" (wall boxes,
        # which DO use object.scale to size) stays on world-space 'side' —
        # see _load_tex_image's caller for why (object-space on a SCALED
        # box re-introduces the exact same-frequency-different-sizes
        # mismatch mood_valheim's own bump pass already had to fix once).
        tex_coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        nt.links.new(geo.outputs["Position"], mapping.inputs["Vector"])

    diff_img = _load_tex_image(_tex_path(slug, "diff"), non_color=False)
    if diff_img is not None:
        tex_d = nt.nodes.new("ShaderNodeTexImage")
        tex_d.image = diff_img
        tex_d.extension = 'REPEAT'
        nt.links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])
        base_color_out = tex_d.outputs["Color"]
        if tint is not None:
            # Subtle MULTIPLY tint (see this function's own `tint` docstring
            # section) — same defensive by-socket-type lookup pattern
            # mood_valheim.py's compositor Mix nodes already use, since
            # ShaderNodeMix's RGBA sockets share a display name and can only
            # be told apart by iteration order / type.
            tint_mix = nt.nodes.new("ShaderNodeMix")
            tint_mix.data_type = 'RGBA'
            tint_mix.blend_type = 'MULTIPLY'
            a_sock = b_sock = factor_sock = result_sock = None
            for s in tint_mix.inputs:
                if s.type == 'RGBA' and a_sock is None:
                    a_sock = s
                elif s.type == 'RGBA' and b_sock is None:
                    b_sock = s
                elif s.type == 'VALUE' and s.name == 'Factor' and factor_sock is None:
                    factor_sock = s
            for o in tint_mix.outputs:
                if o.type == 'RGBA':
                    result_sock = o
                    break
            if a_sock is not None and b_sock is not None and result_sock is not None:
                if factor_sock is not None:
                    factor_sock.default_value = 0.45
                b_sock.default_value = (*tint, 1.0)
                nt.links.new(base_color_out, a_sock)
                base_color_out = result_sock
            else:
                print("[village_gen] mat_textured: Mix node RGBA sockets not found — skipping tint (%s)" % key)
        nt.links.new(base_color_out, bsdf.inputs["Base Color"])

    rough_img = _load_tex_image(_tex_path(slug, "rough"), non_color=True)
    if rough_img is not None:
        tex_r = nt.nodes.new("ShaderNodeTexImage")
        tex_r.image = rough_img
        tex_r.extension = 'REPEAT'
        nt.links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        if rough_mult != 1.0:
            rm = nt.nodes.new("ShaderNodeMath")
            rm.operation = 'MULTIPLY'
            rm.inputs[1].default_value = rough_mult
            nt.links.new(tex_r.outputs["Color"], rm.inputs[0])
            nt.links.new(rm.outputs["Value"], bsdf.inputs["Roughness"])
        else:
            nt.links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

    norm_img = _load_tex_image(_tex_path(slug, "nor"), non_color=True)
    if norm_img is not None:
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        tex_n.image = norm_img
        tex_n.extension = 'REPEAT'
        nrm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nt.links.new(tex_n.outputs["Color"], nrm.inputs["Color"])
        nt.links.new(nrm.outputs["Normal"], bsdf.inputs["Normal"])

    _tex_mats[cache_key] = m
    return m


# Per-biome texture picks (v12 PoE pivot) — hielo gets its OWN snow/stone
# set (snow_02 ground, rocky_trail path, cobblestone_02 plaza), never the
# pradera cobblestone_01/thatch verbatim (Joan: hielo needs a distinct cold
# read, not a recolored copy of the warm biome's materials).
GROUND_TEX_SLUG = {"pradera": "sparse_grass", "bosque": "sparse_grass", "hielo": "snow_02"}
PLAZA_TEX_SLUG = {"pradera": "cobblestone_01", "bosque": "cobblestone_01", "hielo": "cobblestone_02"}
PATH_TEX_SLUG = {"pradera": "brown_mud_dry", "bosque": "brown_mud_dry", "hielo": "rocky_trail"}
# WOOD/WOOD_DARK biome routing (Judgment Day SUSPECT #2 fix, 2026-07-21):
# same GROUND_TEX_SLUG pattern, so a future biome-specific plank/bark photo
# is a one-line dict edit, not a rearchitecture. All 3 biomes currently
# share the one downloaded slug per family (only brown_planks_03/
# bark_brown_01 exist in _textures/ today) — the ROUTING is biome-aware
# even though the VALUES aren't distinct yet; the per-house jitter_tone()
# tint (see mat_textured's `tint` param) is what makes wood visually
# distinct per house/biome in the meantime.
WOOD_TEX_SLUG = {"pradera": "brown_planks_03", "bosque": "brown_planks_03", "hielo": "brown_planks_03"}
WOOD_DARK_TEX_SLUG = {"pradera": "bark_brown_01", "bosque": "bark_brown_01", "hielo": "bark_brown_01"}

USE_REAL_TEXTURES = True  # flip off for a fast geometry-only iteration pass

_mats = {}
def mat(name, color, rough=0.85):
    # Judgment Day SUSPECT #2 fix (2026-07-21): every USE_REAL_TEXTURES
    # branch below now passes `tint=color` into mat_textured() (see its own
    # docstring) — `color` used to be silently dropped here, so
    # jitter_tone()'s per-house tone jitter was dead code for wood/thatch,
    # and wood was NOT biome-keyed (pradera/bosque/hielo shared one texture
    # verbatim, unlike ground/plaza/path's GROUND_TEX_SLUG-style routing).
    # "roof_thatch_dark" (the ridge cap) is checked BEFORE the generic
    # "roof_thatch" prefix match (it also starts with "roof_thatch") and
    # gets its OWN mat_textured `key` ("thatch_dark" vs "thatch") so the
    # cap no longer collapses onto the exact same shared material as the
    # base thatch — its ROOF_THATCH_DARK tint keeps it visibly
    # warmer/darker even under the shared photo texture.
    key = (name, color, rough)
    if key not in _mats:
        if USE_REAL_TEXTURES and name == "ground":
            # Out of scope for this fix — ground is already correctly
            # biome-keyed (GROUND_TEX_SLUG) and untouched by the mat()
            # color-drop bug this pass fixes for wood/wood_dark/thatch.
            _mats[key] = mat_textured("ground_" + BIOME, GROUND_TEX_SLUG[BIOME], scale=5.0, projection='top')
        elif USE_REAL_TEXTURES and name == "roof_thatch_dark":
            _mats[key] = mat_textured("thatch_dark", "thatch_roof_angled", scale=1.4, projection='top', tint=color)
        elif USE_REAL_TEXTURES and name.startswith("roof_thatch"):
            _mats[key] = mat_textured("thatch", "thatch_roof_angled", scale=1.4, projection='top', tint=color)
        elif USE_REAL_TEXTURES and name == "wood":
            _mats[key] = mat_textured("wood_" + BIOME, WOOD_TEX_SLUG[BIOME], scale=1.6, projection='side', tint=color)
        elif USE_REAL_TEXTURES and name == "wood_dark":
            _mats[key] = mat_textured("wood_dark_" + BIOME, WOOD_DARK_TEX_SLUG[BIOME], scale=1.0, projection='side_local', tint=color)
        else:
            m = bpy.data.materials.new(name)
            m.use_nodes = True
            bsdf = m.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            bsdf.inputs["Roughness"].default_value = rough
            _mats[key] = m
    return _mats[key]

def jitter_tone(rng, color, pct=0.07):
    """Per-object subtle tone jitter (PO v7 item 6): every house rolls its
    own +/-pct variant of the biome base wood/roof tone so no two houses
    share an identical hex, the same trick the terrain noise already uses.
    Relies on mat()'s cache key including the exact color tuple — a
    different jittered color always gets its own material automatically."""
    return tuple(max(0.0, min(1.0, c * (1.0 + rng.uniform(-pct, pct)))) for c in color)

_flame_mat = None
def flame_material():
    global _flame_mat
    if _flame_mat is None:
        m = bpy.data.materials.new("flame")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Emission Color"].default_value = (1.0, 0.45, 0.1, 1.0)
        b.inputs["Emission Strength"].default_value = 6.0
        _flame_mat = m
    return _flame_mat

_flame_inner_mat = None
def flame_inner_material():
    """Bright yellow inner-flame layer (PO v8.1 item 3, 2026-07-19) — paired
    with flame_material() (orange outer layer) to build a real two-tone fire
    instead of one flat-colored placeholder cone."""
    global _flame_inner_mat
    if _flame_inner_mat is None:
        m = bpy.data.materials.new("flame_inner")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Emission Color"].default_value = (1.0, 0.85, 0.35, 1.0)
        b.inputs["Emission Strength"].default_value = 11.0
        _flame_inner_mat = m
    return _flame_inner_mat

def link(obj):
    bpy.context.collection.objects.link(obj)
    return obj

def mesh_obj(name, verts, faces, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    return link(ob)

# ── Terrain (noise-displaced grid; height fn shared by all placement) ─────────
# Flattens TWO cores now: the main village (aldea or standalone destacamento)
# at the origin, and — only when a bonus destacamento is active — a second
# pad at DEST_OFFSET, so both settlements sit on buildable ground within one
# shared terrain mesh (avoids a second terrain patch / second camera rig).
def terrain_h(x, y):
    n = noise.noise(Vector((x * 0.045 + SEED, y * 0.045, 0.0)))
    h = n * 2.2
    d_main = math.hypot(x, y)
    flatten_main = RING_R * 0.5
    if d_main < flatten_main:
        h *= (d_main / flatten_main) ** 2
    elif DEST_ACTIVE:
        d_dest = math.hypot(x - DEST_CX, y - DEST_CY)
        flatten_dest = DEST_RING_R * 0.6
        if d_dest < flatten_dest:
            h *= (d_dest / flatten_dest) ** 2
    if BIOME == "bosque" and S["terraces"] > 1 and flatten_main < d_main < RING_R + 4.0:
        h += 0.9  # Irontown terraced rim band (main village only)
    return h

def build_terrain(cx=0.0, cy=0.0, half=None, res=60, name="terrain"):
    """cx/cy/half/name (v11 item 28) — generalized so the destacamento can
    get its OWN small terrain patch centered far away instead of forcing
    one shared grid to stretch across the whole gap (see TERRAIN_HALF's
    comment above)."""
    half = TERRAIN_HALF if half is None else half
    verts, faces = [], []
    for i in range(res + 1):
        for j in range(res + 1):
            x = cx - half + 2 * half * i / res
            y = cy - half + 2 * half * j / res
            verts.append((x, y, terrain_h(x, y)))
    for i in range(res):
        for j in range(res):
            a = i * (res + 1) + j
            faces.append((a, a + 1, a + res + 2, a + res + 1))
    return mesh_obj(name, verts, faces, mat("ground", S["ground"]))

# ── Primitive helpers ─────────────────────────────────────────────────────────
def cylinder(name, r, h, loc, material, verts_n=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts_n, radius=r, depth=h, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    return ob

def box(name, sx, sy, sz, loc, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (sx, sy, sz)
    ob.data.materials.append(material)
    return ob

def ellipsoid(name, sx, sy, sz, loc, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=1.0, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (sx, sy, sz)
    ob.data.materials.append(material)
    return ob

def strut(name, p1, p2, r, material, verts_n=6):
    """Thin cylinder spanning two arbitrary world points (rail/brace/ladder rung/torch arm)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    length = d.length
    mid = (p1 + p2) / 2
    ob = cylinder(name, r, length, tuple(mid), material, verts_n=verts_n)
    if length > 1e-6:
        ob.rotation_euler = d.normalized().to_track_quat('Z', 'Y').to_euler()
    return ob

def oriented_cone(name, r, h, base_pt, direction, material, verts_n=8):
    """Cone spanning from base_pt along an arbitrary 3D direction (length h).
    Uses the same to_track_quat trick as strut() — round-2 fix: the gate's
    reinforced spikes used a raw single-axis Euler rotation that ignored the
    gate's actual world orientation, producing a stray diagonal stick
    crossing the entrance in the render (caught eyeballing round 1)."""
    base_pt = Vector(base_pt)
    direction = Vector(direction).normalized()
    tip = base_pt + direction * h
    mid = (base_pt + tip) / 2
    bpy.ops.mesh.primitive_cone_add(vertices=verts_n, radius1=r, depth=h, location=tuple(mid))
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    ob.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    return ob

# ── Real campfire (PO v8.1 item 3, 2026-07-19) ─────────────────────────────
# Replaces the old single white placeholder cone (used identically by the
# plaza campfire, the destacamento campfire, AND the casona's interior
# hearth — see build_hearth()) with crossed firewood + 2-3 interlocking
# flame wedges (orange outer / yellow inner, both emissive) + an ember-glow
# point light helper. Shared so all three fires get the same upgrade instead
# of three divergent one-off cones.
def build_campfire_logs(name, cx, cy, base_z, rng, scale=1.0):
    """2-3 crossed log pieces at a campfire's base — real firewood instead
    of bare ground under the flame."""
    wood_mat = mat("campfire_log", (0.24, 0.16, 0.10), rough=0.9)
    n = rng.randint(2, 3)
    length = 0.6 * scale
    for i in range(n):
        ang = (i / n) * math.pi + rng.uniform(-0.2, 0.2)
        r = 0.045 * scale
        dx, dy = math.cos(ang) * length / 2, math.sin(ang) * length / 2
        z = base_z + 0.04 + i * 0.05
        strut("%s_log_%d" % (name, i), (cx + dx, cy + dy, z), (cx - dx, cy - dy, z), r, wood_mat, verts_n=6)

def build_campfire_flames(name, cx, cy, base_z, rng, scale=1.0):
    """Low-poly campfire flame core — 2-3 interlocking tapered wedges
    (thin 4-sided pyramids doubling as flame "shards"), an orange outer
    layer + a smaller/taller brighter-yellow inner layer nested inside each
    wedge, both emissive. Each wedge leans a different random direction so
    the cluster interlocks instead of reading as N identical cones."""
    outer = flame_material()
    inner = flame_inner_material()
    n = rng.randint(2, 3)
    for i in range(n):
        a = (i / n) * math.tau + rng.uniform(-0.35, 0.35)
        lean_x = math.cos(a) * rng.uniform(0.15, 0.35)
        lean_y = math.sin(a) * rng.uniform(0.15, 0.35)
        h = rng.uniform(0.42, 0.62) * scale
        r = rng.uniform(0.09, 0.15) * scale
        base = (cx + math.cos(a) * 0.07 * scale, cy + math.sin(a) * 0.07 * scale, base_z + 0.06)
        direction = (lean_x, lean_y, 1.0)
        oriented_cone("%s_wedge_%d" % (name, i), r, h, base, direction, outer, verts_n=4)
        oriented_cone("%s_wedge_inner_%d" % (name, i), r * 0.5, h * 0.8,
                       (base[0], base[1], base[2] + 0.03), direction, inner, verts_n=4)

def build_small_flame(name, cx, cy, base_z, rng, scale=1.0):
    """Small 2-wedge interlocking flame (v11 item 19, 2026-07-20) — every
    torch/brazier in the village used a single placeholder CONE (Joan:
    "reads oddly against its point light"), while the campfire/hearth
    already had the nicer orange-outer/yellow-inner interlocking-wedge
    treatment (build_campfire_flames). Reuses the exact same technique at
    torch scale (2 wedges instead of 2-3, smaller) so every lit point in
    the village reads consistently, not just the 3 big fires."""
    outer = flame_material()
    inner = flame_inner_material()
    for i in range(2):
        a = (i / 2) * math.tau + rng.uniform(-0.35, 0.35)
        lean_x = math.cos(a) * rng.uniform(0.12, 0.24) * scale
        lean_y = math.sin(a) * rng.uniform(0.12, 0.24) * scale
        h = rng.uniform(0.22, 0.32) * scale
        r = rng.uniform(0.07, 0.11) * scale
        direction = (lean_x, lean_y, 1.0)
        oriented_cone("%s_flame_%d" % (name, i), r, h, (cx, cy, base_z), direction, outer, verts_n=4)
        oriented_cone("%s_flame_inner_%d" % (name, i), r * 0.5, h * 0.75,
                       (cx, cy, base_z + 0.02), direction, inner, verts_n=4)

def build_ember_light(name, cx, cy, base_z, energy=250.0):
    """Warm ember-glow point light near a fire's base."""
    fl = bpy.data.lights.new(name + "_emberlight", 'POINT')
    fl.energy = energy
    fl.color = (1.0, 0.5, 0.18)
    flo = bpy.data.objects.new(name + "_emberlight", fl)
    flo.location = (cx, cy, base_z + 0.55)
    return link(flo)

# ── Micro-dressing: cobwebs (PO v9 item 1, 2026-07-19) ─────────────────────
_cobweb_mat = None
def cobweb_material():
    """Thin alpha-blend grey-white material for cobweb fans. Kept as one
    shared material (not per-object) since it's purely a translucency
    prop — no tone variation needed. `surface_render_method` is the
    Blender 5.x EEVEE Next transparency toggle (renamed from the old
    `blend_method`); both are tried defensively since a bare AttributeError
    here must never take down an otherwise-good render."""
    global _cobweb_mat
    if _cobweb_mat is None:
        m = bpy.data.materials.new("cobweb")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.90, 0.90, 0.87, 1.0)
        b.inputs["Roughness"].default_value = 0.55
        alpha_in = b.inputs.get("Alpha")
        if alpha_in is not None:
            alpha_in.default_value = 0.22
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            try:
                m.blend_method = 'BLEND'
            except Exception:
                pass
        _cobweb_mat = m
    return _cobweb_mat

def build_cobweb(name, corner, dir_a, dir_b, rng, scale=0.30):
    """Thin alpha triangle fan filling a CONCAVE corner (wall-top meeting
    the eave underside, fence post meeting a rail) — PO v9 item 1: 'small
    cobweb fans in corners'. `dir_a`/`dir_b` are the two (roughly unit)
    directions along the surfaces meeting at `corner`; the fan's strands
    radiate between them so it visually bridges the corner like a real web
    would, instead of floating in open air."""
    mat_cw = cobweb_material()
    n_outer = rng.randint(5, 7)
    cx, cy, cz = corner
    verts = [(cx, cy, cz)]
    for i in range(n_outer):
        f = i / (n_outer - 1)
        dx = dir_a[0] * (1 - f) + dir_b[0] * f
        dy = dir_a[1] * (1 - f) + dir_b[1] * f
        dz = dir_a[2] * (1 - f) + dir_b[2] * f
        r = scale * (1.0 + rng.uniform(-0.15, 0.15))
        verts.append((cx + dx * r, cy + dy * r, cz + dz * r))
    faces = [(0, i, i + 1) for i in range(1, n_outer)]
    return mesh_obj(name, verts, faces, mat_cw)

def make_rock(name, base_r, loc, rng, flatten=0.65, disp=0.18):
    """Unique low-poly boulder — see game/docs/art/_references/rocks/_synthesis.md."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=base_r)
    bm.normal_update()
    seed_off = Vector((rng.uniform(0, 200), rng.uniform(0, 200), rng.uniform(0, 200)))
    freq = rng.uniform(1.6, 2.6)
    strength = base_r * rng.uniform(0.12, disp)
    for v in bm.verts:
        n = noise.noise(v.co * freq + seed_off)
        v.co += v.normal * n * strength
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    tone = ROCK_TONES[rng.randrange(len(ROCK_TONES))]
    ob.data.materials.append(mat("rock_%.2f_%.2f_%.2f" % tone, tone))
    link(ob)
    ob.location = loc
    ob.scale = (rng.uniform(0.75, 1.3), rng.uniform(0.75, 1.3),
                flatten * rng.uniform(0.75, 1.25))
    ob.rotation_euler = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3),
                         rng.uniform(0, math.tau))
    return ob

_wood_knot_mat = None
def wood_knot_material():
    global _wood_knot_mat
    if _wood_knot_mat is None:
        _wood_knot_mat = mat("wood_knot_detail", (0.10, 0.07, 0.05), rough=0.9)
    return _wood_knot_mat

def add_wood_knot(name, pos, rng, r=0.05):
    """Small dark flattened-ellipse decal simulating a wood knot (v11 item
    14, HANDMADE-IMPERFECTION principle) — hugs the surface it's placed
    against, purely a silhouette/albedo detail, no structural meaning."""
    k = ellipsoid(name, r * rng.uniform(0.8, 1.2), r * rng.uniform(0.6, 1.0), r * 0.30,
                  pos, wood_knot_material())
    k.rotation_euler = (0, 0, rng.uniform(0, math.tau))
    return k

def add_moss_patch(name, pos, rng, r=0.09):
    """Small green/brown moss blob at a log base or shaded face (v11 item
    14, HANDMADE-IMPERFECTION principle)."""
    tone = (rng.uniform(0.16, 0.26), rng.uniform(0.28, 0.40), rng.uniform(0.13, 0.20))
    moss_mat = mat("moss_patch_%.2f_%.2f_%.2f" % tone, tone, rough=1.0)
    m = ellipsoid(name, r * rng.uniform(0.8, 1.3), r * rng.uniform(0.8, 1.3), r * 0.28, pos, moss_mat)
    m.rotation_euler = (0, 0, rng.uniform(0, math.tau))
    return m

def gable_roof(name, sx, sy, rise, loc, material, ridge_inset=0.0, ridge_y_frac=0.0):
    """`ridge_inset` (PO v8 item 4, ROOF SILHOUETTE): >0 shortens the ridge
    line so the end faces (0,4,3)/(1,5,2) become slanted HIP faces instead
    of flat vertical gable walls — a hip roof is just a gable roof whose
    ridge doesn't reach the corners. `ridge_y_frac` shifts the ridge off
    the Y centerline (asymmetric pitch — one slope steeper than the
    other). Both default to 0.0 = the original symmetric gable, so every
    existing call site (well/coop/granary/tower/plaza/shed roofs) is
    unaffected."""
    hx, hy = sx / 2, sy / 2
    rx = hx - ridge_inset
    ry = hy * ridge_y_frac
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0),
         (-rx, ry, rise), (rx, ry, rise)]
    f = [(0, 1, 5, 4), (3, 2, 5, 4), (0, 1, 2, 3), (0, 4, 3), (1, 5, 2)]
    ob = mesh_obj(name, v, f, material)
    ob.location = loc
    return ob

# ── Roofs with life (PO v5 feedback — see village_roofs/_synthesis.md) ─────
# Colors sampled off real references, not invented: thatch = warm grey-straw
# (thatch_roof_detail_closeup.jpg), tile = terracotta (tile_roof_toscana.jpg).
## COLOR CONTRAST NOTE (round-1 self-fix, 2026-07-18): the initial palette was
## sampled too literally off the reference photos and read as near-invisible
## against the wall tone once EEVEE's Filmic view transform desaturates it —
## the geometry (banding/layering) was correct but colors need to be pushed
## DARKER/more saturated than the wall to read at all (same "roof reads as a
## distinct darker cap" strategy the OLD flat roof used, kept here on top of
## the new banded/layered geometry instead of a flat single tone).
# Round-2 retune (orchestrator eyeball, seed 21): the grey-straw sample read
# as CONCRETE at overview distance — aged thatch needs the golden-brown end
# of the reference range to say "straw" at a glance.
# (Second push: the first retune (0.55,0.42,0.20) was still visually identical
# to the grey-straw under Filmic — per the contrast note above, the value must
# overshoot the photo sample hard to read as STRAW at overview distance.)
ROOF_THATCH = (0.66, 0.46, 0.12)
ROOF_THATCH_DARK = (0.44, 0.29, 0.08)   # ridge-cap band, warmer to match
ROOF_TILE = (0.58, 0.28, 0.16)
ROOF_TILE_DARK = (0.42, 0.18, 0.09)     # coursing shadow band, same ref

def mesh_obj_multi(name, verts, faces, face_mats, materials, loc=(0, 0, 0)):
    """Like mesh_obj() but supports a per-face material_index — used for
    roof coursing bands (tile/shingle) that alternate 2 tones per row
    (village_roofs/_synthesis.md: real roofs read as ROWS, never one flat
    color plane)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for m in materials:
        me.materials.append(m)
    for poly, mi in zip(me.polygons, face_mats):
        poly.material_index = mi
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    return link(ob)

def banded_roof(name, sx, sy, rise, loc, mat_a, mat_b, rows=4, ridge_y_frac=0.0):
    """Gable roof subdivided into `rows` horizontal coursing bands per slope,
    alternating mat_a/mat_b — the cheap low-poly trick for 'tile' (terracotta
    rows) and 'shingle' (dark wood rows): real roofs show clear banding, not
    a single flat color (PO 2026-07-18: 'tiles = subtle row steps or color
    banding'). Face layout mirrors gable_roof()'s winding exactly, just
    subdivided along the slope instead of one quad per side.

    `ridge_y_frac` (PO v8 item 4, ASYMMETRIC PITCH): shifts the ridge off
    the Y centerline so the front/back slopes are unequal length (one
    reads steeper than the other) — 0.0 = symmetric, matches v7 exactly."""
    hx, hy = sx / 2, sy / 2
    ry = hy * ridge_y_frac
    verts, faces, fmats = [], [], []

    def add_row(y_a, y_b, z_a, z_b, mat_i):
        base = len(verts)
        verts.extend([(-hx, y_a, z_a), (hx, y_a, z_a), (hx, y_b, z_b), (-hx, y_b, z_b)])
        faces.append((base, base + 1, base + 2, base + 3))
        fmats.append(mat_i)

    for i in range(rows):  # front slope: eave (y=-hy) -> ridge (y=ry)
        y_a = -hy + (ry - (-hy)) * i / rows
        y_b = -hy + (ry - (-hy)) * (i + 1) / rows
        z_a, z_b = rise * i / rows, rise * (i + 1) / rows
        add_row(y_a, y_b, z_a, z_b, i % 2)
    for i in range(rows):  # back slope: eave (y=hy) -> ridge (y=ry)
        y_a = hy - (hy - ry) * i / rows
        y_b = hy - (hy - ry) * (i + 1) / rows
        z_a, z_b = rise * i / rows, rise * (i + 1) / rows
        add_row(y_a, y_b, z_a, z_b, i % 2)
    for hx_sign in (-1, 1):  # gable end triangles (flat, mat index 0)
        base = len(verts)
        verts.extend([(hx_sign * hx, -hy, 0), (hx_sign * hx, ry, rise), (hx_sign * hx, hy, 0)])
        faces.append((base, base + 1, base + 2))
        fmats.append(0)
    base = len(verts)  # underside (watertightness, matches original gable_roof)
    verts.extend([(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0)])
    faces.append((base, base + 1, base + 2, base + 3))
    fmats.append(0)

    return mesh_obj_multi(name, verts, faces, fmats, [mat_a, mat_b], loc)

def thatch_roof(name, sx, sy, rise, loc, rng, ridge_y_frac=0.0):
    """Individual overlapping thatch BUNDLES laid in rows (v11 item 16,
    2026-07-20 — a real geometry change, not a color tweak). The prior
    version stacked 3 smooth layered gable PLANES — from any distance that
    reads as 3 clean banded prisms, not straw. Now: a thin solid gable base
    (silhouette/watertightness only, hidden under the bundles) is covered
    by rows of small flattened-ellipsoid loaf/wedge shapes running eave to
    ridge on both slopes, staggered row-to-row like real laid courses, each
    bundle jittered in size/position/tilt — plus a few thin binding-cord
    cylinders per slope "tying bundles down" (village_roofs reference: real
    thatch is bound to the roof structure with cord at intervals, not just
    piled on). Ridge cap keeps its v8 sag treatment.

    RIDGE SAG (PO v8 item 4): real thatch ridges droop slightly between
    their end supports — the cap is 3 segments, the middle one dipped a
    few cm, instead of a perfectly straight line (which read as a man-made
    plank, not straw)."""
    x, y, z = loc
    thatch_mat = mat("roof_thatch", ROOF_THATCH, rough=0.95)
    cap_mat = mat("roof_thatch_dark", ROOF_THATCH_DARK, rough=0.95)
    cord_mat = mat("thatch_cord", (0.28, 0.22, 0.13), rough=0.85)
    hx, hy = sx / 2, sy / 2
    ry = hy * ridge_y_frac

    # Thin solid base — keeps the roof watertight/silhouette-correct even
    # though the bundle rows above don't perfectly tile every gap.
    gable_roof(name + "_base", sx * 0.98, sy * 0.98, rise * 0.97, (x, y, z), thatch_mat,
               ridge_y_frac=ridge_y_frac)

    n_rows = max(3, int(rise / 0.20))
    for side_sign in (-1, 1):  # front (-Y) / back (+Y) slope
        eave_y = -hy if side_sign == -1 else hy
        ridge_y = ry
        slope_run = ridge_y - eave_y
        slope_len = math.hypot(slope_run, rise)
        slope_tilt = math.atan2(rise, abs(slope_run)) * (-side_sign)
        n_bunches = max(4, int(sx / 0.55))
        bunch_w = sx / n_bunches
        for row in range(n_rows):
            f = (row + 0.5) / n_rows  # 0 near eave, ~1 near ridge
            row_y = eave_y + slope_run * f
            row_z = rise * f
            row_offset = (bunch_w * 0.5) if (row % 2) else 0.0  # stagger like laid courses
            for bi in range(n_bunches + 1):
                bx = x - hx + (bi + 0.5) * bunch_w + row_offset
                if bx < x - hx - 0.05 or bx > x + hx + 0.05:
                    continue
                by = y + row_y + rng.uniform(-0.03, 0.03)
                bz = z + row_z + 0.02 + rng.uniform(-0.015, 0.02)
                bw = bunch_w * rng.uniform(0.95, 1.20)
                bl = (slope_len / n_rows) * rng.uniform(1.25, 1.55)  # overlaps the row below
                bh = rng.uniform(0.075, 0.115)
                bundle = ellipsoid("%s_bundle_%d_%d_%d" % (name, side_sign, row, bi),
                                    bw * 0.5, bl * 0.5, bh, (bx, by, bz), thatch_mat)
                bundle.rotation_euler = (slope_tilt + rng.uniform(-0.06, 0.06), 0,
                                          rng.uniform(-0.05, 0.05))
        # BINDING CORDS — thin horizontal cylinders spanning the slope
        # width at a few intervals, "tying the bundles down".
        n_cords = max(2, n_rows // 2)
        for ci in range(n_cords):
            f = (ci + 1) / (n_cords + 1)
            cord_y = y + eave_y + slope_run * f
            cord_z = z + rise * f + 0.055
            strut("%s_cord_%d_%d" % (name, side_sign, ci), (x - hx, cord_y, cord_z),
                  (x + hx, cord_y, cord_z), 0.014, cord_mat, verts_n=4)

    # BUG FIX (v7, PO orbit-report "tabla cruzada fea"): this box's sx/sy
    # args were SWAPPED — gable_roof()'s ridge line runs along X (see its
    # verts), so the cap must be LONG in X (matches sx) and THIN in Y
    # (perpendicular straddle of the ridge).
    cap_h = max(0.06, rise * 0.14)
    sag = min(0.05, cap_h * 0.6)
    seg_sx = sx * 1.08 / 3
    for si, dz in enumerate((0.0, -sag, 0.0)):  # 3 segments, middle one droops
        seg_x = x + (si - 1) * seg_sx
        box(name + "_ridge_cap_%d" % si, seg_sx * 1.04, sy * 0.16, cap_h,
            (seg_x, y + ry, z + rise * 0.94 + dz), cap_mat)

def add_eave_irregularity(name, sx, sy, rise, loc, ridge_y_frac, tone_mat, rng):
    """Slight silhouette irregularity for the non-thatch roof kinds (v11
    item 15, 2026-07-20 — broader than the thatch rework: even tile/
    shingle should show a bit of the same handmade-imperfection principle).
    A handful of small displaced tile/shingle chips along both eave lines
    reads as an uneven eave line instead of one perfectly straight edge —
    cheap, doesn't touch the underlying banded_roof geometry."""
    x, y, z = loc
    hx, hy = sx / 2, sy / 2
    ry = hy * ridge_y_frac
    n_chips = max(3, int(sx / 0.9))
    for side_sign in (-1, 1):
        eave_y = -hy if side_sign == -1 else hy
        for ci in range(n_chips):
            f = (ci + 0.5) / n_chips
            cx_ = x - hx + f * sx
            cy_ = y + eave_y + rng.uniform(-0.05, 0.10) * side_sign
            cz_ = z + rng.uniform(-0.02, 0.03)
            chip = box("%s_eavechip_%d_%d" % (name, side_sign, ci), sx / n_chips * 0.55, 0.10,
                       rng.uniform(0.03, 0.06), (cx_, cy_, cz_), tone_mat)
            chip.rotation_euler = (rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0.0)

def build_roof(name, sx, sy, rise, loc, style, kind, rng, snow=None, ridge_y_frac=None):
    """Dispatcher — ALWAYS call this instead of a raw gable_roof() for a
    house/casona roof. kind in {'thatch','tile','shingle','hip'}. snow=None
    uses style['snow']; the snow cap always layers ON TOP of the base kind
    (never replaces it — hielo houses keep a visible shingle understructure
    peeking at the eaves, per PO principle 4). Also adds 4 corner support
    struts under the roof's overhang (village_roofs/_synthesis.md:
    rdr2_colter_loading.jpg's exposed knee-brace — nothing floats).

    ROOF SILHOUETTE OVERHAUL (PO v8 item 4, 2026-07-19): v7's roofs "read
    square" — every house was a plain symmetric gable. Two changes fix this
    UNIVERSALLY (every build_roof call, no per-caller opt-in needed):
    (1) `ridge_y_frac=None` auto-rolls a small asymmetric ridge offset
    (+-0.16) so front/back pitches are never perfectly equal — pass 0.0
    explicitly to force a symmetric ridge (unused today, kept as an
    escape hatch). (2) a new 'hip' kind (pyramid-ended silhouette, no
    vertical gable wall) joins the existing thatch/tile/shingle pool —
    see STYLES[...]['roof_kinds']. Rafter tails (exposed dowel stubs past
    the eave line) are added below for every kind, not just hip/tile."""
    snow = style["snow"] if snow is None else snow
    if ridge_y_frac is None:
        ridge_y_frac = rng.uniform(-0.16, 0.16)
    x, y, z = loc
    hx, hy = sx / 2, sy / 2
    if kind == "thatch":
        thatch_roof(name, sx, sy, rise, loc, rng, ridge_y_frac=ridge_y_frac)
    elif kind == "tile":
        m_a = mat("roof_tile", ROOF_TILE, rough=0.55)
        m_b = mat("roof_tile_dark", ROOF_TILE_DARK, rough=0.55)
        banded_roof(name + "_tile", sx * 1.10, sy * 1.10, rise, loc, m_a, m_b, rows=4,
                    ridge_y_frac=ridge_y_frac)
        add_eave_irregularity(name + "_tile", sx * 1.10, sy * 1.10, rise, loc, ridge_y_frac, m_a, rng)
    elif kind == "hip":
        # Hip roof (PO v8 item 4) — all 4 eaves slope down, no vertical
        # gable end; rounder, more "cottage" silhouette against the sharp
        # gable peaks elsewhere in the same village.
        gable_roof(name + "_hip", sx * 1.10, sy * 1.10, rise, loc, mat("roof", style["roof"]),
                   ridge_inset=hx * 0.55, ridge_y_frac=ridge_y_frac * 0.4)
    else:  # shingle — biome-toned dark wood, banded
        base = style["roof"]
        light = tuple(min(1.0, c * 1.65 + 0.05) for c in base)
        dark = tuple(c * 0.75 for c in base)
        m_a = mat("roof_shingle_light_%.2f_%.2f_%.2f" % light, light, rough=0.8)
        m_b = mat("roof_shingle_dark_%.2f_%.2f_%.2f" % dark, dark, rough=0.8)
        banded_roof(name + "_shingle", sx * 1.10, sy * 1.10, rise, loc, m_a, m_b, rows=5,
                    ridge_y_frac=ridge_y_frac)
        add_eave_irregularity(name + "_shingle", sx * 1.10, sy * 1.10, rise, loc, ridge_y_frac, m_b, rng)
    if snow:
        gable_roof(name + "_snow", sx * 1.14, sy * 1.14, rise * 1.02,
                   (x, y, z + 0.08), mat("snow", (0.92, 0.94, 0.97), rough=0.6),
                   ridge_inset=(hx * 0.55 if kind == "hip" else 0.0), ridge_y_frac=ridge_y_frac)
    # Round-2 tune (self-eyeball): 0.032 radius braces were invisible at
    # render distance — thickened + lengthened so the "roof doesn't float"
    # detail actually READS, not just exists in the mesh data.
    wood_dark = mat("wood_dark", style["wood_dark"])
    brace_h = rise * 0.30
    for xs in (-1, 1):
        for ys in (-1, 1):
            wall_pt = (x + xs * hx * 0.90, y + ys * hy * 0.90, z)
            roof_pt = (x + xs * hx * 0.90, y + ys * hy * 0.50, z + brace_h)
            strut(name + "_brace_%d_%d" % (xs, ys), wall_pt, roof_pt, 0.055, wood_dark, verts_n=5)
            # HANDMADE-IMPERFECTION (v11 item 14) — occasional knot on a
            # roof structural member.
            if rng.random() < 0.20:
                add_wood_knot(name + "_brace_knot_%d_%d" % (xs, ys),
                              ((wall_pt[0] + roof_pt[0]) / 2, (wall_pt[1] + roof_pt[1]) / 2,
                               (wall_pt[2] + roof_pt[2]) / 2), rng, r=0.045)
            # COBWEB (PO v9 item 1 micro-dressing) — the concave corner
            # right under the eave, where a wall meets the roof overhang,
            # is exactly where a real cobweb collects; ~28% chance per
            # corner so not every roof is festooned.
            if rng.random() < 0.28:
                dir_a = (0.0, -ys, 0.65)   # up along the eave underside
                dir_b = (-xs, 0.0, 0.65)   # up along the wall corner
                build_cobweb(name + "_web_%d_%d" % (xs, ys), wall_pt, dir_a, dir_b, rng)
    # RAFTER TAILS (PO v8 item 4) — small exposed dowel ends poking past the
    # front/back eave lines, cheap silhouette break so the eave doesn't read
    # as one clean straight edge (village_roofs references: exposed rafter
    # tails under the overhang, distinct from the corner knee-braces above).
    n_tails = 4
    for sign in (-1, 1):
        for i in range(n_tails):
            f = (i + 0.5) / n_tails - 0.5
            tx = x + f * sx * 0.8
            base_pt = (tx, y + sign * hy, z + 0.03)
            tip_pt = (tx, y + sign * (hy + 0.24), z + 0.03)
            strut(name + "_raftertail_%d_%d" % (sign, i), base_pt, tip_pt, 0.045, wood_dark, verts_n=5)
    # STRAY LEAVES ON ROOF (PO v9 item 1 micro-dressing) — a handful of
    # tiny wind-blown leaf flecks scattered across the roof slope so it
    # reads as a real weathered surface at plaza-camera distance, not a
    # clean geometric prism. Skipped on snow caps (nothing lands loose on
    # fresh snow) — the underlying non-snow roof kinds still get them.
    if not snow:
        leaf_tones = [(0.42, 0.46, 0.14), (0.55, 0.38, 0.12), (0.30, 0.34, 0.10)]
        for li in range(rng.randint(3, 7)):
            lf_x = x + rng.uniform(-0.42, 0.42) * sx
            lf_y = y + rng.uniform(-0.35, 0.35) * sy
            lf_z = z + rise * rng.uniform(0.18, 0.75) + 0.03
            tone = leaf_tones[rng.randrange(len(leaf_tones))]
            leaf = ellipsoid(name + "_leaf_%d" % li, 0.06, 0.045, 0.012, (lf_x, lf_y, lf_z),
                              mat("roof_leaf_%.2f_%.2f_%.2f" % tone, tone, rough=0.85))
            leaf.rotation_euler = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, math.tau))

# ── Doors / windows / stairs (PO principle 5 — houses must LIVE) ───────────
DOOR_HS, WINDOW_HS = [], []  # audit trackers, printed at the end

def add_door(name, x, y, base_z, sx, wall_h, style):
    """Recessed-look door: a dark inset slab (proud of the wall face by a hair
    to avoid z-fighting — the sanctioned cheap trick for an 'opening' without
    boolean geometry) + a frame of 2 posts + a lintel. Always on the -Y
    ('front') face, matching the existing porch/kitchen convention.

    door_h is clamped to [1.9, 2.2] AND to `wall_h - 0.35` (round-2 fix —
    round 1 let door_h float down to 1.5 on tiny huts, sinking the mannequin's
    head 30cm above the frame; every house's base `wall_h` was bumped so this
    floor is always reachable without the lintel poking through the roof).
    """
    # DOOR STANDARDIZATION (v11 item 12, 2026-07-20): door_w used to scale
    # with the hut's own footprint (sx * 0.30) — a "dwarf door" on the tiny
    # outhouse (sx=1.3 -> 0.39m wide, narrower than the mannequin's
    # shoulders) and an oversized one on the casona. Every door in the
    # village now targets the SAME opening (~0.9m wide) regardless of hut
    # size, only shrinking on genuinely tiny footprints so the door never
    # exceeds the wall it's cut into.
    door_w = min(0.90, sx * 0.85)
    # BUG FIX (v7, PO orbit-report "madera a la altura del cuello"): the real
    # culprit turned out to be the PORCH beam (see house()'s porch block),
    # but this floor is tightened too as a hard guarantee — lintel BOTTOM
    # must clear >=1.95m over the 1.80m mannequin (was 1.9 floor -> as low
    # as 1.91m bottom edge, too close to the head for comfort).
    door_h = max(1.90, min(wall_h - 0.30, 1.98))
    DOOR_HS.append(door_h)
    door_mat = mat("door_slab", tuple(c * 0.5 for c in style["wood_dark"]), rough=0.9)
    frame_mat = mat("wood_dark", style["wood_dark"])
    return door_w, door_h, door_mat, frame_mat

def build_door_at(name, x, front_face_y, base_z, door_w, door_h, door_mat, frame_mat, no_slab=False):
    if not no_slab:
        box(name + "_slab", door_w, 0.06, door_h, (x, front_face_y - 0.03, base_z + door_h / 2), door_mat)
    for side in (-1, 1):
        box(name + "_frame_%d" % side, 0.06, 0.10, door_h + 0.12,
            (x + side * (door_w / 2 + 0.05), front_face_y - 0.02, base_z + (door_h + 0.12) / 2),
            frame_mat)
    box(name + "_lintel", door_w + 0.24, 0.10, 0.10,
        (x, front_face_y - 0.02, base_z + door_h + 0.06), frame_mat)

def window_glass_material():
    """Warm emissive glass most of the time (PO v7 item 5 — life signal at
    dusk-ish lighting: a lived-in village has lit windows), a plain dark
    pane the rest (some houses read as empty/asleep, not every window glows
    identically). Cached per-variant, not per-house, so it stays cheap.

    LIGHT-DENSITY BUMP (PO v10 item 5, 2026-07-20): raised 0.7->0.85 — a
    settlement should read as "populated" partly through window-glow
    DENSITY, independent of structure count (DanMachi 18F reference:
    hundreds of warm window-lights at night is what sells "populous", not
    raw geometry count). Cheap win — one probability constant, no new
    objects."""
    warm = rng.random() < 0.85
    key = "window_glass_warm" if warm else "window_glass_dark"
    if key not in _mats:
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        if warm:
            b.inputs["Base Color"].default_value = (0.85, 0.55, 0.22, 1.0)
            b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.24, 1.0)
            b.inputs["Emission Strength"].default_value = 1.8
        else:
            b.inputs["Base Color"].default_value = (0.03, 0.03, 0.045, 1.0)
        b.inputs["Roughness"].default_value = 0.3
        # GLASS TINT / TRANSPARENCY (v11 item 11, 2026-07-20): windows used
        # to be solid opaque insets — read as "a colored block", not glass.
        # A real cut hole would need boolean geometry (out of scope this
        # pass); the cheap correct fix is the same alpha-blend trick already
        # proven on cobweb_material()/smoke — a low-opacity tinted pane that
        # still reads as glass (keeps the warm/dark emissive read) instead
        # of a solid slab.
        alpha_in = b.inputs.get("Alpha")
        if alpha_in is not None:
            alpha_in.default_value = 0.55 if warm else 0.35
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            try:
                m.blend_method = 'BLEND'
            except Exception:
                pass
        _mats[key] = m
    return _mats[key]

def build_window_at(name, x, y, wall_face_axis, half_perp, z_center, style, w=0.55, h=0.55):
    """Dark inset + backing frame on a side wall (+X/-X face). wall_face_axis
    is +1 or -1 (which side); half_perp is the wall's half-extent along that
    axis so the window sits flush on the true outer face.

    Round-2 fix: `wood_dark` reused as the frame color read as invisible on
    hielo (both wood_dark AND the dark glass sit in the same near-black
    range in that biome's night palette — "windows visible" audit item
    failed there). Frame now LIGHTENS the biome's wood tone instead of
    reusing it raw, so the frame always contrasts against both the wall and
    the glass regardless of how dark the biome's base wood is.
    """
    w *= style["window_scale"]
    h *= style["window_scale"]
    WINDOW_HS.append(h)
    wd = style["wood_dark"]
    trim = tuple(min(1.0, c * 1.8 + 0.10) for c in wd)
    frame_mat = mat("window_trim", trim, rough=0.7)
    glass_mat = window_glass_material()
    ox = x + wall_face_axis * (half_perp + 0.035)
    box(name + "_frame", 0.05, w + 0.14, h + 0.14, (ox, y, z_center), frame_mat)
    box(name + "_glass", 0.03, w, h, (ox + wall_face_axis * 0.02, y, z_center), glass_mat)

def build_stairs(name, x, y0, z0, z1, steps, style, width=0.9):
    """Stacked-box steps climbing from ground (z0) to a raised floor (z1),
    running along -Y in front of the house (matches the door's -Y face).

    BUG FIX (v8, PO "las escaleras estan al reves"): the tread-height
    formula used to grow WITH distance from the wall (`z0 + rise*f`), so the
    step farthest from the door sat at the platform's full height and the
    step touching the wall was barely raised above the ground — a visitor
    standing right at the threshold would find the tallest step floating
    far away and a near-flat step underfoot. Steps must be TALLEST right at
    the platform/door (nearest tread, small f) and shortest at the far end
    where a climber starts from bare ground (largest f) — i.e. height must
    DECREASE with f, not increase. Root cause: the original formula was
    written from "distance already climbed" instead of "distance still to
    climb", which is easy to invert by accident — hence the mirrored bug.

    STAIRS BUG FIX (v11 item 3, 2026-07-20 — confirmed on casona AND the
    chicken coop, this ONE shared helper fixes both): the previous version
    shrank every tread box 8% on BOTH axes ("* 0.92") to dodge z-fighting,
    which left a visible gap between every step — "steps are disconnected
    floating blocks, no riser/support connecting them". Fixed by (1) sizing
    treads to their EXACT tread/rise so consecutive steps touch flush (no
    gap, no z-fighting risk either since adjacent faces are coplanar, not
    overlapping) and (2) two diagonal STRINGER beams along the outer edges
    spanning ground->platform in one continuous slanted board — the actual
    physical support member a real staircase reads as having, not just a
    stack of boxes."""
    wood = mat("wood_dark", style["wood_dark"])
    rise = (z1 - z0) / steps
    tread = 0.32
    for i in range(steps):
        f = i + 1  # 1 = nearest tread to the wall/platform, steps = farthest (ground)
        sy = y0 - tread * f + tread / 2
        sz = z1 - rise * f + rise / 2
        box("%s_step_%d" % (name, i), width, tread, rise, (x, sy, sz), wood)
    # STRINGERS — diagonal support beam under each outer edge, ground to
    # platform, so the staircase reads as ONE connected structure.
    run = steps * tread
    for side in (-1, 1):
        sx_ = x + side * (width / 2 - 0.03)
        p_ground = (sx_, y0 - run, z0 + 0.03)
        p_top = (sx_, y0, z1 + 0.03)
        strut("%s_stringer_%d" % (name, side), p_ground, p_top, 0.05, wood, verts_n=4)

# ── Enterable interiors — real wall gap + furniture (PO v7 item 4) ─────────
def build_shell_walls(name, sx, sy, wall_h, base_z, x, y, door_w, door_h,
                       wood_mat, floor_mat, wall_thick=0.10):
    """Hollow wall SHELL with a real door opening, replacing the old single
    solid `box()` used for every house — that box had no cavity at all, so
    the door/windows were purely cosmetic insets on solid geometry ("no es
    una puerta, es una mancha oscura", PO v7 item 4). Front (-Y) wall is
    split into two side segments + a header above the door gap; back/left/
    right stay solid slabs — together they form an actual box you can see
    (and the mannequin could walk) into."""
    hx, hy = sx / 2, sy / 2
    half_gap = door_w / 2 + 0.05
    seg_w = hx - half_gap
    if seg_w > 0.05:
        for side in (-1, 1):
            seg_cx = x + side * (half_gap + seg_w / 2)
            box("%s_frontwall_%d" % (name, side), seg_w, wall_thick, wall_h,
                (seg_cx, y - hy + wall_thick / 2, base_z + wall_h / 2), wood_mat)
    header_h = wall_h - door_h
    if header_h > 0.05:
        box(name + "_frontheader", door_w + 0.10, wall_thick, header_h,
            (x, y - hy + wall_thick / 2, base_z + door_h + header_h / 2), wood_mat)
    box(name + "_backwall", sx, wall_thick, wall_h, (x, y + hy - wall_thick / 2, base_z + wall_h / 2), wood_mat)
    box(name + "_leftwall", wall_thick, sy, wall_h, (x - hx + wall_thick / 2, y, base_z + wall_h / 2), wood_mat)
    box(name + "_rightwall", wall_thick, sy, wall_h, (x + hx - wall_thick / 2, y, base_z + wall_h / 2), wood_mat)
    box(name + "_floor", sx * 0.96, sy * 0.96, 0.06, (x, y, base_z + 0.03), floor_mat)

def build_table_benches(cx, cy, cz, wood_mat):
    """Table + 2 flanking benches — the casona's furnished-interior read
    (PO v7 item 4), simple box-and-leg construction matching the existing
    low-poly toon style (no new primitive vocabulary introduced)."""
    box("furn_table_top", 0.9, 0.5, 0.06, (cx, cy, cz + 0.42), wood_mat)
    for lx, ly in ((-0.4, -0.2), (-0.4, 0.2), (0.4, -0.2), (0.4, 0.2)):
        cylinder("furn_table_leg_%d_%d" % (int(lx * 100), int(ly * 100)), 0.03, 0.40,
                  (cx + lx, cy + ly, cz + 0.20), wood_mat, verts_n=6)
    for s in (-1, 1):
        box("furn_bench_%d" % s, 0.8, 0.2, 0.05, (cx, cy + s * 0.42, cz + 0.22), wood_mat)

def build_bed(name, cx, cy, cz, rot, wood_mat, cloth_mat):
    ob = box(name + "_frame", 0.55, 1.05, 0.12, (cx, cy, cz + 0.06), wood_mat)
    ob.rotation_euler = (0, 0, rot)
    m = box(name + "_mattress", 0.50, 1.0, 0.10, (cx, cy, cz + 0.17), cloth_mat)
    m.rotation_euler = (0, 0, rot)
    p = box(name + "_pillow", 0.30, 0.18, 0.06, (cx, cy, cz + 0.24), mat("pillow", (0.90, 0.88, 0.82)))
    p.rotation_euler = (0, 0, rot)

def build_hearth(name, cx, cy, cz, rng):
    """Ring of fire-stones + real low-poly flame wedges + crossed logs + ONE
    warm point light — the interior only needs to read from the doorway/
    windows (PO v7 item 4), no full lighting rig required. Flame geometry
    upgraded PO v8.1 item 3 (2026-07-19): the old single white placeholder
    cone read as fake; now shares build_campfire_logs()/build_campfire_
    flames() with the exterior campfire so both fires get the same
    real-flame treatment."""
    for i in range(6):
        a = i / 6 * math.tau
        make_rock(name + "_stone_%d" % i, rng.uniform(0.14, 0.20),
                   (cx + math.cos(a) * 0.5, cy + math.sin(a) * 0.5, cz + 0.10), rng, flatten=0.7)
    build_campfire_logs(name, cx, cy, cz + 0.10, rng, scale=0.8)
    build_campfire_flames(name, cx, cy, cz + 0.10, rng, scale=0.8)
    fl = bpy.data.lights.new(name + "_light", 'POINT')
    fl.energy = 120.0
    fl.color = (1.0, 0.55, 0.2)
    flo = bpy.data.objects.new(name + "_light", fl)
    flo.location = (cx, cy, cz + 0.6)
    link(flo)

def build_chest(cx, cy, cz, rng):
    """Loot chest — always built INSIDE a structure now (hut_storage), never
    open-air (PO v7 item 4)."""
    body_mat = mat("chest_wood", (0.30, 0.19, 0.10), rough=0.8)
    trim_mat = mat("chest_trim", (0.55, 0.50, 0.30), rough=0.35)
    box("chest_body", 0.45, 0.30, 0.28, (cx, cy, cz + 0.14), body_mat)
    lid = box("chest_lid", 0.47, 0.32, 0.08, (cx, cy - 0.02, cz + 0.30), body_mat)
    lid.rotation_euler = (math.radians(-16), 0, 0)  # slightly ajar — reads as loot, not furniture
    box("chest_band_1", 0.47, 0.05, 0.30, (cx, cy - 0.13, cz + 0.15), trim_mat)
    box("chest_band_2", 0.47, 0.05, 0.30, (cx, cy + 0.13, cz + 0.15), trim_mat)

def build_chimney_smoke(cx, cy, top_z, rng):
    """Chimney stack + 4 stacked semi-transparent grey spheres drifting up
    and sideways — a static, low-poly smoke read with NO particle system
    (PO v7 item 5)."""
    stone = mat("stone_chimney", (0.40, 0.39, 0.36), rough=0.8)
    chim_h = 1.1
    box("chimney", 0.35, 0.35, chim_h, (cx, cy, top_z + chim_h / 2), stone)
    key = "smoke_wisp"
    if key not in _mats:
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.65, 0.65, 0.68, 1.0)
        b.inputs["Alpha"].default_value = 0.32
        b.inputs["Roughness"].default_value = 1.0
        for attr, val in (("blend_method", 'BLEND'), ("surface_render_method", 'BLENDED'),
                          ("show_transparent_back", False)):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
        _mats[key] = m
    smoke_mat = _mats[key]
    sz = top_z + chim_h
    for i in range(4):
        f = i / 3.0
        r = 0.11 + f * 0.17
        oz = sz + 0.15 + f * 0.95 + rng.uniform(-0.05, 0.05)
        ox = cx + math.sin(f * 2.4 + rng.uniform(-0.3, 0.3)) * f * 0.28
        oy = cy + f * 0.18
        ellipsoid("smoke_%d" % i, r, r, r * 0.85, (ox, oy, oz), smoke_mat)

def rotate_group(name, start_idx, pivot, angle_deg):
    """Join every mesh object created since `start_idx` into one object,
    then rotate it around `pivot` by angle_deg around Z (PO v8 item 2b —
    'place some huts rotated 30-60 deg so facades vary'). Cheaper than
    rewriting every wall/door/window/roof helper to build in a local rotated
    frame: they all still build axis-aligned in world space, and THIS
    collapses + spins the whole group afterward. object.join works headless
    in Object Mode (no VIEW_3D area needed, per blender-asset-smith's
    headless-safe-ops notes); origin_set(ORIGIN_CURSOR) likewise."""
    objs = [o for o in list(bpy.context.collection.objects)[start_idx:] if o.type == 'MESH']
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        joined = objs[0]
    else:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        joined = bpy.context.view_layer.objects.active
        joined.name = name
    if angle_deg:
        scene.cursor.location = pivot
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        joined.rotation_euler = (0, 0, math.radians(angle_deg))
    return joined

def build_poor_footing(name, sx, sy, x, y, z, rng):
    """POOR footing for common huts (PO v10 item 1, 2026-07-20 — Joan's
    direct critique: 'es medio raro encontrar cimiento de cemento en una
    aldea tan chica'). The casona keeps its cut-stone plinth (build_casona's
    monolithic `stone_casona` block) — that's a WEALTH marker and correct
    as-is for the ONE anchor building. Common huts get the OPPOSITE read: a
    ring of loose, uncut fieldstones (real_troglodyte_stone_chimney_village
    .png reference: humble houses sit on the terrain itself, never a clean
    mortared slab) — reuses make_rock()'s per-rock bmesh/noise variation so
    no two stones match, same trick already proven for hearth-stones and
    the cliff wall. Cheaper to implement well than a packed-earth mound
    (make_rock is already battle-tested) and replaces the OLD monolithic
    `stone_base` box this function used to build (that box read as a clean
    poured-cement pad — the exact thing Joan flagged). Returns the new
    base_z (top of the low footing ring, where the wall now sits)."""
    hx, hy = sx / 2, sy / 2
    footing_h = 0.20  # lower than the old 0.35 slab AND far below the
                       # casona's 0.75 cut-stone plinth — reads as poorer.
    spacing = 0.62
    n_x = max(2, int(sx / spacing))
    n_y = max(2, int(sy / spacing))
    pts = []
    for i in range(n_x):
        f = (i + 0.5) / n_x - 0.5
        pts.append((f * sx, -hy - 0.04))
        pts.append((f * sx, hy + 0.04))
    for i in range(n_y):
        f = (i + 0.5) / n_y - 0.5
        pts.append((-hx - 0.04, f * sy))
        pts.append((hx + 0.04, f * sy))
    for i, (px, py) in enumerate(pts):
        r = rng.uniform(0.13, 0.20)
        make_rock("%s_footing_%d" % (name, i), r, (x + px, y + py, z + r * 0.5), rng,
                  flatten=rng.uniform(0.55, 0.75), disp=0.16)
    return z + footing_h


def build_house_annex(name, x, y, sx, sy, base_z, wall_h, style, rng, kind):
    """Secondary lower roof plane (PO v10 item 2, 2026-07-20) — houses read
    as one clean single-pitch gable; ALL 5 references (Old Mill LOTR,
    Whiterun houses, the pencil-sketch cottage row, DanMachi, Skyrim) show
    a multi-break roofline instead: an annex/porch section at a DIFFERENT,
    LOWER ridge height than the main roof. build_casona() already has this
    (its attached wing) — this extends the same pattern to regular houses.
    Attached on the -X side (clear of the door's -Y face, the porch's -Y
    overhang, and the +X drying_rack prop) so nothing collides."""
    asx, asy = sx * 0.55, sy * 0.85
    awall_h = wall_h * 0.62
    ax = x - sx / 2 - asx / 2 + 0.10  # slight overlap so it reads ATTACHED
    ay = y
    wood = mat("wood", style["wood"])
    box(name + "_annex_walls", asx, asy, awall_h, (ax, ay, base_z + awall_h / 2), wood)
    arise = style["roof_pitch"] * (asy * 0.42)
    build_roof(name + "_annex_roof", asx, asy, arise, (ax, ay, base_z + awall_h), style, kind, rng)


def house(name, sx, sy, wall_h, loc_xy, style, stone_base=None,
          porch=None, thatch=False, roof_kind=None, raised=False, terrace=False,
          windows=2, rng=None, real_door=False, chest=False, facing_deg=0, annex=None):
    """Composite house: walls + a roof-with-life (build_roof — thatch/tile/
    shingle per biome, never a flat prism) + corner posts + DOOR + WINDOWS +
    optional raised-on-stilts (with stairs) or terrace (elevation variety
    across the village, PO principle 5). The central anchor building is a
    SEPARATE dedicated builder now — see build_casona() — this function only
    ever builds a regular hut.

    `facing_deg` (PO v8 item 2b): rotates the WHOLE finished hut (walls,
    roof, door, windows, porch, stairs — everything) around its own base
    point by this many degrees. 0 = axis-aligned door-faces-(-Y), matching
    every prior house(). Non-zero values (used for a fraction of extra
    houses) are what makes a cluster of huts read as varied facades instead
    of a grid of identical boxes all facing the same way — see
    rotate_group().
    """
    rng = rng or random
    _group_start = len(bpy.context.collection.objects)
    x, y = loc_xy
    z = terrain_h(x, y)
    # MATERIAL VARIATION (PO v7 item 6): every house rolls its own +/-jitter
    # off the biome base wood/roof tone so no two houses share an identical
    # hex (mirrors the terrain's existing per-vertex noise). A shallow copy
    # keeps every OTHER style key (pitch, window_scale, roof_kinds, ...)
    # exactly as the biome defines it; reassigning `style` means every
    # existing style["..."] lookup below picks up the jittered version for
    # free, no further textual changes needed.
    hstyle = dict(style)
    hstyle["wood"] = jitter_tone(rng, style["wood"])
    hstyle["wood_dark"] = jitter_tone(rng, style["wood_dark"])
    hstyle["roof"] = jitter_tone(rng, style["roof"])
    style = hstyle
    if stone_base is None:
        stone_base = rng.random() < style["stone_base_chance"]
    if porch is None:
        porch = rng.random() < style["porch_chance"]
    ground_z = z
    base_z = z
    stilt_h = 0.0

    if stone_base and not raised:
        base_z = build_poor_footing(name, sx, sy, x, y, z, rng)
    if terrace and not raised and not stone_base:
        terrace_h = rng.uniform(0.18, 0.45)
        box(name + "_terrace", sx * 1.20, sy * 1.20, terrace_h, (x, y, z + terrace_h / 2),
            mat("stone", (0.42, 0.40, 0.36)))
        base_z = z + terrace_h
        if terrace_h > 0.25:
            build_stairs(name + "_terrace_stairs", x, y - sy / 2, z, base_z, 2, style, width=sx * 0.4)
    if raised:
        stilt_h = rng.uniform(1.0, 1.5)
        floor_z = z + stilt_h
        post_r = 0.11
        # SUPPORT-BUG FIX (v11 item 4, 2026-07-20): the 4 stilts used to
        # share ONE height (stilt_h) centered on the HOUSE's own terrain_h
        # sample (z, at the house center) — on sloped ground each corner's
        # true local ground differs from that center sample, so only the
        # corner closest to the center height actually touched the ground;
        # the others floated above or sank into the terrain ("leaning hut
        # supported at only one corner/point"). Each stilt now spans from
        # its OWN local terrain_h at that corner up to the SAME shared
        # floor_z — every corner is flush with its own ground, all four
        # tops still meet the platform exactly level.
        for cx_, cy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            spx = x + cx_ * sx * 0.42
            spy = y + cy_ * sy * 0.42
            sgz = terrain_h(spx, spy)
            sh = max(0.3, floor_z - sgz)
            cylinder(name + "_stilt_%d_%d" % (cx_, cy_), post_r, sh,
                      (spx, spy, sgz + sh / 2),
                      mat("wood_dark", style["wood_dark"]), verts_n=8)
        box(name + "_floor", sx * 1.06, sy * 1.06, 0.12, (x, y, floor_z), mat("wood", style["wood"]))
        base_z = floor_z + 0.06
        build_stairs(name + "_stairs", x, y - sy / 2, z, base_z, max(3, int(stilt_h / 0.24)), style)

    # DOOR — computed BEFORE the wall so a real_door house knows the gap
    # size (PO v7 item 4). Sized against MANNEQUIN_H (printed at the end).
    door_w, door_h, door_mat, frame_mat = add_door(name, x, y, base_z, sx, wall_h, style)

    if real_door:
        # ENTERABLE — an actual gap in the wall, not a dark inset (PO v7
        # item 4: "no es una puerta, es una mancha oscura").
        build_shell_walls(name, sx, sy, wall_h, base_z, x, y, door_w, door_h,
                           mat("wood", style["wood"]),
                           mat("wood_floor_%.2f_%.2f_%.2f" % style["wood"],
                               tuple(c * 0.82 for c in style["wood"])))
    else:
        box(name + "_walls", sx, sy, wall_h, (x, y, base_z + wall_h / 2), mat("wood", style["wood"]))

    post_r = 0.07
    post_h = wall_h + 0.05
    for cx_, cy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        cylinder(name + "_post_%d_%d" % (cx_, cy_), post_r, post_h,
                  (x + cx_ * sx / 2, y + cy_ * sy / 2, base_z + post_h / 2),
                  mat("wood_dark", style["wood_dark"]), verts_n=6)

    build_door_at(name + "_door", x, y - sy / 2, base_z, door_w, door_h, door_mat, frame_mat,
                   no_slab=real_door)
    if chest:
        # Loot chest lives INSIDE the storage hut now (PO v7 item 4 — never
        # an open-air chest); offset toward the back wall so it reads
        # through the real doorway without blocking it.
        build_chest(x, y + sy * 0.18, base_z, rng)

    # WINDOWS — side walls (+X/-X), chest-to-head height, count scales with size.
    win_h_center = base_z + wall_h * 0.58
    win_positions = [(-1, -0.15), (1, -0.15), (-1, 0.25), (1, 0.25)][:max(1, windows)]
    for side, yfrac in win_positions:
        build_window_at(name + "_win_%d_%d" % (side, int((yfrac + 1) * 100)),
                          x, y + yfrac * sy, side, sx / 2, win_h_center, style)

    rise = style["roof_pitch"] * (sy * 0.45)
    kind = roof_kind or ("thatch" if thatch else roll_weighted(rng, style["roof_kinds"]))
    build_roof(name + "_roof", sx, sy, rise, (x, y, base_z + wall_h), style, kind, rng)

    # MULTI-BREAK ROOF (PO v10 item 2): auto-rolled for bigger huts only
    # (small footprint = nothing to visually justify a second volume), and
    # skipped on raised/terrace variants (their base_z is already elevated
    # on stilts/a terrace slab that doesn't extend far enough to support an
    # annex without a floating-box bug — flat-ground huts only, for now).
    if annex is None:
        annex = (not raised and not terrace) and (sx * sy > 5.0) and rng.random() < 0.45
    if annex and not raised and not terrace:
        annex_kind = roll_weighted(rng, style["roof_kinds"])
        build_house_annex(name, x, y, sx, sy, base_z, wall_h, style, rng, annex_kind)

    if porch:
        # BUG FIX (v7, PO orbit-report "madera a la altura del cuello"): this
        # was the actual neck-height bar — poles at wall_h*0.55 put the porch
        # roof beam around ~1.2-1.3m, squarely blocking the entrance at chest/
        # neck height. Poles now run almost the full wall height so the porch
        # roof tucks just under the eave (>=1.95m clearance for any wall_h
        # this generator produces, see the door_h floor above).
        # FLOATING-GAP FIX (v11 item 1, 2026-07-20): poles used to run from
        # base_z (the HOUSE's own terrain sample) even though each pole
        # sits 0.5m out in front of the house — on anything but dead-flat
        # ground the pole's actual local terrain differs from base_z,
        # leaving either a floating gap under the pole or a buried stub.
        # Each pole's foot now uses its OWN local terrain_h; the top stays
        # the same fixed absolute height so the porch roof beam is
        # unaffected — only the foot-to-ground contact is fixed.
        porch_top_z = base_z + wall_h * 0.92
        for px in (-1, 1):
            ppx = x + px * sx * 0.32
            ppy = y - sy / 2 - 0.5
            pgz = terrain_h(ppx, ppy)
            pole_h = max(0.10, porch_top_z - pgz)
            cylinder(name + "_porch_pole_%d" % px, 0.06, pole_h,
                      (ppx, ppy, pgz + pole_h / 2),
                      mat("wood_dark", style["wood_dark"]), verts_n=6)
        box(name + "_porch_roof", sx * 0.7, 1.1, 0.12,
            (x, y - sy / 2 - 0.5, porch_top_z + 0.06),
            mat("wood_dark", style["wood_dark"]))
    if style["drying_rack"] and rng.random() < 0.5:
        rx, ry = x + sx * 0.75, y
        rz = base_z + 1.1
        for px in (-0.6, 0.6):
            # Same local-ground fix as the porch poles above (item 1) —
            # the rack sits away from the house's own terrain sample.
            rgz = terrain_h(rx + px, ry)
            cylinder(name + "_rack_post_%d" % int(px * 10), 0.045, rz - rgz, (rx + px, ry, (rz + rgz) / 2),
                      mat("wood_dark", style["wood_dark"]), verts_n=6)
        strut(name + "_rack_pole", (rx - 0.6, ry, rz), (rx + 0.6, ry, rz), 0.03,
              mat("wood_dark", style["wood_dark"]))
        cloth = mat("cloth_hide", (0.55, 0.45, 0.32))
        for i in range(3):
            box(name + "_rack_hide_%d" % i, 0.03, 0.35, 0.55,
                (rx - 0.4 + i * 0.4, ry, rz - 0.45), cloth)

    register_footprint(x, y, math.hypot(sx, sy) / 2 + (0.7 if porch else 0.4))
    if facing_deg:
        rotate_group(name, _group_start, (x, y, z), facing_deg)
    return base_z + wall_h  # roof-base height, useful for future stacking

# ── CASONA — the ONE central anchor building (PO v5 feedback, 2026-07-18) ──
def build_casona(name, loc_xy, style, rng):
    """THE central anchor building — every village has exactly one. A
    composite structure (main hall + attached wing/annex), never a scaled-up
    hut. Refs: village_casona/_synthesis.md — jorrvaskr_mead_hall.png /
    dragonsreach.jpg (raised on a visible stone plinth, reached by a
    monumental stair, entrance flanked by posts + braziers) and
    breezehome_exterior.jpg / breezehome_entrance.jpg (stone foundation
    course under wood upper structure — the construction ORDER: foundation
    -> walls -> roof, PO principle 1). Reuses the same door/window/stairs
    helpers as house() so the mannequin-scale audit applies here too."""
    x, y = loc_xy
    z = terrain_h(x, y)
    sx, sy, wall_h = 7.2, 5.2, 3.0
    hx, hy = sx / 2, sy / 2
    wood = mat("wood", style["wood"])
    wood_dark = mat("wood_dark", style["wood_dark"])
    # Round-2 tune (self-eyeball): (0.50,0.49,0.46) at 0.55m read as a thin
    # pale smudge, not "stone" — lightened + a taller course makes the
    # plinth unmistakably a DIFFERENT material the casona sits ON.
    stone = mat("stone_casona", (0.58, 0.57, 0.53), rough=0.7)

    # FOUNDATION — taller + more "cut stone" than a hut's thin stone_base
    # slab: the casona visibly SITS ON something (PO principle 1).
    plinth_h = 0.75
    box(name + "_plinth", sx * 1.14, sy * 1.14, plinth_h, (x, y, z + plinth_h / 2), stone)
    base_z = z + plinth_h

    # DOOR — computed BEFORE the wall shell so it knows the gap size.
    door_w, door_h, door_mat, frame_mat = add_door(name, x, y, base_z, sx, wall_h, style)

    # MAIN HALL — ENTERABLE now (PO v7 item 4): a real hollow shell with a
    # gap at the door instead of one solid box, furnished inside (see
    # below), same visible wall-to-roof support language as house().
    build_shell_walls(name, sx, sy, wall_h, base_z, x, y, door_w, door_h, wood,
                       mat("wood_floor_casona", tuple(c * 0.82 for c in style["wood"])))
    for cx_, cy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        cylinder(name + "_post_%d_%d" % (cx_, cy_), 0.10, wall_h + 0.06,
                  (x + cx_ * hx, y + cy_ * hy, base_z + (wall_h + 0.06) / 2), wood_dark, verts_n=8)
        # HANDMADE-IMPERFECTION (v11 item 14) — casona framing gets the
        # same knot/moss treatment as the palisade/roof members.
        if rng.random() < 0.30:
            add_wood_knot(name + "_post_knot_%d_%d" % (cx_, cy_),
                          (x + cx_ * hx + 0.09, y + cy_ * hy, base_z + wall_h * rng.uniform(0.3, 0.75)),
                          rng, r=0.055)
        if rng.random() < 0.20:
            add_moss_patch(name + "_post_moss_%d_%d" % (cx_, cy_),
                           (x + cx_ * hx, y + cy_ * hy, base_z + 0.10), rng, r=0.10)

    # WING/ANNEX — attached, smaller, own plinth + lower roof (composite
    # volume, not one scaled box — jorrvaskr/dragonsreach massing).
    wsx, wsy, wwall_h = sx * 0.45, sy * 0.75, wall_h * 0.72
    wx, wy = x + hx + wsx / 2 - 0.15, y - hy * 0.15  # slight overlap so it reads ATTACHED
    wplinth_h = plinth_h * 0.85
    box(name + "_wing_plinth", wsx * 1.12, wsy * 1.12, wplinth_h, (wx, wy, z + wplinth_h / 2), stone)
    wbase_z = z + wplinth_h
    box(name + "_wing_walls", wsx, wsy, wwall_h, (wx, wy, wbase_z + wwall_h / 2), wood)
    wing_rise = style["roof_pitch"] * (wsy * 0.42)
    build_roof(name + "_wing_roof", wsx, wsy, wing_rise, (wx, wy, wbase_z + wwall_h), style,
               style["casona_roof_kind"], rng)

    # ENTRANCE — monumental steps + door flanked by posts and lit braziers
    # (jorrvaskr_mead_hall.png: the casona announces itself).
    build_stairs(name + "_stairs", x, y - hy, z, base_z, 3, style, width=sx * 0.32)
    build_door_at(name + "_door", x, y - hy, base_z, door_w, door_h, door_mat, frame_mat, no_slab=True)

    # FURNISHED INTERIOR (PO v7 item 4) — reads through the real doorway:
    # table+benches near the front, a hearth (fire + one warm point light —
    # the only interior light this needs) further back, 2 beds against the
    # back wall. Depth order front-to-back matches what a viewer standing
    # at the door actually sees first.
    cloth_mat = mat("bed_cloth", (0.45, 0.38, 0.30), rough=0.9)
    build_table_benches(x - hx * 0.38, y - hy * 0.10, base_z, wood_dark)
    build_hearth(name + "_hearth", x, y + hy * 0.50, base_z, rng)
    build_bed(name + "_bed_l", x - hx * 0.62, y + hy * 0.65, base_z, 0, wood_dark, cloth_mat)
    build_bed(name + "_bed_r", x + hx * 0.62, y + hy * 0.65, base_z, 0, wood_dark, cloth_mat)

    # RICHER INTERIOR (PO v8 item 5) — "more than fire": wall shelves with
    # stored jars, pots hanging over the hearth, a rug patch underfoot,
    # stools around the table, and sacks/a barrel along the back wall. A
    # hall that's actually lived-in stores things, it doesn't just eat and
    # sleep (module-internal coherence rule — same one that gave the forge
    # its fuel pile).
    shelf_y = y - hy * 0.55
    shelf_x = x - hx * 0.85
    box(name + "_shelf_board_hi", 0.22, 1.4, 0.05, (shelf_x, shelf_y, base_z + 1.3), wood_dark)
    box(name + "_shelf_board_lo", 0.22, 1.4, 0.05, (shelf_x, shelf_y, base_z + 0.75), wood_dark)
    jar_tones = [(0.55, 0.40, 0.20), (0.40, 0.36, 0.30), (0.60, 0.52, 0.28)]
    for i in range(4):
        jy = shelf_y - 0.55 + i * 0.37
        tone = jar_tones[i % len(jar_tones)]
        cylinder(name + "_shelf_jar_%d" % i, 0.08, 0.20, (shelf_x, jy, base_z + 1.4),
                  mat("jar_%.2f_%.2f_%.2f" % tone, tone, rough=0.75), verts_n=8)
    for i in range(3):
        jy = shelf_y - 0.4 + i * 0.4
        tone = jar_tones[(i + 1) % len(jar_tones)]
        box(name + "_shelf_lo_item_%d" % i, 0.14, 0.14, 0.16, (shelf_x, jy, base_z + 0.85),
            mat("jar_%.2f_%.2f_%.2f" % tone, tone, rough=0.75))

    # Pots hanging over the hearth (matches build_hearth's own coordinates
    # below) — a working hearth has cookware right there, not bare fire.
    hearth_x, hearth_y = x, y + hy * 0.50
    rack_z = base_z + wall_h - 0.35
    strut(name + "_potrack_bar", (hearth_x - 0.5, hearth_y, rack_z), (hearth_x + 0.5, hearth_y, rack_z),
          0.025, wood_dark, verts_n=5)
    pot_mat = mat("hearth_iron_pot", (0.20, 0.20, 0.22), rough=0.4)
    for i, px in enumerate((-0.35, -0.05, 0.30)):
        cylinder(name + "_hangpot_%d" % i, 0.09, 0.14, (hearth_x + px, hearth_y, rack_z - 0.22),
                  pot_mat, verts_n=8)

    # Rug patch underfoot near the table (flat slab a hair above the floor —
    # same anti-z-fighting trick as the door slab).
    rug_tone = tuple(min(1.0, c * 1.3) for c in style["accent"])
    box(name + "_rug", 1.6, 1.1, 0.02, (x - hx * 0.15, y - hy * 0.05, base_z + 0.04),
        mat("rug_%.2f_%.2f_%.2f" % rug_tone, rug_tone, rough=0.95))

    # Stools around the table (in addition to the 2 flanking benches).
    for sx_, sy_ in ((-0.75, -0.35), (0.75, 0.35)):
        cylinder(name + "_stool_%d_%d" % (int(sx_ * 10), int(sy_ * 10)), 0.14, 0.32,
                  (x - hx * 0.38 + sx_ * 0.3, y - hy * 0.10 + sy_ * 0.3, base_z + 0.16), wood_dark, verts_n=8)

    # Stored goods along the back wall, IN THE GAP between the two beds
    # (bed_l/bed_r sit at +-hx*0.62 — this stays well clear of both) —
    # sacks + a barrel, the casona's granary-adjacent storage read (item 5).
    sack_mat = mat("sack_cloth", (0.55, 0.48, 0.34), rough=0.95)
    for i in range(3):
        bx_ = x - 0.55 + i * 0.42
        by_ = y + hy * 0.82
        sack = ellipsoid(name + "_sack_%d" % i, 0.22, 0.20, 0.26, (bx_, by_, base_z + 0.26), sack_mat)
        sack.rotation_euler = (0, 0, rng.uniform(-0.2, 0.2))
    cylinder(name + "_barrel", 0.24, 0.55, (x + 0.95, y + hy * 0.78, base_z + 0.275), wood_dark, verts_n=10)

    for px in (-1, 1):
        bx, by = x + px * (door_w / 2 + 0.55), y - hy - 0.35
        cylinder(name + "_brazier_post_%d" % px, 0.06, 1.1, (bx, by, base_z + 0.55), wood_dark, verts_n=6)
        build_small_flame(name + "_brazier_%d" % px, bx, by, base_z + 1.13, rng, scale=1.2)

    # WINDOWS — 4 total (2 per side), chest-to-head height (mannequin audit).
    win_h_center = base_z + wall_h * 0.58
    for side in (-1, 1):
        for yfrac in (-0.2, 0.25):
            build_window_at(name + "_win_%d_%d" % (side, int((yfrac + 1) * 100)),
                              x, y + yfrac * sy, side, hx, win_h_center, style, w=0.65, h=0.65)

    # ROOF — the biome's "civilized" roof kind (village_roofs/_synthesis.md),
    # sized to read as the anchor silhouette against the smaller huts.
    rise = style["roof_pitch"] * (sy * 0.48)
    build_roof(name + "_roof", sx, sy, rise, (x, y, base_z + wall_h), style,
               style["casona_roof_kind"], rng)
    # CHIMNEY + SMOKE (PO v7 item 5 — life signal): planted near the ridge,
    # over the hearth below, embedded into the roof volume so its base
    # doesn't float above the slope.
    build_chimney_smoke(x + hx * 0.30, y + hy * 0.25, base_z + wall_h + rise * 0.82, rng)
    if style["tower_stone"]:  # hielo — stone eave trim, echoes the stone watchtower
        box(name + "_stone_trim", sx * 1.02, sy * 1.02, 0.14, (x, y, base_z + wall_h + 0.02),
            mat("stone", (0.45, 0.46, 0.50)))
    return base_z + wall_h

# ── STRUCTURE: palisade ring + double gate ────────────────────────────────────
GATE_ANG = -math.pi / 2  # gate faces -Y (camera side)

def _in_arc(a, arc):
    """True if angle `a` falls inside `arc` = (lo, hi) (handles wraparound
    by normalizing the difference into [-pi, pi], same trick the gate-clear
    checks already use elsewhere in this file)."""
    lo, hi = arc
    mid = (lo + hi) / 2
    half = (hi - lo) / 2
    return abs(((a - mid + math.pi) % math.tau) - math.pi) < half

def build_palisade(cx, cy, ring_r, gate_ang, style, wall_h_mult, ring_radius_fn=None, cliff_arc=None):
    """`ring_radius_fn(angle)` (PO v9 item 3, 2026-07-19): NON-CIRCULAR
    PERIMETER — 'la aldea siempre es un circulo, hace que la muralla se
    adapte'. When provided, each stake's radial distance comes from this
    per-angle function instead of the flat scalar `ring_r`, producing an
    elongated/irregular ring silhouette per seed (see its construction at
    the call site). Falls back to the old flat-circle behavior when None
    (destacamento's small wall fragment keeps the simple circle — out of
    this pass's scope).

    `cliff_arc` (lo, hi): when set, NO stakes/rails/patches are placed in
    that angular arc — a natural rock outcrop stands in for the wall there
    instead (see build_cliff_wall, called separately by the caller right
    after this function returns), exactly like Rivira backing onto its own
    cliff face for part of its perimeter."""
    touching = style.get("palisade_touching", False)
    cov = style["ring_coverage"]
    gate_half = 0.10
    wood = mat("wood_dark", style["wood_dark"])
    if touching:
        nominal_spacing = style["stake_r"] * 2 * 0.92
        n = max(style["stake_count"], math.ceil(math.tau * ring_r / nominal_spacing))
        n = min(n, 520)  # perf safety cap — see module docstring runtime note
    else:
        n = style["stake_count"]
    ring_heights = []
    placed = []
    for i in range(n):
        t = i / n
        if cov < 1.0 and not (-cov / 2 < ((t + 0.25) % 1.0) - 0.5 < cov / 2):
            continue
        a = t * math.tau
        if abs(((a - gate_ang + math.pi) % math.tau) - math.pi) < gate_half:
            continue
        if cliff_arc is not None and _in_arc(a, cliff_arc):
            continue  # the cliff occupies this stretch instead of stakes
        j = style["jitter"]
        base_r = ring_radius_fn(a) if ring_radius_fn is not None else ring_r
        rr = base_r + rng.uniform(-0.4, 0.4) * j
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        z = terrain_h(x, y)
        h = style["stake_h"] * wall_h_mult * (1.0 + rng.uniform(-0.18, 0.18) * j)
        # MIXED DIAMETERS (v11 item 14, HANDMADE-IMPERFECTION) — used to be
        # a FIXED radius on any biome with palisade_touching unset/False
        # (hielo), so its stakes were perfectly uniform. Every stake now
        # varies +/-, touching or not.
        r = style["stake_r"] * (1.0 + rng.uniform(-0.15, 0.35))
        st = cylinder("stake_%d" % i, r, h, (x, y, z + h / 2), wood)
        tip_h = r * 1.8
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r, depth=tip_h,
            location=(x, y, z + h / 2 + tip_h / 2))
        cone = bpy.context.object
        cone.name = "stake_%d_tip" % i
        cone.data.materials.append(wood)
        cone.parent = st
        cone.matrix_parent_inverse = st.matrix_world.inverted()
        lean = (rng.uniform(-0.06, 0.06) * j, rng.uniform(-0.06, 0.06) * j, 0)
        st.rotation_euler = lean
        # KNOTS + MOSS (v11 item 14) — sparse per-stake decals so the wall
        # doesn't read as one repeated clean cylinder.
        if rng.random() < 0.22:
            add_wood_knot("stake_%d_knot" % i, (x + r * 0.9, y, z + h * rng.uniform(0.25, 0.7)),
                          rng, r=r * 1.1)
        if rng.random() < 0.18:
            add_moss_patch("stake_%d_moss" % i, (x, y, z + 0.06), rng, r=r * 1.6)
        ring_heights.append((z, x, y))
        placed.append((a, x, y, z, h))
    if placed:
        step = math.tau / n
        nominal_h = style["stake_h"] * wall_h_mult
        rail_inset = style["stake_r"] * 1.6 if touching else 0.0
        for k in range(len(placed)):
            a1, x1, y1, z1, h1 = placed[k]
            a2, x2, y2, z2, h2 = placed[(k + 1) % len(placed)]
            gap = (a2 - a1) % math.tau
            if gap > step * 1.6:
                continue
            ang = math.atan2(y2 - y1, x2 - x1)
            length = math.hypot(x2 - x1, y2 - y1) + style["stake_r"]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if rail_inset:
                d = math.hypot(mx - cx, my - cy) or 1.0
                mx -= (mx - cx) / d * rail_inset
                my -= (my - cy) / d * rail_inset
            for idx, frac in enumerate((0.62, 0.30)):
                zr = (z1 + z2) / 2 + frac * nominal_h
                rail = box("rail_%d_%d" % (k, idx), length, 0.07, 0.09, (mx, my, zr), wood)
                rail.rotation_euler = (0, 0, ang)
    placed_patches = 0
    patch_tries = 0
    while placed_patches < 2 and patch_tries < 40:
        patch_tries += 1
        a = rng.uniform(0, math.tau)
        if abs(((a - gate_ang + math.pi) % math.tau) - math.pi) < 0.6:
            continue
        if cliff_arc is not None and _in_arc(a, cliff_arc):
            continue
        base_r = ring_radius_fn(a) if ring_radius_fn is not None else ring_r
        x, y = cx + math.cos(a) * (base_r - 0.5), cy + math.sin(a) * (base_r - 0.5)
        z = terrain_h(x, y)
        pl = box("patch_%d" % placed_patches, 0.14, 0.5, 2.6, (x, y, z + 1.1), wood)
        pl.rotation_euler = (rng.uniform(0.3, 0.5), 0, a + math.pi / 2)
        placed_patches += 1
    return ring_heights

def build_cliff_wall(cx, cy, ring_radius_fn, cliff_arc, rng, style, wall_h_mult):
    """PO v9 item 3 (2026-07-19): where the village backs onto a natural
    rock outcrop, the cliff ITSELF stands in for the palisade along that
    arc — Rivira-style ('el risco es la muralla ahí'), no stakes needed
    because nothing on foot is scaling a jagged rock face. Stacks 2-4
    make_rock() boulders at each of a handful of points along the arc,
    each stack taller than the ordinary palisade (so it visibly reads as a
    BARRIER, not decorative scatter), following `ring_radius_fn` so it
    sits flush with the rest of the irregular perimeter."""
    a0, a1 = cliff_arc
    span = a1 - a0
    mid_r = ring_radius_fn((a0 + a1) / 2)
    # ROUND-2 SCALE-DOWN (self-eyeball, seed 21): the first pass's boulder
    # radius (0.9-1.6) x tight stack spacing (n ~ span*r/1.4) x wide radial
    # jitter (+-0.7) fused into a solid MOUNTAIN dwarfing the tower/houses,
    # not a cliff FACE standing in for a ~3.7m palisade. Smaller boulders,
    # fewer/wider-spaced stacks, a tighter radial band, and a shorter height
    # target read as a rocky ridge instead.
    #
    # CONTINUOUS ROCK FACE (v11 item 17, 2026-07-20): that round-2 tune
    # over-corrected into individually-spaced boulder "pillars" with visible
    # gaps between stacks — Joan confirmed it does NOT read as a barrier.
    # Fixed by (1) roughly DOUBLING stack density (spacing 2.6 -> 1.15) so
    # neighboring stacks' boulder radii overlap, (2) a staggered FILLER
    # stack at the angular MIDPOINT between every pair of primary stacks
    # (smaller boulders, wider radial jitter) closing the remaining gaps,
    # and (3) tighter vertical overlap per stack (0.85x boulder radius step
    # instead of 1.15x) so each stack itself reads as one solid mass, not
    # loosely-touching spheres.
    n = max(6, int(span * mid_r / 1.15))
    cliff_h_target = style["stake_h"] * wall_h_mult * rng.uniform(1.3, 1.7)

    def place_stack(a, tag, radial_jitter, r_lo, r_hi):
        rr = ring_radius_fn(a) + rng.uniform(-radial_jitter, radial_jitter)
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        z = terrain_h(x, y)
        stack_h = 0.0
        si = 0
        while stack_h < cliff_h_target:
            br = rng.uniform(r_lo, r_hi)
            make_rock("cliff_%s_%d" % (tag, si), br, (x, y, z + stack_h + br * 0.5), rng,
                      flatten=rng.uniform(0.6, 0.9), disp=0.22)
            stack_h += br * 0.85
            si += 1
            if si > 4:
                break
        return x, y, a

    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.5
        a = a0 + span * t
        x, y, _ = place_stack(a, "%d" % i, radial_jitter=0.35, r_lo=0.55, r_hi=1.05)
        if i > 0 and n > 1:
            fa = a0 + span * (t - 0.5 / (n - 1))
            place_stack(fa, "fill%d" % i, radial_jitter=0.5, r_lo=0.40, r_hi=0.75)
        # A couple of loose scree boulders at the cliff's own foot, inside
        # the village side, so the transition from wall to rock doesn't
        # look like a clean geometric seam.
        if rng.random() < 0.5:
            sx_, sy_ = x + math.cos(a) * -1.3, y + math.sin(a) * -1.3
            make_rock("cliff_scree_%d" % i, rng.uniform(0.35, 0.6), (sx_, sy_, terrain_h(sx_, sy_) + 0.15),
                      rng, flatten=0.7)

def build_double_gate(cx, cy, ring_r, gate_ang, style, gate_reinforced, single=False, ring_radius_fn=None):
    """Axlin airlock: exterior gate + interior gate ~5m inward, corridor
    stubs. `gate_reinforced` (ground_beasts threat) thickens gateposts and
    adds 2 flanking angled spikes per gate — the entrance is the wall's
    weakest point, so a ground-threat profile hardens it specifically.
    `single` (calm threat INTENSITY, PO addendum 2026-07-18) drops the
    interior gate entirely — a calm village doesn't need a double-gate
    airlock, one simple gate reads as a boundary marker, not a fortress.

    BAFFLE (PO v8 item 2a, 2026-07-19, SIMPLIFIED v2): v7's corridor was a
    dead-straight 5m tunnel — full line-of-sight from outside clean through
    to the plaza ("one fast view reveals ~80%"). ROUND-1 FIX ATTEMPT bent
    the whole corridor (relocated interior gate + a second wall leg) and
    that broke the existing "plaza" eye-level shot — its fixed camera
    position sat exactly where the new interior-gate geometry now stood,
    rendering solid wall (self-caught via render, not assumed). REVERTED to
    the ORIGINAL straight ext/int gate positions and side walls (byte-
    identical to v7, so the plaza camera is provably clear again — it was
    already validated safe there) and add exactly ONE new object: a baffle
    wall spanning most of the corridor width at its midpoint, gap on one
    side only (`turn_side`, seeded). You still can't see through — the
    baffle sits directly in the exterior gate's eyeline — but nothing about
    the proven-safe gate/corridor geometry moved."""
    wood = mat("wood", style["wood"])
    wood_dark = mat("wood_dark", style["wood_dark"])
    gate_reinforced = gate_reinforced and not single
    post_r = 0.22 * (1.3 if gate_reinforced else 1.0)
    gate_specs = ((0.0, "ext"),) if single else ((0.0, "ext"), (5.0, "int"))
    perp = (math.cos(gate_ang + math.pi / 2), math.sin(gate_ang + math.pi / 2))
    for depth, tag in gate_specs:
        r = ring_r - depth
        gx, gy = cx + math.cos(gate_ang) * r, cy + math.sin(gate_ang) * r
        for s in (-1, 1):
            px, py = gx + perp[0] * 1.6 * s, gy + perp[1] * 1.6 * s
            z = terrain_h(px, py)
            cylinder("gatepost_%s_%d" % (tag, s), post_r, 4.2, (px, py, z + 2.1), wood)
            if gate_reinforced:
                # Flanking spike: base at the post's outer foot, leaning
                # outward-and-up along the corridor's own perpendicular axis
                # (perp), never a raw fixed-axis rotation (that's what broke
                # in round 1 — see oriented_cone() docstring).
                base_pt = (px + perp[0] * 0.35 * s, py + perp[1] * 0.35 * s, z + 0.15)
                direction = (perp[0] * s * 0.55, perp[1] * s * 0.55, 1.0)
                oriented_cone("gate_spike_%s_%d" % (tag, s), 0.09, 1.0, base_pt, direction, wood_dark)
        z = terrain_h(gx, gy)
        lintel = box("lintel_%s" % tag, 3.9, 0.3, 0.35, (gx, gy, z + 4.1), wood)
        lintel.rotation_euler = (0, 0, gate_ang + math.pi / 2)
    for s in (-1, 1):
        mx = cx + math.cos(gate_ang) * (ring_r - 2.5)
        my = cy + math.sin(gate_ang) * (ring_r - 2.5)
        px, py = mx + perp[0] * 1.6 * s, my + perp[1] * 1.6 * s
        z = terrain_h(px, py)
        wall = box("gatewall_%d" % s, 0.2, 5.0, 2.4, (px, py, z + 1.2), wood_dark)
        wall.rotation_euler = (0, 0, gate_ang + math.pi / 2)

    # JOINT FILLER (v11 item 7, 2026-07-20): the exterior gateposts sit at a
    # perpendicular corridor offset (perp*1.6 from the gate's own radial
    # line) while build_palisade's regular stakes resume at gate_half=0.10
    # rad along the RING's own curve — two different placement schemes that
    # don't naturally meet, leaving a visible gap/seam where the gate
    # structure should join the wall. Two low rails bridge the exterior
    # gatepost to the point where the palisade wall actually resumes,
    # closing the seam without touching either proven-safe placement
    # scheme (same rail technique build_palisade already uses between its
    # own stakes).
    gate_half = 0.10
    ext_gx, ext_gy = cx + math.cos(gate_ang) * ring_r, cy + math.sin(gate_ang) * ring_r
    for s in (-1, 1):
        px, py = ext_gx + perp[0] * 1.6 * s, ext_gy + perp[1] * 1.6 * s
        pz = terrain_h(px, py)
        a_resume = gate_ang + s * gate_half
        rr = ring_radius_fn(a_resume) if ring_radius_fn is not None else ring_r
        wx = cx + math.cos(a_resume) * rr
        wy = cy + math.sin(a_resume) * rr
        wz = terrain_h(wx, wy)
        for frac in (0.55, 0.20):
            strut("gate_jointfill_%d_%d" % (s, int(frac * 100)),
                  (px, py, pz + 0.2 + frac * 3.6), (wx, wy, wz + 0.2 + frac * 3.6),
                  0.05, wood_dark, verts_n=4)

    if single:
        return

    # BAFFLE — one new wall, positioned 3.2m inside the exterior gate
    # (within the existing 5m corridor span, well clear of both the ext
    # gate at r=ring_r and the plaza camera which sits at r<=ring_r-6),
    # spanning [-1.6, +1.6] minus a `baffle_len`-wide gap on turn_side.
    # Whichever side the gap lands on, dead center (x=0, where every eye-
    # level audit camera sits) is inside the SOLID portion — see the math
    # in the comment below — so the straight sightline is always blocked.
    turn_side = rng.choice((-1, 1))
    baffle_r = ring_r - 3.2
    bcx = cx + math.cos(gate_ang) * baffle_r
    bcy = cy + math.sin(gate_ang) * baffle_r
    baffle_len = 1.9  # leaves a (3.2 - 1.9) = 1.3m gap on turn_side — walkable
    # Baffle spans perp-offset [-1.6, -1.6+len] on the non-turn side
    # (center at -1.6+len/2), mirrored by turn_side. For len=1.9 that
    # center offset is +-0.65 — either way, x=0 (dead center) falls inside
    # the solid span [-1.6, 0.3] or [-0.3, 1.6].
    baffle_off = -turn_side * (1.6 - baffle_len / 2)
    bx = bcx + perp[0] * baffle_off
    by = bcy + perp[1] * baffle_off
    bz = terrain_h(bx, by)
    baffle = box("gate_baffle", baffle_len, 0.22, 2.4, (bx, by, bz + 1.2), wood_dark)
    baffle.rotation_euler = (0, 0, gate_ang + math.pi / 2)

    # INVITING ALLEY (PO v8.1 item 1, 2026-07-19): the baffle above fully
    # blocks the casona sightline, but PO's v8 playtest found it now reads
    # as a blank wall filling most of the fastview frame — occlusion
    # overcorrected into "blind the viewer" instead of "channel the view".
    # Fix: mount a lit torch dead-center on the baffle's outward (camera-
    # facing) face, so the alley terminates at a warm, designed focal point
    # instead of raw flat wood, plus a small accent banner strung overhead
    # between the corridor's own side walls so the passage reads as an
    # intentional threshold, not an accidental dead end. Neither object
    # opens the sightline — both sit ON/ABOVE the same blocking geometry.
    face_dir = (math.cos(gate_ang), math.sin(gate_ang))  # outward, toward the ext gate/camera
    tx = bx + face_dir[0] * 0.16
    ty = by + face_dir[1] * 0.16
    tz = bz + 1.85
    cylinder("gate_baffle_torch_arm", 0.035, 0.30, (tx, ty, tz - 0.06), wood_dark, verts_n=6)
    build_small_flame("gate_baffle_torch", tx, ty, tz + 0.10, rng, scale=1.1)
    tl = bpy.data.lights.new("gate_baffle_torch_light", 'POINT')
    tl.energy = 90.0
    tl.color = (1.0, 0.55, 0.2)
    tlo = bpy.data.objects.new("gate_baffle_torch_light", tl)
    tlo.location = (tx, ty, tz + 0.15)
    link(tlo)

    ban_z = bz + 2.55
    bp1 = (bcx + perp[0] * 1.55, bcy + perp[1] * 1.55, ban_z)
    bp2 = (bcx - perp[0] * 1.55, bcy - perp[1] * 1.55, ban_z)
    strut("gate_banner_rope", bp1, bp2, 0.012, wood_dark, verts_n=4)
    banner_mat = mat("gate_banner_cloth", style["accent"])
    bmx, bmy = (bp1[0] + bp2[0]) / 2, (bp1[1] + bp2[1]) / 2
    banner = box("gate_banner_cloth", 0.9, 0.02, 0.4, (bmx, bmy, ban_z - 0.24), banner_mat)
    banner.rotation_euler = (0, 0, gate_ang + math.pi / 2)

def build_torches(cx, cy, ring_r, gate_ang, style, count=8, ring_radius_fn=None, cliff_arc=None):
    """Night-predators threat: lit posts around the inner wall. Every other
    torch carries a real POINT light (perf/light-count guard); the rest are
    emissive-only — still reads as a lit ring in a render. `ring_radius_fn`/
    `cliff_arc` (PO v9 item 3) keep torches flush with the irregular wall
    and skip the arc where the cliff stands in for the palisade instead."""
    wood = mat("wood_dark", style["wood_dark"])
    gate_half = 0.14
    placed = []
    for i in range(count):
        a = i / count * math.tau
        if abs(((a - gate_ang + math.pi) % math.tau) - math.pi) < gate_half:
            continue
        if cliff_arc is not None and _in_arc(a, cliff_arc):
            continue
        base_r = ring_radius_fn(a) if ring_radius_fn is not None else ring_r
        x, y = cx + math.cos(a) * (base_r - 1.4), cy + math.sin(a) * (base_r - 1.4)
        z = terrain_h(x, y)
        cylinder("torch_post_%d" % i, 0.06, 1.6, (x, y, z + 0.8), wood, verts_n=6)
        build_small_flame("torch_%d" % i, x, y, z + 1.62, rng, scale=1.0)
        if i % 2 == 0:
            fl = bpy.data.lights.new("torch_light_%d" % i, 'POINT')
            fl.energy = 90.0
            fl.color = (1.0, 0.55, 0.2)
            flo = bpy.data.objects.new("torch_light_%d" % i, fl)
            flo.location = (x, y, z + 1.7)
            link(flo)
        placed.append((a, x, y, z))
    # LOW FENCE RAILS (v11 item 23, 2026-07-20): the night_predators torch
    # ring used to be standalone lit posts with nothing connecting them —
    # "just floating lights with no fence structure". Two horizontal rails
    # at a real low-fence height now link consecutive posts (same
    # technique build_palisade already uses between its own stakes), so
    # this reads as an actual lit fence, not disconnected lights.
    if placed:
        step = math.tau / count
        for k in range(len(placed)):
            a1, x1, y1, z1 = placed[k]
            a2, x2, y2, z2 = placed[(k + 1) % len(placed)]
            gap = (a2 - a1) % math.tau
            if gap > step * 1.6:
                continue
            for frac in (0.55, 0.22):
                zr = (z1 + z2) / 2 + frac * 1.0
                strut("torchfence_rail_%d_%d" % (k, int(frac * 100)), (x1, y1, zr), (x2, y2, zr),
                      0.03, wood, verts_n=5)

def build_tower(cx, cy, ring_heights, style, threat_name):
    z, x, y = max(ring_heights)
    x = cx + (x - cx) * 0.92; y = cy + (y - cy) * 0.92
    if style["tower_stone"]:
        # HIELO WATCHTOWER REBUILD (v11 item 22, 2026-07-20): the old tower
        # was a plain grey cylinder + a flat wood disc cap — no windows, no
        # peaked roof (a flat cap is physically implausible, snow/water
        # would pool), and no way to climb it. Fixed at the geometry level:
        # window openings (dark inset boxes) around the body, a SLOPED
        # conical cap (+ a small snow tip in snow biomes), and a real
        # ladder (2 rails + rungs) up one side — same fix as item 8 below.
        tower_stone_mat = mat("stone", (0.45, 0.46, 0.50))
        cylinder("tower_body", 1.5, 7.0, (x, y, z + 3.5), tower_stone_mat, verts_n=12)
        win_mat = mat("tower_window_dark", (0.04, 0.04, 0.06), rough=0.3)
        for wi in range(4):
            wa = wi / 4 * math.tau + math.pi / 4
            wx_ = x + math.cos(wa) * 1.53
            wy_ = y + math.sin(wa) * 1.53
            wz_ = z + 5.6
            wobj = box("tower_window_%d" % wi, 0.32, 0.10, 0.55, (wx_, wy_, wz_), win_mat)
            wobj.rotation_euler = (0, 0, wa)
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=2.0, depth=1.8,
                                         location=(x, y, z + 7.0 + 0.9))
        cap = bpy.context.object
        cap.name = "tower_roof_cap"
        cap.data.materials.append(mat("roof", style["roof"]))
        if style["snow"]:
            bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=2.05, depth=0.3,
                                             location=(x, y, z + 7.0 + 1.75))
            snowcap = bpy.context.object
            snowcap.name = "tower_roof_snowtip"
            snowcap.data.materials.append(mat("snow", (0.92, 0.94, 0.97)))
        # LADDER (v11 item 8, "watchtower needs a visible way to climb") —
        # 2 vertical rails + rungs flanking one point on the tower's
        # circumference, well clear of the window openings.
        ladder_mat = mat("wood_dark", style["wood_dark"])
        ladder_ang = math.radians(200)
        tx_ = x + math.cos(ladder_ang) * 1.5
        ty_ = y + math.sin(ladder_ang) * 1.5
        perp_x, perp_y = -math.sin(ladder_ang), math.cos(ladder_ang)
        rail_h = 6.6
        for side in (-1, 1):
            rlx = tx_ + perp_x * 0.18 * side
            rly = ty_ + perp_y * 0.18 * side
            cylinder("tower_ladder_rail_%d" % side, 0.028, rail_h, (rlx, rly, z + rail_h / 2),
                      ladder_mat, verts_n=5)
        rungs = 11
        for ri in range(rungs + 1):
            f = ri / rungs
            rz = z + 0.3 + f * (rail_h - 0.6)
            p1 = (tx_ - perp_x * 0.18, ty_ - perp_y * 0.18, rz)
            p2 = (tx_ + perp_x * 0.18, ty_ + perp_y * 0.18, rz)
            strut("tower_ladder_rung_%d" % ri, p1, p2, 0.022, ladder_mat, verts_n=4)
    else:
        wood = mat("wood_dark", style["wood_dark"])
        half_w = 1.1
        total_h = 6.5
        z0 = z
        corners = ((-1, -1), (-1, 1), (1, 1), (1, -1))
        leg_pts = []
        for sx, sy in corners:
            lx, ly = x + sx * half_w, y + sy * half_w
            cylinder("tower_leg_%d_%d" % (sx, sy), 0.14, total_h,
                      (lx, ly, z0 + total_h / 2), wood)
            leg_pts.append((lx, ly))
        for ridx, frac in enumerate((0.34, 0.68)):
            zc = z0 + total_h * frac
            for i in range(4):
                x1, y1 = leg_pts[i]
                x2, y2 = leg_pts[(i + 1) % 4]
                strut("tower_ring_%d_%d" % (ridx, i), (x1, y1, zc), (x2, y2, zc), 0.05, wood)
        tiers = ((0.06, 0.34), (0.34, 0.68))
        for i in range(4):
            x1, y1 = leg_pts[i]
            x2, y2 = leg_pts[(i + 1) % 4]
            for tidx, (f_lo, f_hi) in enumerate(tiers):
                z_lo, z_hi = z0 + total_h * f_lo, z0 + total_h * f_hi
                strut("tower_brace_%d_%d_a" % (i, tidx), (x1, y1, z_lo), (x2, y2, z_hi), 0.045, wood)
                strut("tower_brace_%d_%d_b" % (i, tidx), (x1, y1, z_hi), (x2, y2, z_lo), 0.045, wood)
        lx1, ly1 = leg_pts[0]
        lx2, ly2 = leg_pts[1]
        rungs = 7
        for ridx in range(rungs + 1):
            f = ridx / rungs
            zc = z0 + 0.3 + f * (total_h - 0.6)
            strut("tower_ladder_rung_%d" % ridx, (lx1, ly1, zc), (lx2, ly2, zc), 0.035, wood)
        box("tower_floor", 3.0, 3.0, 0.22, (x, y, z + 6.4), wood)
        for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            cylinder("tower_post", 0.09, 1.2, (x + sx * 1.3, y + sy * 1.3, z + 7.1), wood)
        gable_roof("tower_roof", 3.4, 3.4, 1.1, (x, y, z + 7.7), mat("roof", style["roof"]))
        if style["snow"]:
            gable_roof("tower_snow", 3.5, 3.5, 1.12, (x, y, z + 7.76),
                       mat("snow", (0.92, 0.94, 0.97)))
    bz = z + (7.6 if not style["tower_stone"] else 7.4)
    cylinder("banner_pole", 0.05, 2.0, (x, y, bz + 1.0), mat("wood", style["wood"]))
    box("banner_cloth", 0.06, 0.9, 1.1, (x, y + 0.5, bz + 1.4), mat("accent", style["accent"]))
    if threat_name == "night_predators":
        # a lit brazier on the tower platform — the vigilance point is the
        # first thing to carry a torch under this threat profile.
        build_small_flame("tower_brazier", x, y + 1.0, z + 6.65, rng, scale=1.3)
        fl = bpy.data.lights.new("tower_brazier_light", 'POINT')
        fl.energy = 140.0
        fl.color = (1.0, 0.55, 0.2)
        flo = bpy.data.objects.new("tower_brazier_light", fl)
        flo.location = (x, y + 1.0, z + 6.9)
        link(flo)

# ── Footprint registry — overlap rejection (PO v8 item 7) ───────────────────
# Structures self-report an approximate footprint radius when placed; every
# subsequent spot search rejects candidates too close to an already-placed
# structure. Deliberately approximate (a circle, not the real box/roof
# silhouette) — cheap and good enough to stop the visible failure mode
# (two huts overlapping) without needing real collision geometry.
PLACED_FOOTPRINTS = []  # [(x, y, radius), ...]

def register_footprint(x, y, radius):
    PLACED_FOOTPRINTS.append((x, y, radius))

def spot_clear(x, y, radius, min_gap=0.8):
    for fx, fy, fr in PLACED_FOOTPRINTS:
        if math.hypot(x - fx, y - fy) < (radius + fr + min_gap):
            return False
    return True

def find_flat_spot(cx, cy, dmin, dmax, gate_ang, gate_clear=0.5, max_tries=60, foot_r=1.2):
    for threshold in (1.2, 3.0):
        for _ in range(max_tries):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(dmin, dmax)
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            if abs(((a - gate_ang + math.pi) % math.tau) - math.pi) < gate_clear:
                continue
            if not spot_clear(x, y, foot_r):
                continue
            samples = [terrain_h(x + dx, y + dy) for dx, dy in
                       ((0, 0), (1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5))]
            if max(samples) - min(samples) > threshold:
                continue
            return x, y, a
    # Last-resort fallback (unchanged from v7): ignore overlap on this final
    # try too, rather than silently dropping the structure — a slightly
    # tight fit beats a missing well/hut.
    a = gate_ang + math.pi
    d = (dmin + dmax) / 2
    return cx + math.cos(a) * d, cy + math.sin(a) * d, a

def make_cluster_centers(rng):
    """2-3 residential BLOCKS (PO v8 item 2b) — angular sectors that houses
    bias toward, instead of scattering evenly around the full annulus. Real
    settlements read as discrete neighborhoods with alleys/gaps between them
    (occlusion + navigability), not a uniform ring of huts. Fixed spacing
    between sectors (tau/n) plus jitter so blocks don't collide with each
    other, angle-wise."""
    n = rng.choice((2, 3))
    base = rng.uniform(0, math.tau)
    spread = math.tau / n
    return [base + i * spread + rng.uniform(-0.35, 0.35) for i in range(n)]

def find_clustered_spot(cx, cy, dmin, dmax, gate_ang, cluster_angles, spread=0.5,
                         gate_clear=0.5, max_tries=40, foot_r=1.2):
    """Like find_flat_spot but biases the angle toward one of the village's
    2-3 cluster centers instead of sampling the full circle — this is what
    actually produces BLOCKS with gaps between them instead of an even
    scatter. Falls back to the unbiased search if clustering can't find a
    clear, flat spot (keeps the generator robust at any density)."""
    for _ in range(max_tries):
        center_a = rng.choice(cluster_angles)
        a = center_a + rng.uniform(-spread, spread)
        d = rng.uniform(dmin, dmax)
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if abs(((a - gate_ang + math.pi) % math.tau) - math.pi) < gate_clear:
            continue
        if not spot_clear(x, y, foot_r):
            continue
        samples = [terrain_h(x + dx, y + dy) for dx, dy in
                   ((0, 0), (1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5))]
        if max(samples) - min(samples) > 2.2:
            continue
        return x, y, a
    return find_flat_spot(cx, cy, dmin, dmax, gate_ang, gate_clear=gate_clear, foot_r=foot_r)

# ── Paths — dirt strips + trampled/mud ground patches (PO v7 item 1,
#    "the highest-impact item" — this is what makes the village explorable
#    instead of a diorama you review in 5 seconds) ─────────────────────────
DIRT_PATH = (0.34, 0.24, 0.15)
DIRT_PATH_WORN = (0.30, 0.20, 0.12)
MUD_PATCH = (0.27, 0.23, 0.19)
_path_ctr = [0]

def _next_id():
    _path_ctr[0] += 1
    return _path_ctr[0]

def _desire_path_curve(p1, p2, rng, avoid_pad=1.1):
    """Compute a small chain of curve CONTROL points between p1/p2 for a
    DESIRE PATH (PO v9 item 2, 2026-07-19): 'los caminos son rectos como
    reglas hacia la casona — los caminos reales de uso CURVAN
    orgánicamente, evitan obstáculos'. 1-2 interior control points, each
    offset perpendicular to the straight chord by seeded noise (organic
    wobble, not a straight ruler line) AND pushed away from any already-
    placed structure footprint it would otherwise cut through
    (PLACED_FOOTPRINTS — the same registry build_interior's overlap
    rejection already maintains, reused here for free). Returns the full
    ordered point list [p1, ctrl..., p2]; the caller (build_path) samples a
    Catmull-Rom-ish spline through it instead of a straight lerp."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length  # unit perpendicular
    n_ctrl = 1 if length < 7.0 else 2
    pts = [p1]
    for i in range(1, n_ctrl + 1):
        t = i / (n_ctrl + 1)
        bx, by = x1 + dx * t, y1 + dy * t
        wobble = rng.uniform(-0.14, 0.14) * length  # organic curve, scaled to span
        bx += nx * wobble
        by += ny * wobble
        # Obstacle avoidance: push the control point away from any
        # structure footprint it would currently cut through — a real worn
        # path bends AROUND a hut, it doesn't overlap it.
        for fx, fy, fr in PLACED_FOOTPRINTS:
            d = math.hypot(bx - fx, by - fy)
            clear_r = fr + avoid_pad
            if 1e-3 < d < clear_r:
                push = (clear_r - d)
                bx += (bx - fx) / d * push
                by += (by - fy) / d * push
        pts.append((bx, by))
    pts.append(p2)
    return pts

def _catmull_rom(pts, t):
    """Sample a Catmull-Rom spline through `pts` at global parameter
    t in [0,1] (uniform knot spacing) — smooth C1 curve through EVERY
    control point (unlike a Bezier, which only touches the endpoints),
    so the desire-path wobble/obstacle-avoidance offsets computed above
    land exactly where placed. Duplicates the end points as phantom
    control points (the standard trick) so the curve still passes cleanly
    through p1/p2 at t=0/t=1."""
    n = len(pts) - 1
    ext = [pts[0]] + pts + [pts[-1]]
    seg_t = t * n
    i = min(int(seg_t), n - 1)
    lt = seg_t - i
    p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
    lt2, lt3 = lt * lt, lt * lt * lt
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * lt +
               (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * lt2 +
               (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * lt3)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * lt +
               (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * lt2 +
               (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * lt3)
    return x, y

def build_path(p1, p2, width, rng, segs=14, wear=0.5):
    """Flattened dirt-earth path ribbon following terrain between two
    points — a low-poly quad strip, height-matched to terrain_h with a
    hair of lift (+0.02) to avoid z-fighting; width jitters per-segment so
    it reads as trampled ground, not a ruler-straight road.

    DESIRE PATH CURVE (PO v9 item 2, 2026-07-19): the centerline now
    follows a Catmull-Rom spline through `_desire_path_curve`'s
    seeded/obstacle-avoiding control points instead of a straight lerp —
    real wear paths bend organically and route around obstacles, a
    ruler-straight line reads as an artificial diorama path. `segs` bumped
    10->14 (default) so the curve samples smoothly instead of faceting.

    Returns (mesh_object, polyline) — polyline is the ordered list of
    sampled centerline (x, y) points, used by build_interior's hanging-
    decoration placement (PO v9 item 4) to test for path crossings.

    TRAFFIC-WEIGHTED WEAR (v11 item 21, 2026-07-20): `wear` in [0,1] — high
    for a well/plaza/dining destination, low for a private hut/storage —
    scales both the path's WIDTH (wider = more trampled) and its COLOR
    (darker, closer to DIRT_PATH_WORN vs the lighter DIRT_PATH) so
    high-traffic paths visibly read as more worn than low-traffic ones,
    instead of every path sharing one flat tone/width regardless of
    destination."""
    tone = tuple(DIRT_PATH[i] * (1.0 - wear) + DIRT_PATH_WORN[i] * wear for i in range(3))
    if USE_REAL_TEXTURES:
        # v12 pivot: real dirt/mud (or hielo's rocky_trail) photo texture
        # instead of a flat lerped tone — see mat_textured() top docstring.
        dirt = mat_textured("path_" + BIOME, PATH_TEX_SLUG[BIOME], scale=2.2, projection='top')
    else:
        dirt = mat("dirt_path_w%.2f" % wear, tone, rough=0.95)
    ctrl = _desire_path_curve(p1, p2, rng)
    verts, faces, centerline = [], [], []
    prev = None
    for i in range(segs + 1):
        t = i / segs
        x, y = _catmull_rom(ctrl, t)
        centerline.append((x, y))
        # local tangent direction (for the perpendicular ribbon offset) via
        # a small finite-difference sample — cheap and good enough at this
        # curve smoothness/segment count.
        t2 = min(1.0, t + 0.01)
        x2, y2 = _catmull_rom(ctrl, t2)
        dx, dy = x2 - x, y2 - y
        dlen = math.hypot(dx, dy) or 1.0
        px, py = -dy / dlen, dx / dlen
        z = terrain_h(x, y) + 0.02
        w = width * (0.75 + 0.5 * wear) * (1.0 + rng.uniform(-0.15, 0.15))
        verts.append((x + px * w / 2, y + py * w / 2, z))
        verts.append((x - px * w / 2, y - py * w / 2, z))
    for i in range(segs):
        a, b = i * 2, i * 2 + 1
        c, d = (i + 1) * 2, (i + 1) * 2 + 1
        faces.append((a, b, d, c))
    ob = mesh_obj("path_%d" % _next_id(), verts, faces, dirt)
    return ob, centerline

def build_ground_patch(cx, cy, radius, rng, tone=DIRT_PATH_WORN, segs=14, surface="dirt"):
    """Trampled/worn circular ground patch (plaza dirt, mud around the
    well) — same terrain-following technique as build_path, a triangle fan
    instead of a strip. `surface` ('dirt'|'cobblestone', v12 pivot) picks
    the real texture family: 'cobblestone' for the plaza (PoE reference —
    adoquin/paving with dark mossy joints, not flat trampled dirt), 'dirt'
    (default, unchanged) for every other patch (well surrounds etc)."""
    if USE_REAL_TEXTURES and surface == "cobblestone":
        patch_mat = mat_textured("plaza_" + BIOME, PLAZA_TEX_SLUG[BIOME], scale=1.3, projection='top')
    elif USE_REAL_TEXTURES:
        patch_mat = mat_textured("path_" + BIOME, PATH_TEX_SLUG[BIOME], scale=2.2, projection='top')
    else:
        patch_mat = mat("ground_patch_%.2f_%.2f_%.2f" % tone, tone, rough=0.95)
    verts = [(cx, cy, terrain_h(cx, cy) + 0.02)]
    faces = []
    for i in range(segs):
        a = i / segs * math.tau
        r = radius * (1.0 + rng.uniform(-0.12, 0.12))
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        verts.append((x, y, terrain_h(x, y) + 0.02))
    for i in range(segs):
        faces.append((0, 1 + i, 1 + (i + 1) % segs))
    return mesh_obj("ground_patch_%d" % _next_id(), verts, faces, patch_mat)

# ── Commons zone (well / garden / livestock / crafts) — aldea only ─────────
def build_well(cx, cy):
    """OBJECT-IDENTITY PASS (v11 item 9, 2026-07-20): the well used to be a
    solid stone puck (no visible opening), a solid cube "bucket", a single
    rigid rope stick, and a flat-ish roof cap. Fixed at the geometry level:
    (1) the shaft now shows a genuinely darker recessed HOLE inset from the
    ring's top face (cheap no-boolean trick — a matching-radius dark disc
    sunk a hair below the ring's rim reads as an opening, not a solid top);
    (2) the bucket is a tapered frustum (real bucket silhouette, wider top
    than base) with a dark inset top disc for the hollow/carved look; (3)
    the rope is now a short multi-segment polyline with a slight outward
    bulge (implies slack) instead of one dead-straight stick; (4) the roof
    rise is pushed up for a sharper, more clearly PEAKED cap."""
    z = terrain_h(cx, cy)
    stone = mat("stone", (0.47, 0.47, 0.44))
    wood = mat("wood_dark", S["wood_dark"])
    cylinder("well_ring", 0.55, 0.55, (cx, cy, z + 0.275), stone, verts_n=12)
    # SHAFT HOLE — a dark disc recessed just under the ring's rim reads as
    # a genuine opening rather than the ring's solid top face.
    hole_mat = mat("well_hole_dark", (0.03, 0.03, 0.035), rough=0.95)
    cylinder("well_hole", 0.40, 0.10, (cx, cy, z + 0.50), hole_mat, verts_n=12)
    for px in (-0.55, 0.55):
        cylinder("well_post_%.2f" % px, 0.05, 1.3, (cx + px, cy, z + 0.55 + 0.65), wood, verts_n=6)
    gable_roof("well_roof", 1.4, 1.4, 0.68, (cx, cy, z + 1.9), mat("roof", S["roof"]))
    # ROPE — short multi-segment polyline with a slight outward bulge
    # (implies slack) instead of one rigid straight stick.
    rope_top, rope_bot = z + 1.85, z + 0.76
    rope_n = 4
    rope_pts = []
    for ri in range(rope_n + 1):
        f = ri / rope_n
        rz = rope_top + (rope_bot - rope_top) * f
        bulge = math.sin(f * math.pi) * 0.035
        rope_pts.append((cx + bulge, cy, rz))
    for ri in range(rope_n):
        strut("well_rope_%d" % ri, rope_pts[ri], rope_pts[ri + 1], 0.018, wood, verts_n=5)
    # BUCKET — tapered frustum (wider top than base, real bucket
    # silhouette) with a dark inset disc suggesting a hollow/carved vessel.
    # radius1 = BASE (bottom, -Z), radius2 = TOP (+Z) for primitive_cone_add
    # — a real bucket is narrower at the base than at the open top.
    bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.095, radius2=0.13, depth=0.20,
                                     location=(cx, cy, z + 0.65))
    bucket = bpy.context.object
    bucket.name = "well_bucket"
    bucket.data.materials.append(wood)
    cylinder("well_bucket_hollow", 0.10, 0.02, (cx, cy, z + 0.65 + 0.095), hole_mat, verts_n=10)
    strut("well_bucket_handle", (cx - 0.09, cy, z + 0.65 + 0.11), (cx + 0.09, cy, z + 0.65 + 0.11),
          0.012, wood, verts_n=4)

def build_garden(cx, cy, idx, rng):
    """CROP VARIETY (v11 item 26, 2026-07-20): the old version repeated ONE
    silhouette (a flattened ellipsoid "circle-on-top") in only 3 green-ish
    tones — reads as one crop copy-pasted. Now rolls one of 3 DISTINCT
    silhouettes per bed (leafy cluster / tall stalk / round vegetable)
    across a widened tone palette (greens, yellows, a couple of reddish
    roots) so the plot doesn't read as a single repeated object."""
    z = terrain_h(cx, cy)
    soil = mat("soil", (0.24, 0.16, 0.10))
    crop_tones = [(0.20, 0.42, 0.16), (0.55, 0.45, 0.10), (0.30, 0.44, 0.14),
                  (0.62, 0.24, 0.16), (0.68, 0.58, 0.18)]
    rows, cols = 2, 3
    for r in range(rows):
        for c in range(cols):
            bx = cx + (c - (cols - 1) / 2) * 0.55
            by = cy + (r - (rows - 1) / 2) * 0.55
            box("garden_%d_bed_%d_%d" % (idx, r, c), 0.48, 0.48, 0.10, (bx, by, z + 0.05), soil)
            crop = crop_tones[rng.randrange(len(crop_tones))]
            crop_mat = mat("crop_%.2f_%.2f_%.2f" % crop, crop)
            silhouette = rng.choice(("leafy", "stalk", "vegetable"))
            if silhouette == "stalk":
                cylinder("garden_%d_crop_%d_%d" % (idx, r, c), 0.045, 0.32,
                          (bx, by, z + 0.21), crop_mat, verts_n=6)
                ellipsoid("garden_%d_crop_%d_%d_top" % (idx, r, c), 0.09, 0.09, 0.07,
                          (bx, by, z + 0.40), crop_mat)
            elif silhouette == "vegetable":
                ellipsoid("garden_%d_crop_%d_%d" % (idx, r, c), 0.13, 0.13, 0.12,
                           (bx, by, z + 0.14), crop_mat)
            else:  # leafy cluster — the original wide flattened silhouette
                ellipsoid("garden_%d_crop_%d_%d" % (idx, r, c), 0.16, 0.16, 0.10,
                           (bx, by, z + 0.16), crop_mat)

def build_sheep(cx, cy, cz, rng, pose=None):
    """Real-silhouette sheep (PO v7 item 3): identity through SILHOUETTE, not
    polycount — wool-mass rounded body, a narrow head poking out the front,
    side ears, 4 thin DARK legs (contrast against the pale wool), small
    tail. Legs built via strut() — the same point-to-point cylinder
    technique as clown_gen.py's limb().

    POSE VARIETY (PO v8 item 6): `pose` in {'graze','alert','lying'}
    (rolled per-sheep if None, weighted so most graze, some watch, a few
    lie down) — a flock of identically-posed sheep reads as copy-paste.
    REAL motion (walking, chewing, tail flick) stays GAME-SIDE (Godot);
    this generator only varies the STATIC pose so a still render carries
    some life without pretending to animate anything."""
    pose = pose or rng.choices(("graze", "alert", "lying"), weights=(0.5, 0.35, 0.15))[0]
    n = _next_id()
    wool = (0.80 + rng.uniform(-0.05, 0.05), 0.78 + rng.uniform(-0.05, 0.05), 0.70 + rng.uniform(-0.05, 0.05))
    wool_mat = mat("sheep_wool_%.2f_%.2f_%.2f" % wool, wool, rough=0.95)
    dark_mat = mat("sheep_dark", (0.15, 0.12, 0.10), rough=0.6)
    if pose == "lying":
        body_h = 0.26
        ellipsoid("sheep_%d_body" % n, 0.34, 0.27, body_h, (cx, cy, cz + body_h), wool_mat)
        head_z = cz + body_h * 0.85
        head_x = cx + 0.32
        ellipsoid("sheep_%d_head" % n, 0.11, 0.09, 0.10, (head_x, cy, head_z), dark_mat)
        for s in (-1, 1):
            ellipsoid("sheep_%d_ear_%d" % (n, s), 0.06, 0.02, 0.03,
                       (head_x - 0.02, cy + s * 0.09, head_z + 0.02), dark_mat)
        # Legs folded under — short stubs, most of the leg hidden under the
        # settled body (the actual "lying down" tell vs. standing).
        for lx, ly in ((-0.16, -0.13), (-0.16, 0.13), (0.14, -0.12), (0.14, 0.12)):
            strut("sheep_%d_leg_%d_%d" % (n, int(lx * 100), int(ly * 100)),
                  (cx + lx, cy + ly, cz + body_h * 0.55), (cx + lx, cy + ly, cz - 0.01),
                  0.026, dark_mat, verts_n=5)
        ellipsoid("sheep_%d_tail" % n, 0.05, 0.05, 0.06, (cx - 0.34, cy, cz + body_h * 0.9), wool_mat)
        return
    body_h = 0.42
    ellipsoid("sheep_%d_body" % n, 0.32, 0.24, 0.22, (cx, cy, cz + body_h), wool_mat)
    head_x = cx + 0.34
    if pose == "alert":
        head_z = cz + body_h + 0.06   # level with / just above the back — watching, ears up
    else:  # graze — LOWER than the wool mass's top, the head-down tell
        head_z = cz + body_h - 0.22
    ellipsoid("sheep_%d_head" % n, 0.11, 0.09, 0.10, (head_x, cy, head_z), dark_mat)
    for s in (-1, 1):  # side ears — perked a touch higher when alert
        ear_z = head_z + (0.05 if pose == "alert" else 0.02)
        ellipsoid("sheep_%d_ear_%d" % (n, s), 0.06, 0.02, 0.03,
                   (head_x - 0.02, cy + s * 0.09, ear_z), dark_mat)
    for lx, ly in ((-0.16, -0.13), (-0.16, 0.13), (0.14, -0.12), (0.14, 0.12)):
        strut("sheep_%d_leg_%d_%d" % (n, int(lx * 100), int(ly * 100)),
              (cx + lx, cy + ly, cz + body_h - 0.14), (cx + lx, cy + ly, cz - 0.02),
              0.028, dark_mat, verts_n=5)
    ellipsoid("sheep_%d_tail" % n, 0.05, 0.05, 0.06, (cx - 0.34, cy, cz + body_h - 0.02), wool_mat)

def build_goat(cx, cy, cz, rng, pose=None):
    """Goat variant (PO v10 item 4, 2026-07-20 — Axlin's bestiary text
    explicitly names goat wool, not sheep, as the enclave's livestock).
    Reuses build_sheep()'s exact silhouette GRAMMAR (hide/wool mass + head
    + legs + tail, same strut()-based legs) but with goat-specific cues,
    kept CHEAP per the item's own "modest" instruction: (1) NO dense wool
    poof — a narrower, straighter/leaner body mass instead of sheep's round
    wool blob; (2) small backswept horns on the head; (3) a short upturned
    tail instead of sheep's low tuft. Pose reuses the same
    graze/alert/lying enum as build_sheep (PO v8 item 6 pose variety) —
    the grammar is shared, only the proportions/horns differ."""
    pose = pose or rng.choices(("graze", "alert", "lying"), weights=(0.5, 0.35, 0.15))[0]
    n = _next_id()
    hide = (0.62 + rng.uniform(-0.08, 0.08), 0.58 + rng.uniform(-0.08, 0.08), 0.52 + rng.uniform(-0.06, 0.06))
    hide_mat = mat("goat_hide_%.2f_%.2f_%.2f" % hide, hide, rough=0.85)
    dark_mat = mat("sheep_dark", (0.15, 0.12, 0.10), rough=0.6)
    horn_mat = mat("goat_horn", (0.30, 0.27, 0.22), rough=0.5)

    def horns(head_x, head_z):
        for s in (-1, 1):
            base = (head_x - 0.02, cy + s * 0.05, head_z + 0.06)
            tip = (head_x - 0.14, cy + s * 0.10, head_z + 0.22)
            strut("goat_%d_horn_%d" % (n, s), base, tip, 0.018, horn_mat, verts_n=4)

    if pose == "lying":
        body_h = 0.22
        ellipsoid("goat_%d_body" % n, 0.32, 0.20, body_h, (cx, cy, cz + body_h), hide_mat)
        head_z = cz + body_h * 0.9
        head_x = cx + 0.33
        ellipsoid("goat_%d_head" % n, 0.10, 0.08, 0.09, (head_x, cy, head_z), hide_mat)
        horns(head_x, head_z)
        for lx, ly in ((-0.15, -0.11), (-0.15, 0.11), (0.14, -0.10), (0.14, 0.10)):
            strut("goat_%d_leg_%d_%d" % (n, int(lx * 100), int(ly * 100)),
                  (cx + lx, cy + ly, cz + body_h * 0.55), (cx + lx, cy + ly, cz - 0.01),
                  0.022, dark_mat, verts_n=5)
        ellipsoid("goat_%d_tail" % n, 0.04, 0.03, 0.05, (cx - 0.32, cy, cz + body_h * 1.1), hide_mat)
        return
    # STRAIGHTER BODY (goat cue vs sheep's round wool mass): narrower/
    # leaner ellipsoid proportions, no extra "wool poof" scale-up.
    body_h = 0.40
    ellipsoid("goat_%d_body" % n, 0.28, 0.17, 0.19, (cx, cy, cz + body_h), hide_mat)
    head_x = cx + 0.35
    head_z = cz + body_h + 0.05 if pose == "alert" else cz + body_h - 0.16
    ellipsoid("goat_%d_head" % n, 0.10, 0.08, 0.09, (head_x, cy, head_z), hide_mat)
    horns(head_x, head_z)
    for s in (-1, 1):
        ear_z = head_z + (0.03 if pose == "alert" else 0.0)
        ellipsoid("goat_%d_ear_%d" % (n, s), 0.05, 0.02, 0.025,
                   (head_x - 0.02, cy + s * 0.08, ear_z), hide_mat)
    for lx, ly in ((-0.14, -0.11), (-0.14, 0.11), (0.13, -0.10), (0.13, 0.10)):
        strut("goat_%d_leg_%d_%d" % (n, int(lx * 100), int(ly * 100)),
              (cx + lx, cy + ly, cz + body_h - 0.13), (cx + lx, cy + ly, cz - 0.02),
              0.024, dark_mat, verts_n=5)
    # Short UPTURNED tail (vs sheep's low wool tuft) — the other cheap
    # goat-vs-sheep silhouette tell.
    tail = ellipsoid("goat_%d_tail" % n, 0.035, 0.03, 0.06, (cx - 0.32, cy, cz + body_h + 0.02), hide_mat)
    tail.rotation_euler = (math.radians(-25), 0, 0)


def build_chicken(cx, cy, cz, rng, pose=None):
    """Real-silhouette chicken (PO v7 item 3): body + small head + beak +
    tail wedge + 2 legs.

    POSE VARIETY (PO v8 item 6): `pose` in {'normal','pecking'} (rolled
    per-bird if None) — a scattered flock should show some mid-peck (body
    tilted forward, head down at the ground), not every bird standing
    identically upright. Real motion is GAME-SIDE (Godot); this only varies
    the static pose."""
    pose = pose or ("pecking" if rng.random() < 0.4 else "normal")
    n = _next_id()
    tones = [(0.85, 0.82, 0.75), (0.55, 0.38, 0.22), (0.25, 0.22, 0.20)]
    tone = tones[rng.randrange(len(tones))]
    body_mat = mat("chicken_%.2f_%.2f_%.2f" % tone, tone, rough=0.9)
    beak_mat = mat("chicken_beak", (0.85, 0.55, 0.12), rough=0.5)
    leg_mat = mat("chicken_leg", (0.75, 0.45, 0.12), rough=0.6)
    body_h = 0.16
    body_tilt = math.radians(24) if pose == "pecking" else 0.0
    body = ellipsoid("chicken_%d_body" % n, 0.11, 0.09, body_h, (cx, cy, cz + body_h), body_mat)
    body.rotation_euler = (0, body_tilt, 0)
    if pose == "pecking":
        head_z = cz + body_h * 0.5   # down near the ground — the peck
        head_x = cx + 0.15
    else:
        head_z = cz + body_h * 2.0
        head_x = cx + 0.09
    ellipsoid("chicken_%d_head" % n, 0.045, 0.045, 0.045, (head_x, cy, head_z), body_mat)
    bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.02, depth=0.05, location=(head_x + 0.06, cy, head_z))
    beak = bpy.context.object
    beak.name = "chicken_%d_beak" % n
    beak.data.materials.append(beak_mat)
    beak.rotation_euler = (0, math.radians(90) + body_tilt, 0)
    tail_z = cz + body_h * (1.7 if pose == "pecking" else 1.5)
    box("chicken_%d_tail" % n, 0.03, 0.09, 0.10, (cx - 0.12, cy, tail_z), body_mat)
    for ly in (-0.03, 0.03):
        strut("chicken_%d_leg_%d" % (n, int(ly * 100)), (cx, cy + ly, cz + 0.06), (cx, cy + ly, cz - 0.02),
              0.012, leg_mat, verts_n=4)

def build_livestock_pen(cx, cy, rng, size="small"):
    """Sheep pen — footprint AND flock size scale together (PO v7 item 3
    coherence rule: 'big pen 6-8 sheep, small pen 2-3', never a fixed count
    independent of the fence you drew)."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", S["wood_dark"])
    # ENLARGED PEN (v11 item 25, 2026-07-20): the old footprint (4.6x3.8 /
    # 3.2x2.6) read as a decorative 4-post marker rather than a real
    # grazing enclosure. No dedicated reference-image research was done
    # this pass (time-boxed — flagged honestly per the item's own
    # instruction rather than skipped silently); sizes below are a
    # reasonable proportion bump from general knowledge (a working pen
    # needs meaningfully more area per animal than a token rectangle) —
    # confirm with real sheep-pen/coop reference photos before a bigger
    # swing. See game/docs/art/_references/livestock_pens/ (not yet
    # populated).
    if size == "big":
        w, d, count = 6.2, 5.0, rng.randint(6, 8)
    else:
        w, d, count = 4.3, 3.5, rng.randint(2, 3)
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        p1 = (cx + x1, cy + y1, z + 0.5)
        p2 = (cx + x2, cy + y2, z + 0.5)
        strut("pen_rail_%d" % i, p1, p2, 0.035, wood, verts_n=6)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        cylinder("pen_post_%d" % i, 0.05, 0.9, (cx + mx, cy + my, z + 0.45), wood, verts_n=6)
    for a in range(count):
        ax = cx + rng.uniform(-w * 0.32, w * 0.32)
        ay = cy + rng.uniform(-d * 0.32, d * 0.32)
        az = terrain_h(ax, ay)
        # PO v8 item 6 explicitly asks for "one lying" — guarantee it on the
        # first sheep of any pen with 3+ (rather than leave it to chance,
        # which could roll an all-standing flock on an unlucky seed).
        pose = "lying" if (a == 0 and count >= 3) else None
        # GOAT COHERENCE (PO v10 item 4, 2026-07-20): Axlin's bestiary text
        # names goat wool specifically (not sheep) as the enclave's
        # livestock — a 'pieles' economy roll should PREFER goats; every
        # other economy still gets a MODEST goat sprinkle for variety
        # (sheep working is fine, this is an alternate roll, not a
        # replacement — per the item's own "keep this modest" instruction).
        goat_chance = 0.65 if ECONOMY_NAME == "pieles" else 0.15
        if rng.random() < goat_chance:
            build_goat(ax, ay, az, rng, pose=pose)
        else:
            build_sheep(ax, ay, az, rng, pose=pose)

def build_coop(cx, cy, rng, style):
    """Small chicken coop + a few chickens scratching nearby (PO v7 item 3
    — 'chickens near a coop')."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    box("coop_box", 1.0, 0.8, 0.55, (cx, cy, z + 0.275), mat("wood", style["wood"]))
    gable_roof("coop_roof", 1.15, 0.95, 0.3, (cx, cy, z + 0.55), mat("roof", style["roof"]))
    box("coop_ramp", 0.3, 0.5, 0.05, (cx, cy - 0.55, z + 0.12), wood)
    for i in range(rng.randint(3, 5)):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.6, 1.4)
        cx2, cy2 = cx + math.cos(a) * r, cy + math.sin(a) * r
        build_chicken(cx2, cy2, terrain_h(cx2, cy2), rng)

def build_storage_shed(cx, cy, rng, style):
    """Small utility lean-to (PO v7 item 2 density) — cheaper than a full
    named hut so it reads as background population filling out the ~12
    structure target without competing with the functional zones."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    box("shed_walls", 1.4, 1.1, 1.5, (cx, cy, z + 0.75), mat("wood", style["wood"]))
    gable_roof("shed_roof", 1.55, 1.25, 0.5, (cx, cy, z + 1.5), mat("roof", style["roof"]))
    for li in range(3):
        log_ob = cylinder("shed_log_%d" % li, 0.08, 0.9, (cx + 0.9 + li * 0.02, cy, z + 0.09 + li * 0.15),
                            wood, verts_n=7)
        log_ob.rotation_euler = (0, math.pi / 2, rng.uniform(-0.1, 0.1))

def build_woodpile_axe(cx, cy, rng, style):
    """Woodpile + axe embedded in a stump (PO v7 item 5 life signal) — an
    unconditional background prop, independent of whether crafts_area
    rolled (that one already has its own smaller woodpile)."""
    z = terrain_h(cx, cy)
    wood_dark = mat("wood_dark", style["wood_dark"])
    stump = cylinder("woodpile_stump", 0.22, 0.4, (cx, cy, z + 0.2), mat("stone", (0.38, 0.34, 0.26)), verts_n=9)
    handle_top = (cx + 0.05, cy, z + 0.55)
    strut("woodpile_axe_handle", (cx, cy, z + 0.40), handle_top, 0.025, wood_dark, verts_n=6)
    blade = box("woodpile_axe_blade", 0.05, 0.16, 0.12, (cx + 0.10, cy, z + 0.55),
                mat("axe_blade", (0.55, 0.56, 0.58), rough=0.35))
    blade.rotation_euler = (0, math.radians(20), 0)
    for li in range(4):
        log_ob = cylinder("woodpile_log_%d" % li, 0.10, 1.0,
                            (cx - 0.55 + li * 0.03, cy + 0.5, z + 0.11 + li * 0.19), wood_dark, verts_n=7)
        log_ob.rotation_euler = (0, math.pi / 2, rng.uniform(-0.12, 0.12))

def build_log_pile(cx, cy, z, rng, wood_mat, n_logs=16, log_len=0.55, layers=4):
    """Chopped/split firewood stack (v11 item 18, 2026-07-20) — was a
    handful of long whole logs in a single row, "too small" per Joan.
    Crisscross LAYERS of short split-log segments alternating perpendicular
    direction (like a real stacked woodpile), each log varying radius/
    length slightly so it reads as split wood, not uniform dowels."""
    per_layer = max(2, n_logs // layers)
    for layer in range(layers):
        horiz = (layer % 2 == 0)
        lz = z + 0.08 + layer * 0.16
        for li in range(per_layer):
            off = (li - (per_layer - 1) / 2) * 0.16
            r = rng.uniform(0.06, 0.10)
            ll = log_len * rng.uniform(0.85, 1.15)
            if horiz:
                p1 = (cx - ll / 2, cy + off, lz)
                p2 = (cx + ll / 2, cy + off, lz)
            else:
                p1 = (cx + off, cy - ll / 2, lz)
                p2 = (cx + off, cy + ll / 2, lz)
            strut("logpile_%d_%d_%d_%d" % (int(cx * 10), int(cy * 10), layer, li),
                  p1, p2, r, wood_mat, verts_n=7)

def build_crafts_area(cx, cy, rng, economy_tag=None):
    """economy_tag='metal' (herreria economy, PO principle 5) adds a fuel/
    ingot pile next to the anvil — module-internal coherence rule (PO
    addendum 2026-07-18): a working forge never shows an anvil ALONE, it
    needs its supporting fuel/stock detail right there."""
    z = terrain_h(cx, cy)
    wood = mat("wood", S["wood"])
    wood_dark = mat("wood_dark", S["wood_dark"])
    for lx, ly in ((-0.5, -0.35), (-0.5, 0.35), (0.5, -0.35), (0.5, 0.35)):
        cylinder("craft_bench_leg_%d_%d" % (int(lx * 10), int(ly * 10)), 0.04, 0.75,
                  (cx + lx, cy + ly, z + 0.375), wood_dark, verts_n=6)
    box("craft_bench_top", 1.3, 0.7, 0.08, (cx, cy, z + 0.79), wood)
    stump = cylinder("craft_stump", 0.28, 0.5, (cx + 1.0, cy, z + 0.25), mat("stone", (0.4, 0.4, 0.38)), verts_n=9)
    box("craft_anvil", 0.22, 0.4, 0.22, (cx + 1.0, cy, z + 0.62), mat("stone", (0.25, 0.25, 0.27), rough=0.4))
    if economy_tag == "metal":
        ingot_mat = mat("iron_ingot", (0.58, 0.58, 0.60), rough=0.35)
        for ii in range(3):
            box("craft_ingot_%d" % ii, 0.10, 0.20, 0.06,
                (cx + 1.35, cy - 0.25 + ii * 0.22, z + 0.53), ingot_mat)
    # FIREWOOD PILE (v11 item 18, 2026-07-20) — was 4 long whole logs in a
    # thin row, too small next to the anvil/forge; a bigger crisscross
    # stack of chopped/split segments reads as real fuel supply.
    wx, wy = cx - 1.3, cy
    build_log_pile(wx, wy, z, rng, wood_dark, n_logs=16, log_len=0.55, layers=4)

def build_granary(cx, cy, rng, style):
    """Small raised storage crib (module-pool 'granary', 25% weight) — short
    stilts keep grain off damp/vermin ground, distinct from `hut_storage`
    (which is a full stone-footed room, not a crib)."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    stilt_h = 0.65
    for sx_, sy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        cylinder("granary_stilt_%d_%d" % (sx_, sy_), 0.06, stilt_h,
                  (cx + sx_ * 0.5, cy + sy_ * 0.4, z + stilt_h / 2), wood, verts_n=6)
    box("granary_bin", 1.2, 1.0, 0.85, (cx, cy, z + stilt_h + 0.425), mat("wood", style["wood"]))
    gable_roof("granary_roof", 1.35, 1.15, 0.4, (cx, cy, z + stilt_h + 0.85),
               mat("roof", style["roof"]))
    build_stairs("granary", cx, cy - 0.5, z, z + stilt_h, 2, style, width=0.4)

def build_covered_plaza(cx, cy):
    """Flyers threat — a roofed structure over the commons hub (protects the
    hearth/well cluster from anything descending from above)."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", S["wood_dark"])
    span = 4.6
    for sx_, sy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        cylinder("plaza_post_%d_%d" % (sx_, sy_), 0.10, 2.8,
                  (cx + sx_ * span / 2, cy + sy_ * span / 2, z + 1.4), wood, verts_n=8)
    gable_roof("plaza_roof", span * 1.08, span * 1.08, 1.2, (cx, cy, z + 2.85),
               mat("roof_thatch", (0.52, 0.42, 0.22)))

# ── ERA/TECH COHERENCE RULE (PO live addendum, 2026-07-20 — general
#    principle, applies now and to every future pass) ───────────────────────
# Decoration and props must match the settlement's implied tech level —
# nothing that reads as modern/21st-century on medieval-reading huts.
# Everything built by this generator (wood/cloth/stone/rope/fired-clay only —
# no metal-modern look, no glass beyond the window panes, no printed
# text/plastics) already satisfies this; the NEW v10 additions below stay
# inside the same material vocabulary on purpose: the market stalls are
# wood posts + cloth awning + wood barrels/cloth sacks/woven baskets (same
# families as every hut's door/frame/sack props), the poor-footing rocks
# reuse make_rock()'s existing stone family, and the goat/annex additions
# introduce ZERO new material types at all. Confirm this explicitly before
# adding any future prop family: if it wouldn't exist in a wood/stone/
# cloth/rope/thatch/fired-clay-pot economy, it doesn't belong here.

# ── Market (PO v10 item 3, 2026-07-20) ──────────────────────────────────────
# village_settlement_logic addendum + village_lotr synthesis: "the market is
# NOT a building — it's cloth awnings over stalls clustered at the highest-
# traffic point" (Whiterun's well, DanMachi's main street). Each stall picks
# its OWN awning color (never matching its neighbors) + a barrel/basket/sack
# goods cluster at its base ("inventory lives outdoors"). See build_interior
# for the economy/intensity weighting (Axlin principle: high threat = zero
# commerce, only rare traveling peddlers — a 'dangerous' intensity village
# never rolls a market at all).
STALL_AWNING_COLORS = [
    (0.55, 0.12, 0.10),   # red
    (0.15, 0.30, 0.52),   # blue
    (0.58, 0.42, 0.10),   # mustard/gold
    (0.20, 0.42, 0.22),   # green
]

def build_market_stall(name, cx, cy, rng, style, color):
    """One stall: 4-post frame + a cloth awning plane in `color` (distinct
    per stall, never the biome's shared accent) + a front counter board +
    a barrel/basket/sack cluster at the base — a stall never appears with
    just the awning (module-internal coherence rule: goods imply storage,
    same logic as the forge's fuel pile / kitchen's pots)."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    w, d, h = 1.6, 1.1, 1.7
    for sx_, sy_ in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        cylinder("%s_post_%d_%d" % (name, sx_, sy_), 0.05, h,
                  (cx + sx_ * w / 2, cy + sy_ * d / 2, z + h / 2), wood, verts_n=6)
    awning_mat = mat("market_awning_%.2f_%.2f_%.2f" % color, color, rough=0.85)
    awning = box(name + "_awning", w * 1.15, d * 1.15, 0.06, (cx, cy, z + h + 0.03), awning_mat)
    awning.rotation_euler = (0, 0, rng.uniform(-0.05, 0.05))
    box(name + "_counter", w * 0.92, 0.35, 0.6, (cx, cy - d / 2 + 0.15, z + 0.3), wood)
    # Goods cluster — barrel + basket + sack, "inventory lives outdoors"
    # (village_lotr synthesis: baskets/barrels/sacks stacked informally).
    cylinder(name + "_barrel", 0.20, 0.42, (cx - w * 0.32, cy + d * 0.30, z + 0.21),
              mat("wood", style["wood"]), verts_n=9)
    basket_mat = mat("market_basket", (0.55, 0.42, 0.24), rough=0.9)
    ellipsoid(name + "_basket", 0.18, 0.18, 0.14, (cx + w * 0.10, cy + d * 0.32, z + 0.14), basket_mat)
    sack_mat = mat("sack_cloth", (0.55, 0.48, 0.34), rough=0.95)
    sack = ellipsoid(name + "_sack", 0.16, 0.15, 0.20, (cx + w * 0.32, cy + d * 0.28, z + 0.19), sack_mat)
    sack.rotation_euler = (0, 0, rng.uniform(-0.3, 0.3))
    register_footprint(cx, cy, max(w, d) / 2 + 0.6)

def build_market(cx, cy, count, rng, style):
    """`count` stalls (2 or 3) clustered near the highest-traffic commons
    point — each shuffled to a DISTINCT color from STALL_AWNING_COLORS so
    no two stalls in the same market match."""
    palette = list(STALL_AWNING_COLORS)
    rng.shuffle(palette)
    for i in range(count):
        a = (i / count) * math.tau * 0.55 + rng.uniform(-0.2, 0.2)
        r = 2.0 + rng.uniform(-0.2, 0.3)
        sx_, sy_ = cx + math.cos(a) * r, cy + math.sin(a) * r
        build_market_stall("market_stall_%d" % i, sx_, sy_, rng, style, palette[i % len(palette)])

# ── Cemetery (PO live addendum, 2026-07-20) ─────────────────────────────────
# Small graveyard patch — pure ATMOSPHERE, never a core building, hence the
# deliberately LOW MODULE_POOL weight below. Simple wood-post-and-crossbar
# or upright-stone-slab markers, varied height/lean the same way
# build_palisade already varies its stakes (small per-marker lean jitter,
# never a perfectly upright row) — wood/stone only, satisfies the era/tech
# coherence rule above.
def build_grave_marker(name, x, y, rng, style):
    z = terrain_h(x, y)
    if rng.random() < 0.4:
        wood = mat("wood_dark", style["wood_dark"])
        h = rng.uniform(0.55, 0.85)
        marker = cylinder(name + "_post", 0.035, h, (x, y, z + h / 2), wood, verts_n=6)
        box(name + "_crossbar", 0.32, 0.05, 0.05, (x, y, z + h * 0.72), wood)
    else:
        stone = mat("grave_stone", (0.50, 0.49, 0.46), rough=0.85)
        h = rng.uniform(0.42, 0.70)
        w = rng.uniform(0.22, 0.32)
        marker = box(name + "_slab", w, 0.08, h, (x, y, z + h / 2), stone)
    marker.rotation_euler = (rng.uniform(-0.09, 0.09), rng.uniform(-0.06, 0.06), rng.uniform(0, math.tau))

def build_cemetery(cx, cy, rng, style):
    """3-6 grave markers in a fenced-off corner (build_yard_fence reused —
    same low garden-fence height, never a second palisade)."""
    n = rng.randint(3, 6)
    for i in range(n):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.3, 1.5)
        mx, my = cx + math.cos(a) * r, cy + math.sin(a) * r
        build_grave_marker("grave_%d" % i, mx, my, rng, style)
    build_yard_fence(cx, cy, 3.6, 3.2, rng, style)
    register_footprint(cx, cy, 2.2)

# ── Exterior life accessories (PO v8 item 3) ────────────────────────────────
# The v7 verdict was "nothing to discover" beyond the named functional huts —
# these are yard-scale props (never their own named building) meant to be
# rolled into the module pool and scattered ALONG the residential band so a
# walk-through reveals them one at a time instead of dumping them all next
# to the plaza.
def build_loom(cx, cy, rng, style):
    """Standing loom / telar — frame + taut vertical warp threads. A blank
    frame reads as furniture, not a craft; the alternating-tone threads are
    what say WEAVING at a glance."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    w, h = 0.9, 1.3
    for px in (-w / 2, w / 2):
        cylinder("loom_post_%d" % int(px * 100), 0.035, h, (cx + px, cy, z + h / 2), wood, verts_n=6)
    for pz in (0.08, h - 0.08):
        box("loom_bar_%.2f" % pz, w + 0.10, 0.05, 0.05, (cx, cy, z + pz), wood)
    yarns = [(0.62, 0.22, 0.18), (0.75, 0.65, 0.30)]
    n_threads = 7
    for i in range(n_threads):
        tx = cx - w / 2 + 0.10 + (w - 0.20) * i / (n_threads - 1)
        tone = yarns[i % 2]
        strut("loom_thread_%d" % i, (tx, cy, z + 0.10), (tx, cy, z + h - 0.10), 0.012,
              mat("yarn_%.2f_%.2f_%.2f" % tone, tone, rough=0.9), verts_n=4)
    register_footprint(cx, cy, 0.7)

def build_hide_rack(cx, cy, rng, style):
    """Hide-tanning rack — a stretched pelt lashed to a frame, propped at an
    angle against 2 legs (distinct from the wall-mounted `drying_rack` prop
    already on some houses — this is a standalone yard fixture)."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    hide_tone = (0.58, 0.42, 0.26)
    frame_w, frame_h = 0.9, 1.1
    tilt = math.radians(28)
    for side in (-1, 1):
        p1 = (cx + side * frame_w / 2, cy, z)
        p2 = (cx + side * frame_w / 2, cy - frame_h * math.sin(tilt), z + frame_h * math.cos(tilt))
        strut("hide_rack_leg_%d" % side, p1, p2, 0.04, wood, verts_n=6)
    hide = box("hide_rack_hide", frame_w * 0.92, 0.03, frame_h * 0.85,
               (cx, cy - (frame_h * 0.5) * math.sin(tilt), z + (frame_h * 0.5) * math.cos(tilt)),
               mat("hide_tanning", hide_tone, rough=0.95))
    hide.rotation_euler = (tilt, 0, 0)
    register_footprint(cx, cy, 0.7)

def build_outdoor_kitchen(cx, cy, rng, style):
    """Roofed outdoor cooking counter + pots + bench seats — module-internal
    coherence rule: a cooking counter never appears without its pots, a
    kitchen prop without seating implies no one actually eats there."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    counter_w, counter_d, counter_h = 1.6, 0.6, 0.75
    box("cook_counter", counter_w, counter_d, counter_h, (cx, cy, z + counter_h / 2), mat("wood", style["wood"]))
    # SCALE FIX (v11 item 13, 2026-07-20): pots at r=0.14/h=0.18 (28cm
    # diameter) read oversized against the 1.6m counter/0.32m-tall bench —
    # shrunk to a sensible tabletop-cookware scale.
    pot_mat = mat("iron_pot", (0.22, 0.22, 0.24), rough=0.4)
    for i, px in enumerate((-0.45, 0.0, 0.45)):
        cylinder("cook_pot_%d" % i, 0.085, 0.13, (cx + px, cy, z + counter_h + 0.065), pot_mat, verts_n=9)
    for px in (-counter_w / 2 - 0.1, counter_w / 2 + 0.1):
        for py in (-counter_d / 2 - 0.1, counter_d / 2 + 0.1):
            cylinder("cook_post_%d_%d" % (int(px * 10), int(py * 10)), 0.06, 2.0,
                      (cx + px, cy + py, z + 1.0), wood, verts_n=6)
    gable_roof("cook_roof", counter_w + 0.6, counter_d + 1.4, 0.5, (cx, cy, z + 2.05), mat("roof", style["roof"]))
    for s in (-1, 1):
        box("cook_bench_%d" % s, 1.0, 0.28, 0.32, (cx + s * 0.3, cy + counter_d / 2 + 0.6, z + 0.16), wood)
    register_footprint(cx, cy, 1.4)

def build_outdoor_seat(cx, cy, rng, style):
    """Bench, sit-log, or stump-seat — cheap background seating (PO v8 item
    3 'more outdoor seating'; v11 item 24, 2026-07-20 added the stump
    variant — a short WIDE cylinder standing upright, distinct from the
    long lying sit-log), 3 variants so a scatter of 2-3 doesn't repeat."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    roll = rng.random()
    if roll < 0.35:
        log = cylinder("seat_log", 0.16, 1.1, (cx, cy, z + 0.16), wood, verts_n=9)
        log.rotation_euler = (0, math.pi / 2, rng.uniform(0, math.tau))
    elif roll < 0.65:
        # STUMP SEAT (v11 item 24) — short wide upright cylinder, with a
        # couple of top rings suggesting cut growth lines.
        stump_mat = mat("stump_wood", (0.32, 0.22, 0.13), rough=0.85)
        cylinder("seat_stump", 0.24, 0.36, (cx, cy, z + 0.18), stump_mat, verts_n=10)
        ring_mat = mat("stump_ring", (0.24, 0.16, 0.09), rough=0.85)
        cylinder("seat_stump_ring", 0.16, 0.02, (cx, cy, z + 0.365), ring_mat, verts_n=10)
    else:
        box("seat_bench_top", 1.0, 0.30, 0.06, (cx, cy, z + 0.30), wood)
        for sx_ in (-0.4, 0.4):
            box("seat_bench_leg_%d" % int(sx_ * 10), 0.06, 0.26, 0.28, (cx + sx_, cy, z + 0.14), wood)
    register_footprint(cx, cy, 0.6)

def build_flower_cluster(cx, cy, rng, style):
    """Tiny colored blob cluster on thin stems (v11 item 24, 2026-07-20) —
    cheap life-detail near paths/house corners, not a functional module."""
    z = terrain_h(cx, cy)
    stem_mat = mat("flower_stem", (0.20, 0.34, 0.16), rough=0.9)
    petal_tones = [(0.78, 0.22, 0.30), (0.85, 0.78, 0.20), (0.85, 0.85, 0.88), (0.55, 0.30, 0.62)]
    n = rng.randint(3, 5)
    for i in range(n):
        fx = cx + rng.uniform(-0.22, 0.22)
        fy = cy + rng.uniform(-0.22, 0.22)
        fz = terrain_h(fx, fy)
        stem_h = rng.uniform(0.10, 0.18)
        strut("flower_stem_%d" % i, (fx, fy, fz), (fx, fy, fz + stem_h), 0.006, stem_mat, verts_n=4)
        tone = petal_tones[rng.randrange(len(petal_tones))]
        ellipsoid("flower_bloom_%d" % i, 0.035, 0.035, 0.025, (fx, fy, fz + stem_h + 0.015),
                  mat("flower_%.2f_%.2f_%.2f" % tone, tone, rough=0.8))

def build_cloth_hang(name, cx, cy, cz, w, h, item_mat, rng):
    """Small draped cloth/shirt silhouette (v11 item 10) — a flattened quad
    with the bottom corners pulled inward and back a little (implies
    fabric weight/drape under its own hang-point), instead of a rigid flat
    box that reads as an abstract colored cube."""
    hw = w / 2
    sag = h * 0.14
    fold = w * 0.20 * rng.uniform(0.7, 1.3)
    verts = [(-hw, 0.0, 0.0), (hw, 0.0, 0.0),
             (hw - fold, -sag, -h), (-hw + fold, -sag, -h)]
    verts3 = [(cx + v[0], cy + v[1], cz + v[2]) for v in verts]
    faces = [(0, 1, 2, 3), (3, 2, 1, 0)]  # both winding directions — visible from either side
    return mesh_obj(name, verts3, faces, item_mat)

def build_hanging_line(p1, p2, rng, style, kind="herbs"):
    """Line strung between two existing landmarks with small dangling items
    — banners (accent-colored cloth), drying herbs, or fish — PO v8 item 3
    'hanging decorations between houses'. Reuses actual placed landmarks so
    it always spans real geometry, never a line to nowhere.

    PO v8.1 item 2 (2026-07-19) fix — the v8 version was a single taut
    strut at one FIXED height (2.2m) with items spread evenly along the
    WHOLE span, which read as an overhead power cable, not a laundry/herb
    line: (a) only short spans between ADJACENT landmarks (<8m — real
    hanging lines never cross a whole village); (b) a catenary droop
    (approximated with a short polyline instead of a true catenary formula
    — a few extra segments dipping toward the middle, ~15-20% of span
    length); (c) varied attach height PER SPAN (not one identical height
    for every line in the village); (d) hanging items cluster NEAR the sag
    point instead of spreading uniformly end-to-end."""
    x1, y1 = p1
    x2, y2 = p2
    span = math.hypot(x2 - x1, y2 - y1)
    if span < 0.5 or span > 8.0:
        return  # too far apart to read as a real hung line (item 2a) — skip
    wood_dark = mat("wood_dark", style["wood_dark"])
    h1 = rng.uniform(1.9, 2.5)  # varied per-span attach height (item 2c)
    h2 = rng.uniform(1.9, 2.5)
    z1, z2 = terrain_h(x1, y1) + h1, terrain_h(x2, y2) + h2
    sag = span * rng.uniform(0.15, 0.20)  # catenary droop depth (item 2b)

    # Approximate the catenary with a short 4-segment polyline instead of
    # one straight strut — a parabolic-ish sag (sin bump) reads as real rope
    # slack even at this cheap an approximation.
    segs = 4
    pts = []
    for i in range(segs + 1):
        f = i / segs
        x = x1 + (x2 - x1) * f
        y = y1 + (y2 - y1) * f
        z = z1 + (z2 - z1) * f - sag * math.sin(math.pi * f)
        pts.append((x, y, z))
    for i in range(segs):
        strut("hangline_%s_rope_%d" % (kind, i), pts[i], pts[i + 1], 0.015, wood_dark, verts_n=4)

    n = rng.randint(3, 5)
    if kind == "banner":
        tone = style["accent"]
    elif kind == "fish":
        tone = (0.55, 0.58, 0.62)
    else:
        tone = (0.35, 0.42, 0.20)
    item_mat = mat("hang_%s_%.2f_%.2f_%.2f" % (kind, tone[0], tone[1], tone[2]), tone)
    for i in range(n):
        # Cluster near the sag point (item 2d): sample f from a triangular-
        # ish distribution peaked at the middle instead of an even spread.
        f = 0.5 + (rng.uniform(-1.0, 1.0) + rng.uniform(-1.0, 1.0)) * 0.5 * 0.28
        f = max(0.08, min(0.92, f))
        x = x1 + (x2 - x1) * f
        y = y1 + (y2 - y1) * f
        zt = z1 + (z2 - z1) * f - sag * math.sin(math.pi * f)
        if kind == "banner":
            # RECOGNIZABLE SHAPE (v11 item 10, 2026-07-20): was a solid
            # flat box (read as an abstract colored cube, not cloth) — a
            # single quad with the bottom corners pulled in and back reads
            # as a draped/folded cloth silhouette instead.
            build_cloth_hang("hang_%s_%d" % (kind, i), x, y, zt - 0.04, 0.16, 0.30, item_mat, rng)
        elif kind == "fish":
            ellipsoid("hang_%s_%d" % (kind, i), 0.05, 0.16, 0.05, (x, y, zt - 0.12), item_mat)
        else:
            ellipsoid("hang_%s_%d" % (kind, i), 0.10, 0.10, 0.14, (x, y, zt - 0.14), item_mat)

def _segment_intersect(p1, p2, p3, p4):
    """Standard orientation-based 2D segment intersection test. Returns
    (ix, iy, t) where t is the fraction ALONG p1->p2 at the crossing, or
    None if the segments don't cross."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = cross(p3, p4, p1), cross(p3, p4, p2)
    d3, d4 = cross(p1, p2, p3), cross(p1, p2, p4)
    if not (((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and
            ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))):
        return None
    denom = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(denom) < 1e-9:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / denom
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]), t)

def hangline_path_conflict(p1, p2, path_polylines, min_clear=2.05):
    """PO v9 item 4 (2026-07-19): 'hanging lines must NEVER cross paths at
    person height nor block sightlines'. True if the straight overhead span
    p1->p2 crosses any path polyline at a point where the line's own
    catenary-sag height (see build_hanging_line's sin-bump formula) would
    dip below `min_clear` (2.05m — just above the 1.80m mannequin, matches
    build_hanging_line's own [1.9, 2.5] attach-height floor minus its sag).
    Uses the MIDPOINT of build_hanging_line's per-span attach-height range
    as the height estimate (exact per-span heights aren't rolled yet at
    candidate-selection time — this is deliberately a slightly pessimistic
    approximation, erring toward skipping a borderline span rather than
    building one that turns out too low)."""
    x1, y1 = p1
    x2, y2 = p2
    span = math.hypot(x2 - x1, y2 - y1)
    if span < 1e-6:
        return False
    sag = span * 0.175  # midpoint of build_hanging_line's [0.15, 0.20] sag range
    h_mid = 2.2  # midpoint of build_hanging_line's [1.9, 2.5] attach-height range
    for poly in path_polylines:
        for i in range(len(poly) - 1):
            hit = _segment_intersect(p1, p2, poly[i], poly[i + 1])
            if hit is None:
                continue
            _, _, t = hit
            height_at_t = h_mid - sag * math.sin(math.pi * t)
            if height_at_t < min_clear:
                return True
    return False

def build_yard_fence(cx, cy, w, d, rng, style, facing_deg=0):
    """Low internal yard fence (PO v8 item 2c) — subdivides a house's yard
    from its neighbor's and blocks a slice of ground-level sightline without
    hiding the roofline behind it (real cottage-garden fence height, not a
    palisade). One side is left open (the yard's own gap) — a solid ring
    would look like a second tiny stockade, not a garden boundary.

    ENTRANCE-AWARE (v11 item 5, 2026-07-20): the gap used to be a random
    corner independent of where the house's own door actually is, so the
    fence sometimes walled off the entrance and sometimes left an
    unrelated side open. The gap is now ALWAYS the -Y edge (matching every
    house's door convention — see house()'s docstring), and the whole
    fence rotates by `facing_deg` (the same rotation the caller applies to
    a facing_deg house, see rotate_group()) so the gap tracks the door
    exactly even when the house faces a non-default direction."""
    z = terrain_h(cx, cy)
    wood = mat("wood_dark", style["wood_dark"])
    h = 0.6
    _group_start = len(bpy.context.collection.objects)
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    gap_side = 0  # edge 0 = corner0->corner1 = the -Y (door-facing) edge, ALWAYS
    for i in range(4):
        if i == gap_side:
            continue
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        length = math.hypot(x2 - x1, y2 - y1)
        n_pickets = max(2, int(length / 0.5))
        for pi in range(n_pickets + 1):
            f = pi / n_pickets
            px, py = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            pz = terrain_h(cx + px, cy + py)
            cylinder("fence_picket_%d_%d" % (i, pi), 0.03, h, (cx + px, cy + py, pz + h / 2), wood, verts_n=5)
        strut("fence_rail_%d" % i, (cx + x1, cy + y1, z + h * 0.8), (cx + x2, cy + y2, z + h * 0.8),
              0.025, wood, verts_n=5)
    if facing_deg:
        rotate_group("yardfence_%d_%d" % (int(cx * 10), int(cy * 10)), _group_start, (cx, cy, z), facing_deg)

# ── Interior — settlement logic: commons band (center) -> residential band
#    -> wall (PO principle 1 / village_settlement_logic synthesis) ─────────
def build_interior(cx, cy, ring_r, gate_ang, style, threat):
    commons_r = ring_r * 0.30
    residential_lo = ring_r * 0.34
    # Tighter clustering (PO v7 item 2): pulled in from 0.75 so the extra
    # population added this pass reads as a denser settlement, not a wider
    # sprawl into the same emptiness.
    residential_hi = ring_r * 0.68

    # RESIDENTIAL BLOCKS (PO v8 item 2b) — 2-3 angular sectors the houses
    # bias toward, so the residential band reads as discrete neighborhoods
    # with alleys/gaps between them instead of an even scatter around the
    # full annulus. Computed once per village; every house/hut placement
    # below (except the outhouse, deliberately kept apart) samples from it.
    cluster_angles = make_cluster_centers(rng)

    # Landmarks for the path network (PO v7 item 1) — filled in as each
    # piece is actually placed; paths are drawn once, at the end, from
    # whatever landmarks this seed actually rolled.
    landmarks = {"gate": (cx + math.cos(gate_ang) * (ring_r - 5.0),
                          cy + math.sin(gate_ang) * (ring_r - 5.0))}

    # COMMONS HUB — well, plaza/hearth, crafts, garden plots: all near center.
    plaza_x, plaza_y = cx, cy - commons_r * 0.45
    landmarks["plaza"] = (plaza_x, plaza_y)
    fz = terrain_h(plaza_x, plaza_y)
    for i in range(5):
        a = i / 5 * math.tau
        make_rock("fire_stone_%d" % i, rng.uniform(0.20, 0.28),
                   (plaza_x + math.cos(a) * 0.8, plaza_y + math.sin(a) * 0.8,
                    fz + 0.15), rng, flatten=0.7)
    # Real flame wedges + crossed logs (PO v8.1 item 3) — was a single white
    # placeholder cone.
    build_campfire_logs("plaza_fire", plaza_x, plaza_y, fz + 0.15, rng, scale=1.3)
    build_campfire_flames("plaza_fire", plaza_x, plaza_y, fz + 0.15, rng, scale=1.3)
    fl = bpy.data.lights.new("firelight", 'POINT')
    fl.energy = 300.0
    fl.color = (1.0, 0.55, 0.2)
    flo = bpy.data.objects.new("firelight", fl)
    flo.location = (plaza_x, plaza_y, fz + 1.2)
    link(flo)
    if threat["covered_plaza"]:
        build_covered_plaza(plaza_x, plaza_y)

    # Roll the module pool ONCE, fixed catalog order — deterministic per
    # seed (see module docstring "Weighted module pools"). This decides
    # WHAT exists; the band math below still decides WHERE it goes.
    rolled = roll_module_pool(rng, "aldea")
    print("[village_gen] AUDIT modules rolled (aldea):", rolled)

    # ECONOMY axis (PO principle 5): re-roll crafts_area presence with an
    # economy-adjusted weight instead of duplicating the whole pool table per
    # economy. No-op (0 extra rng calls) for the default 'agricola' economy —
    # keeps default runs byte-identical to before this pass.
    if EC["crafts_weight_mult"] != 1.0 and not rolled["crafts_area"]:
        rolled["crafts_area"] = roll_bool(rng, min(0.95, 0.30 * EC["crafts_weight_mult"]))

    # MARKET weighting (PO v10 item 3, 2026-07-20) — Axlin threat principle:
    # high danger means ZERO commerce (only rare traveling peddlers, never a
    # standing market); agricola/costera are the economies with actual
    # surplus goods to sell, so only THEY get the boosted re-roll. Same
    # "re-roll only if the baseline missed" pattern as crafts_area right
    # above — a no-op for economies/intensities that don't apply, so a
    # 'wary'+'herreria'/'pieles'/'nomada' run stays exactly at the pool's
    # sparse baseline (rarely 0 stalls) instead of being force-boosted.
    if INTENSITY_NAME == "dangerous":
        rolled["market"] = 0
    elif ECONOMY_NAME in ("agricola", "costera") and rolled["market"] == 0:
        rolled["market"] = roll_weighted(rng, {0: 0.35, 2: 0.42, 3: 0.23})

    # POPULATION COHERENCE (PO v7 item 2): garden rows and livestock scale
    # with total house count instead of an independent dice roll — more
    # mouths to feed need more crop rows and more animals. Computed once,
    # right after the pool roll, from the extra_house count it just gave us.
    extra_count = rolled["extra_house"]
    total_houses = 4 + extra_count  # casona + storage + kitchen + outhouse + extras
    garden_count = (min(3, max(1, round(total_houses / 3.2))) if rolled["garden"] else 0)
    pen_size = "big" if total_houses >= 9 else "small"

    if rolled["well"]:
        wx, wy = cx + commons_r * 0.5, cy + commons_r * 0.2
        build_well(wx, wy)
        landmarks["well"] = (wx, wy)
        build_ground_patch(wx, wy, 1.3, rng, tone=MUD_PATCH)  # mud patch (item 1)
        register_footprint(wx, wy, 0.8)
    if rolled["crafts_area"]:
        cax, cay = cx - commons_r * 0.55, cy + commons_r * 0.15
        build_crafts_area(cax, cay, rng, economy_tag=EC["prop_tag"])
        register_footprint(cax, cay, 1.4)
        landmarks["crafts_area"] = (cax, cay)
    # GARDEN placed BEFORE market (v11 item 6, 2026-07-20 — footprint
    # exclusion fix): garden never used to call register_footprint() at
    # all, so nothing (market included) ever avoided it — "market stalls
    # spawn overlapping the garden module". Moved ahead of the market spot
    # search (which reads PLACED_FOOTPRINTS) and now registers its own
    # footprint, so market/livestock/coop/etc. all correctly steer clear.
    for gi in range(garden_count):
        ga = math.tau * (0.15 + gi * 0.5)
        gx = cx + math.cos(ga) * commons_r * 0.8
        gy = cy + math.sin(ga) * commons_r * 0.8
        build_garden(gx, gy, gi, rng)
        register_footprint(gx, gy, 1.1)
    if rolled["market"]:
        spot = find_flat_spot(cx, cy, commons_r * 0.55, commons_r * 1.05, gate_ang, foot_r=2.2)
        if spot:
            build_market(spot[0], spot[1], rolled["market"], rng, style)
            landmarks["market"] = (spot[0], spot[1])
    if rolled["granary"]:
        spot = find_flat_spot(cx, cy, residential_lo * 0.9, residential_lo * 1.15, gate_ang, foot_r=0.9)
        if spot:
            build_granary(spot[0], spot[1], rng, style)
            register_footprint(spot[0], spot[1], 0.9)
    if rolled["storage_shed"]:
        spot = find_flat_spot(cx, cy, residential_lo * 1.0, residential_hi * 0.8, gate_ang, foot_r=1.0)
        if spot:
            build_storage_shed(spot[0], spot[1], rng, style)
            register_footprint(spot[0], spot[1], 1.0)

    # Livestock pen — commons/residential boundary (watched from daily-use
    # area, not stashed at the wall — see village_settlement_logic §4).
    pen_spot = None
    if rolled["livestock_pen"]:
        pen_r = 3.0 if pen_size == "big" else 2.3
        pen_spot = find_flat_spot(cx, cy, commons_r * 0.9, residential_lo * 1.1, gate_ang, foot_r=pen_r)
        if pen_spot:
            build_livestock_pen(pen_spot[0], pen_spot[1], rng, size=pen_size)
            register_footprint(pen_spot[0], pen_spot[1], pen_r)
    if rolled["coop"]:
        # Near the sheep pen if one exists (a working farmyard clusters its
        # animals), otherwise anywhere in the commons/residential boundary.
        near = pen_spot or (cx, cy)
        spot = find_flat_spot(near[0], near[1], 1.6, 3.2, gate_ang, foot_r=0.7) if pen_spot else \
            find_flat_spot(cx, cy, commons_r * 0.9, residential_lo * 1.1, gate_ang, foot_r=0.7)
        if spot:
            build_coop(spot[0], spot[1], rng, style)
            register_footprint(spot[0], spot[1], 0.7)

    # EXTERIOR LIFE ACCESSORIES (PO v8 item 3) — pool-rolled, scattered
    # across the residential band via the SAME clustered-spot search as the
    # houses so they land ALONG the paths between blocks (item 3: "walking
    # reveals them one by one") instead of clumped at the plaza.
    if rolled["loom"]:
        spot = find_clustered_spot(cx, cy, residential_lo * 0.95, residential_hi * 0.9,
                                    gate_ang, cluster_angles, foot_r=0.7)
        if spot:
            build_loom(spot[0], spot[1], rng, style)
    if rolled["hide_rack"]:
        spot = find_clustered_spot(cx, cy, residential_lo * 0.95, residential_hi * 0.9,
                                    gate_ang, cluster_angles, foot_r=0.7)
        if spot:
            build_hide_rack(spot[0], spot[1], rng, style)
    if rolled["outdoor_kitchen"]:
        spot = find_clustered_spot(cx, cy, residential_lo, residential_hi, gate_ang, cluster_angles, foot_r=1.4)
        if spot:
            build_outdoor_kitchen(spot[0], spot[1], rng, style)
    for _ in range(rolled["extra_seating"]):
        spot = find_clustered_spot(cx, cy, residential_lo * 0.9, residential_hi, gate_ang, cluster_angles, foot_r=0.6)
        if spot:
            build_outdoor_seat(spot[0], spot[1], rng, style)

    # RESIDENTIAL BAND — the CASONA (protected/dominant, Axlin) sits at the
    # commons/residential boundary; the mandatory functional zones (Joan,
    # round-1 feedback) always exist; extra houses are pool-rolled.
    casona_xy = (cx, cy + commons_r * 0.85)
    build_casona("central", casona_xy, style, rng)
    landmarks["casona"] = casona_xy
    register_footprint(casona_xy[0], casona_xy[1], 5.5)  # main hall + wing, generous radius
    build_woodpile_axe(casona_xy[0] - 4.2, casona_xy[1] + 0.5, rng, style)  # life signal, item 5

    # FLOWER CLUSTERS (v11 item 24, 2026-07-20) — a few small blob clusters
    # near the plaza/casona corners, cheap life-detail scatter.
    for fi in range(rng.randint(3, 5)):
        fa = rng.uniform(0, math.tau)
        fr = commons_r * rng.uniform(0.5, 1.1)
        fx = cx + math.cos(fa) * fr
        fy = cy + math.sin(fa) * fr
        if spot_clear(fx, fy, 0.4, min_gap=0.3):
            build_flower_cluster(fx, fy, rng, style)

    spot = find_clustered_spot(cx, cy, residential_lo, residential_lo * 1.3, gate_ang, cluster_angles, foot_r=1.6)
    if spot:
        x, y, _ = spot
        house("hut_storage", 2.2, 2.0, 2.3, (x, y), style, stone_base=True, windows=1,
              rng=rng, real_door=True, chest=True)
        landmarks["hut_storage"] = (x, y)

    spot = find_clustered_spot(cx, cy, residential_lo * 1.1, residential_hi * 0.75, gate_ang,
                                cluster_angles, foot_r=2.0)
    if spot:
        x, y, a = spot
        house("hut_kitchen", 3.0, 2.4, 2.3, (x, y), style, porch=True, thatch=True, windows=2, rng=rng)
        landmarks["hut_kitchen"] = (x, y)
        perp = (-math.sin(a), math.cos(a))
        for bi in range(3):
            bx = x + perp[0] * (1.6 + bi * 0.55) - math.cos(a) * 1.0
            by = y + perp[1] * (1.6 + bi * 0.55) - math.sin(a) * 1.0
            bz = terrain_h(bx, by)
            cylinder("hut_kitchen_barrel_%d" % bi, 0.28, 0.55, (bx, by, bz + 0.275),
                      mat("wood", style["wood"]), verts_n=9)

    # Outhouse deliberately stays OUT of the clustered blocks (privacy, and
    # real settlements keep it apart) — unbiased search, near the wall.
    spot = find_flat_spot(cx, cy, ring_r - 3.5, ring_r - 1.8, gate_ang, gate_clear=0.7, foot_r=1.0)
    if spot:
        x, y, _ = spot
        house("hut_outhouse", 1.3, 1.2, 2.25, (x, y), style, windows=0, rng=rng)
        landmarks["hut_outhouse"] = (x, y)

    # CEMETERY (PO live addendum, 2026-07-20) — a fenced-off corner near the
    # wall, same unbiased/apart-from-the-blocks logic as the outhouse (real
    # settlements keep a graveyard at the edge, not threaded through the
    # residential blocks).
    if rolled["cemetery"]:
        spot = find_flat_spot(cx, cy, ring_r - 5.5, ring_r - 2.8, gate_ang, gate_clear=0.9, foot_r=2.2)
        if spot:
            build_cemetery(spot[0], spot[1], rng, style)

    # Extra houses — pool-rolled COUNT (now weighted denser, PO v7 item 2 /
    # v8 item 7 density bump). Each one independently rolls a variant so
    # raised-on-stilts/terrace elevation variety (PO principle 5) shows up
    # organically. NEW v8: biased toward the residential BLOCKS (item 2b)
    # via find_clustered_spot instead of a full-circle scatter; ~40% roll a
    # 30-60 deg facade rotation (item 2b "some huts rotated") and ~35% get a
    # low yard fence subdividing their plot from the neighbor's (item 2c).
    variant_weights = {"raised": 0.35, "terrace": 0.35, "flat": 0.30}
    extra_landmarks = []
    for ei in range(extra_count):
        spot = find_clustered_spot(cx, cy, residential_lo * 1.1, residential_hi * 0.85,
                                    gate_ang, cluster_angles, foot_r=1.8)
        if not spot:
            continue
        x, y, _ = spot
        variant = roll_weighted(rng, variant_weights)
        hsx = 2.3 + rng.uniform(-0.2, 0.4)
        hsy = 2.0 + rng.uniform(-0.2, 0.3)
        # ROTATION BUG FIX (v12, Joan: "la casa sigue rotada como en 45deg",
        # reported across MULTIPLE scenes/seeds, not seed-specific). Root
        # cause: this range was rng.uniform(30, 60) — a jitter window that
        # AVERAGES 45deg and was applied with zero relation to the house's
        # neighbors or its own position (find_clustered_spot's returned
        # angle `a` is discarded here, never fed into facing_deg). A single
        # hut swung 30-60deg away from its axis-aligned neighbors doesn't
        # read as "varied facade" (the intent, see house()'s facing_deg
        # docstring) — it reads as one broken/mis-rotated building sitting
        # in an otherwise axis-aligned row. Narrowed to a SUBTLE off-axis
        # nudge (8-18deg) that still breaks the "grid of identical boxes"
        # monotony without looking like a placement error.
        facing_deg = rng.uniform(8, 18) * rng.choice((-1, 1)) if rng.random() < 0.40 else 0
        # Wider height jitter (PO v8 item 4 "bigger height variety between
        # buildings") — v7's +-0.1/0.2 range barely varied the roofline;
        # this spans roughly 2.05-3.0m so the skyline actually reads uneven.
        house("hut_extra_%d" % ei, hsx, hsy,
              2.35 + rng.uniform(-0.30, 0.65), (x, y), style,
              raised=(variant == "raised"), terrace=(variant == "terrace"),
              windows=rng.choice((1, 2)), rng=rng, facing_deg=facing_deg)
        if rng.random() < 0.35:
            build_yard_fence(x, y, hsx * 1.7, hsy * 1.7, rng, style, facing_deg=facing_deg)
        extra_landmarks.append((x, y))
        if ei == 0:
            landmarks["hut_extra_0"] = (x, y)
        elif ei == 1:
            landmarks["hut_extra_1"] = (x, y)

    # PATHS (PO v7 item 1 — the highest-impact make-it-explorable item):
    # gate -> plaza -> casona -> well, plus a spur from the commons hub out
    # to each named functional hut, all following the actual terrain.
    # MOVED BEFORE hanging decorations (PO v9 item 4, 2026-07-19): the
    # decoration-placement conflict check below needs the actual (now
    # curved, PO v9 item 2) path polylines to test against, so paths must
    # exist first. `path_polylines` collects every centerline build_path()
    # returns for that check.
    # TRAFFIC WEIGHT (v11 item 21, 2026-07-20) — rough per-module traffic
    # so path width/wear-color scales with how much a destination is
    # actually used (well/plaza = constant daily traffic; a private hut or
    # storage shed = occasional).
    TRAFFIC_WEIGHT = {
        "well": 1.0, "plaza": 1.0, "market": 0.9, "casona": 0.75, "crafts_area": 0.6,
        "hut_kitchen": 0.55, "hut_storage": 0.30, "hut_outhouse": 0.15,
        "hut_extra_0": 0.35, "hut_extra_1": 0.35,
    }
    path_polylines = []
    hub_chain = [k for k in ("gate", "plaza", "casona", "well") if k in landmarks]
    for i in range(len(hub_chain) - 1):
        dest = hub_chain[i + 1]
        _, poly = build_path(landmarks[hub_chain[i]], landmarks[dest], 1.4, rng,
                              wear=TRAFFIC_WEIGHT.get(dest, 0.6))
        path_polylines.append(poly)
    hub = landmarks.get("casona", landmarks["plaza"])
    for hut_key in ("hut_storage", "hut_kitchen", "hut_outhouse", "hut_extra_0", "hut_extra_1"):
        if hut_key in landmarks:
            _, poly = build_path(hub, landmarks[hut_key], 1.1, rng, wear=TRAFFIC_WEIGHT.get(hut_key, 0.3))
            path_polylines.append(poly)
    # INTERCONNECTION (v11 item 20, 2026-07-20) — paths used to radiate
    # ONLY to/from the casona hub (pure hub-and-spoke). At least one
    # segment now connects two NON-casona modules directly when both
    # exist, tried in order of "most plausible real desire line" first.
    for a_key, b_key in (("well", "crafts_area"), ("hut_storage", "hut_kitchen"),
                          ("hut_extra_0", "hut_extra_1")):
        if a_key in landmarks and b_key in landmarks:
            _, poly = build_path(landmarks[a_key], landmarks[b_key], 1.0, rng,
                                  wear=min(TRAFFIC_WEIGHT.get(a_key, 0.4), TRAFFIC_WEIGHT.get(b_key, 0.4)))
            path_polylines.append(poly)
            break
    # Trampled dirt plaza around the hearth.
    build_ground_patch(plaza_x, plaza_y, 2.4, rng, tone=DIRT_PATH_WORN, surface="cobblestone")

    # HANGING DECORATIONS (PO v8 item 3, retuned PO v8.1 item 2, PO v9 item 4
    # 2026-07-19) — strung between NEAREST-NEIGHBOR building pairs instead
    # of a FIXED named-pair list. The original fixed list (hut_kitchen<->
    # hut_storage, hut_extra_0<->hut_extra_1, hut_kitchen<->hut_extra_0)
    # assumed those specific huts sit near each other, but they're placed
    # independently across the whole residential band — often 15-20m apart.
    # Once build_hanging_line() gained its <8m adjacency cap (item 2a, its
    # own docstring), that fixed list started silently producing ZERO lines
    # on most seeds (verified empirically: a forced-100%-roll diagnostic
    # run on this exact seed still built 0 hanging-line objects). Fixed by
    # picking each candidate building's NEAREST clear neighbor within 8m
    # instead of a hardcoded pairing, deduped, capped at 3 lines/village
    # (same budget as before) so it doesn't turn into clutter.
    #
    # PLACEMENT LOGIC (PO v9 item 4): "hanging lines must NEVER cross paths
    # at person height nor block sightlines" — a span is only accepted if
    # it does NOT cross any built path polyline below head clearance (see
    # hangline_path_conflict below); if the nearest neighbor conflicts, the
    # NEXT-nearest is tried before the candidate is skipped outright
    # (reroute-by-picking-a-different-partner, since a hung rope line can't
    # meaningfully "bend" around an obstacle the way a path can).
    hang_candidates = []
    if "hut_kitchen" in landmarks:
        hang_candidates.append(("hut_kitchen", landmarks["hut_kitchen"]))
    if "hut_storage" in landmarks:
        hang_candidates.append(("hut_storage", landmarks["hut_storage"]))
    for ei, pos in enumerate(extra_landmarks):
        hang_candidates.append(("hut_extra_%d" % ei, pos))

    hang_kinds = ("herbs", "banner", "fish")
    seen_pairs = set()
    hang_lines_built = 0
    for i, (name_a, pos_a) in enumerate(hang_candidates):
        if hang_lines_built >= 3:
            break
        neighbors = []
        for j, (name_b, pos_b) in enumerate(hang_candidates):
            if i == j:
                continue
            d = math.hypot(pos_a[0] - pos_b[0], pos_a[1] - pos_b[1])
            if d < 8.0:
                neighbors.append((d, name_b, pos_b))
        neighbors.sort(key=lambda n: n[0])
        chosen = None
        for d, name_b, pos_b in neighbors:
            pair_key = frozenset((name_a, name_b))
            if pair_key in seen_pairs:
                continue
            if hangline_path_conflict(pos_a, pos_b, path_polylines):
                continue  # would cross a path below head height — try next neighbor
            chosen = (name_b, pos_b, pair_key)
            break
        if chosen is None:
            continue
        name_b, pos_b, pair_key = chosen
        seen_pairs.add(pair_key)
        if rng.random() < 0.6:
            kind = hang_kinds[hang_lines_built % len(hang_kinds)]
            build_hanging_line(pos_a, pos_b, rng, style, kind=kind)
            hang_lines_built += 1

def build_vegetation(cx, cy, ring_r, style, exclude=(), ring_radius_fn=None):
    """`ring_radius_fn` (PO v9 item 3): with the wall now irregular/bulging
    up to 1.35x ring_r on its widest side, the OLD flat `ring_r + 3.0`
    inner exclusion could let a tree roll inside the bulge and clip through
    the palisade — each tree's minimum distance now follows the wall's own
    per-angle radius when available."""
    kind = style["trees"]
    count = 40
    for i in range(count):
        a = rng.uniform(0, math.tau)
        d_min = (ring_radius_fn(a) if ring_radius_fn is not None else ring_r) + 3.0
        d = rng.uniform(d_min, TERRAIN_HALF - 2.0)
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if any(math.hypot(x - ex, y - ey) < er for ex, ey, er in exclude):
            continue
        z = terrain_h(x, y)
        if kind == "rocks":
            base_r = rng.uniform(0.5, 1.4)
            make_rock("rock_%d" % i, base_r, (x, y, z + base_r * 0.25), rng)
        else:
            trunk_h = rng.uniform(1.2, 2.2)
            cylinder("trunk_%d" % i, 0.14, trunk_h, (x, y, z + trunk_h / 2),
                     mat("wood_dark", style["wood_dark"]), verts_n=7)
            green = (0.10, 0.22, 0.12) if kind == "pines" else (0.16, 0.26, 0.20)
            for lvl in range(3):
                rr = 1.3 - lvl * 0.35
                bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=rr, depth=1.1,
                    location=(x, y, z + trunk_h + 0.45 + lvl * 0.75))
                c = bpy.context.object
                c.data.materials.append(mat("pine", green))
                if kind == "pines_snow" and lvl == 2:
                    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=rr * 0.7,
                        depth=0.35, location=(x, y, z + trunk_h + 0.75 + lvl * 0.75))
                    sc = bpy.context.object
                    sc.data.materials.append(mat("snow", (0.92, 0.94, 0.97)))

def build_scale_ref(cx, cy, ring_r, gate_ang):
    """1.80 m human mannequin — proportion ground truth, placed just inside
    the gate corridor so doors/windows/stairs read against it."""
    x = cx + 2.5
    y = cy + math.sin(gate_ang) * (ring_r - 4.0)
    z = terrain_h(x, y)
    m = mat("scale_ref", (0.80, 0.20, 0.18), rough=0.5)
    cylinder("ref_human_body_%d_%d" % (int(cx), int(cy)), 0.20, 1.50, (x, y, z + 0.75), m, verts_n=8)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=0.15,
                                         location=(x, y, z + 1.65))
    head = bpy.context.object
    head.name = "ref_human_head_%d_%d" % (int(cx), int(cy))
    head.data.materials.append(m)

# ── DESTACAMENTO — small outpost: 2-3 structures + wall fragment + tower ──
def build_destacamento(cx, cy, ring_r, style, threat):
    gate_ang = GATE_ANG
    wood = mat("wood_dark", style["wood_dark"])
    arc = math.radians(150)  # wall FRAGMENT — not a full ring, this is an outpost
    facing = gate_ang + math.pi  # fragment faces away from the "open" side
    n = max(10, int(ring_r * 2.2))
    ring_heights = []
    placed = []
    for i in range(n):
        t = i / (n - 1)
        a = facing - arc / 2 + t * arc
        j = style["jitter"]
        rr = ring_r + rng.uniform(-0.3, 0.3) * j
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        z = terrain_h(x, y)
        h = style["stake_h"] * threat["wall_h_mult"] * 0.9 * (1.0 + rng.uniform(-0.15, 0.15) * j)
        r = style["stake_r"] * (1.0 + rng.uniform(0.0, 0.3))
        st = cylinder("dest_stake_%d" % i, r, h, (x, y, z + h / 2), wood)
        tip_h = r * 1.8
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=r, depth=tip_h,
            location=(x, y, z + h / 2 + tip_h / 2))
        cone = bpy.context.object
        cone.name = "dest_stake_%d_tip" % i
        cone.data.materials.append(wood)
        cone.parent = st
        cone.matrix_parent_inverse = st.matrix_world.inverted()
        ring_heights.append((z, x, y))
        placed.append((x, y, z, h))
    for k in range(len(placed) - 1):
        x1, y1, z1, h1 = placed[k]
        x2, y2, z2, h2 = placed[k + 1]
        ang = math.atan2(y2 - y1, x2 - x1)
        length = math.hypot(x2 - x1, y2 - y1) + style["stake_r"]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        for idx, frac in enumerate((0.6, 0.28)):
            zr = (z1 + z2) / 2 + frac * style["stake_h"] * 0.9
            rail = box("dest_rail_%d_%d" % (k, idx), length, 0.06, 0.08, (mx, my, zr), wood)
            rail.rotation_euler = (0, 0, ang)
    if ring_heights:
        build_tower(cx, cy, ring_heights, style, "none")

    # Command tent is mandatory identity (outpost always has SOMETHING);
    # bunk_hut/third_structure are pool-rolled — "2-3 structures" per PO
    # principle 4, with a deterministic fallback if both rolls miss (an
    # outpost of exactly 1 tent reads as abandoned, not "sparse by design").
    rolled = roll_module_pool(rng, "destacamento")
    print("[village_gen] AUDIT modules rolled (destacamento @ %.0f,%.0f):" % (cx, cy), rolled)
    if not rolled["bunk_hut"] and not rolled["third_structure"]:
        rolled["bunk_hut"] = True

    a1 = facing
    tx, ty = cx + math.cos(a1) * ring_r * 0.35, cy + math.sin(a1) * ring_r * 0.35
    house("dest_tent", 3.0, 2.4, 2.3, (tx, ty), style, windows=1, rng=rng)
    if rolled["bunk_hut"]:
        a2 = facing + math.radians(35)
        hx, hy = cx + math.cos(a2) * ring_r * 0.45, cy + math.sin(a2) * ring_r * 0.45
        house("dest_bunk", 2.0, 1.8, 2.25, (hx, hy), style, windows=1, rng=rng)
    if rolled["third_structure"]:
        a3 = facing - math.radians(40)
        sx3, sy3 = cx + math.cos(a3) * ring_r * 0.4, cy + math.sin(a3) * ring_r * 0.4
        sz3 = terrain_h(sx3, sy3)
        crate_mat = mat("wood_dark", style["wood_dark"])
        for ci in range(3):
            box("dest_crate_%d" % ci, 0.5, 0.5, 0.5,
                (sx3 + (ci % 2) * 0.55, sy3 + (ci // 2) * 0.55, sz3 + 0.25), crate_mat)

    # small campfire, no full plaza — this is an outpost, not a commons hub.
    # Real flame wedges + crossed logs + ember light (PO v8.1 item 3) — was
    # a single white placeholder cone with no light at all.
    fx, fy = cx, cy
    fz = terrain_h(fx, fy)
    for i in range(4):
        a = i / 4 * math.tau
        make_rock("dest_fire_stone_%d" % i, rng.uniform(0.16, 0.22),
                   (fx + math.cos(a) * 0.6, fy + math.sin(a) * 0.6, fz + 0.12), rng, flatten=0.7)
    build_campfire_logs("dest_fire", fx, fy, fz + 0.12, rng, scale=1.0)
    build_campfire_flames("dest_fire", fx, fy, fz + 0.12, rng, scale=1.0)
    build_ember_light("dest_fire", fx, fy, fz + 0.12, energy=180.0)

    build_scale_ref(cx, cy, ring_r, gate_ang)
    return ring_heights

# ── Build ─────────────────────────────────────────────────────────────────────
build_terrain()
if DEST_ACTIVE:
    # SEPARATE small terrain patch for the far-offset destacamento (v11
    # item 28) — its own grid, doesn't touch the main village's resolution.
    build_terrain(DEST_CX, DEST_CY, half=DEST_RING_R * 1.8 + 4.0, res=26, name="terrain_dest")

# THREAT INTENSITY wiring (PO addendum 2026-07-18) — applied ONLY to the main
# ring wall, not destacamento (small outpost wall is out of scope this pass).
# S_wall is a SHALLOW COPY so the shared style dict S used everywhere else
# (interior, tower, vegetation) is untouched. At INTENSITY_NAME="wary" every
# multiplier is 1.0, so S_wall == S and wall_h_mult == T["wall_h_mult"]
# exactly — the default 3-arg invocation renders byte-identical to before
# this pass.
S_wall = dict(S)
S_wall["stake_count"] = max(6, int(S["stake_count"] * IN["stake_count_mult"]))
S_wall["ring_coverage"] = max(0.15, S["ring_coverage"] * IN["ring_coverage_mult"])
wall_h_mult = T["wall_h_mult"] * IN["wall_h_mult"]

# ── NON-CIRCULAR PERIMETER (PO v9 item 3, 2026-07-19) ───────────────────────
# 'la aldea siempre es un circulo, hace que la muralla se adapte'. Two
# seeded harmonics deform the wall's radius per-angle into an elongated/
# irregular ring instead of a perfect circle. ANCHORED at GATE_ANG (each
# term is built as amp*(cos(freq*rel+phase) - cos(phase)), so `rel=0` at
# the gate always contributes exactly 0) — this guarantees
# ring_radius(GATE_ANG) == RING_R EXACTLY, so the gate position, the
# heavily-tuned fastview/plaza/gate camera shots (all built against the
# flat RING_R constant, with their own hard-won framing history — see the
# shot() calls below), and build_scale_ref's mannequin placement all stay
# byte-identical without needing to touch any of that fragile math. Only
# the OTHER angles bulge/pinch, which is exactly where the irregularity
# should read anyway (not at the audited entrance shot). Clamped to
# [0.75, 1.35]x so the residential band (out to 0.68x RING_R) always keeps
# clearance from the tightest pinch.
## Round-2 retune (self-eyeball, seed 21): the original amp ranges
## (0.08-0.16 / 0.03-0.07) rarely reached the [0.75, 1.35] clamp, so the
## overview shot read as "still basically a circle" — widened so the wall
## visibly elongates/pinches per seed, not just a barely-perceptible wobble.
_ring_terms = [(rng.uniform(0.14, 0.24), rng.choice((1, 2)), rng.uniform(0, math.tau)),
               (rng.uniform(0.05, 0.10), rng.choice((2, 3)), rng.uniform(0, math.tau))]

def ring_radius(a, _base=RING_R, _terms=_ring_terms, _anchor=GATE_ANG):
    rel = a - _anchor
    factor = 1.0
    for amp, freq, phase in _terms:
        factor += amp * (math.cos(freq * rel + phase) - math.cos(phase))
    return _base * max(0.75, min(1.35, factor))

# CLIFF WALL (PO v9 item 3): ~55% of seeds back onto a natural rock outcrop
# for part of their perimeter — the cliff itself stands in for the wall
# along that arc. Kept well clear of the gate (>= ~65 deg on either side)
# so it never interferes with the audited entrance corridor.
HAS_CLIFF = SCALE_NAME == "aldea" and rng.random() < 0.55
if HAS_CLIFF:
    _cliff_span = math.radians(rng.uniform(55.0, 85.0))
    _cliff_center = GATE_ANG + math.pi + rng.uniform(-0.5, 0.5)  # roughly opposite the gate
    CLIFF_ARC = (_cliff_center - _cliff_span / 2, _cliff_center + _cliff_span / 2)
else:
    CLIFF_ARC = None

if SCALE_NAME == "destacamento":
    build_destacamento(0.0, 0.0, RING_R, S, T)
else:
    ring = build_palisade(0.0, 0.0, RING_R, GATE_ANG, S_wall, wall_h_mult,
                           ring_radius_fn=ring_radius, cliff_arc=CLIFF_ARC)
    if CLIFF_ARC is not None:
        build_cliff_wall(0.0, 0.0, ring_radius, CLIFF_ARC, rng, S_wall, wall_h_mult)
    build_double_gate(0.0, 0.0, RING_R, GATE_ANG, S, T["gate_reinforced"], single=not IN["gate_heavy"],
                       ring_radius_fn=ring_radius)
    if T["torch_ring"]:
        build_torches(0.0, 0.0, RING_R, GATE_ANG, S, count=10,
                       ring_radius_fn=ring_radius, cliff_arc=CLIFF_ARC)
    build_tower(0.0, 0.0, ring, S, THREAT_NAME)
    build_interior(0.0, 0.0, RING_R, GATE_ANG, S, T)
    build_scale_ref(0.0, 0.0, RING_R, GATE_ANG)
    if DEST_ACTIVE:
        build_destacamento(DEST_CX, DEST_CY, DEST_RING_R, S, T)

build_vegetation(0.0, 0.0, RING_R, S, exclude=((DEST_CX, DEST_CY, DEST_RING_R + 6.0),) if DEST_ACTIVE else (),
                  ring_radius_fn=ring_radius if SCALE_NAME != "destacamento" else None)

# ── Lighting / atmosphere (style-driven) ──────────────────────────────────────
sun = bpy.data.lights.new("sun", 'SUN')
sun.energy = S["sun_energy"]
sun.color = S["sun_color"]
so = bpy.data.objects.new("sun", sun)
so.rotation_euler = (math.radians(90 - S["sun_elev"]), 0, math.radians(-35))
link(so)
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (*S["sky"], 1.0)
bg.inputs[1].default_value = 0.7 if BIOME != "hielo" else 0.35
if S["fog"]:
    scene.view_settings.look = 'None'
    world.mist_settings.use_mist = True

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1100
scene.render.resolution_y = 680
scene.view_settings.view_transform = 'Filmic'

cam_d = bpy.data.cameras.new("C")
cam_d.lens = 42
cam = bpy.data.objects.new("C", cam_d)
link(cam)
scene.camera = cam

# ── Mood/lookdev layer (PO v8.1 item 4, 2026-07-19) ───────────────────────
# Separate, importable module (lookdev/mood_valheim.py) — geometry
# generation stays decoupled from material/lighting mood. Applied AFTER all
# scene geometry/lights/world/camera exist and BEFORE the first render call,
# so every shot() below (including .blend save) sees the moodier scene.
# Wrapped defensively: a lookdev failure must never take down an otherwise-
# good geometry render.
if MOOD_ON:
    try:
        import mood_valheim
        mood_valheim.apply_mood(scene, S)
        print("[village_gen] mood_valheim applied")
    except Exception as e:
        print("[village_gen] MOOD layer failed, continuing WITHOUT it:", repr(e))
else:
    print("[village_gen] mood layer disabled (mood=off)")

def shot(label, cam_pos, target):
    cam.location = cam_pos
    cam.rotation_euler = (Vector(target) - Vector(cam_pos)).normalized().to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT_DIR, "village_%s_%s.png" % (BIOME, label))
    bpy.ops.render.render(write_still=True)
    print("[village_gen] shot", label, "->", scene.render.filepath)

if SCALE_NAME == "destacamento":
    shot("destacamento_only", (RING_R * 1.7, -RING_R * 2.0, RING_R * 1.3), (0.0, 0.0, 1.5))
else:
    shot("overview", (RING_R * 1.62, -RING_R * 1.88, RING_R * 1.06), (0.0, 0.0, 2.0))
    shot("gate", (2.5, -RING_R * 1.62, RING_R * 0.21), (0.0, -(RING_R - 3.0), 2.6))
    # FASTVIEW — PERMANENT occlusion/discovery audit camera (PO v8 item 2,
    # 2026-07-19): standing just inside the EXTERIOR gate (0.8m past the
    # threshold) at 1.7m mannequin eye height, looking straight ahead along
    # the entry direction — the exact "one fast glance from the gate" the
    # v7 verdict complained reveals ~80% of the village. Target is a fixed
    # 8m-ahead offset (not the casona/plaza position) so this shot always
    # tests the RAW sightline the baffle is supposed to block, independent
    # of where any given seed happens to place the casona.
    # PASS = casona door NOT visible in this frame AND < 50% of structures
    # identifiable. Re-check this shot every round — it is the v8 audit
    # metric, not a cosmetic extra.
    # Round-3 tune (self-eyeball, seed 21): the ROUND-1 bent-corridor design
    # broke the "plaza" shot (camera ended up inside the new interior-gate
    # geometry — see build_double_gate's docstring) and even after fixing
    # distances still filled the frame edge-to-edge with flat wall, unclear
    # as an audit image. Reverted to the single-baffle design (baffle at
    # ring_r-3.2, well inside the untouched 5m corridor); camera pulled back
    # to 0.8m past the threshold puts it ~2.4m from the baffle — close
    # enough to fully block the view, far enough to read as a real scene.
    # v8.1 re-tune (PO calibration, 2026-07-19): that 2.4m framing STILL read
    # as a blank wall filling ~70% of frame (overcorrected — "blind the
    # viewer" instead of "channel the view"). Camera moved to 0.3m past the
    # threshold (right at the gate, ~2.9m from the baffle) so more of the
    # corridor's own side walls recede into the frame before hitting the
    # baffle — a real sense of alley depth — and the baffle now carries a
    # lit torch + banner (see build_double_gate) so the far end is a warm
    # focal point, not raw wood.
    shot("fastview", (0.0, -(RING_R - 0.3), 1.7), (0.0, -(RING_R - 0.3) + 8.0, 1.7))
    # PLAZA — eye-level shot (PO v7 iteration protocol, permanent addition):
    # standing just inside the gate at mannequin eye height (~1.7m), looking
    # toward the casona across the plaza/paths. This is the PO's immersion
    # test — judge every future round from here, not just the drone-height
    # overview/gate shots.
    shot("plaza", (0.8, -(RING_R - 6.0), 1.7), (0.0, RING_R * 0.30 * 0.85, 1.7))
    # AUDIT (v11 item 2 diagnosis, temporary): close-up on the casona
    # entrance to check for the reported roof-canopy-blocks-door bug.
    _casona_y = RING_R * 0.30 * 0.85
    shot("casona_door_closeup", (0.3, _casona_y - 6.0, 1.7), (0.0, _casona_y - 2.6, 1.85))
    # AUDIT (v11 item 3 stairs-bug diagnosis, temporary): low side angle on
    # the casona's monumental entrance stairs to check tread/stringer
    # connectivity.
    shot("casona_stairs_side", (3.2, _casona_y - 3.3, 0.9), (0.0, _casona_y - 3.3, 0.4))
    # AUDIT (v11 item 9 well diagnosis, temporary).
    _commons_r = RING_R * 0.30
    _well_x, _well_y = _commons_r * 0.5, _commons_r * 0.2
    shot("well_closeup", (_well_x + 1.6, _well_y - 1.8, 1.4), (_well_x, _well_y, 1.0))
    if DEST_ACTIVE:
        shot("destacamento", (DEST_CX + DEST_RING_R * 1.7, DEST_CY - DEST_RING_R * 2.0, DEST_RING_R * 1.4),
             (DEST_CX, DEST_CY, 1.5))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "village_%s.blend" % BIOME))

if DOOR_HS:
    print("[village_gen] AUDIT door_h min=%.2f max=%.2f mannequin=%.2f" %
          (min(DOOR_HS), max(DOOR_HS), MANNEQUIN_H))
if WINDOW_HS:
    print("[village_gen] AUDIT window_h min=%.2f max=%.2f (sill~chest, head~mannequin_top)" %
          (min(WINDOW_HS), max(WINDOW_HS)))
print("[village_gen] DONE biome=%s threat=%s scale=%s seed=%d ring_r=%.1f" %
      (BIOME, THREAT_NAME, SCALE_NAME, SEED, RING_R))
