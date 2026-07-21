# RECETA — engordar_anatomico (spec: engordar_anatomico_SPEC.md, status DISENO->prueba 2026-07-16)
# Fat = soft tissue over an unchanged scaffold: radial-to-bone displacement, proportional to
# local thickness, masked by the rig's own skinning weights, joints taper to zero, Laplacian-
# smoothed field, delivered as a SHAPE KEY (reversible, composable). Never axis scaling.
import bpy
import bmesh
from mathutils import Vector

# gains: anatomical mass map (SPEC section 1) keyed by the REAL Filomeno_rig bones
GAINS_GORDO = {
    "root": 0.85,        # pelvis / ancas
    "spine": 1.00,       # belly — absolute max
    "chest": 0.60,
    "neck": 0.70,        # papada
    "clavicle_L": 0.50, "clavicle_R": 0.50,
    "upperarm_L": 0.50, "upperarm_R": 0.50,
    "forearm_L": 0.25, "forearm_R": 0.25,
    "thigh_L": 0.70, "thigh_R": 0.70,
    "shin_L": 0.30, "shin_R": 0.30,
}
PROTECT = ("head", "jaw", "ear_L", "ear_R", "eye_L", "eye_R", "hand_L", "hand_R", "foot_L", "foot_R")
SAG = {"spine": 1.0, "root": 0.5, "neck": 0.8, "chest": 0.5}  # gravity share per bone


def engordar(obj_name="base_v2", arm_name="Filomeno_rig", gains=None, amount=0.12,
             gravity=0.35, normal_blend=0.25, smooth_iters=3, key_name="fat_gordo"):
    gains = gains or GAINS_GORDO
    o = bpy.data.objects[obj_name]
    arm = bpy.data.objects[arm_name]
    me = o.data
    n = len(me.vertices)

    # bones in the MESH's local space (rest pose = shape-key space)
    to_local = o.matrix_world.inverted() @ arm.matrix_world
    bones = {}
    for bn, g in gains.items():
        b = arm.data.bones.get(bn)
        if b is None:
            continue
        h = to_local @ b.head_local
        t = to_local @ b.tail_local
        ax = (t - h)
        L = ax.length
        bones[bn] = (h, ax.normalized() if L > 1e-6 else Vector((0, 0, 1)), L, g)

    gidx = {vg.index: vg.name for vg in o.vertex_groups}
    down = Vector((0, 0, -1))

    # smoothed normals (2 iters of 1-ring averaging)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    nbrs = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
    normals = [v.normal.copy() for v in bm.verts]
    for _ in range(2):
        normals = [(normals[i] + sum((normals[j] for j in nbrs[i]), Vector())).normalized()
                   if nbrs[i] else normals[i] for i in range(n)]
    bm.free()

    disp = [Vector((0, 0, 0))] * n
    for v in me.vertices:
        w_gain, w_prot, dom, wdom = 0.0, 0.0, None, 0.0
        for g in v.groups:
            name = gidx.get(g.group)
            if name in gains and name in bones:
                w_gain += g.weight
                if g.weight > wdom:
                    dom, wdom = name, g.weight
            elif name in PROTECT:
                w_prot += g.weight
        mask = min(w_gain, 1.0) * max(0.0, 1.0 - w_prot)
        if mask < 1e-4 or dom is None:
            continue
        h, ax, L, g = bones[dom]
        p = v.co
        t = max(0.0, min(1.0, (p - h).dot(ax) / max(L, 1e-6)))
        radial = p - (h + ax * (t * L))
        r_local = radial.length
        if r_local < 1e-5:
            rdir = normals[v.index]
        else:
            rdir = radial / r_local
        taper = 4.0 * t * (1.0 - t)
        d = (rdir * (1.0 - normal_blend) + normals[v.index] * normal_blend).normalized()
        d = d - d.project(ax)  # axial lock: never lengthen the bone
        if d.length < 1e-5:
            continue
        d.normalize()
        mag = amount * g * mask * taper * max(r_local, 0.02)
        vec = d * mag + down * (mag * gravity * SAG.get(dom, 0.0))
        disp[v.index] = vec

    # Laplacian smoothing of the displacement FIELD (anti-step between regions)
    for _ in range(smooth_iters):
        disp = [disp[i] * 0.5 + (sum((disp[j] for j in nbrs[i]), Vector()) / len(nbrs[i])) * 0.5
                if nbrs[i] else disp[i] for i in range(n)]

    # deliver as shape key
    if me.shape_keys is None:
        o.shape_key_add(name="Basis", from_mix=False)
    kb = me.shape_keys.key_blocks.get(key_name) or o.shape_key_add(name=key_name, from_mix=False)
    basis = me.shape_keys.key_blocks["Basis"]
    for i in range(n):
        kb.data[i].co = basis.data[i].co + disp[i]
    kb.value = 1.0
    moved = sum(1 for d in disp if d.length > 1e-5)
    dmax = max((d.length for d in disp), default=0)
    print(f"[engordar] key '{key_name}' -> {moved}/{n} verts moved, max disp {dmax*100:.1f}cm, amount={amount}")
    return kb


