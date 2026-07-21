"""lookdev/mood_valheim.py — reusable Blender/EEVEE mood & lookdev layer.

Kills the flat/toylike look of a bare procedural render (PO Front B request,
2026-07-19, "dungeon-party/village-gen-feedback") WITHOUT touching any
geometry. Applies, to an ALREADY-BUILT scene:

  1. A warm-key / cool-fill LIGHT HIERARCHY (temperature contrast).
  2. Procedural ALBEDO variation (PO v9, 2026-07-19 — the highest-impact
     addition: multi-tone noise mixed into BASE COLOR, not just normals, so
     it reads regardless of light angle/distance) + BUMP detail (no UV
     unwrap needed) on the shared hard-surface materials (wood / stone-rock
     / thatch-roof / ground-dirt) via name-pattern matching.
  3. Very-low ATMOSPHERE via the World MIST PASS (`world.mist_settings` +
     `view_layer.use_pass_mist`, blended in by the compositor step) so
     distant geometry softens instead of reading as a flat cardboard cutout.
  4. A compositor POST pass — glare/bloom, the mist tint from step 3, a
     subtle vignette, and a color grade derived from the caller's own
     sky/sun_color values (never a hardcoded per-biome branch).

This module is intentionally GENERATOR-AGNOSTIC: nothing in it references
villages, huts, or biome names. It only reads a plain dict with a handful of
STYLES-shaped keys (`sky`, `sun_color`, `sun_energy`, `sun_elev`, `fog` —
all optional, every read is defensive) — any Blender script that builds
that same shape of dict can reuse it on any scene, not just this village
generator. `recetas/village_gen.py` is today's only caller (imports this
module via a `sys.path.append` one directory up — see its CLI docstring for
the `mood` on/off flag).

Public API — the ONLY function callers should use:

    apply_mood(scene, biome_style)

Everything else (`_...` prefixed) is a private implementation detail and
may change shape between sessions.

Seeding: every pseudo-random choice in this module (bump frequency jitter,
flame/wedge-style variation is NOT here — that's village_gen.py's own rng)
derives from a `random.Random` seeded deterministically from the scene name
+ the style dict's own sky/sun_color values — NEVER wall-clock/os time. Two
runs on the same scene name + same biome style always produce byte-
identical mood tuning. See `_seed()`.

Known gaps / Blender-version defensiveness (2026-07-19, Blender 5.1.2):
  - Every `world.mist_settings.*` / `view_layer.use_pass_mist` property set
    is wrapped (`_safe_set`) so a renamed/missing property on a different
    Blender build just gets skipped (printed once) instead of crashing the
    whole render.
  - ATMOSPHERE GOTCHA (see `_add_atmosphere`'s own docstring for the full
    story): a WORLD VOLUME SCATTER shader (the more "physically real" 3D-fog
    option) was tried FIRST and caused a near-total blackout of the whole
    village at even very low nominal density, empirically confirmed via an
    A/B re-render of the saved .blend. Switched to the World Mist Pass
    (bounded 0-1, blended in by the compositor) instead — lower risk, and
    it was the explicitly preferred option in this module's own design
    brief. If a future Blender build's compositor doesn't expose a "Mist"
    render-pass output on the Render Layers node, `_setup_compositor` skips
    the tint stage cleanly (prints once, vignette/grade still apply) rather
    than throwing.
  - Blender 5.1.2 replaced the classic `scene.node_tree` compositor with a
    node-GROUP system (`scene.compositing_node_group`, a `CompositorNodeTree`
    with its own `interface` + `NodeGroupOutput` — no `CompositorNodeComposite`
    node exists anymore) and moved most per-node parameters (glare type,
    ellipse mask position/size, color-balance gain, blur size, ...) from
    Python attributes onto INPUT SOCKETS. `_setup_compositor` is written
    entirely against that shape — see its own docstring.
"""
import bpy
import math
import random

# ── internal: deterministic seeding ─────────────────────────────────────────

def _seed(scene, biome_style):
    key = (
        scene.name,
        tuple(biome_style.get("sky", (0.0, 0.0, 0.0))),
        tuple(biome_style.get("sun_color", (0.0, 0.0, 0.0))),
    )
    return random.Random(hash(key) & 0xFFFFFFFF)


def _safe_set(obj, attr, value, label):
    """Set obj.attr = value; on any failure (renamed/missing property on a
    different Blender build) print once and continue — a lookdev nicety
    must never crash an otherwise-good render."""
    try:
        setattr(obj, attr, value)
        return True
    except Exception as e:
        print("[mood_valheim] skipped %s (%s)" % (label, e))
        return False


