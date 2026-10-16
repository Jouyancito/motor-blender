# RECETA: bake_procedural -- resolve a procedural shader graph into data glTF can carry.
# QUE: bake_procedural_to_float_color(obj, part=...) bakes the DIFFUSE colour of a
#      node-graph material (noise, voronoi, ramps...) into a FLOAT_COLOR corner attribute
#      and rewires Base Color to read it. image_to_blender_srgb_verified(arr) is the
#      sibling for detail finer than the mesh: a numpy array becomes a Blender image
#      that is encoded once, tagged sRGB and READ BACK before anyone trusts it.
# CUANDO: any asset whose look comes from shader nodes and ships as .glb. The exporter
#      drops node graphs silently and writes baseColorFactor 1,1,1 (5 mobs shipped
#      WHITE for a month, engram #2540; LECCIONES 9, 14).
# GOTCHAS: (1) FLOAT_COLOR, never BYTE_COLOR (sRGB decode on read ~12x darker);
#      (2) vertex colour resolves AT THE VERTEX: a pattern finer than the mesh cannot
#      survive, so below `need` vertices the recipe refuses to bake and flattens to a
#      deliberate tone instead of a muddy average (use the image path for those);
#      (3) a bake that writes one constant looks identical to the bug it fixes, so a
#      luma spread <= min_spread raises; (4) an IMAGE TEXTURE feeding Base Color is
#      left alone (it survives glTF; rewiring it throws real detail away);
#      (5) Image.foreach_set on a fresh image can write NOTHING and raise nothing ->
#      always read back; (6) a glTF baseColorTexture is sRGB BY SPEC: encode once and
#      tag sRGB, never hand over linear floats tagged Non-Color.
# FUENTE: Dungeon Party game/tools/blender/_bake_vcol.py:38-165 and
#      _carapace_texture.py:145-195 (hawk/_feather_texture.py:65 is a verbatim copy).
# EXEMPLAR:
#   from recetas.bake_procedural import bake_procedural_to_float_color
#   lo, hi, mean = bake_procedural_to_float_color(body, part="body", samples=8)
import numpy as np

try:
    import bpy
except ImportError:  # the pure helpers stay importable without Blender
    bpy = None
try:
    from recetas.motor_stamp import stamp_object as _motor_stamp
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from motor_stamp import stamp_object as _motor_stamp

TECHNIQUE = "bake_procedural_to_float_color"
FALLBACK_MARK = "flat_fallback"   # sparse mesh: flattened, NOT baked


def enough_vertices(obj, need=600):
    """(ok, n): is the mesh dense enough for per-vertex colour to carry its pattern?"""
    n = len(obj.data.vertices)
    return n >= need, n


def flatten_to_base_colour(obj, fallback=(0.55, 0.55, 0.58)):
    """Give a too-small mesh a flat NON-white baseColorFactor (a dropped node graph
    exports as 1,1,1 white; a deliberate flat tone is the honest floor)."""
    done = []
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None or not mat.use_nodes:
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        inp = bsdf.inputs["Base Color"]
        cur = tuple(inp.default_value)[:3]
        if all(abs(c - 1.0) < 0.02 for c in cur):
            cur = fallback
        for link in list(inp.links):
            mat.node_tree.links.remove(link)
        inp.default_value = (*cur, 1.0)
        done.append(mat.name)
    return done


def _bake_diffuse(obj, samples, name):
    scene = bpy.context.scene
    prev_engine, prev_samples, prev_device = scene.render.engine, None, None
    try:
        prev_samples = scene.cycles.samples
        prev_device = scene.cycles.device
    except AttributeError:   # cycles not registered yet
        pass
    try:
        _bake_diffuse_inner(obj, samples, name)
    finally:                 # a failed bake must not leave the scene on Cycles/CPU/low samples
        scene.render.engine = prev_engine
        if prev_samples is not None:
            scene.cycles.samples = prev_samples
            scene.cycles.device = prev_device


def _bake_diffuse_inner(obj, samples, name):
    me = obj.data
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    me.color_attributes.new(name=name, type="FLOAT_COLOR", domain="CORNER")
    me.color_attributes.active_color_index = me.color_attributes.find(name)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"          # deterministic; GPU bakes vary per driver
    bk = scene.render.bake
    bk.target = "VERTEX_COLORS"
    bk.use_pass_direct = False           # albedo only -- lighting is the engine's job
    bk.use_pass_indirect = False
    bk.use_pass_color = True
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="DIFFUSE")