# --- vectorized variant for heavy meshes (110k+ verts; the Python-loop version freezes MCP) ---
GAINS_MACIZO = {
    "chest": 0.90,
    "clavicle_L": 0.80, "clavicle_R": 0.80,
    "upperarm_L": 0.70, "upperarm_R": 0.70,
    "forearm_L": 0.35, "forearm_R": 0.35,
    "spine": 0.45, "root": 0.45,
    "neck": 0.40,
    "thigh_L": 0.60, "thigh_R": 0.60,
    "shin_L": 0.35, "shin_R": 0.35,
}


def engordar_np(obj_name=None, arm_name="Filomeno_rig", gains=None, amount=0.15,
                gravity=0.0, normal_blend=0.25, smooth_iters=3, key_name="fat_macizo"):
    import numpy as np
    if obj_name is None:
        import json as _j, os as _o
        cfg = _o.path.join(_o.path.dirname(bpy.data.filepath), "..", "motor.config.json")
        obj_name = _j.load(open(cfg)).get("main_object", "body_united")
    gains = gains or GAINS_MACIZO
    o = bpy.data.objects[obj_name]
    arm = bpy.data.objects[arm_name]
    me = o.data
    n = len(me.vertices)

    P = np.empty(n * 3); me.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
    N = np.empty(n * 3); me.vertices.foreach_get("normal", N); N = N.reshape(-1, 3)

    # weight arrays per gain bone + protection (single light Python pass)
    gidx = {vg.index: vg.name for vg in o.vertex_groups}
    W = {bn: np.zeros(n) for bn in gains}
    prot = np.zeros(n)
    for v in me.vertices:
        for g in v.groups:
            nm = gidx.get(g.group)
            if nm in W:
                W[nm][v.index] = g.weight
            elif nm in PROTECT:
                prot[v.index] += g.weight
    fade = np.clip(1.0 - prot, 0.0, 1.0)

    to_local = np.array(o.matrix_world.inverted() @ arm.matrix_world)
    disp = np.zeros((n, 3))
    for bn, g in gains.items():
        b = arm.data.bones.get(bn)
        w = W[bn] * fade
        idx = np.where(w > 1e-4)[0]
        if b is None or len(idx) == 0:
            continue
        h = (to_local @ np.append(np.array(b.head_local), 1.0))[:3]
        t_ = (to_local @ np.append(np.array(b.tail_local), 1.0))[:3]
        ax = t_ - h; L = np.linalg.norm(ax)
        if L < 1e-6:
            continue
        ax /= L
        rel = P[idx] - h
        t = np.clip(rel @ ax / L, 0.0, 1.0)
        radial = rel - np.outer(t * L, ax)
        r = np.linalg.norm(radial, axis=1)
        rdir = np.where(r[:, None] > 1e-5, radial / np.maximum(r[:, None], 1e-9), N[idx])
        d = rdir * (1.0 - normal_blend) + N[idx] * normal_blend
        d -= np.outer(d @ ax, ax)                      # axial lock
        dl = np.linalg.norm(d, axis=1)
        ok = dl > 1e-5
        d[ok] /= dl[ok, None]
        taper = 4.0 * t * (1.0 - t)
        mag = amount * g * w[idx] * taper * np.maximum(r, 0.02)
        vec = d * mag[:, None]
        vec[:, 2] -= mag * gravity * SAG.get(bn, 0.0)
        vec[~ok] = 0.0
        disp[idx] += vec

    # Laplacian smoothing via edge adjacency (vectorized with np.add.at)
    ne = len(me.edges)
    E = np.empty(ne * 2, dtype=np.int64); me.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
    deg = np.zeros(n); np.add.at(deg, E[:, 0], 1); np.add.at(deg, E[:, 1], 1)
    deg = np.maximum(deg, 1)[:, None]
    for _ in range(smooth_iters):
        acc = np.zeros((n, 3))
        np.add.at(acc, E[:, 0], disp[E[:, 1]])
        np.add.at(acc, E[:, 1], disp[E[:, 0]])
        disp = disp * 0.5 + (acc / deg) * 0.5

    if me.shape_keys is None:
        o.shape_key_add(name="Basis", from_mix=False)
    kb = me.shape_keys.key_blocks.get(key_name) or o.shape_key_add(name=key_name, from_mix=False)
    basis = np.empty(n * 3); me.shape_keys.key_blocks["Basis"].data.foreach_get("co", basis)
    kb.data.foreach_set("co", (basis.reshape(-1, 3) + disp).ravel())
    kb.value = 1.0
    me.update()
    moved = int((np.linalg.norm(disp, axis=1) > 1e-5).sum())
    print(f"[engordar_np] key '{key_name}' -> {moved}/{n} verts, max {np.linalg.norm(disp,axis=1).max()*100:.1f}cm")
    return kb