# ── 1. Light hierarchy: warm key + cool fill ────────────────────────────────

def _tune_lights(scene, biome_style, rng):
    """Bias the existing SUN (built by the caller) toward a lower, warmer,
    stronger KEY light (long dramatic shadows), then add a weak, cool-blue
    FILL sun from a different azimuth — the goal is temperature CONTRAST
    between light and shadow, not raw brightness."""
    key_sun = None
    for o in scene.objects:
        if o.type == 'LIGHT' and o.data.type == 'SUN':
            key_sun = o
            break

    base_elev = float(biome_style.get("sun_elev", 40.0))
    base_color = biome_style.get("sun_color", (1.0, 0.9, 0.8))
    base_energy = float(biome_style.get("sun_energy", 2.0))

    if key_sun is not None:
        # Lower + more dramatic elevation (bias down, never below ~8 deg so
        # shadows stay readable instead of edge-on/black).
        new_elev = max(8.0, base_elev * rng.uniform(0.62, 0.78))
        warm_target = (1.0, 0.62, 0.28)
        warm_amt = rng.uniform(0.20, 0.32)
        warm_color = tuple(
            base_color[i] * (1.0 - warm_amt) + warm_target[i] * warm_amt for i in range(3)
        )
        key_sun.data.color = warm_color
        # PoE GRADE (v12, Joan: "mas Path of Exile, menos animado" —
        # village_poe_style/_synthesis.md: "el resto de la escena es FRIO Y
        # OSCURO... contraste extremo, no el 'calido general' que tenemos
        # ahora"). Was 1.10-1.25 (BOOSTED above the biome baseline, flat
        # even daylight); pulled DOWN below baseline so the sun alone no
        # longer evenly floods the whole village — torches/braziers/hearth
        # (their own point lights + emissive boost below) become the
        # dominant light POOLS instead of a uniform wash.
        key_sun.data.energy = base_energy * rng.uniform(0.70, 0.85)
        # Preserve the existing azimuth (-35 deg, set by the caller) — only
        # the elevation/drama changes, so composition/shadow direction the
        # caller already tuned doesn't shift underneath it.
        az = key_sun.rotation_euler[2]
        key_sun.rotation_euler = (math.radians(90 - new_elev), 0.0, az)

    # Cool ambient fill — a second, much weaker sun-like lamp, tinted
    # cool-blue, from a different azimuth, for temperature contrast against
    # the warm key. Idempotent: reuse the object if apply_mood ever runs
    # twice on the same scene instead of stacking duplicate fills.
    fill = bpy.data.objects.get("mood_fill_sun")
    if fill is None:
        fill_data = bpy.data.lights.new("mood_fill_sun", 'SUN')
        fill = bpy.data.objects.new("mood_fill_sun", fill_data)
        scene.collection.objects.link(fill)
    # PoE GRADE (v12): fill pulled down further too (was 0.12-0.20) — a
    # colder, DARKER ambient is the whole point of the "tight warm pools
    # against cold-dark surroundings" reference read, not just a cooler tint
    # at the same brightness.
    fill_energy = base_energy * rng.uniform(0.05, 0.09)
    fill.data.energy = max(0.03, fill_energy)
    sky = biome_style.get("sky", (0.4, 0.5, 0.6))
    cool_target = (0.45, 0.62, 0.95)
    cool_amt = 0.55
    fill.data.color = tuple(sky[i] * (1.0 - cool_amt) + cool_target[i] * cool_amt for i in range(3))
    key_az = key_sun.rotation_euler[2] if key_sun is not None else math.radians(-35)
    fill_az = key_az + math.radians(rng.uniform(130.0, 160.0))
    fill_elev = min(65.0, base_elev * rng.uniform(1.1, 1.4) + 10.0)
    fill.rotation_euler = (math.radians(90 - fill_elev), 0.0, fill_az)

    # PoE GRADE (v12) — dim the World background strength too (the ambient
    # sky-dome light every surface receives regardless of sun angle) so the
    # darker key/fill above isn't offset by an unchanged flat ambient floor.
    world = scene.world
    if world is not None and world.use_nodes:
        bg = world.node_tree.nodes.get("Background")
        if bg is not None:
            try:
                cur = bg.inputs[1].default_value
                bg.inputs[1].default_value = cur * rng.uniform(0.60, 0.75)
            except Exception as e:
                print("[mood_valheim] skipped world background dim (%s)" % e)


