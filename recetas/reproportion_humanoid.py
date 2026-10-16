# RECETA: reproportion_humanoid -- re-proportion an MPFB human by POSITION maps on ALL verts.
# QUE: reproportion_humanoid(body, ...) stretches the legs (integral of a band mask between
#      ankle and hip), dilates the head about a chin pivot, thickens the neck, shrinks the
#      ears and scales hands/feet -- on EVERY vertex, helper/joint cubes included, so the
#      rig fitted afterwards lands on the new proportions. slim_limbs_radial(body, rig, ...)
#      then slims arms/shins radially about each bone axis, ramped so joints stay put.
#      scale_data(body, rig, r) scales mesh + armature rest pose together.
# CUANDO: stylised humans (anime legs, big head, small hands). Adjacent to
#      engordar_anatomico (which adds soft tissue after this; run engordar BEFORE scaling
#      to figure size: its 2 cm radius floor assumes human scale, #2968).
# GOTCHAS: (1) the maps act on positions, not on a rigged pose: do them BEFORE
#      add_human_rig(). (2) K_HEAD > ~1.15 on a REALISTIC MPFB head = bobblehead on a
#      stock neck (rem v7/v8); the function refuses unless head_replaceable=True, i.e. you
#      WILL cut the head at mid-neck and swap an authored one (heuristic threshold; the
#      evidence is qualitative). Neck thickening (k_neck) only partly hides it.
#      (3) the pivot of the head dilation is the CHIN (found as the lowest front-centre
#      vertex after the leg stretch), not the head joint. (4) ear shrink uses the "ears"
#      vertex group at weight > 0.5. (5) slim_limbs needs the rig in REST pose.
#      (6) lengths are in the MPFB std units of the call (scale=0.1 basemesh ~1.6-1.8).
# FUENTE: rem/v8/rem_v8_body_gen.py:113-169 reproportion, :187-231 slim_limbs, :234-246
#      scale_data. Defaults here are NEUTRAL (1.0); rem v8 passed K_LEG=1.26, K_HEAD=1.0,
#      EAR_SCALE=0.60, KS_HAND=0.85, KS_FOOT=0.90, SLIM arms .86/.86 legs .92/.88.
# EXEMPLAR:
#   J = reproportion_humanoid(body, k_leg=1.26, ear_scale=0.60, ks_hand=0.85, ks_foot=0.90)
import numpy as np

import bpy
from mathutils import Matrix

try:
    from recetas.motor_stamp import stamp_object as _motor_stamp
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from motor_stamp import stamp_object as _motor_stamp

TECHNIQUE = "reproportion_humanoid"
BOBBLEHEAD_K = 1.15


