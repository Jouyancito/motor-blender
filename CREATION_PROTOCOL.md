# Creation Protocol — reference research + coherence reasoning BEFORE building

Joan's ask (verbatim intent): a gate has to run in the designer's head *before* the first
`bpy` call, the same way `recetas/RECETAS.md` gates *how* to build (which verified technique)
and `preflight_destructivo.py` gates *right before* a destructive op. This file gates *what*
to build and *whether it makes sense* — upstream of both. His own examples: a gate has hinges
and posts sized to what it carries, wood/steel/concrete depending on the economy that owns it;
a chicken coop's height and mesh-vs-post construction depend on the size of the birds it holds
— that reasoning has to run BEFORE the first `bpy` call, not get discovered by him after.

Every numbered step below is grounded in a REAL defect from the `village_gen.py` +
`mood_valheim.py` v1→v12 Judgment Day arc (dual-judge review, 2026-07-18) — the step exists
because that exact category of bug already happened once and cost a round (or several) to fix.

## 0. Scope

Applies to any new asset/module generator in this motor (`recetas/*.py`, `game/tools/blender/gen_*.py`,
`village_gen.py`-style scene composers, `lookdev/*.py` presets). Not a replacement for
`RECETAS.md` (technique library) or `preflight_destructivo` (pre-destructive-op safety) — this
runs BEFORE both, at the design stage.

## 1. Identify the real-world object category

Before writing geometry code, name the object's real-world category explicitly and ask: *does
this motor already have a generator for a sibling of this category?* If yes, the new object
inherits that sibling's shared grammar — it does not get a fresh hand-rolled implementation.

**Real example this step would have caught:** `build_goat()` (`village_gen.py:2887-2943`) is
documented as reusing `build_sheep()`'s grammar (2834-2885) but is actually a ~55-line
copy-paste with hand-tweaked constants (SUSPECT #4). "Goat" was never identified as *the same
category as sheep, parametrized differently* — it was treated as a new category from
scratch, so every future quadruped grammar fix now has to be applied twice by hand, and the
two will silently drift. Naming the category correctly at step 1 is what the v10 "fix the
shared function, not the call site" rule is actually about — it has to start at design time,
not get retrofitted after the copy-paste already shipped.

## 2. Multi-source reference research — visual AND functional

Two separate research passes, both mandatory, neither optional even for a "simple" prop:

### 2a. Visual — never a single source
Pull images from multiple independent references (photos, game art, prior in-motor assets of
a related category) before modeling. A single reference locks in that one photographer's
angle, lighting, and accidents of framing as if they were the object's defining features.

**Real example:** the *"give placeholders a real, recognizable silhouette instead of a
generic primitive"* principle — re-taught and successfully applied across 4 unrelated systems
in this arc (animals v7, campfire v8.1→v11, hanging cloth v11, firewood v11) — only worked
because each system was built by silhouette-matching against what that real object actually
looks like, not a stand-in cube/cylinder. It is the one principle in the whole retrospective
with **zero confirmed regressions** — proof that visual reference research, done up front,
is the cheapest bug prevention in this pipeline.

### 2b. Functional/logical — what components make this object make sense
Before modeling, list the components the object *needs* to be structurally/functionally
coherent, and the real-world logic that sizes/chooses them:
- **Structural components**: a gate needs hinges + posts that support its own weight and
  swing arc; a hanging line needs enough sag clearance for its own worst-case droop, not just
  its nominal midpoint.
- **Material implied by economy**: wood vs. stone vs. metal should follow the wealth/resources
  of whoever owns the structure in-fiction, not be picked arbitrarily per building.
- **Size implied by content**: a pen/coop's footprint should scale with what it holds (animal
  count, animal size) — not a fixed constant reused regardless of occupancy.