def _tighten_light_pools(rng):
    """PoE GRADE (v12) — boost every POINT light's energy (torches, braziers,
    the hearth/campfire ember lights built by village_gen.py's
    build_ember_light) so their pool of illumination reads as a genuinely
    BRIGHT, TIGHT hotspot against the now-darker key/fill/ambient above,
    instead of a weak glow that gets lost once the general scene dims.
    Mirrors _boost_emissives' same-shaped light-side counterpart: the
    material boost makes fire/window SURFACES read hot, this makes the
    LIGHT they cast read as a real pool. Sun/Area lights untouched — this
    is specifically the "torch against cold dark" contrast lever."""
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and o.data.type == 'POINT':
            o.data.energy = o.data.energy * rng.uniform(1.35, 1.65)


def _boost_emissives(rng):
    """Fire/window emissive materials read warmer and bloom-friendlier —
    nudge any material's existing Emission Strength up a bit (capped) and
    push its Emission Color slightly warmer, so the compositor Glare node
    (see _setup_compositor) has something bright enough to actually bloom.
    Never touches materials with zero emission (leaves plain wood/stone/etc
    alone)."""
    for m in bpy.data.materials:
        if not m.use_nodes or m.node_tree is None:
            continue
        for n in m.node_tree.nodes:
            if n.type != 'BSDF_PRINCIPLED':
                continue
            strength_in = n.inputs.get("Emission Strength")
            color_in = n.inputs.get("Emission Color")
            if strength_in is None or color_in is None:
                continue
            cur = strength_in.default_value
            if cur <= 0.0:
                continue
            strength_in.default_value = min(16.0, cur * rng.uniform(1.15, 1.35))
            col = color_in.default_value
            warm_amt = 0.12
            color_in.default_value = (
                col[0] * (1.0 - warm_amt) + 1.0 * warm_amt,
                col[1] * (1.0 - warm_amt) + col[1] * warm_amt,
                col[2] * (1.0 - warm_amt) + col[2] * 0.7 * warm_amt,
                col[3],
            )


# ── 2. Procedural bump detail (no UV unwrap needed) ─────────────────────────

def _add_bump(mat, rng, freq, distortion, strength, stretch=None):
    """Inject Geometry(Position) -> Mapping -> Noise -> Bump -> BSDF.Normal
    into an existing Principled-BSDF material. No UV unwrap requirement.
    Idempotent: if the BSDF's Normal input is already linked (a previous
    apply_mood() call, or a material that already had its own bump), it's
    left untouched.

    WORLD-SPACE GOTCHA (PO v9 self-fix, 2026-07-19): originally sourced
    from `TexCoord.Object`, which returns the RAW MESH-LOCAL coordinate
    (pre object.scale — village_gen.py's box()/cylinder() helpers scale
    the OBJECT, not the mesh data, so every box's local verts sit at the
    same +-0.5 regardless of final world size). A shared material like
    "wood_dark" is reused on both a huge gate wall AND a tiny fence
    picket, so the SAME noise frequency read as a few giant blotches on
    the wall and fine grain on the picket — confirmed via an actual v9
    round-1 render (giant amoeba-shaped patches on the gate baffle, not
    streaky wood grain). Switched to `Geometry.Position` (true WORLD-space
    meters, unaffected by any one object's local scale) so a shared
    material's frequency reads as the same real-world grain size on every
    object it's applied to, small or huge."""
    if not mat.use_nodes or mat.node_tree is None:
        return False
    nt = mat.node_tree
    bsdf = None
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
            break
    if bsdf is None:
        return False
    normal_in = bsdf.inputs.get("Normal")
    if normal_in is None or normal_in.is_linked:
        return False

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mapping = nt.nodes.new("ShaderNodeMapping")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    bump = nt.nodes.new("ShaderNodeBump")
    for n in (geo, mapping, noise, bump):
        n.location = (bsdf.location.x - 800, bsdf.location.y - 200)

    if stretch is not None:
        mapping.inputs["Scale"].default_value = stretch
    noise.inputs["Scale"].default_value = freq
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Distortion"].default_value = distortion
    bump.inputs["Strength"].default_value = strength

    nt.links.new(geo.outputs["Position"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], normal_in)
    return True


def _jitter_tone(base, rng, pct):
    return tuple(max(0.0, min(1.0, c * (1.0 + rng.uniform(-pct, pct)))) for c in base)