def _rewire_base_colour(obj, name):
    kept = []
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None or not mat.use_nodes:
            continue
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        feeds = [l.from_node for l in bsdf.inputs["Base Color"].links]
        if any(nd.type == "TEX_IMAGE" for nd in feeds):
            kept.append(mat.name)        # an image survives glTF: leave it
            continue
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = name
        for link in list(bsdf.inputs["Base Color"].links):
            nt.links.remove(link)
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    return kept


def luma_stats(obj, name="Col"):
    """(min, max, mean) Rec.709 luma of the corner attribute `name`."""
    ca = obj.data.color_attributes[name]
    lum = [0.2126 * d.color[0] + 0.7152 * d.color[1] + 0.0722 * d.color[2] for d in ca.data]
    return min(lum), max(lum), sum(lum) / max(len(lum), 1)


def bake_procedural_to_float_color(obj, part=None, samples=8, name="Col",
                                   need=600, min_spread=0.02):
    """Bake DIFFUSE -> FLOAT_COLOR `name`, rewire Base Color, stamp `obj`.

    Returns (luma_min, luma_max, luma_mean), or None when the mesh has fewer than
    `need` vertices: then NO bake is done (it would be a muddy average), the
    material is flattened to a deliberate non-white tone, and the object is still
    stamped. Raises SystemExit when the bake came out flat (spread <= min_spread):
    a constant fill is indistinguishable from the white-mob bug. min_spread=None
    disables that check (for materials that really are one colour).

    DELIBERATE DIFFERENCE from the source (_bake_vcol.bake_and_report): the source only
    PRINTED "PLANO, el bake no capturo nada" and carried on; here a flat bake raises
    SystemExit, because a build that continues has shipped the white-mob bug with a warning
    nobody reads. Below `need` vertices the source also returned None after flattening;
    this recipe additionally refuses to stamp TECHNIQUE for it (it stamps flat_fallback)."""
    ok, n = enough_vertices(obj, need)
    if not ok:
        flatten_to_base_colour(obj)
        # NOT stamped with TECHNIQUE: nothing was baked, so the object must not claim it.
        # The distinct marker keeps it a stamped part (not "unstamped geometry") while
        # verify_asset's part:<p>:technique row FAILS for a part that declared this recipe.
        _motor_stamp(obj, part, FALLBACK_MARK)
        return None
    _bake_diffuse(obj, samples, name)
    _rewire_base_colour(obj, name)
    lo, hi, mean = luma_stats(obj, name)
    _motor_stamp(obj, part, TECHNIQUE)
    if min_spread is not None and (hi - lo) <= min_spread:
        raise SystemExit(
            "bake_procedural_to_float_color: %s baked FLAT (luma %.3f..%.3f, spread %.4f <= %.3f): "
            "the bake captured nothing -- check that the shader graph reaches Base Color"
            % (obj.name, lo, hi, hi - lo, min_spread))
    return lo, hi, mean


def srgb_encode(lin):
    """Linear [0,1] -> sRGB-encoded (IEC 61966-2-1). numpy in, numpy out."""
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92,
                    1.055 * np.power(np.maximum(lin, 1e-8), 1 / 2.4) - 0.055)


def image_to_blender_srgb_verified(arr, name="baked_image"):
    """Wrap a float (H, W, 4) LINEAR array (top-down) as a packed Blender image.

    Encodes to sRGB once, tags the image sRGB, writes bottom-up, then READS THE
    BUFFER BACK; falls back to the slow path; raises SystemExit if the buffer
    still refuses (never ships a black texture)."""
    h, w, _ = arr.shape
    im = bpy.data.images.get(name)
    if im is not None:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, width=w, height=h, alpha=True, float_buffer=True)
    lin = np.clip(arr, 0.0, 1.0)
    out = np.concatenate([srgb_encode(lin[..., :3]), lin[..., 3:4]], axis=2)
    im.colorspace_settings.name = "sRGB"
    src = np.ascontiguousarray(out[::-1], dtype=np.float32).ravel()
    im.pixels.foreach_set(src)
    im.update()
    back = np.empty(len(im.pixels), dtype=np.float32)
    im.pixels.foreach_get(back)
    if abs(float(back.mean()) - float(src.mean())) > 1e-4:
        im.pixels[:] = src.tolist()
        im.update()
        im.pixels.foreach_get(back)
        if abs(float(back.mean()) - float(src.mean())) > 1e-4:
            raise SystemExit(
                "image_to_blender_srgb_verified: the image buffer will not take the bake "
                "(wrote %.4f, read %.4f)" % (src.mean(), back.mean()))
    im.pack()
    return im
