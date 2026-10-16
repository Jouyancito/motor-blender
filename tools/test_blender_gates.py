"""test_blender_gates.py -- fixtures for the gates that need bpy.

    blender -b --factory-startup --python-exit-code 1 --python tools/test_blender_gates.py

tools/test_gates.py launches this itself (and FAILS if Blender is missing unless
MOTOR_TESTS_NO_BLENDER=1 says so explicitly). Prints `BLENDER_RESULT ok total`.
Every detector is shown a known-bad input AND a clean control.
"""
import math
import os
import sys
import tempfile

import bpy
import bmesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from recetas import mesh_quality as mq          # noqa: E402
from recetas import gltf_check                   # noqa: E402
from recetas import physics as ph                # noqa: E402
from recetas import router_knowledge as RK       # noqa: E402
from recetas.verdict import PASS, FAIL, NOT_APPLICABLE as NA   # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", name,
                          (" -- " + str(detail)) if detail and not cond else ""))


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def obj_from(bm, name="t"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    return ob


def cube(name="cube"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    return obj_from(bm, name)


def uv_cube(name="uvcube"):
    """primitive_cube_add ships a clean UV unwrap (bmesh create_cube does not)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.object
    ob.name = name
    return ob


def rows(rep):
    return {r["prop"].split(": ", 1)[-1]: r["state"] for r in rep.rows}


def judged(ob, limits=None):
    rep, m = mq.check_mesh([ob], limits or {}, verbose=False)
    return rows(rep), m[ob.name]


def box(name, size, center):
    """Axis-aligned box (sx, sy, sz) centred at `center`, verts in world space."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = v.co.x * size[0] + center[0]
        v.co.y = v.co.y * size[1] + center[1]
        v.co.z = v.co.z * size[2] + center[2]
    return obj_from(bm, name)


def cone_tip_down(name):
    """A cone balanced on its tip at z=0 (a stance with ONE contact point)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.0,
                          radius2=0.3, depth=0.6)
    for v in bm.verts:
        v.co.z += 0.3
    return obj_from(bm, name)


def cfg(**over):
    c = dict(RK.PHYSICS_DEFAULT)
    c.update(over)
    return c


def phys(objs, **over):
    rep, m = ph.check_physics(objs, cfg(**over), verbose=False)
    return {r["prop"]: r["state"] for r in rep.rows}, m


def main():
    print("\nmesh_quality.py (Blender)")
    fresh()
    st, m = judged(cube())
    check("control: un cubo limpio pasa nonmanifold/degenerate/winding/normales",
          st["nonmanifold_edges"] == PASS and st["degenerate_faces"] == PASS
          and st["inconsistent_winding_edges"] == PASS
          and st["normals_outward"] == PASS, st)
    check("control: el volumen del cubo es +1 m3 y esta cerrado",
          abs(m["signed_volume"] - 1.0) < 1e-6 and m["closed"], m["signed_volume"])

    fresh()
    bm = bmesh.new()
    v = [bm.verts.new(c) for c in ((0, 0, 0), (1, 0, 0), (0.5, 1, 0), (0.5, -1, 0),
                                   (0.5, 0, 1))]
    bm.faces.new((v[0], v[1], v[2]))
    bm.faces.new((v[0], v[1], v[3]))
    bm.faces.new((v[0], v[1], v[4]))   # three faces on edge v0-v1
    st, m = judged(obj_from(bm))
    check("non-manifold (3 caras en una arista) -> FAIL",
          st["nonmanifold_edges"] == FAIL and m["nonmanifold_edges"] == 1, st)

    fresh()
    bm = bmesh.new()
    a, b, c = (bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (2, 0, 0)))
    bm.faces.new((a, b, c))            # collinear -> zero area
    st, m = judged(obj_from(bm))
    check("cara degenerada (area 0) -> FAIL",
          st["degenerate_faces"] == FAIL and m["degenerate_faces"] == 1, st)

    fresh()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.faces.ensure_lookup_table()
    bmesh.ops.reverse_faces(bm, faces=[bm.faces[0]])
    st, m = judged(obj_from(bm))
    check("una cara invertida (winding inconsistente) -> FAIL",
          st["inconsistent_winding_edges"] == FAIL and m["inconsistent_edges"] == 4, m)

    fresh()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    st, m = judged(obj_from(bm))
    check("cubo entero con normales hacia adentro -> FAIL normals_outward",
          st["normals_outward"] == FAIL and m["inconsistent_edges"] == 0
          and m["inward_closed"], (st, m["signed_volume"]))

    fresh()
    ob = uv_cube()
    st, m = judged(ob, {"needs_uv": True})
    check("control: cubo con UV por defecto, sin solapamiento -> PASS",
          m["uv"]["has_uv"] and st["uv_present"] == PASS and st["uv_overlap"] == PASS,
          (st, m["uv"]))
    uv = ob.data.uv_layers.active.data
    for i, loop in enumerate(uv):        # overlap: map every face onto the same square
        loop.uv = ((0, 0), (1, 0), (1, 1), (0, 1))[i % 4]
    st, m = judged(ob, {"needs_uv": True})
    check("todas las caras sobre el mismo cuadrado UV -> uv_overlap FAIL",
          st["uv_overlap"] == FAIL and m["uv"]["overlap"] > 0.5, m["uv"])

    fresh()
    ob = uv_cube()
    ob.data.uv_layers.remove(ob.data.uv_layers.active)
    st, m = judged(ob, {"needs_uv": True})
    check("familia que exige texturas y malla SIN UV -> uv_present FAIL",
          st["uv_present"] == FAIL and not m["uv"]["has_uv"], st)
    st, _ = judged(ob, {"needs_uv": False})
    check("control: sin exigir texturas, la falta de UV no falla",
          "uv_present" in st and st["uv_present"] != FAIL, st)
    st, m = judged(cube("c2"), {"max_tris": 5})
    check("presupuesto de triangulos excedido (12 > 5) -> FAIL",
          st["tri_budget"] == FAIL, st)
    st, m = judged(cube("c3"), {"max_tris": 12})
    check("control: 12 tris con presupuesto 12 -> PASS", st["tri_budget"] == PASS, st)

    check("UV overlap puro: 2 triangulos identicos solapan al 50 %",
          abs(mq.uv_overlap_ratio([((0, 0), (1, 0), (0, 1))] * 2) - 0.5) < 0.02)
    check("UV overlap puro: 2 triangulos disjuntos -> 0",
          mq.uv_overlap_ratio([((0, 0), (0.4, 0), (0, 0.4)),
                               ((0.6, 0.6), (1, 0.6), (0.6, 1))]) < 0.01)

    print("\ngltf_check.py (Blender export + node validator)")
    fresh()
    cube("g")
    with tempfile.TemporaryDirectory() as tmp:
        good = os.path.join(tmp, "good.glb")
        bpy.ops.export_scene.gltf(filepath=good)
        res = gltf_check.validate(good)
        state, detail = gltf_check.judge(res)
        check("control: un GLB exportado por Blender valida con 0 errores",
              state == PASS and res.get("numErrors") == 0, (res, detail))
        bad = os.path.join(tmp, "bad.glb")
        with open(good, "rb") as fh, open(bad, "wb") as out:
            out.write(fh.read(200))
        res = gltf_check.validate(bad)
        state, _ = gltf_check.judge(res)
        check("un GLB truncado -> el validador lo rechaza (FAIL)",
              state == FAIL and res.get("numErrors", 0) >= 1, res)
        old = os.environ.get("MOTOR_GLTF_VALIDATOR_DIR")
        os.environ["MOTOR_GLTF_VALIDATOR_DIR"] = os.path.join(tmp, "nope")
        try:
            res = gltf_check.validate(good)
        finally:
            if old is None:
                del os.environ["MOTOR_GLTF_VALIDATOR_DIR"]
            else:
                os.environ["MOTOR_GLTF_VALIDATOR_DIR"] = old
        state, detail = gltf_check.judge(res)
        check("validador no instalado -> FAIL ruidoso, no pase silencioso",
              state == FAIL and "validator not installed" in detail, detail)

    print("\nphysics.py (Blender)")
    # 1. support polygon + ground contact
    fresh()
    st, m = phys([box("b", (1, 1, 1), (0, 0, 0.5))], drop_test=False)
    check("control: cubo apoyado en z=0 -> contacto y COM dentro del poligono",
          st["ground_contact"] == PASS and st["com_in_support"] == PASS
          and abs(m["support_margin_m"] - 0.5) < 1e-3, (st, m))
    check("control: el COM de un cubo 1x1x1 esta en su centro (volumen)",
          all(abs(a - b) < 1e-4 for a, b in zip(m["com"], (0, 0, 0.5)))
          and m["com_kind"] == "volume", m["com"])
    fresh()
    st, m = phys([box("b", (1, 1, 1), (0, 0, 0.8))], drop_test=False)
    check("cubo FLOTANDO 0.3 m sobre el suelo -> ground_contact FAIL",
          st["ground_contact"] == FAIL and abs(m["ground_gap_m"] - 0.3) < 1e-3, m)
    fresh()
    st, m = phys([box("b", (1, 1, 1), (0, 0, 0.2))], drop_test=False)
    check("cubo HUNDIDO 0.3 m bajo el suelo -> ground_contact FAIL",
          st["ground_contact"] == FAIL and m["ground_gap_m"] < -0.25, m)
    fresh()
    base = box("base", (0.2, 0.2, 0.2), (0, 0, 0.1))
    top = box("top", (2.0, 2.0, 1.0), (1.2, 0, 0.7))       # heavy, hangs off to +x
    top.data.update()
    st, m = phys([base, top], drop_test=False, islands="skip", interpenetration="skip")
    check("peso colgando fuera de la base -> COM fuera del poligono (FAIL)",
          st["com_in_support"] == FAIL and m["support_margin_m"] < 0, m)
    fresh()
    st, m = phys([box("a", (1, 1, 1), (0, 0, 0.5)), box("b", (0.2, 0.2, 0.2), (3, 0, 0.1))],
                 drop_test=False, islands="skip", interpenetration="skip")
    check("control: dos apoyos separados en el suelo -> el hull los abarca y el COM cae dentro",
          st["com_in_support"] == PASS and m["support_margin_m"] > 0
          and m["support_contacts"] == 8 and m["support_hull_area_m2"] > 2.0, m)
    fresh()
    cone = cone_tip_down("cone")
    st, m = phys([cone], drop_test=False)
    check("cono sobre su punta: un solo contacto -> COM fuera de un hull sin area (FAIL)",
          st["com_in_support"] == FAIL and m["support_hull_area_m2"] == 0.0
          and m["support_contacts"] >= 1, m)

    # 2. drop / settle
    fresh()
    st, m = phys([box("b", (1, 1, 1), (0, 0, 0.5))], drop_test=True,
                 islands="skip", interpenetration="skip")
    d = m["drop"]
    check("control: un cubo soltado 5 cm queda quieto (tilt<1 deg, drift<2 cm)",
          st["drop_settle"] == PASS and d["tilt_deg"] < 1.0 and d["drift_m"] < 0.02, d)
    check("control: el cubo asienta con su cara inferior en z~0",
          abs(d["rest_min_z"]) < 0.02, d)
    fresh()
    st, m = phys([cone_tip_down("cone")], drop_test=True, islands="skip",
                 interpenetration="skip", stands=False)
    d = m["drop"]
    check("cono sobre su punta: la simulacion lo VUELCA (tilt > 15 deg -> FAIL)",
          st["drop_settle"] == FAIL and d["tilt_deg"] > 15.0, d)
    fresh()
    keep = box("keep", (1, 1, 1), (0, 0, 0.5))
    bpy.context.scene.frame_current = 7
    ph.drop_measure([keep], 0.0, 0.05, 30)
    check("el drop test restaura la escena (sin objetos temporales, frame, rigidbody)",
          bpy.context.scene.frame_current == 7
          and not [o for o in bpy.data.objects if o.name.startswith("__phys")]
          and bpy.context.scene.rigidbody_world is None
          and abs(keep.location.z) < 1e-9)

    # 3. floating islands
    fresh()
    st, m = phys([box("body", (1, 1, 1), (0, 0, 0.5)),
                  box("float", (0.2, 0.2, 0.2), (2, 0, 1.5))],
                 drop_test=False, islands="fail", interpenetration="skip")
    check("una pieza SUELTA en el aire -> floating_islands FAIL",
          st["floating_islands"] == FAIL and m["islands"]["count"] == 1, m["islands"])
    fresh()
    st, m = phys([box("body", (1, 1, 1), (0, 0, 0.5)),
                  box("cap", (0.4, 0.4, 0.2), (0, 0, 1.1))],
                 drop_test=False, islands="fail", interpenetration="skip")
    check("control: una pieza apoyada encima del cuerpo NO es isla",
          st["floating_islands"] == PASS and m["islands"]["count"] == 0, m["islands"])
    fresh()
    st, m = phys([box("body", (1, 1, 1), (0, 0, 0.5)),
                  box("pebble", (0.2, 0.2, 0.2), (3, 0, 0.1))],
                 drop_test=False, islands="fail", interpenetration="skip")
    check("control: una pieza separada pero APOYADA en el suelo no esta flotando",
          st["floating_islands"] == PASS, m["islands"])
    fresh()
    st, m = phys([box("body", (1, 1, 1), (0, 0, 2.5)),
                  box("pebble", (0.2, 0.2, 0.2), (3, 0, 0.1))],
                 drop_test=False, islands="fail", interpenetration="skip", stands=False)
    check("stands=False: apoyarse en el suelo NO salva a una pieza suelta de un volador",
          st["floating_islands"] == FAIL and m["islands"]["count"] == 1
          and st["ground_contact"] == NA, (st, m["islands"]))
    fresh()
    st, m = phys([box("body", (1, 1, 1), (0, 0, 0.5)),
                  box("float", (0.2, 0.2, 0.2), (2, 0, 1.5))],
                 drop_test=False, islands="report", interpenetration="skip")
    check("islands='report': la isla se MIDE pero no falla",
          st["floating_islands"] == PASS and m["islands"]["count"] == 1, m["islands"])

    # 4. interpenetration
    fresh()
    st, m = phys([box("a", (1, 1, 1), (0, 0, 0.5)), box("b", (1, 1, 1), (0.5, 0, 0.5))],
                 drop_test=False, islands="skip", interpenetration="fail")
    check("dos cubos que se atraviesan -> interpenetration FAIL",
          st["interpenetration"] == FAIL and m["interpenetration"]["pairs"] == 1
          and m["interpenetration"]["triangle_pairs"] > 0, m["interpenetration"])
    fresh()
    st, m = phys([box("a", (1, 1, 1), (0, 0, 0.5)), box("b", (1, 1, 1), (3, 0, 0.5))],
                 drop_test=False, islands="skip", interpenetration="fail")
    check("control: cubos separados -> 0 pares",
          st["interpenetration"] == PASS and m["interpenetration"]["pairs"] == 0)
    fresh()
    st, m = phys([box("a", (1, 1, 1), (0, 0, 0.5)), box("b", (1, 1, 1), (0.5, 0, 0.5))],
                 drop_test=False, islands="skip", interpenetration="report")
    check("interpenetration='report': se mide, no falla",
          st["interpenetration"] == PASS and m["interpenetration"]["pairs"] == 1)
    fresh()
    st, m = phys([box("a", (1, 1, 1), (0, 0, 0.5))], drop_test=False, islands="skip",
                 interpenetration="fail")
    check("un solo objeto: nada que atravesar (NOT_APPLICABLE con razon)",
          st["interpenetration"] == NA)

    # ------------------------------------------------------------------ cosecha-1
    import numpy as np
    from recetas import bake_procedural as bp

    def noisy_sphere(segments=40, rings=24, flat=False):
        fresh()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings)
        ob = bpy.context.active_object
        mat = bpy.data.materials.new("m")
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        if flat:
            bsdf.inputs["Base Color"].default_value = (0.3, 0.5, 0.2, 1)
        else:
            tc, no = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexNoise")
            cr = nt.nodes.new("ShaderNodeValToRGB")
            cr.color_ramp.elements[0].color = (0.05, 0.2, 0.02, 1)
            cr.color_ramp.elements[1].color = (0.8, 0.7, 0.1, 1)
            nt.links.new(tc.outputs["Object"], no.inputs["Vector"])
            nt.links.new(no.outputs["Fac"], cr.inputs["Fac"])
            nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])
        ob.data.materials.append(mat)
        return ob, mat

    ob, mat = noisy_sphere()
    r = bp.bake_procedural_to_float_color(ob, part="body", samples=2)
    ca = ob.data.color_attributes["Col"]
    srcs = [l.from_node.bl_idname for l in mat.node_tree.links
            if l.to_node.bl_idname == "ShaderNodeBsdfPrincipled" and l.to_socket.name == "Base Color"]
    check("bake_procedural: textured sphere -> FLOAT_COLOR, luma spread > 0.02, Base Color reads the attribute",
          r is not None and (r[1] - r[0]) > 0.02 and ca.data_type == "FLOAT_COLOR"
          and srcs == ["ShaderNodeAttribute"], (r, ca.data_type, srcs))
    check("bake_procedural: object stamped with part + technique",
          ob.get("motor_part") == "body"
          and "bake_procedural_to_float_color" in ob.get("motor_technique", ""))
    ob, mat = noisy_sphere(flat=True)
    try:
        bp.bake_procedural_to_float_color(ob, part="body", samples=2)
        flat_raised = False
    except SystemExit as e:
        flat_raised = "FLAT" in str(e)
    check("bake_procedural control: a single-colour material (flat bake) raises instead of passing",
          flat_raised)
    ob, mat = noisy_sphere(flat=True)
    r = bp.bake_procedural_to_float_color(ob, part="body", samples=2, min_spread=None)
    check("bake_procedural: min_spread=None accepts a genuinely uniform material",
          r is not None and (r[1] - r[0]) <= 0.02)
    fresh()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cub = bpy.context.active_object
    cm = bpy.data.materials.new("c")
    cm.use_nodes = True
    cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)
    cub.data.materials.append(cm)
    r = bp.bake_procedural_to_float_color(cub, part="body", samples=2)
    after = tuple(cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)[:3]
    check("bake_procedural control: 8-vertex mesh is NOT baked (None) and its white material becomes a deliberate tone",
          r is None and "Col" not in cub.data.color_attributes and all(abs(c - 1.0) > 0.1 for c in after),
          (r, after))
    ob, mat = noisy_sphere()
    img = bpy.data.images.new("t", 4, 4)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    for l in list(bsdf.inputs["Base Color"].links):
        mat.node_tree.links.remove(l)
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    kept = bp._rewire_base_colour(ob, "Col")
    check("bake_procedural: an IMAGE texture feeding Base Color is left alone (survives glTF)",
          kept == [mat.name]
          and [l.from_node.bl_idname for l in bsdf.inputs["Base Color"].links] == ["ShaderNodeTexImage"])

    fresh()
    arr = np.random.RandomState(3).rand(8, 8, 4).astype(np.float32)
    arr[..., 3] = 1
    im = bp.image_to_blender_srgb_verified(arr, "t1")
    px = np.empty(len(im.pixels), np.float32)
    im.pixels.foreach_get(px)
    want = np.ascontiguousarray(np.concatenate(
        [bp.srgb_encode(arr[..., :3]), arr[..., 3:4]], axis=2)[::-1], dtype=np.float32).ravel()
    check("image_to_blender_srgb_verified: buffer reads back == encoded source, tagged sRGB, packed",
          im.colorspace_settings.name == "sRGB" and np.abs(px - want).max() < 1e-6 and im.packed_file is not None)
    arr2 = arr.copy()
    arr2[0, 0, :3] = 1.0 - arr2[0, 0, :3]
    px2 = np.empty(len(px), np.float32)
    bp.image_to_blender_srgb_verified(arr2, "t2").pixels.foreach_get(px2)
    check("image_to_blender_srgb_verified control: one perturbed texel IS visible in the read-back",
          np.abs(px - px2).max() > 0.05)
    check("srgb_encode: linear 0.214 -> ~0.5 (IEC 61966-2-1), 0 -> 0, 1 -> 1",
          abs(float(bp.srgb_encode(np.array(0.2140))) - 0.5) < 0.002
          and float(bp.srgb_encode(np.array(0.0))) == 0.0 and abs(float(bp.srgb_encode(np.array(1.0))) - 1.0) < 1e-6)

    from recetas import evaluated_mesh as em

    def shapekeyed(masked=False):
        fresh()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16)
        ob = bpy.context.active_object
        ob.location = (0.3, -0.2, 1.0)
        ob.shape_key_add(name="Basis")
        rs = np.random.RandomState(1)
        for k in range(3):
            sk = ob.shape_key_add(name="k%d" % k, from_mix=False)
            sk.value = 0.5
            for d in sk.data:
                d.co.x += 0.1 * rs.rand()
                d.co.z += 0.05 * rs.rand()
        if masked:
            vg = ob.vertex_groups.new(name="g")
            vg.add(list(range(0, 200)), 1.0, "REPLACE")
            ob.modifiers.new("mask", "MASK").vertex_group = "g"
        bpy.context.view_layer.update()
        return ob

    ob = shapekeyed(masked=True)
    W, N = em.morphed_coords(ob)
    base = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", base)
    Wb = base.reshape(-1, 3) + np.array(ob.matrix_world)[:3, 3]
    check("morphed_coords: 1:1 with base indices even with a MASK on (362 verts), modifier restored",
          len(W) == len(ob.data.vertices) and ob.modifiers["mask"].show_viewport)
    check("morphed_coords control: the base cage is >5 cm off the morphed mesh (the bug it prevents)",
          np.linalg.norm(Wb - W, axis=1).mean() > 0.05)
    check("shapekey_drift: morphed mesh drifts, a plain cube does not",
          em.shapekey_drift(ob) > 0.05 and (bpy.ops.mesh.primitive_cube_add() or True)
          and em.shapekey_drift(bpy.context.active_object) < 1e-9)
    ob = shapekeyed(masked=True)
    real = em.masks_muted

    class _noop:
        def __init__(self, *a):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    em.masks_muted = _noop
    try:
        em.morphed_coords(ob)
        refused = False
    except RuntimeError as e:
        refused = "mask not muted" in str(e)
    em.masks_muted = real
    check("morphed_coords control: with the mask NOT muted it REFUSES instead of returning shifted indices", refused)

    from recetas import surface_decal as sd

    def decal_target():
        fresh()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=40, radius=1.0)
        t = bpy.context.active_object
        bpy.ops.object.shade_smooth()
        m = bpy.data.materials.new("black")
        return t, m

    def vcoords(ob):
        a = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", a)
        return a.reshape(-1, 3)

    t, m = decal_target()
    hit, n = sd.surface_decal("d0", t, (0.1, -5, 0.2), (0, 1, 0), 0.2, 0.15, m, wobble=0.1, part="decals")
    d = bpy.data.objects["d0"]
    r = np.linalg.norm(vcoords(d), axis=1)
    cn = np.array([tuple(c.vector) for c in d.data.corner_normals])
    rad = vcoords(d)[[l.vertex_index for l in d.data.loops]]
    rad = rad / np.linalg.norm(rad, axis=1, keepdims=True)
    check("surface_decal: every decal vertex sits ON the sphere (|r-1| < 0.01), 1+14*48 verts",
          len(d.data.vertices) == 1 + 14 * 48 and np.abs(r - 1).max() < 0.01, (r.min(), r.max()))
    check("surface_decal: custom split normals follow the target's smooth normals (radial dot > 0.99)",
          float((cn * rad).sum(axis=1).min()) > 0.99)
    check("surface_decal: stamped with part + technique",
          d.get("motor_part") == "decals" and "surface_decal" in d.get("motor_technique", ""))
    sd.surface_decal("same", t, (0.1, -5, 0.2), (0, 1, 0), 0.2, 0.15, m, wobble=0.1)
    a = vcoords(bpy.data.objects["same"]).copy()
    bpy.data.objects.remove(bpy.data.objects["same"])
    sd.surface_decal("same", t, (0.1, -5, 0.2), (0, 1, 0), 0.2, 0.15, m, wobble=0.1)
    check("surface_decal: wobble seed is stable across calls (crc32, not hash(str))",
          np.abs(a - vcoords(bpy.data.objects["same"])).max() == 0.0)
    sd.surface_decal("d2", t, (0.1, -5, 0.2), (0, 1, 0), 0.2, 0.15, m, wobble=0.1, seed=7)
    check("surface_decal control: another seed changes the outline; a shifted origin moves the decal",
          np.abs(a - vcoords(bpy.data.objects["d2"])).max() > 1e-4
          and (sd.surface_decal("d3", t, (0.5, -5, 0.2), (0, 1, 0), 0.2, 0.15, m) or True)
          and np.abs(vcoords(bpy.data.objects["d3"]).mean(axis=0) - a.mean(axis=0)).max() > 0.1)
    try:
        sd.surface_decal("d4", t, (3.0, -5, 0.0), (0, 1, 0), 0.2, 0.15, m)
        missed = False
    except SystemExit as e:
        missed = "missed" in str(e)
    check("surface_decal control: a ray that misses the target RAISES instead of dropping the decal", missed)
    t.location = (0.5, 0, 0)
    t.rotation_euler = (0, 0, 0.5)
    bpy.context.view_layer.update()
    sd.surface_decal("d5", t, (0.5, -5, 0.0), (0, 1, 0), 0.1, 0.1, m)
    d5 = bpy.data.objects["d5"]
    wp = np.array([tuple(d5.matrix_world @ v.co) for v in d5.data.vertices]) - np.array([0.5, 0, 0])
    check("surface_decal: honours the target's matrix_world (decal rides a moved/rotated target)",
          abs(np.linalg.norm(wp, axis=1).mean() - 1.0) < 0.01)

    from recetas import bake_shading_check as bsc

    def pit_surface(paint):
        """40x40 grid with a Gaussian pit and raised rim (real occlusion variance). `paint`
        maps (x, y, z) -> luma, written to a FLOAT_COLOR corner layer."""
        fresh()
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=40, y_segments=40, size=1.0)
        for v in bm.verts:
            r2 = v.co.x ** 2 + v.co.y ** 2
            v.co.z = -0.35 * math.exp(-r2 / 0.08) + 0.12 * math.exp(-((math.sqrt(r2) - 0.45) / 0.1) ** 2)
        bm.normal_update()
        lay = bm.loops.layers.float_color.new("Col")
        for f in bm.faces:
            for l in f.loops:
                g = paint(*l.vert.co)
                l[lay] = (g, g, g, 1.0)
        ob = obj_from(bm, "pit")
        return ob

    rs2 = np.random.RandomState(4)
    stain = lambda x, y, z: 0.5 + 0.1 * math.sin(37.0 * x + 11.0 * y) * math.cos(23.0 * y - 5.0 * x)
    painted_shadow = lambda x, y, z: 0.55 + 1.2 * z        # dark in the pit, bright on the rim: baked AO
    rep = bsc.bake_shading_check(pit_surface(stain))
    check("bake_shading_check known-PASS fixture: position-noise stains on a pitted surface -> PASS",
          rep.verdict() == PASS, rep.rows)
    rep = bsc.bake_shading_check(pit_surface(painted_shadow))
    check("bake_shading_check known-FAIL fixture: luma painted by depth (baked shadow) -> FAIL",
          rep.verdict() == FAIL and "r(luma" in rep.rows[0]["detail"], rep.rows)
    rep = bsc.bake_shading_check(pit_surface(lambda x, y, z: 0.5))
    check("bake_shading_check control: a single flat colour is NOT_TESTED, never PASS",
          rep.verdict() == "NOT_TESTED", rep.rows)
    rep = bsc.bake_shading_check(pit_surface(painted_shadow), ray_len=1e-9)
    check("bake_shading_check control: rays that cannot hit anything (blind instrument) -> NOT_TESTED, not a clean PASS",
          rep.verdict() == "NOT_TESTED", rep.rows)
    rep = bsc.bake_shading_check(pit_surface(painted_shadow), attr_name="nope")
    check("bake_shading_check control: missing colour attribute -> NOT_TESTED", rep.verdict() == "NOT_TESTED")
    flat = pit_surface(stain)
    for v in flat.data.vertices:
        v.co.z = 0.0
    flat.data.update()
    rep = bsc.bake_shading_check(flat)
    check("bake_shading_check control: a flat plane has no occlusion to correlate with -> NOT_TESTED",
          rep.verdict() == "NOT_TESTED", rep.rows)

    # ------------------------------------------------------------- cosecha-1: human recipes
    from mathutils import Vector
    from recetas import mpfb_human as MH, reproportion_humanoid as RH, pose_solver as PS

    # factory objects: removed; anything else is left alone
    fresh()
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    bpy.context.active_object.name = "Cube"
    bpy.ops.mesh.primitive_cube_add(size=0.5)
    bpy.context.active_object.name = "keepme"
    gone = MH.clean_factory_scene()
    check("clean_factory_scene: removes the 2 m factory Cube and ONLY it",
          gone == ["Cube"] and "keepme" in bpy.data.objects and "Cube" not in bpy.data.objects, gone)
    fresh()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    bpy.context.active_object.name = "Cube"
    check("clean_factory_scene control: a user object that is merely NAMED Cube (1 m) is kept",
          MH.clean_factory_scene() == [] and "Cube" in bpy.data.objects)

    real_mod = MH.MPFB_MODULE
    MH.MPFB_MODULE = "bl_ext.user_default.no_such_addon"
    try:
        MH.ensure_mpfb()
        failed_loud = False
    except SystemExit as e:
        failed_loud = "install-file" in str(e)
    MH.MPFB_MODULE = real_mod
    check("ensure_mpfb control: a missing addon exits LOUDLY with the install-file command", failed_loud)

    fresh()
    body = MH.mpfb_human_base(dict(gender=0.0, age=0.33, muscle=0.15, weight=0.12, proportions=0.55,
                                   height=0.5, cupsize=0.38, firmness=0.5),
                              dict(asian=0.7, caucasian=0.3, african=0.0), name="hb", part="body")
    jg = [g.name for g in body.vertex_groups if g.name.startswith("joint-")]
    check("mpfb_human_base: 19158-vertex basemesh WITH the joint-* helper cubes (detailed_helpers on), no shape keys, stamped",
          len(body.data.vertices) == 19158 and len(jg) > 20 and not body.data.shape_keys
          and body.get("motor_part") == "body" and "mpfb_human_base" in body.get("motor_technique", ""),
          (len(body.data.vertices), len(jg)))
    J0 = RH.joint_centroids(body)
    rig = MH.add_human_rig(body, "hr", part="body")
    uh = np.array(rig.data.bones["upperleg01.L"].head_local)
    near, far = np.linalg.norm(uh - J0["joint-l-upper-leg"]), np.linalg.norm(uh - J0["joint-l-hand"])
    check("add_human_rig: the rig is FITTED to the joint cubes (upper leg within 3 cm of its cube; control: 25+ cm from the hand cube)",
          near < 0.03 and far > 0.25 and rig.get("motor_part") == "body", (near, far))
    check("region_ids: bone-prefix whitelist labels thighs and head (not 'skin' for everything)",
          set(np.unique(MH.region_ids(body))) >= {MH.REG["thigh"], MH.REG["head"], MH.REG["torso"]})

    # reproportion: neutral = identity; k_leg stretches the legs; bobblehead guard
    def zspan(b):
        a = np.empty(len(b.data.vertices) * 3)
        b.data.vertices.foreach_get("co", a)
        return a.reshape(-1, 3)[:, 2].max() - a.reshape(-1, 3)[:, 2].min(), a.copy()
    fresh()
    b1 = MH.mpfb_human_base(dict(gender=0.0), dict(asian=1.0), name="b1")
    h0, c0 = zspan(b1)
    Jb = RH.joint_centroids(b1)
    RH.reproportion_humanoid(b1)
    h1, c1 = zspan(b1)
    check("reproportion_humanoid control: all-neutral parameters leave the mesh unchanged (max dev < 1e-9)",
          np.abs(c0 - c1).max() < 1e-9, np.abs(c0 - c1).max())
    RH.reproportion_humanoid(b1, k_leg=1.26, ear_scale=0.6, ks_hand=0.85, ks_foot=0.9, part="body")
    J1 = RH.joint_centroids(b1)
    h2, c2 = zspan(b1)
    leg0 = Jb["joint-l-upper-leg"][2] - Jb["joint-l-ankle"][2]
    leg1 = J1["joint-l-upper-leg"][2] - J1["joint-l-ankle"][2]
    check("reproportion_humanoid: k_leg=1.26 stretches the hip-ankle span by ~26%% (ratio %.3f) and the figure grows" % (leg1 / leg0),
          1.15 < leg1 / leg0 < 1.35 and h2 > h1 + 0.1 and "reproportion_humanoid" in b1.get("motor_technique", ""),
          (leg1 / leg0, h1, h2))
    try:
        RH.reproportion_humanoid(MH.mpfb_human_base(dict(gender=0.0), dict(asian=1.0), name="b2"), k_head=1.4)
        refused = False
    except SystemExit as e:
        refused = "bobblehead" in str(e)
    check("reproportion_humanoid control: k_head=1.4 on the realistic head REFUSES (bobblehead) unless head_replaceable=True", refused)
    b3 = MH.mpfb_human_base(dict(gender=0.0), dict(asian=1.0), name="b3")
    RH.reproportion_humanoid(b3, k_head=1.4, head_replaceable=True)
    check("reproportion_humanoid: head_replaceable=True allows the dilation", True)

    # slim_limbs_radial
    fresh()
    sb = MH.mpfb_human_base(dict(gender=0.0), dict(asian=1.0), name="sb")
    srig = MH.add_human_rig(sb, "sr")
    _, s0 = zspan(sb)
    RH.slim_limbs_radial(sb, srig)           # all 1.0
    _, s1 = zspan(sb)
    check("slim_limbs_radial control: factors of 1.0 move nothing (max dev < 1e-6)", np.abs(s0 - s1).max() < 1e-6, np.abs(s0 - s1).max())
    moved = RH.slim_limbs_radial(sb, srig, leg_low=0.5)
    _, s2 = zspan(sb)
    d = np.abs(s2 - s1).reshape(-1, 3).max(axis=1)
    check("slim_limbs_radial: leg_low=0.5 moves shin vertices (>0.5 cm) and leaves the head alone",
          moved > 500 and d.max() > 0.005 and (d > 1e-9).mean() < 0.3, (moved, d.max(), (d > 1e-9).mean()))

    # pose solver
    fresh()
    pb_ = MH.mpfb_human_base(dict(gender=0.0), dict(asian=1.0), name="pb")
    prig = MH.add_human_rig(pb_, "pr")
    PS.reset_pose(prig)
    want = Vector((0.2, -0.5, -0.84)).normalized()
    pbn = prig.pose.bones
    d_before = (pbn["lowerleg01.L"].head - pbn["upperleg01.L"].head).normalized()
    PS.aim(prig, "upperleg01.L", ("head", "lowerleg01.L"), want, part="body")
    d_after = (pbn["lowerleg01.L"].head - pbn["upperleg01.L"].head).normalized()
    check("pose_solver.aim: the thigh now points along the requested direction (<0.5 deg); control: it did not before (>5 deg)",
          math.degrees(d_after.angle(want)) < 0.5 and math.degrees(d_before.angle(want)) > 5.0,
          (math.degrees(d_after.angle(want)), math.degrees(d_before.angle(want))))
    check("pose_solver.aim: stamps the rig with the technique", "pose_solver" in prig.get("motor_technique", "") and prig.get("motor_part") == "body")
    S_, W_ = Vector((0, 0, 0)), Vector((0.3, 0.1, -0.2))
    M_ = PS.two_bone_ik(S_, 0.3, 0.3, W_, Vector((0, -1, 0)))
    check("pose_solver.two_bone_ik: mid joint is exactly a from S and b from W; bends toward the pole",
          abs((M_ - S_).length - 0.3) < 1e-6 and abs((W_ - M_).length - 0.3) < 1e-6 and M_.y < 0, (M_,))
    far_ = PS.two_bone_ik(S_, 0.3, 0.3, Vector((5, 0, 0)), Vector((0, -1, 0)))
    check("pose_solver.two_bone_ik control: an unreachable target clamps (arm fully extended, no NaN)",
          abs((far_ - S_).length - 0.3) < 1e-3 and not any(math.isnan(c) for c in far_))
    u_, n_ = PS.palm_normal(prig, "L")
    tgt = Vector((0.0, 1.0, 0.15)).normalized()
    PS.orient_palm(prig, "L", 1.0, tgt)
    u2, n2 = PS.palm_normal(prig, "L")
    a_, b_ = n2 - u2 * n2.dot(u2), tgt - u2 * tgt.dot(u2)
    check("pose_solver.orient_palm: the palm normal ends up facing the target (in-plane angle < 1 deg)",
          math.degrees(a_.angle(b_)) < 1.0 and u2.length > 0.99, math.degrees(a_.angle(b_)))

    # ------------------------------------------------------------- cosecha-1: harvest in verify_asset
    import json
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import verify_asset as VA

    GEN_SRC = ("from recetas.bvh_glue import glue_to_surface\n"      # 1
               "def build(a, b):\n"                                 # 2
               "    n = glue_to_surface(a, b, part='body')\n"       # 3
               "    return n\n"                                     # 4
               "X = 1\n")                                           # 5

    def verified(harvest_section, outputs="blend", save=True):
        fresh()
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cube_ = bpy.context.active_object
        cube_["motor_part"] = "body"
        cube_["motor_technique"] = "bvh_glue"
        d_ = tempfile.mkdtemp()
        os.makedirs(os.path.join(d_, "_motor"))
        open(os.path.join(d_, "gen.py"), "w").write(GEN_SRC)
        blend_ = os.path.join(d_, "a.blend")
        if save:
            bpy.ops.wm.save_as_mainfile(filepath=blend_)
        doc_ = {"schema": 2, "subject": "gato", "created": "2026-01-01T00:00:00", "generators": ["gen.py"],
                "outputs": [blend_] if outputs == "blend" else outputs,
                "parts": {"body": {"technique": "bvh_glue"}}}
        if harvest_section is not None:
            doc_["harvest"] = harvest_section
        man_ = os.path.join(d_, "_motor", "manifest.json")
        json.dump(doc_, open(man_, "w"))
        rep_ = VA.check(blend_, man_)
        return rep_, {r["prop"]: r for r in rep_.rows}

    good_entry = {"source": "gen.py:2-4", "why": "glue strip keeps its proud offset", "status": "proposed"}
    rep, rows = verified({"entries": [good_entry]})
    check("verify_asset harvest: stamped asset + ONE entry -> overall PASS", rep.verdict() == PASS and rows["harvest"]["state"] == PASS, rep.rows)
    rep, rows = verified({"none": "reused_only:bvh_glue"})
    check("verify_asset harvest: stamped asset + reused_only evidenced by the generator -> overall PASS", rep.verdict() == PASS, rep.rows)
    rep, rows = verified(None)
    check("verify_asset harvest control: manifest with NO harvest section -> FAIL (everything else is clean)",
          rep.verdict() == FAIL and rows["harvest"]["state"] == FAIL and rows["part:body:exists"]["state"] == PASS, rep.rows)
    rep, rows = verified({"entries": [], "none": ""})
    check("verify_asset harvest control: EMPTY section -> FAIL", rep.verdict() == FAIL and rows["harvest"]["state"] == FAIL)
    rep, rows = verified({"none": "aaaaaaaaaaaaaaaa"})
    check("verify_asset harvest control: junk `none` -> FAIL", rows["harvest"]["state"] == FAIL)
    rep, rows = verified({"entries": [dict(good_entry, source="gen.py:99")]})
    check("verify_asset harvest control: an entry citing a line that does not exist -> FAIL", rows["harvest"]["state"] == FAIL)
    check("verify_asset harvest: the FAIL row tells you the command that fixes it", "harvest_asset.py" in rows["harvest"]["detail"])
    # precedence: a blend that could not be judged stays NOT_TESTED even with a bad harvest
    rep, rows = verified(None, outputs="blend", save=False)
    check("PRECEDENCE: unreadable blend + MISSING harvest -> overall NOT_TESTED (harvest does not turn it into FAIL)",
          rep.verdict() == "NOT_TESTED" and rows["harvest"]["state"] == "NOT_TESTED", rep.rows)
    rep, rows = verified(None, outputs=5)
    check("PRECEDENCE: crashed verifier + missing harvest -> overall NOT_TESTED",
          rep.verdict() == "NOT_TESTED" and rows["verifier_crashed"]["state"] == "NOT_TESTED", rep.rows)
    rep, rows = verified(None, outputs=["/nowhere/else.blend"])
    check("PRECEDENCE control: a REAL failure (undeclared blend) stays FAIL", rep.verdict() == FAIL)
    rep, rows = verified({"entries": [good_entry]}, outputs="blend", save=False)
    check("PRECEDENCE control: unreadable blend + VALID harvest -> NOT_TESTED, harvest row PASS",
          rep.verdict() == "NOT_TESTED" and rows["harvest"]["state"] == PASS)

    # ---- review round: shading world space, procedural fallback + engine restore, pose stamps, decal scale
    from recetas import bake_shading_check as bsc2
    base = pit_surface(stain)
    r_a = bsc2.bake_shading_check(pit_surface(painted_shadow)).rows[0]["detail"]
    moved = pit_surface(painted_shadow)
    moved.location = (3.0, -2.0, 1.0)
    moved.rotation_euler = (0.4, 0.2, 0.9)
    bpy.context.view_layer.update()
    r_b = bsc2.bake_shading_check(moved).rows[0]["detail"]
    check("bake_shading_check: world-space rays -- a moved+rotated asset reads the SAME r (%s vs %s)" % (r_a[:32], r_b[:32]),
          r_a[:34] == r_b[:34], (r_a, r_b))
    fresh()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cub2 = bpy.context.active_object
    bp.bake_procedural_to_float_color(cub2, part="body", samples=2)
    check("bake_procedural: a sparse mesh is NOT stamped with the recipe's technique (flat_fallback marker; verify's technique row would FAIL)",
          cub2.get("motor_technique") == "flat_fallback" and cub2.get("motor_part") == "body", dict(cub2.items()))
    ob, mat = noisy_sphere()
    scene_ = bpy.context.scene
    scene_.render.engine = "BLENDER_EEVEE"
    ob.hide_set(True)              # a hidden object cannot be baked: RuntimeError
    try:
        bp.bake_procedural_to_float_color(ob, part="body", samples=2, min_spread=None)
        raised_ = False
    except Exception:
        raised_ = True
    check("bake_procedural: engine restored after a FAILED bake (control: the bake really did fail)",
          raised_ and scene_.render.engine == "BLENDER_EEVEE", (raised_, scene_.render.engine))
    ob, mat = noisy_sphere()
    scene_ = bpy.context.scene
    scene_.render.engine = "BLENDER_EEVEE"
    bp.bake_procedural_to_float_color(ob, part="body", samples=2)
    check("bake_procedural: engine restored after a successful bake", scene_.render.engine == "BLENDER_EEVEE")
    fresh()
    pbody = MH.mpfb_human_base(dict(gender=0.0), dict(asian=1.0), name="pbody", part="body")
    prig2 = MH.add_human_rig(pbody, "prig2", part="body")
    for m_ in pbody.modifiers:
        pass
    PS.reset_pose(prig2)
    PS.aim(prig2, "upperleg01.L", ("head", "lowerleg01.L"), Vector((0.1, -0.2, -0.97)), part="body")
    check("pose_solver.aim: the mesh bound to the rig by an Armature modifier ends up stamped too (verify requires ALL objects of a part)",
          "pose_solver" in pbody.get("motor_technique", "") and "pose_solver" in prig2.get("motor_technique", "")
          and any(m_.type == "ARMATURE" for m_ in pbody.modifiers), (dict(pbody.items()), [m_.type for m_ in pbody.modifiers]))
    # decal probe distances scale with the target
    def decal_spread(scale):
        fresh()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=40, radius=scale)
        t_ = bpy.context.active_object
        bpy.ops.object.shade_smooth()
        m_ = bpy.data.materials.new("m")
        sd.surface_decal("d", t_, (0.1 * scale, -5 * scale, 0.2 * scale), (0, 1, 0), 0.2 * scale, 0.15 * scale, m_)
        d_ = bpy.data.objects["d"]
        r_ = np.linalg.norm(vcoords(d_), axis=1) / scale
        return float(np.abs(r_ - 1).max())
    check("surface_decal: a 50x larger target projects equally well (probe distances scale with the bbox diagonal)",
          decal_spread(1.0) < 0.01 and decal_spread(50.0) < 0.01, (decal_spread(1.0), decal_spread(50.0)))

    ok = sum(1 for _, c in results if c)
    print("\nBLENDER_RESULT %d %d" % (ok, len(results)))
    if ok != len(results):
        for n, c in results:
            if not c:
                print("  FALLO:", n)
        sys.exit(1)


main()