def _add_albedo_noise(mat, rng, tones, freq, distortion, stretch=None, interpolation='LINEAR'):
    """Inject Geometry(Position) -> Mapping -> Noise -> ColorRamp(tones)
    into an existing Principled BSDF's Base Color — same no-UV WORLD-space
    pattern as `_add_bump` (see its docstring for why world-space, not
    object-space: a shared material's frequency must read as the same
    real-world grain/mottle size whether it's on a huge wall or a tiny
    picket, and object-local coords don't guarantee that). Idempotent:
    skips if Base Color is already linked (window glass, flame emissives,
    etc. stay untouched)."""
    if not mat.use_nodes or mat.node_tree is None:
        return False
    nt = mat.node_tree
    bsdf = None
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            bsdf = n
            break
    if bsdf is None:
        return False
    color_in = bsdf.inputs.get("Base Color")
    if color_in is None or color_in.is_linked:
        return False

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mapping = nt.nodes.new("ShaderNodeMapping")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    for n in (geo, mapping, noise, ramp):
        n.location = (bsdf.location.x - 1100, bsdf.location.y + 220)

    if stretch is not None:
        mapping.inputs["Scale"].default_value = stretch
    noise.inputs["Scale"].default_value = freq
    noise.inputs["Detail"].default_value = rng.uniform(2.0, 4.0)
    noise.inputs["Distortion"].default_value = distortion

    ramp.color_ramp.interpolation = interpolation
    elements = ramp.color_ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    elements[0].position = 0.0
    elements[0].color = (*tones[0], 1.0)
    for i, tone in enumerate(tones[1:], start=1):
        pos = i / (len(tones) - 1)
        el = elements.new(pos)
        el.color = (*tone, 1.0)

    nt.links.new(geo.outputs["Position"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], color_in)
    return True


def _inject_albedo_variation(rng):
    """PO v9 item 1 (2026-07-19, THE BIG ONE — Joan's own rendered-viewport
    screenshot): 'la paja no es un bloque color paja: son texturas,
    relieves, azar, superposicion'. The v8.1 bump pass above only perturbs
    the NORMAL — invisible on a flat-lit face, at overview distance, or in
    any shading mode that doesn't catch the light at the right grazing
    angle. This is the complementary, higher-impact fix: multi-tone noise
    mixed directly into BASE COLOR (the same no-UV Object-space
    TexCoord->Mapping->Noise chain `_inject_bump` already proved, feeding a
    ColorRamp instead of a Bump node) so the material reads as textured
    regardless of light angle, camera distance, or shading mode — fixed AT
    THE ALBEDO, not just the relief.

    Pattern-matched by material name (same families `_inject_bump` already
    keys off), each tuned to what that surface looks like up close:
      - thatch: 2-3 straw tones, CONSTANT ramp (blotchy distinct bundles,
        not a smooth gradient) + heavy directional stretch (streaks like
        laid straw, matches the bump pass's own stretch axis).
      - tile/shingle: coursing-tone variation, CONSTANT ramp + directional
        stretch (reinforces the existing row-banding geometry).
      - wood: CONSTANT ramp + heavy stretch = hard-edged plank-stripe
        bands, mixed with the same noise's continuous grain tone.
      - stone/rock: LINEAR ramp, undirected coarse noise = mottled patches.
      - ground/dirt/soil/path: CONSTANT ramp, undirected coarse noise =
        dirt blotching."""
    for m in bpy.data.materials:
        name = m.name.lower()
        if not m.use_nodes or m.node_tree is None:
            continue
        base_rgba = None
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                base_rgba = tuple(n.inputs["Base Color"].default_value)[:3]
                break
        if base_rgba is None:
            continue
        if "thatch" in name:
            tones = [_jitter_tone(base_rgba, rng, 0.10),
                     tuple(min(1.0, c * 1.28) for c in base_rgba),
                     tuple(c * 0.72 for c in base_rgba)]
            _add_albedo_noise(m, rng, tones, freq=rng.uniform(8.0, 13.0), distortion=0.3,
                               stretch=(1.0, rng.uniform(7.0, 10.0), 1.0), interpolation='CONSTANT')
        elif "tile" in name or "shingle" in name:
            tones = [base_rgba, tuple(min(1.0, c * 1.18) for c in base_rgba),
                     tuple(c * 0.78 for c in base_rgba)]
            _add_albedo_noise(m, rng, tones, freq=rng.uniform(9.0, 14.0), distortion=0.25,
                               stretch=(1.0, rng.uniform(8.0, 12.0), 1.0), interpolation='CONSTANT')
        elif "wood" in name:
            tones = [base_rgba, tuple(min(1.0, c * 1.22) for c in base_rgba),
                     tuple(c * 0.75 for c in base_rgba)]
            _add_albedo_noise(m, rng, tones, freq=rng.uniform(5.0, 9.0), distortion=0.3,
                               stretch=(1.0, rng.uniform(3.5, 5.5), 1.0), interpolation='CONSTANT')
        elif "stone" in name or "rock" in name:
            tones = [tuple(c * 0.80 for c in base_rgba), base_rgba,
                     tuple(min(1.0, c * 1.20) for c in base_rgba)]
            _add_albedo_noise(m, rng, tones, freq=rng.uniform(2.0, 3.5), distortion=0.6,
                               stretch=None, interpolation='LINEAR')
        elif "ground" in name or "dirt" in name or "soil" in name or "path" in name or "patch" in name:
            tones = [tuple(c * 0.78 for c in base_rgba), base_rgba,
                     tuple(min(1.0, c * 1.20) for c in base_rgba)]
            _add_albedo_noise(m, rng, tones, freq=rng.uniform(1.6, 2.6), distortion=0.55,
                               stretch=None, interpolation='CONSTANT')