def ss(x):
    """Smoothstep on [0, 1]."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def joint_centroids(ob):
    """name -> centroid of every `joint-*` vertex group (the cubes MPFB fits its rig to)."""
    from mathutils import Vector
    gi = {vg.index: vg.name for vg in ob.vertex_groups}
    acc, cnt = {}, {}
    for v in ob.data.vertices:
        for g in v.groups:
            n = gi[g.group]
            if n.startswith("joint-"):
                acc[n] = acc.get(n, Vector()) + v.co
                cnt[n] = cnt.get(n, 0) + 1
    return {n: np.array(acc[n] / cnt[n]) for n in acc}


def reproportion_humanoid(body, k_leg=1.0, k_head=1.0, k_neck=1.0, ear_scale=1.0, kw_head=1.0,
                          neck_lift=0.0, ks_hand=1.0, ks_foot=1.0, head_replaceable=False,
                          part=None):
    """Apply the maps to `body` in place. Returns the joint centroids as they were BEFORE
    the maps (call joint_centroids(body) again for the new positions)."""
    if k_head > BOBBLEHEAD_K and not head_replaceable:
        raise SystemExit(
            "reproportion_humanoid: k_head=%.2f on a realistic MPFB head gives a bobblehead "
            "(anime proportions need an authored head). Pass head_replaceable=True only if "
            "you will cut at mid-neck and swap the head." % k_head)
    me = body.data
    n = len(me.vertices)
    Pt = np.empty(n * 3)
    me.vertices.foreach_get("co", Pt)
    Pt = Pt.reshape(-1, 3)
    J = joint_centroids(body)
    for s in ("l", "r"):
        sgn = 1.0 if s == "l" else -1.0
        W, E = J["joint-%s-hand" % s], J["joint-%s-elbow" % s]
        u = (W - E) / np.linalg.norm(W - E)
        w = ss(((Pt - W) @ u) / 0.03) * (((Pt[:, 0] * sgn) > abs(W[0]) - 0.10) & (Pt[:, 2] < W[2] + 0.12))
        Pt += (ks_hand - 1.0) * w[:, None] * (Pt - W)
        A = J["joint-%s-ankle" % s]
        w = ss((A[2] + 0.02 - Pt[:, 2]) / 0.04) * (((Pt[:, 0] * sgn) > 0.02) & (Pt[:, 2] < A[2] + 0.04))
        Pt += (ks_foot - 1.0) * w[:, None] * (Pt - A)
    Az = 0.5 * (J["joint-l-ankle"][2] + J["joint-r-ankle"][2])
    Hz = 0.5 * (J["joint-l-upper-leg"][2] + J["joint-r-upper-leg"][2])
    zg = np.linspace(-0.3, 2.4, 5401)
    B = ss((zg - (Az - 0.02)) / 0.06) * (1.0 - ss((zg - (Hz - 0.02)) / 0.10))
    zmap = zg + (k_leg - 1.0) * np.concatenate([[0.0], np.cumsum(0.5 * (B[1:] + B[:-1]) * np.diff(zg))])
    zn0 = float(np.interp(J["joint-neck"][2], zg, zmap))
    zn1 = zn0 + 0.09
    z_in = np.interp(Pt[:, 2], zg, zmap)
    mx = np.where(z_in > zn1, 1.0, ss(1.0 - (np.abs(Pt[:, 0]) - 0.045) / 0.03))   # neck column only below the head
    Pt[:, 2] = z_in + neck_lift * ss((z_in - zn0) / (zn1 - zn0)) * mx
    Hd = J["joint-head"].copy()
    # chin = lowest front-centre vertex of the face (neck front sits further back in y), after stretch + lift
    face = (np.abs(Pt[:, 0]) < 0.02) & (Pt[:, 1] < Hd[1] - 0.06) & (Pt[:, 2] > zn0)
    chin0 = Pt[face, 2].min()
    # thicker neck: a dilated head on the stock MPFB neck reads as a lollipop
    wn = ss((Pt[:, 2] - zn0) / 0.03) * (1.0 - ss((Pt[:, 2] - (chin0 - 0.02)) / 0.04)) * (np.abs(Pt[:, 0]) < 0.08)
    ncy = J["joint-neck"][1]
    Pt[:, 0] *= 1.0 + (k_neck - 1.0) * wn
    Pt[:, 1] = ncy + (Pt[:, 1] - ncy) * (1.0 + (k_neck - 1.0) * wn)
    piv = np.array([0.0, Hd[1], chin0 - 0.030])
    w = ss((Pt[:, 2] - piv[2]) / 0.08)
    Pt += (k_head - 1.0) * w[:, None] * (Pt - piv)
    Pt[:, 0] *= 1.0 + (kw_head - 1.0) * w
    # ears stay small on an anime head: shrink them about their own centre after the dilation
    gi = {vg.index: vg.name for vg in body.vertex_groups}
    ear = np.array([v.index for v in me.vertices for g in v.groups if gi[g.group] == "ears" and g.weight > 0.5])
    for sg in (1.0, -1.0):
        e = ear[(Pt[ear, 0] * sg) > 0]
        c = Pt[e].mean(0)
        Pt[e] = c + (Pt[e] - c) * ear_scale
    me.vertices.foreach_set("co", Pt.ravel())
    me.update()
    body.location = (0, 0, 0)
    _motor_stamp(body, part, TECHNIQUE)
    return J


def slim_limbs_radial(body, rig, arm_up=1.0, arm_fore=1.0, leg_up=1.0, leg_low=1.0):
    """Radial slimming about each bone axis in REST pose: per vertex, dominant bone group
    -> its segment; the factor ramps in along the segment so joints stay put."""
    slim = {"arm_up": arm_up, "arm_fore": arm_fore, "leg_up": leg_up, "leg_low": leg_low}
    me = body.data
    n = len(me.vertices)
    Pt = np.empty(n * 3)
    me.vertices.foreach_get("co", Pt)
    Pt = Pt.reshape(-1, 3)
    gi = {vg.index: vg.name for vg in body.vertex_groups}
    segs = {}
    for sd in ("L", "R"):
        eb = rig.data.bones
        segs["upperarm01.%s" % sd] = (eb["upperarm01.%s" % sd].head_local, eb["lowerarm01.%s" % sd].head_local, "arm_up")
        segs["upperarm02.%s" % sd] = segs["upperarm01.%s" % sd]
        segs["lowerarm01.%s" % sd] = (eb["lowerarm01.%s" % sd].head_local, eb["wrist.%s" % sd].head_local, "arm_fore")
        segs["lowerarm02.%s" % sd] = segs["lowerarm01.%s" % sd]
        segs["lowerleg01.%s" % sd] = (eb["lowerleg01.%s" % sd].head_local, eb["foot.%s" % sd].head_local, "leg_low")
        segs["lowerleg02.%s" % sd] = segs["lowerleg01.%s" % sd]
        segs["upperleg01.%s" % sd] = (eb["upperleg01.%s" % sd].head_local, eb["lowerleg01.%s" % sd].head_local, "leg_up")
        segs["upperleg02.%s" % sd] = segs["upperleg01.%s" % sd]
    moved = 0
    new = Pt.copy()
    for v in me.vertices:
        best, wb = None, 0.35
        for g in v.groups:
            nm = gi.get(g.group)
            if nm in segs and g.weight > wb:
                best, wb = nm, g.weight
        if best is None:
            continue
        h, t_, kind = segs[best]
        h = np.array(h)
        ax = np.array(t_) - h
        L = np.linalg.norm(ax)
        axn = ax / L
        p = Pt[v.index]
        t = float(np.dot(p - h, axn) / L)
        ramp = float(ss((t - 0.05) / 0.25) * ss((1.02 - t) / 0.20))
        f = 1.0 + (slim[kind] - 1.0) * ramp * min(1.0, wb * 1.3)
        c = h + axn * np.dot(p - h, axn)
        new[v.index] = c + (p - c) * f
        moved += 1
    me.vertices.foreach_set("co", new.ravel())
    me.update()
    return moved


def scale_data(body, rig, r):
    """Scale mesh data and the armature REST pose together by `r` (object transforms stay 1)."""
    body.data.transform(Matrix.Scale(r, 4), shape_keys=True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    snap = [(eb, eb.head.copy() * r, eb.tail.copy() * r) for eb in rig.data.edit_bones]
    for eb, h, t in snap:
        eb.head, eb.tail = h, t
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