**Real example (component logic skipped):** `hangline_path_conflict`'s clearance check
(`village_gen.py:3463-3491`) validates against the *midpoint* of the height/sag ranges used by
`build_hanging_line` (3378-3417), but the builder can independently roll to the low end
(h=1.9, sag=0.20·span) — a real, buildable combination the check never actually clears
against (SUSPECT #5). The functional logic ("what's the worst case this component can
produce, and does my clearance check cover it, not just the average case") wasn't reasoned
through before the check was written.

**Real example (economy/scale logic skipped):** `total_houses = 4 + extra_count`
(`village_gen.py:3607`) counts the outhouse as a population unit, silently inflating
garden/livestock scaling off a structure that houses zero people (SUSPECT #7) — a content-size
rule (population → garden/livestock budget) applied without checking that every term in the
count actually represents what the rule assumes it represents.

### 2c. The research must end in PARAMETERS — and in BOTH halves of them

Joan, 2026-08-23: *"a veces te digo investigar, pero me buscas 1 o 2 referencias y eso es todo,
**necesito parámetros**"*. Minimum 4-5 independent sources, covering the RANGE of variation, and
the synthesis ends in a table the generator can consume — name, value, unit, source. Prose that
has to be re-interpreted at modelling time gets re-decided by eye, which is the thing the
research existed to prevent.

**The table has TWO halves, and both are mandatory:**

| Half | What it holds | How it fails |
|---|---|---|
| **MEASURE** | how long, how many, how fast, what ratio | easy to source, easy to verify — so it is the half that always gets written |
| **STRUCTURE** | per moving part: what PLANE it occupies, what ANGLE it holds relative to the body, and what LIMITS it | needs anatomy, not a fact sheet — so it is the half that always gets skipped |

**A part with no structural row is not modelled. It is researched first.**

**The real example this rule is made of (turtle, 2026-08-24).** The reference sheet had every
measure: carapace 0.845 m, height/length band 0.28-0.32, 5 vertebral scutes, 12 marginal pairs,
gait `lateral_sequence`, 0.54 m/s. All of it was hit. The ratio landed in band. And Joan looked
at the model and said the legs all point the same way and the head is just a sphere — because
not one of those parameters was STRUCTURAL. The sheet described how big the turtle is and never
described how it is put together.

One search closed it: in turtles *"the movement of the humerus occurs predominantly in the
horizontal plane while the movements of the distal limb occur predominantly in the vertical
plane, hence a typical sprawled posture"* (J. Exp. Biol.). The upper arm goes OUT sideways, the
forearm drops DOWN — an L-shaped elbow, which is why the four legs point into four different
quadrants. Four identical vertical cones cannot read as a turtle no matter how correct the
shell is. Same search also gave the animation its asymmetry: forelimb protraction is unusually
high, retraction is limited by the carapace-plastron bridge.

**None of that needed the client to explain it.** It is a documented fact about an animal that
exists. Joan's framing is the rule: *"si te digo que inventes algo que no hay en la realidad...
ahí sí hay que explicarte cada movimiento. Pero todo lo que estamos haciendo está en la
realidad. Están las referencias."* When the subject is real, missing structure is a research
failure, not a briefing failure.

### 2d. Every structural parameter needs a VISIBILITY assert

Implementing a structural parameter is not the same as making it visible, and the difference is
invisible in the code. Turtle, 2026-08-24, second pass: the sprawling posture was implemented
correctly — humerus horizontal, forearm vertical, one quadrant per leg — and the model still
read as four posts, because the shoulder sat at x=0.148 with a 0.105 humerus, putting the elbow
at 0.25 **inside a shell of radius 0.295**. The horizontal humerus was there in the data and
hidden under the carapace.

So for each structural parameter, write the geometric condition that makes it VISIBLE, and make
the build fail on it:

```python
print("[turtle] codo a %.3f m del eje, borde del caparazon %.3f m -> %s" % (...))
if max(_elbow_out) <= SHELL_OVERHANG:
    raise SystemExit("el codo queda bajo el caparazon -- la postura esparrancada no se lee")
```

That assert caught it on the very next run and refused to export. Without it the parameter would
have shipped correct-and-invisible, which is indistinguishable from not having it — and it is
exactly the shape of every other failure in this motor: the scute attribute that was painted and
never wired, the shell overlap that measured 74% while rendering as a smooth cap, the showcase
gate that checked a PNG existed rather than what was in it.

**The pattern, stated once:** *a value that is correct in the data and invisible on screen is
not done.* Structure asserts close the gap between the two, and they are cheap — one comparison
and one `SystemExit` per parameter.

**Translation rule for step 1** (the other half of this): every sentence of "what it is" must
end in a NUMBER or an ORIENTATION. *"Webbed feet"* is not a completed point; *"humerus
horizontal, forearm vertical, yaw ±40° per quadrant"* is. Correct prose that never becomes
geometry is the recurring failure — it also produced hair modelled as a uniform offset after
writing "hair is combed in one direction".

## 3. Concrete dimensions/proportions against the 1.80 m mannequin

Before building, write down the object's key dimensions as explicit numbers checked against
a 1.80 m human-scale reference (mannequin, doorway, existing rigged character) — not "looks
about right" in the viewport. This includes clearance heights (nothing should sit at a height
that would injure or clip a person walking under/past it) and load-bearing proportions
(a support post's cross-section relative to what it holds up).

**Real example:** the "wood at neck height" defect (v7) is exactly a missed dimension check —
a beam/prop placed at a height that reads as a neck-level hazard against the human scale
this village is built for. It had to be fixed in **two separate code paths** because the
height logic wasn't shared yet (the same category-1 gap `build_goat()` has today) — the exact
duplication v10's "shared function" rule was later written to close. A single "this dimension
is measured against MANNEQUIN_HEIGHT_M = 1.80, here is the clearance budget" check at design
time would have caught it once, in one place, instead of twice, in two.

**Real example (proportion, not just height):** `add_door()`'s docstring claims a clamp range
of `[1.9, 2.2]` at `wall_h - 0.35`; the code actually clamps `[1.90, 1.98]` at `wall_h - 0.30`
(`village_gen.py:1370-1394`, SUSPECT #3). Whichever number is correct, the fact that
*docstring and code disagree* means the dimension was never pinned to one deliberate,
verified value — write the number down against the mannequin BEFORE building, then keep the
docstring and the code reading the same number off that one source.

## 4. Build — into the shared function, not a new call site

Only after steps 1-3 are answered does geometry code get written. If step 1 identified a
sibling category, build by extending/parametrizing the sibling's existing function. If this
is a genuinely new category, build the shared function itself (parametrized for the variants
you already know are coming), not a one-off.

**Real example (this worked):** v12's `mat()` texture-pivot consolidation reused ~40 call
sites through a single interception point with zero per-site edits — direct, successful
reapplication of the v10 "shared function" lesson at the call-site level. The world-space vs.
object-local UV bug on destacamento struts was even caught and fixed the same round, with a
surgically scoped fix (bark→local, walls stayed world) — proof the pattern works when applied
deliberately.

**Corollary this arc surfaced (apply during this step, not after):** "shared function" isn't
done just because call sites got shorter — audit whether the new shared path still honors
every parameter the old call sites depended on. `mat()`'s cache key silently drops the
`color` arg for wood/thatch (CONFIRMED-adjacent, SUSPECT #2, `village_gen.py:735-753,1101`),
which orphaned `jitter_tone()` (dead code under `USE_REAL_TEXTURES=True`) and erased
per-biome wood/thatch tone variation — a real consolidation that succeeded at the call-site
level while quietly failing at the parameter-contract level. When you finish this step, list
every parameter the old call sites passed and confirm the new shared function still reads
each one.

## 5. Self-critique BEFORE presenting — render multiple angles, then compare against references

Do not present to Joan straight off a single overview render. Before presenting:

1. **Render multiple angles + close-ups** of the new object/scene — not one hero shot. A
   single distant overview hides exactly the defects that only show up in close proximity or
   from a specific angle.
2. **Check for floating geometry / scale errors / material incoherence** across those renders.
3. **Diff against the reference set gathered in step 2** — does the silhouette, proportion,
   and material read match what was actually researched, or did it drift during building?
4. **Re-run determinism-sensitive modules twice** with identical inputs and diff the output —
   do not assume a documented "deterministic" claim is true without having actually run it
   twice.

**Real example (this step, skipped, is exactly how the CONFIRMED bug survived to Judgment
Day):** `mood_valheim.py` documents a "byte-identical... same scene name + biome style"
determinism guarantee (docstring 36-41), but `_seed()` hashes `scene.name` — a Python `str`
— into the RNG seed (73-79), and CPython randomizes string hashing per-process unless
`PYTHONHASHSEED` is pinned, which nothing in this codebase does. This is CONFIRMED —
independently flagged by both blind judges — precisely the kind of defect a two-run diff at
self-critique time would surface immediately (the mood/light/bump jitter would visibly differ
run to run for an "identical" input), instead of shipping as a documented guarantee that was
never actually verified.

**Real example (close-up catches what an overview hides):** the recurring "no two instances
should look identical" principle escalated across the arc from whole-object variety (animal
silhouettes, v7) to per-object handmade imperfection (wood knots, mixed log diameters, v11) —
each step only got caught because someone looked closely enough to notice repetition, not
because a wide shot flagged it. The v13-candidate gap (bark has no per-instance jitter at the
material level) is exactly the granularity a close-up self-review is built to catch before
Joan does.

**Also check for orphaned/dead config while you're in there:** the vestigial fog block
(`village_gen.py:4126-4128`, sets `use_mist=True` without `start`/`depth`) and the hardcoded
`USE_REAL_TEXTURES` flag (732, not wired to CLI unlike every other flag in the file) are both
things a "does every flag/block in this diff still do something, and does it match this
file's own conventions" self-check would have caught at build time instead of leaving them
for the next reviewer to puzzle over.

## 6. Present to Joan

Only after steps 1-5 are complete: present the render set (multiple angles/close-ups, not
one), the reference set it was checked against, and — for anything that touches a shared
function — which call sites/parameters were audited in step 4's corollary. If step 5 surfaced
an open question (a dimension you couldn't verify, a determinism check you couldn't run), say
so explicitly rather than presenting a guess as verified.

## Anti-patterns (symmetry with RECETAS.md's "Anti-recetas")

- Copy-pasting a sibling category's implementation instead of parametrizing the shared
  function (`build_goat` vs `build_sheep`) — cheap now, doubles every future fix forever.
- Validating a range/clearance check against the *midpoint* of a randomized parameter instead
  of its worst case (`hangline_path_conflict`).
- Claiming a determinism/reproducibility guarantee in a docstring without having run the code
  twice and diffed the output (`mood_valheim._seed`).
- Consolidating call sites into a shared function without auditing whether every parameter
  the old call sites relied on is still honored (`mat()` dropping `color`).
- Presenting a single overview render as "done" — close-up/multi-angle self-review is
  what catches floating geometry, scale drift, and material incoherence before Joan does.
- Hardcoding a flag that every sibling flag in the same file exposes via CLI
  (`USE_REAL_TEXTURES`), or leaving a config block that sets one required field of a pair
  without the other (the vestigial `use_mist` fog block).

Living document — first written 2026-07-21, grounded in the village_gen.py v1→v12 Judgment
Day retrospective. Extend it the same way `RECETAS.md`/`blender-asset-smith` grow: append a
new real example under the step it would have caught, don't rewrite the step from scratch.