def _inject_bump(rng):
    """Pattern-match every material already created by the caller (by NAME
    substring — village_gen.py's `mat()` cache keys already put "wood" /
    "wood_dark" / "stone_*" / "roof" / "thatch" / "shingle" in most relevant
    material names) and inject a bump appropriate to that surface family.
    Strength always stays in the 0.1-0.3 range (subtle surface response to
    light, never visible noise/banding)."""
    for m in bpy.data.materials:
        name = m.name.lower()
        if "wood" in name:
            # Anisotropic wood-grain read: stretch the noise heavily along
            # one axis so it streaks like grain instead of blobbing.
            _add_bump(m, rng, freq=rng.uniform(6.0, 10.0), distortion=0.35,
                      strength=rng.uniform(0.15, 0.25), stretch=(1.0, rng.uniform(4.0, 6.0), 1.0))
        elif "stone" in name or "rock" in name:
            # Coarser, undirected noise — rough stone grain, not streaky.
            _add_bump(m, rng, freq=rng.uniform(2.5, 4.0), distortion=0.6,
                      strength=rng.uniform(0.20, 0.30), stretch=None)
        elif "roof" in name or "thatch" in name or "shingle" in name:
            # Directional/streaky — reads as combed straw / laid shingle
            # courses (heavier stretch than wood grain).
            _add_bump(m, rng, freq=rng.uniform(10.0, 16.0), distortion=0.2,
                      strength=rng.uniform(0.12, 0.20), stretch=(1.0, rng.uniform(10.0, 14.0), 1.0))


# ── 3. Atmosphere: World Mist Pass (NOT a 3D volume — see gotcha below) ─────

def _add_atmosphere(scene, biome_style):
    """World MIST PASS (`world.mist_settings` + `view_layer.use_pass_mist`)
    so distant geometry (far palisade, background trees) softens at range
    instead of reading as a flat cardboard cutout. The actual visible
    blending happens in the compositor (`_setup_compositor`), which mixes a
    biome fog tint over the image using the Mist pass's 0-1 distance factor,
    capped low so it softens rather than fogs out.

    GOTCHA (2026-07-19, this exact Blender/EEVEE build, found via a
    render-vs-render A/B test, not assumed): an EARLIER version of this
    function used a WORLD VOLUME SCATTER shader (density fed by a height
    gradient) instead of the Mist Pass, reasoning that the Mist Pass "only
    reaches the compositor and isn't directly visible on its own". That
    volume-scatter approach caused a NEAR-TOTAL BLACKOUT of the whole
    village at even very low nominal density (~0.002-0.006) — confirmed by
    reloading the saved .blend and re-rendering with the world Volume link
    removed (render returned to normal) vs. with volumetric shadows merely
    disabled (STILL black — so it wasn't just shadow attenuation, the
    camera-side scattering/absorption itself was the problem at village-
    scale camera distances in this EEVEE build). The Mist Pass is bounded
    (0-1, driven by `mist_settings.start/depth`, no runaway optical-depth
    blowup) and is the explicitly-preferred, lower-risk option per this
    module's own design brief — use it, not the volume cube."""
    world = scene.world
    if world is None:
        return
    has_fog_hint = bool(biome_style.get("fog"))
    ms = world.mist_settings
    _safe_set(ms, "use_mist", True, "mist_settings.use_mist")
    # Round-1 self-eyeball (pradera seed 21): start=4/depth=85 maxed the
    # mist factor out across almost the WHOLE frame on the far drone-height
    # "overview" camera (which sits ~60-90 world units from its subject at
    # aldea scale) — read as a flat uniform wash instead of a distance
    # gradient, even though the same settings gave a nice, clearly-graduated
    # haze on the closer eye-level "plaza"/"destacamento" shots. Pulled
    # start/depth out further so the overview camera's typical subject
    # distance sits mid-gradient instead of past the far clamp.
    _safe_set(ms, "start", 10.0, "mist_settings.start")
    # Denser-feeling biomes (bosque/hielo, which already set a STYLES "fog"
    # tint) ramp to full mist over a SHORTER distance (reads mistier
    # sooner); the sunnier default (pradera, fog=None) ramps more gradually
    # (a much lighter haze, only at the far edges).
    _safe_set(ms, "depth", 90.0 if has_fog_hint else 150.0, "mist_settings.depth")
    _safe_set(ms, "falloff", 'QUADRATIC', "mist_settings.falloff")

    for vl in scene.view_layers:
        _safe_set(vl, "use_pass_mist", True, "view_layer.use_pass_mist")


# ── 4. Compositor: glare/bloom + mist tint + vignette + color grade ────────

def _biome_grade(biome_style):
    """Derive a subtle per-channel gain FROM the biome's own sky/sun_color
    values — never a hardcoded per-biome branch. Mostly weighted toward the
    sun color (the light identity) with a touch of the sky tint (ambient
    mood), then normalized around 1.0 so it nudges color rather than
    darkening/brightening the whole image.

    Falls out naturally per today's 3 biomes (documented so the choice
    isn't "magic"): pradera's warm sun (1.0,0.93,0.78) + warm-day sky pushes
    R/G up, B down (golden-hour); bosque's greenish sun (0.85,0.95,0.82) +
    dark-green misty sky pushes G up relative to R/B (green-misty); hielo's
    cool-blue sun (0.62,0.72,0.95) + near-black-blue night sky pushes B up
    hard, R down (blue-night)."""
    sun = biome_style.get("sun_color", (1.0, 1.0, 1.0))
    sky = biome_style.get("sky", (0.5, 0.5, 0.5))
    r = 0.7 * sun[0] + 0.3 * sky[0]
    g = 0.7 * sun[1] + 0.3 * sky[1]
    b = 0.7 * sun[2] + 0.3 * sky[2]
    avg = max(1e-4, (r + g + b) / 3.0)
    return (r / avg, g / avg, b / avg)


def _setup_compositor(scene, biome_style):
    """Blender 5.1.2 moved the scene compositor from the old `scene.
    node_tree` + free-floating Composite node to a NODE-GROUP system
    (`scene.compositing_node_group`, a `CompositorNodeTree` datablock with
    its own `interface` + a `NodeGroupOutput` node — no `CompositorNode
    Composite` node type exists anymore) AND moved almost every node
    parameter that used to be a plain Python attribute (glare type/quality/
    mix, ellipse mask width/height/type, color-balance gain, blur size)
    onto INPUT SOCKETS instead (`node.inputs["Name"].default_value`, with
    enum-like "MENU" sockets taking the full human-readable label string,
    e.g. "Fog Glow" / "High" / "Add" — verified empirically against this
    exact Blender build, see the mem_save note for this session). Every
    step below is written against that socket-driven shape; verified by
    an actual full village render, not assumed from older Blender docs."""
    scene.use_nodes = True
    nt = scene.compositing_node_group
    if nt is None:
        nt = bpy.data.node_groups.new("Mood Compositor", 'CompositorNodeTree')
        scene.compositing_node_group = nt
    if not list(nt.interface.items_tree):
        nt.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')

    render_layers = None
    group_out = None
    for n in nt.nodes:
        if n.type == 'R_LAYERS':
            render_layers = n
        elif n.type == 'GROUP_OUTPUT':
            group_out = n
    if render_layers is None:
        render_layers = nt.nodes.new("CompositorNodeRLayers")
    if group_out is None:
        group_out = nt.nodes.new("NodeGroupOutput")

    # Idempotent: if a previous apply_mood() already built this chain, reuse
    # it instead of stacking a second one.
    glare = nt.nodes.get("mood_glare")
    if glare is None:
        glare = nt.nodes.new("CompositorNodeGlare")
        glare.name = "mood_glare"
    glare.inputs["Type"].default_value = "Fog Glow"  # bloom-style glow, catches fire/window emissives
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 0.9
    glare.inputs["Strength"].default_value = 0.35  # subtle — glow, not a blown-out filter
    glare.inputs["Size"].default_value = 7.0

    ellipse = nt.nodes.get("mood_vignette_mask")
    if ellipse is None:
        ellipse = nt.nodes.new("CompositorNodeEllipseMask")
        ellipse.name = "mood_vignette_mask"
    ellipse.inputs["Operation"].default_value = "Add"
    ellipse.inputs["Value"].default_value = 1.0
    ellipse.inputs["Position"].default_value = (0.5, 0.5)
    ellipse.inputs["Size"].default_value = (1.30, 1.30)  # bigger than frame — mask=1 through most of it

    blur = nt.nodes.get("mood_vignette_blur")
    if blur is None:
        blur = nt.nodes.new("CompositorNodeBlur")
        blur.name = "mood_vignette_blur"
    blur.inputs["Size"].default_value = (0.05, 0.05)

    # mask (1 center / 0 far-corner) -> Map Range to a NARROW darkening
    # range (1.0 center / 0.75 corner) so corners dim slightly instead of
    # inverting through a separate Math node.
    maprange = nt.nodes.get("mood_vignette_maprange")
    if maprange is None:
        maprange = nt.nodes.new("ShaderNodeMapRange")
        maprange.name = "mood_vignette_maprange"
    maprange.inputs["From Min"].default_value = 0.0
    maprange.inputs["From Max"].default_value = 1.0
    maprange.inputs["To Min"].default_value = 0.75
    maprange.inputs["To Max"].default_value = 1.0
    maprange.clamp = True

    vig_mix = nt.nodes.get("mood_vignette_mix")
    if vig_mix is None:
        vig_mix = nt.nodes.new("ShaderNodeMix")
        vig_mix.name = "mood_vignette_mix"
        vig_mix.data_type = 'RGBA'
    vig_mix.blend_type = 'MULTIPLY'
    vig_a = None
    vig_b = None
    factor_sock = None
    for s in vig_mix.inputs:
        if s.type == 'RGBA' and vig_a is None:
            vig_a = s
        elif s.type == 'RGBA' and vig_b is None:
            vig_b = s
        elif s.type == 'VALUE' and s.name == 'Factor' and factor_sock is None:
            factor_sock = s
    if factor_sock is not None:
        factor_sock.default_value = 1.0  # always apply; the map-range above already keeps it subtle

    grade = nt.nodes.get("mood_color_balance")
    if grade is None:
        grade = nt.nodes.new("CompositorNodeColorBalance")
        grade.name = "mood_color_balance"
    r, g, b = _biome_grade(biome_style)
    blend = 0.45  # keep the push SUBTLE — this is mood, not a filter
    gain = (1.0 * (1 - blend) + r * blend, 1.0 * (1 - blend) + g * blend, 1.0 * (1 - blend) + b * blend)
    # NOTE: ColorBalance's Lift/Gamma/Gain each expose TWO sockets sharing
    # the display name ("Gain" appears for both a VALUE and an RGBA
    # socket) — only their `identifier` differs ("Base Gain" vs "Color
    # Gain"), so name-based .get("Gain") is ambiguous. Look up by
    # identifier instead (verified empirically against this Blender build).
    gain_sock = grade.inputs.get("Color Gain")
    if gain_sock is not None:
        gain_sock.default_value = (*gain, 1.0)
    else:
        print("[mood_valheim] no 'Color Gain' socket on ColorBalance — skipping color grade")

    # PoE DESATURATION (v12, Joan: "mas Path of Exile, menos animado" —
    # village_poe_style/_synthesis.md: "practicamente TODO desaturado...
    # salvo el fuego"). Pulls overall saturation down hard on the graded
    # image. Fire/window emissives still read vivid despite the flat
    # saturation multiplier below because _boost_emissives (materials) +
    # _tighten_light_pools (lights) already pushed their SOURCE brightness
    # well past 1.0 — Filmic's highlight rolloff reads a very bright warm
    # pixel as a hot glow regardless of the saturation knob, so the "cheap"
    # global desaturation (not a luminance-masked selective one, which would
    # need a much bigger node graph) still lands the "near-total desaturation
    # except fire" read without the extra complexity/failure surface.
    desat = nt.nodes.get("mood_desaturate")
    if desat is None:
        desat = nt.nodes.new("CompositorNodeHueSat")
        desat.name = "mood_desaturate"
    try:
        desat.inputs["Saturation"].default_value = 0.42
        desat.inputs["Hue"].default_value = 0.5  # 0.5 = no hue shift on this node's 0-1 wheel
        desat.inputs["Value"].default_value = 1.0
    except Exception as e:
        print("[mood_valheim] skipped PoE desaturation (%s)" % e)
        desat = None

    # MIST TINT (item 3, Atmosphere) — blend the graded image toward a
    # biome fog color, driven by the Mist render pass (0 near camera / 1 at
    # `mist_settings.depth`), remapped to a LOW cap so distance softens
    # instead of fogging out. This is the compositor half of _add_atmosphere
    # (see its docstring for why this replaced an earlier world-volume
    # attempt that blacked out the whole village).
    mist_out = render_layers.outputs.get("Mist")
    mist_maprange = nt.nodes.get("mood_mist_maprange")
    if mist_maprange is None:
        mist_maprange = nt.nodes.new("ShaderNodeMapRange")
        mist_maprange.name = "mood_mist_maprange"
    mist_maprange.inputs["From Min"].default_value = 0.0
    mist_maprange.inputs["From Max"].default_value = 1.0
    mist_maprange.inputs["To Min"].default_value = 0.0
    mist_maprange.inputs["To Max"].default_value = 0.32  # cap — soften, never fully fog out
    mist_maprange.clamp = True

    mist_mix = nt.nodes.get("mood_mist_mix")
    if mist_mix is None:
        mist_mix = nt.nodes.new("ShaderNodeMix")
        mist_mix.name = "mood_mist_mix"
        mist_mix.data_type = 'RGBA'
    mist_mix.blend_type = 'MIX'
    mist_a, mist_b, mist_factor = None, None, None
    for s in mist_mix.inputs:
        if s.type == 'RGBA' and mist_a is None:
            mist_a = s
        elif s.type == 'RGBA' and mist_b is None:
            mist_b = s
        elif s.type == 'VALUE' and s.name == 'Factor' and mist_factor is None:
            mist_factor = s
    fog_color = biome_style.get("fog") or biome_style.get("sky", (0.6, 0.65, 0.7))
    if mist_b is not None:
        mist_b.default_value = (*fog_color, 1.0)

    nt.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], grade.inputs["Image"])
    nt.links.new(ellipse.outputs["Mask"], blur.inputs["Image"])
    nt.links.new(blur.outputs["Image"], maprange.inputs["Value"])

    # Chain: grade -> [desaturate] -> mist tint (if the Mist pass is
    # available) -> vignette -> group output. Falls back to skipping the
    # mist stage cleanly if the pass isn't there (e.g. use_pass_mist failed
    # to stick on this build); same fallback pattern for desaturation.
    pre_vig_output = grade.outputs["Image"]
    if desat is not None:
        nt.links.new(grade.outputs["Image"], desat.inputs["Image"])
        pre_vig_output = desat.outputs["Image"]
    if mist_out is not None and mist_a is not None and mist_b is not None and mist_factor is not None:
        nt.links.new(mist_out, mist_maprange.inputs["Value"])
        nt.links.new(grade.outputs["Image"], mist_a)
        nt.links.new(mist_maprange.outputs["Result"], mist_factor)
        mist_result = None
        for o in mist_mix.outputs:
            if o.type == 'RGBA':
                mist_result = o
                break
        if mist_result is not None:
            pre_vig_output = mist_result
    else:
        print("[mood_valheim] Mist pass not available — skipping atmosphere tint (vignette/grade still applied)")

    vig_result = None
    for o in vig_mix.outputs:
        if o.type == 'RGBA':
            vig_result = o
            break
    if vig_a is not None and vig_b is not None and vig_result is not None:
        nt.links.new(pre_vig_output, vig_a)
        nt.links.new(maprange.outputs["Result"], vig_b)  # VALUE->RGBA auto-broadcasts to gray
        nt.links.new(vig_result, group_out.inputs["Image"])
    else:
        print("[mood_valheim] Mix node RGBA sockets not found — wiring straight to output (no vignette)")
        nt.links.new(pre_vig_output, group_out.inputs["Image"])


# ── Public API ───────────────────────────────────────────────────────────────

def apply_mood(scene, biome_style):
    """Apply the full mood/lookdev layer to `scene`, tuned by `biome_style`
    (the same STYLES[biome] dict shape village_gen.py already builds — only
    `sky`, `sun_color`, `sun_energy`, `sun_elev`, `fog` are read, all
    optionally). Call once, after all geometry/lights/world/camera exist,
    right before the first render. Safe to call more than once on the same
    scene (every step is idempotent by construction)."""
    rng = _seed(scene, biome_style)
    try:
        _tune_lights(scene, biome_style, rng)
    except Exception as e:
        print("[mood_valheim] light hierarchy step failed (%s)" % e)
    try:
        _boost_emissives(rng)
    except Exception as e:
        print("[mood_valheim] emissive-boost step failed (%s)" % e)
    try:
        _tighten_light_pools(rng)
    except Exception as e:
        print("[mood_valheim] light-pool tightening step failed (%s)" % e)
    try:
        _inject_albedo_variation(rng)
    except Exception as e:
        print("[mood_valheim] albedo-variation step failed (%s)" % e)
    try:
        _inject_bump(rng)
    except Exception as e:
        print("[mood_valheim] bump-injection step failed (%s)" % e)
    try:
        _add_atmosphere(scene, biome_style)
    except Exception as e:
        print("[mood_valheim] atmosphere step failed (%s)" % e)
    try:
        _setup_compositor(scene, biome_style)
    except Exception as e:
        print("[mood_valheim] compositor step failed (%s)" % e)
