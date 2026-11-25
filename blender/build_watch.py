"""Builds the Meridian Calibre 01 watch, renders Cycles reference stills and
exports a GLB for the web.

    Blender -b --factory-startup -P blender/build_watch.py -- [--render] [--samples N]

Units match the web scene (case radius 1.24, about 38.5mm across). The dial
faces +Z and 12 o'clock is +Y. The GLB is exported without the Y-up
conversion, so these coordinates reach Three.js unchanged.

Every node the site animates is an empty named part_* (slides in the exploded
view) or spin_* (rotates: hands, gears, balance, rotor). Materials are named
by role so the site can swap in its own tuned versions.
"""

import math
import os
import sys
from math import cos, sin, pi, tau, radians

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_DIR = os.path.join(ROOT, 'public', 'models')
TEX_DIR = os.path.join(ROOT, 'blender', 'out', 'textures')  # full-res sources; web copies are JPEGs
RENDER_DIR = os.path.join(ROOT, 'blender', 'renders')
RENDER = '--render' in ARGS
SAMPLES = int(ARGS[ARGS.index('--samples') + 1]) if '--samples' in ARGS else 128
for d in (MODEL_DIR, TEX_DIR, RENDER_DIR):
    os.makedirs(d, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
WATCH = bpy.data.collections.new('watch')
STUDIO = bpy.data.collections.new('studio')
scene.collection.children.link(WATCH)
scene.collection.children.link(STUDIO)


# ---------------------------------------------------------------- helpers

def srgb(hex_):
    """Hex sRGB -> linear RGB, which is what Principled BSDF expects."""
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.1
    e.location = loc
    e.parent = parent
    WATCH.objects.link(e)
    return e


def mesh_object(name, me, material, parent=None, sharp=35, collection=WATCH):
    if material is not None:
        for m in material if isinstance(material, (list, tuple)) else [material]:
            me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    if sharp is not None:
        me.set_sharp_from_angle(angle=radians(sharp))
    ob = bpy.data.objects.new(name, me)
    ob.parent = parent
    collection.objects.link(ob)
    return ob


def bm_to_mesh(name, bm):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def pydata_mesh(name, verts, faces):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass  # duplicate face from a collapsed tip
    return bm_to_mesh(name, bm)


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = ob.name
    bpy.data.meshes.remove(old)


def bevel(ob, width, segments=3, angle=30, material=-1, harden=True):
    m = ob.modifiers.new('bevel', 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = radians(angle)
    m.harden_normals = harden
    m.miter_outer = 'MITER_ARC'
    m.material = material
    apply_modifiers(ob)
    return ob


def planar_uv(ob, scale=0.5, offset=0.5):
    """UV = world XY mapped to 0..1 over the case diameter, so textures line up across parts."""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    mw = ob.matrix_world if ob.parent is None else ob.parent.matrix_world @ ob.matrix_basis
    for loop in me.loops:
        co = mw @ me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x * scale + offset, co.y * scale + offset)


def fillet(points, closed=True, steps=6):
    """Round the corners of a 2D polyline. points: (x, y) or (x, y, radius)."""
    points = [p if len(p) == 3 else (*p, 0.0) for p in points]
    out = []
    n = len(points)
    for i, (x, y, r) in enumerate(points):
        if r <= 0 or (not closed and i in (0, n - 1)):
            out.append((x, y))
            continue
        P = Vector((x, y))
        A = Vector(points[i - 1][:2])
        B = Vector(points[(i + 1) % n][:2])
        u = (A - P).normalized()
        v = (B - P).normalized()
        ang = u.angle(v)
        if ang < 1e-4 or abs(ang - pi) < 1e-4:
            out.append((x, y))
            continue
        d = min(r / math.tan(ang / 2), (A - P).length * 0.49, (B - P).length * 0.49)
        rr = d * math.tan(ang / 2)
        T1, T2 = P + u * d, P + v * d
        C = P + (u + v).normalized() * (rr / math.sin(ang / 2))
        a1 = math.atan2((T1 - C).y, (T1 - C).x)
        a2 = math.atan2((T2 - C).y, (T2 - C).x)
        delta = (a2 - a1 + pi) % tau - pi
        for k in range(steps + 1):
            a = a1 + delta * k / steps
            out.append((C.x + rr * cos(a), C.y + rr * sin(a)))
    return out


def lathe(name, profile, segments=192, closed=True, deform=None):
    """Revolve an (r, z) profile around Z. deform(r, z, angle) -> (r, z) for flutes and knurling."""
    bm = bmesh.new()
    rings = []
    for i in range(segments):
        a = tau * i / segments
        ring = []
        for r, z in profile:
            rr, zz = deform(r, z, a) if deform else (r, z)
            ring.append(bm.verts.new((rr * cos(a), rr * sin(a), zz)))
        rings.append(ring)
    n = len(profile)
    for i in range(segments):
        A, B = rings[i], rings[(i + 1) % segments]
        for j in range(n if closed else n - 1):
            k = (j + 1) % n
            quad = [A[j], B[j], B[k], A[k]]
            if len({v.co.to_tuple(7) for v in quad}) >= 3:
                bm.faces.new(quad)
    return bm_to_mesh(name, bm)


def curve_mesh(name, loops, depth, bevel_depth=0.0, bevel_res=2):
    """Extrude closed 2D loops (inner loops become holes) into a solid with rounded edges.
    The result spans z = 0..depth."""
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = max(depth / 2 - bevel_depth, 0.0)
    cu.bevel_depth = bevel_depth
    cu.bevel_resolution = bevel_res
    cu.offset = -bevel_depth if bevel_depth else 0.0
    for loop in loops:
        sp = cu.splines.new('POLY')
        sp.points.add(len(loop) - 1)
        for p, (x, y) in zip(sp.points, loop):
            p.co = (x, y, 0, 1)
        sp.use_cyclic_u = True
    tmp = bpy.data.objects.new(name + '_tmp', cu)
    scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.transform(Matrix.Translation((0, 0, depth / 2)))
    return me


def tube_mesh(name, points, radius, res=6):
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = res // 2
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1)
    tmp = bpy.data.objects.new(name + '_tmp', cu)
    scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    return me


def merge_copies(name, me, matrices):
    """One mesh holding transformed copies of `me` (screws, indices, jewels)."""
    bm = bmesh.new()
    for M in matrices:
        tmp = me.copy()
        tmp.transform(M)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    return out


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * cos(a0 + (a1 - a0) * i / n), cy + r * sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def circle(cx, cy, r, n=64):
    return arc(cx, cy, r, 0, tau, n)[:-1]


def capsule(p0, p1, w, n=24):
    (x0, y0), (x1, y1) = p0, p1
    phi = math.atan2(y1 - y0, x1 - x0)
    return arc(x1, y1, w / 2, phi - pi / 2, phi + pi / 2, n) + arc(x0, y0, w / 2, phi + pi / 2, phi + 3 * pi / 2, n)


def box(x0, x1, y0, y1, z0, z1):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


def rounded_rect(cx, cz, w, h, r, seg=5):
    """Rounded rectangle cross-section in the XZ plane (constant vertex count, for lofting)."""
    r = max(1e-4, min(r, w / 2 - 1e-4, h / 2 - 1e-4))
    pts = []
    for ox, oz, a0 in ((cx + w / 2 - r, cz + h / 2 - r, 0), (cx - w / 2 + r, cz + h / 2 - r, pi / 2),
                       (cx - w / 2 + r, cz - h / 2 + r, pi), (cx + w / 2 - r, cz - h / 2 + r, 3 * pi / 2)):
        for i in range(seg + 1):
            a = a0 + (pi / 2) * i / seg
            pts.append((ox + r * cos(a), oz + r * sin(a)))
    return pts


def loft(name, sections):
    """Skin XZ cross-sections placed along Y. sections: [(y, [(x, z), ...]), ...]"""
    n = len(sections[0][1])
    verts = [(x, y, z) for y, ring in sections for x, z in ring]
    faces = []
    for k in range(len(sections) - 1):
        a, b = k * n, (k + 1) * n
        faces += [(a + i, a + (i + 1) % n, b + (i + 1) % n, b + i) for i in range(n)]
    last = (len(sections) - 1) * n
    faces += [tuple(range(n))[::-1], tuple(range(last, last + n))]
    return pydata_mesh(name, verts, faces)


def catmull_rom(points, steps=80):
    P = [Vector(points[0])] + [Vector(p) for p in points] + [Vector(points[-1])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1:i + 3]
        for k in range(steps):
            t = k / steps
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2].copy())
    return out


# ---------------------------------------------------------------- textures

def save_png(name, rgb):
    path = os.path.join(TEX_DIR, name + '.png')
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    rgba = np.concatenate([rgb, np.ones((h, w, 1))], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    return img


def height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def grid(size):
    v, u = np.mgrid[0:size, 0:size].astype(np.float64)
    return (u + 0.5) / size * 2 - 1, (v + 0.5) / size * 2 - 1  # world x, y over the case


def cotes_de_geneve(size=2048, width=0.11, angle=radians(35)):
    """Parallel bands with a rounded cross-section and fine curved graining, like Côtes de Genève."""
    x, y = grid(size)
    s = x * cos(angle) + y * sin(angle)
    t = -x * sin(angle) + y * cos(angle)
    f = np.mod(s / width, 1.0)
    lobe = 1 - (2 * f - 1) ** 2
    grain = np.sin((t * 2.2 + (f - 0.5) ** 2 * 3.0) * 520) * 0.035
    return height_to_normal(lobe * 0.5 + grain, strength=size * 0.0016)


def perlage(size=2048, spacing=0.075):
    """Overlapping circular graining spots on a staggered grid."""
    x, y = grid(size)
    row_h = spacing * 0.866
    rc = spacing * 0.72
    best_order = np.full(x.shape, -1e9)
    best_d = np.zeros_like(x)
    r0 = np.floor(y / row_h)
    for dr in (-1, 0, 1, 2):
        row = r0 + dr
        shift = np.where(np.mod(row, 2) == 0, 0.0, spacing / 2)
        c0 = np.floor((x - shift) / spacing)
        for dc in (-1, 0, 1, 2):
            col = c0 + dc
            cx = col * spacing + shift
            cy = row * row_h
            d = np.hypot(x - cx, y - cy)
            order = row * 10000 + col
            take = (d < rc) & (order > best_order)
            best_order = np.where(take, order, best_order)
            best_d = np.where(take, d, best_d)
    r = best_d / rc
    h = 0.35 * r ** 2 + 0.05 * np.sin(r * tau * 9)
    return height_to_normal(h, strength=size * 0.0012)


print('Generating finishing textures...')
COTES = save_png('cotes', cotes_de_geneve())
PERLAGE = save_png('perlage', perlage())


# ---------------------------------------------------------------- materials

def material(name, color, metallic=1.0, rough=0.2, normal_img=None, tangent=None, **inputs):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = rough
    for k, v in inputs.items():
        bsdf.inputs[k.replace('_', ' ')].default_value = v
    if normal_img:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = normal_img
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = 0.6
        nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if tangent:
        tg = nt.nodes.new('ShaderNodeTangent')
        tg.direction_type = tangent
        if tangent == 'RADIAL':
            tg.axis = 'Z'
        nt.links.new(tg.outputs['Tangent'], bsdf.inputs['Tangent'])
    return m


GOLD = srgb('#f7d293')
M = {
    'case': material('case', GOLD, rough=0.12),
    'brushed': material('bracelet_brushed', GOLD, rough=0.3, tangent='UV_MAP', Anisotropic=0.75),
    'polished': material('bracelet_polished', GOLD, rough=0.1),
    'hand': material('hand', srgb('#ffdca6'), rough=0.08),
    'seconds': material('seconds', srgb('#c23a1e'), metallic=0.0, rough=0.25, Coat_Weight=1.0),
    'dial': material('dial', srgb('#16130f'), metallic=0.7, rough=0.28, tangent='RADIAL', Anisotropic=0.85, Anisotropic_Rotation=0.25, Coat_Weight=1.0, Coat_Roughness=0.03),
    'print': material('print', srgb('#e9c48c'), rough=0.3),
    'sapphire': material('sapphire', (1, 1, 1), metallic=0.0, rough=0.0, IOR=1.77, Transmission_Weight=1.0),
    'perlage': material('rhodium_perlage', srgb('#d6d8dc'), rough=0.3, normal_img=PERLAGE),
    'cotes': material('rhodium_cotes', srgb('#d9dbdf'), rough=0.18, normal_img=COTES),
    'gold_mvt': material('gold_movement', srgb('#e8b96f'), rough=0.18),
    'blued': material('blued', srgb('#1b2f7a'), rough=0.18, Thin_Film_Thickness=320.0, Thin_Film_IOR=2.0),
    'ruby': material('ruby', srgb('#9b0d24'), metallic=0.0, rough=0.02, IOR=1.77, Transmission_Weight=0.6, Coat_Weight=1.0),
}


# ---------------------------------------------------------------- the watch

print('Modelling...')
root = empty('watch')

# Case middle: bulged flanks, a chamfer into the bezel seat.
part_case = empty('part_case', root)
case_profile = fillet([
    (0.99, -0.20, 0.0), (1.12, -0.20, 0.02), (1.225, -0.165, 0.06), (1.252, -0.05, 0.25),
    (1.248, 0.09, 0.25), (1.215, 0.19, 0.04), (1.17, 0.20, 0.01), (0.99, 0.20, 0.0),
], steps=8)
mesh_object('case_body', lathe('case_body', case_profile, 256), M['case'], part_case)

# Lugs: lofted cross-sections. Wide where they leave the case, tapering and
# curving down towards the wrist, finishing in a rounded tip.
def lug_mesh(x0):
    def profile(y):
        u = min(1.0, max(0.0, (y - 1.02) / 0.58))
        s = smoothstep(0.0, 1.0, u)
        return 0.3 - 0.06 * s, 0.05 + 0.12 * (0.5 + 0.5 * cos(pi * u)), -0.17 + 0.05 * s  # width, top, bottom
    secs = []
    for y in np.linspace(0.92, 1.6, 30):
        w, zt, zb = profile(y)
        secs.append((y, rounded_rect(x0, (zt + zb) / 2, w, zt - zb, 0.05)))
    w, zt, zb = profile(1.6)
    for t in np.linspace(0.2, 1.0, 7):
        k = max(cos(t * pi / 2), 0.05)
        h = (zt - zb) * k
        secs.append((1.6 + 0.07 * sin(t * pi / 2), rounded_rect(x0, (zt + zb) / 2, w * (0.85 + 0.15 * k), h, min(0.05, h / 2))))
    return loft('lug', secs)


for sx in (-1, 1):
    for sy in (-1, 1):
        me = lug_mesh(sx * 0.6)
        if sy < 0:
            me.transform(Matrix.Scale(-1, 4, (0, 1, 0)))
            me.flip_normals()
        mesh_object(f'lug_{"l" if sx < 0 else "r"}{"t" if sy > 0 else "b"}', me, M['case'], part_case, sharp=50)

# Crown: knurled grip, polished cap.
crown_profile = [(0.0, 0.0), (0.055, 0.0), (0.055, 0.04), (0.125, 0.045), (0.14, 0.065), (0.14, 0.165), (0.128, 0.185), (0.06, 0.195), (0.0, 0.198)]
knurl = lambda r, z, a: (r - 0.009 * max(0.0, cos(36 * a)) if (r > 0.135 and 0.07 < z < 0.16) else r, z)
crown_me = lathe('crown', crown_profile, 288, closed=False, deform=knurl)
crown_me.transform(Matrix.Translation((1.2, 0, 0)) @ Matrix.Rotation(pi / 2, 4, 'Y'))
mesh_object('crown', crown_me, M['case'], part_case)

# Bezel: fluted outer slope, polished inner edge.
part_bezel = empty('part_bezel', root)
bezel_profile = fillet([
    (1.0, 0.19, 0.0), (1.19, 0.19, 0.008), (1.205, 0.235, 0.015), (1.14, 0.31, 0.012),
    (1.045, 0.318, 0.01), (1.0, 0.30, 0.004),
], steps=6)
flute = lambda r, z, a: (r - 0.016 * (0.5 - 0.5 * cos(72 * a)) * smoothstep(0.215, 0.27, z) * smoothstep(1.06, 1.12, r), z)
mesh_object('bezel', lathe('bezel', bezel_profile, 72 * 10, deform=flute), M['case'], part_bezel, sharp=50)

# Sapphire: flat underside, gently domed top.
part_crystal = empty('part_crystal', root)
dome = [(0.0, 0.265), (1.02, 0.265), (1.032, 0.272), (1.032, 0.298)]
for i in range(1, 25):
    r = 1.025 * (1 - i / 24)
    dome.append((r, 0.30 + 0.04 * (1 - (r / 1.025) ** 2)))
mesh_object('crystal', lathe('crystal', dome, 192, closed=False), M['sapphire'], part_crystal, sharp=60)

# Dial: lacquered sunburst base, printed layer, faceted applied indices.
part_dial = empty('part_dial', root)
dial_profile = fillet([(0.0, 0.1), (1.0, 0.1, 0.004), (1.0, 0.115, 0.004), (0.0, 0.115)], closed=False)
dial = mesh_object('dial_base', lathe('dial_base', [(p[0], p[1]) for p in dial_profile], 192, closed=False), M['dial'], part_dial)
planar_uv(dial)
FONT_SERIF = bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Didot.ttc')
FONT_SANS = bpy.data.fonts.load('/System/Library/Fonts/Avenir Next.ttc')
PRINT_Z = 0.1152
PRINT_DEPTH = 0.0012


def text_mesh(body, font, size, y, spacing=1.0):
    cu = bpy.data.curves.new('txt', 'FONT')
    cu.body = body
    cu.font = font
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.space_character = spacing
    cu.extrude = PRINT_DEPTH / 2
    tmp = bpy.data.objects.new('txt_tmp', cu)
    scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.transform(Matrix.Translation((0, y, PRINT_Z + PRINT_DEPTH / 2)))
    return me


# Raised dial printing: logo and text as real geometry, plus the minute track.
print_parts = [
    text_mesh('MERIDIAN', FONT_SERIF, 0.13, 0.4, 1.25),
    text_mesh('SHEFFIELD', FONT_SANS, 0.034, 0.29, 1.6),
    text_mesh('AUTOMATIC', FONT_SANS, 0.036, -0.3, 1.6),
    text_mesh('Calibre 01', FONT_SERIF, 0.07, -0.39, 1.05),
]
tick = {}
for major in (False, True):
    w, l = (0.011, 0.06) if major else (0.0055, 0.034)
    v, f = box(-w / 2, w / 2, 0.975 - l, 0.975, PRINT_Z, PRINT_Z + PRINT_DEPTH)
    tick[major] = pydata_mesh('tick', v, f)
for i in range(60):
    if i % 5 == 0:
        continue  # applied indices cover the hours
    me = tick[False].copy()
    me.transform(Matrix.Rotation(-tau * i / 60, 4, 'Z'))
    print_parts.append(me)
print_parts.append(lathe('track', [(0.893, PRINT_Z), (0.899, PRINT_Z), (0.899, PRINT_Z + PRINT_DEPTH), (0.893, PRINT_Z + PRINT_DEPTH)], 192))
bm = bmesh.new()
for me in print_parts:
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
for me in tick.values():
    bpy.data.meshes.remove(me)
mesh_object('dial_print', bm_to_mesh('dial_print', bm), M['print'], part_dial, sharp=30)

v, f = box(-0.027, 0.027, -0.085, 0.085, 0.0, 0.02)
v = [(x * (0.15 if z > 0 else 1.0), y * (0.92 if z > 0 else 1.0), z) for x, y, z in v]  # roof-shaped facets
index_me = pydata_mesh('index', v, f)
mats = []
for i in range(12):
    a = tau * i / 12
    for dx in ((-0.04, 0.04) if i == 0 else (0.0,)):
        mats.append(Matrix.Rotation(-a, 4, 'Z') @ Matrix.Translation((dx, 0.78, 0.115)))
indices = mesh_object('dial_indices', merge_copies('dial_indices', index_me, mats), M['hand'], part_dial, sharp=25)
bevel(indices, 0.004, segments=2, angle=40)


def dauphine(name, length, width, tail, ridge=0.012, edge=0.003, n=40):
    """Faceted dauphine hand: two sloped facets meeting at a raised centre ridge."""
    verts, faces = [], []
    for k in range(n + 1):
        y = -tail + (length + tail) * k / n
        f = (y + tail) / (length + tail)
        wid = width * (0.55 + 0.45 * f / 0.22) if f < 0.22 else width * (1 - (f - 0.22) / 0.78)
        hw = max(wid / 2, 1e-5)
        verts += [(-hw, y, edge), (0, y, ridge * (1 - 0.6 * f ** 3)), (hw, y, edge), (hw, y, 0), (-hw, y, 0)]
    for k in range(n):
        a, b = k * 5, (k + 1) * 5
        for i in range(5):
            j = (i + 1) % 5
            faces.append((a + i, a + j, b + j, b + i))
    faces.append((4, 3, 2, 1, 0))
    last = n * 5
    faces.append((last, last + 1, last + 2, last + 3, last + 4))
    me = pydata_mesh(name, verts, faces)
    hub = lathe(name + '_hub', fillet([(0.0, 0.0), (0.045, 0.0, 0.004), (0.045, 0.012, 0.004), (0.0, 0.012)], closed=False), 64, closed=False)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.from_mesh(hub)
    bpy.data.meshes.remove(hub)
    bpy.data.meshes.remove(me)
    return bm_to_mesh(name, bm)


def hand(name, z, mesh, mat):
    part = empty(f'part_{name}', root)
    spin = empty(f'spin_{name}', part, (0, 0, z))
    mesh_object(f'hand_{name}', mesh, mat, spin, sharp=20)


hand('hour', 0.15, dauphine('hand_hour', 0.5, 0.085, 0.08), M['hand'])
hand('minute', 0.168, dauphine('hand_minute', 0.8, 0.062, 0.1), M['hand'])
sec = bmesh.new()
for v_, f_ in (box(-0.005, 0.005, -0.22, 0.92, 0.0, 0.006),):
    vs = [sec.verts.new(p) for p in v_]
    for ff in f_:
        sec.faces.new([vs[i] for i in ff])
bmesh.ops.create_cone(sec, cap_ends=True, segments=48, radius1=0.032, radius2=0.032, depth=0.006,
                      matrix=Matrix.Translation((0, -0.16, 0.003)))
bmesh.ops.create_cone(sec, cap_ends=True, segments=48, radius1=0.026, radius2=0.022, depth=0.016,
                      matrix=Matrix.Translation((0, 0, 0.008)))
hand('second', 0.186, bm_to_mesh('hand_second', sec), M['seconds'])

# Movement: perlaged main plate, Côtes de Genève bridges with chamfered edges,
# gold train wheels, jewels in chatons, blued screws.
part_plate = empty('part_plate', root)
part_bridges = empty('part_bridges', root)  # sits behind the wheels, so it must explode further than them
plate_me = lathe('plate', fillet([(0.0, -0.12), (0.97, -0.12, 0.01), (0.97, -0.02, 0.01), (0.0, -0.02)], closed=False), 192, closed=False)
plate = mesh_object('plate', plate_me, M['perlage'], part_plate)
planar_uv(plate)

BRIDGES = {
    'bridge_train': ((-0.66, 0.37), (0.68, 0.33), 0.2),
    'bridge_center': ((-0.62, -0.26), (0.2, -0.05), 0.17),
    'bridge_cock': ((0.86, -0.58), (0.5, -0.42), 0.15),
}
for name, (p0, p1, w) in BRIDGES.items():
    me = curve_mesh(name, [capsule(p0, p1, w)], 0.024, bevel_depth=0.006)
    me.transform(Matrix.Translation((0, 0, -0.176)))
    ob = mesh_object(name, me, M['cotes'], part_bridges, sharp=40)
    planar_uv(ob)

screw_me = lathe('screw', fillet([(0.0, 0.0), (0.028, 0.0, 0.003), (0.028, 0.006, 0.004)] + [(0.028 * cos(t), 0.006 + 0.01 * sin(t)) for t in np.linspace(0.3, pi / 2, 8)], closed=False), 48, closed=False)
slot = bmesh.new()
for v_, f_ in (box(-0.0045, 0.0045, -0.04, 0.04, 0.008, 0.03),):
    vs = [slot.verts.new(p) for p in v_]
    for ff in f_:
        slot.faces.new([vs[i] for i in ff])
slot_ob = bpy.data.objects.new('slot', bm_to_mesh('slot', slot))
screw_ob = bpy.data.objects.new('screw_tmp', screw_me)
scene.collection.objects.link(slot_ob)
scene.collection.objects.link(screw_ob)
boolean = screw_ob.modifiers.new('slot', 'BOOLEAN')
boolean.operation = 'DIFFERENCE'
boolean.object = slot_ob
apply_modifiers(screw_ob)
screw_me = screw_ob.data.copy()
bpy.data.objects.remove(screw_ob)
bpy.data.objects.remove(slot_ob)

flip = Matrix.Rotation(pi, 4, 'X')  # screw heads face the caseback (-Z)
screw_spots = [BRIDGES['bridge_train'][0], BRIDGES['bridge_train'][1], BRIDGES['bridge_center'][0], BRIDGES['bridge_center'][1], BRIDGES['bridge_cock'][0]]
mesh_object('plate_screws', merge_copies('plate_screws', screw_me, [
    Matrix.Translation((x, y, -0.176)) @ flip @ Matrix.Rotation(i * 1.3, 4, 'Z') for i, (x, y) in enumerate(screw_spots)
]), M['blued'], part_bridges, sharp=40)

chaton_me = lathe('chaton', fillet([(0.016, 0.0), (0.034, 0.0, 0.002), (0.034, 0.007, 0.003), (0.016, 0.007, 0.002)]), 64)
jewel_me = lathe('jewel', [(0.0, 0.0), (0.018, 0.0)] + [(0.018 * cos(t), 0.007 * sin(t)) for t in np.linspace(0.2, pi / 2, 8)], 48, closed=False)


def jewel_set(name, spots, z, parent):
    Ms = [Matrix.Translation((x, y, z)) @ flip for x, y in spots]
    mesh_object(name + '_chatons', merge_copies(name + '_chatons', chaton_me, Ms), M['gold_mvt'], parent, sharp=40)
    mesh_object(name + '_jewels', merge_copies(name + '_jewels', jewel_me, Ms), M['ruby'], parent, sharp=None)


def gear_outline(r_tip, teeth, h):
    pts = []
    for i in range(teeth * 12):
        a = tau * i / (teeth * 12)
        r = r_tip - h + h * smoothstep(-0.35, 0.55, cos(teeth * a))
        pts.append((r * cos(a), r * sin(a)))
    return pts


def spoke_holes(r_in, r_out, count, gap=0.22):
    holes = []
    for k in range(count):
        a0, a1 = tau * k / count + gap, tau * (k + 1) / count - gap
        pts = [(x, y, 0.0) for x, y in arc(0, 0, r_out, a0, a1, 16)] + [(x, y, 0.0) for x, y in arc(0, 0, r_in, a1, a0, 8)]
        for i in (0, 16, 17, len(pts) - 1):
            pts[i] = (*pts[i][:2], 0.012)
        holes.append(fillet(pts, steps=4))
    return holes


GEARS = [
    ('gear1', (-0.3, 0.3), 0.3, 40),
    ('gear2', (-0.05, -0.12), 0.18, 24),
    ('gear3', (0.38, 0.32), 0.24, 32),
    ('gear4', (-0.42, -0.45), 0.14, 18),
]
for name, (gx, gy), r, teeth in GEARS:
    part = empty(f'part_{name}', root)
    spin = empty(f'spin_{name}', part, (gx, gy, -0.146))
    loops = [gear_outline(r, teeth, 0.03)]
    if r > 0.17:
        loops += spoke_holes(0.07, r - 0.075, 5 if r > 0.2 else 4)
    loops.append(circle(0, 0, 0.014, 24))
    gear = curve_mesh(name, loops, 0.018, bevel_depth=0.003, bevel_res=1)
    pinion = lathe(name + '_arbor', [(0.0, -0.03), (0.016, -0.03), (0.016, 0.03), (0.0, 0.03)], 32, closed=False)
    bm = bmesh.new()
    bm.from_mesh(gear)
    bm.from_mesh(pinion)
    bpy.data.meshes.remove(gear)
    bpy.data.meshes.remove(pinion)
    mesh_object(f'{name}_wheel', bm_to_mesh(name, bm), M['gold_mvt'], spin, sharp=40)
    jewel_set(name, [(gx, gy)], -0.176 if name != 'gear4' else -0.122, part_bridges if name != 'gear4' else part_plate)

# Balance: gold rim with timing screws, blued hairspring, jewel on the cock.
part_balance = empty('part_balance', root)
spin_balance = empty('spin_balance', part_balance, (0.5, -0.42, -0.14))
rim = lathe('balance_rim', fillet([(0.148, -0.008), (0.172, -0.008, 0.003), (0.172, 0.008, 0.003), (0.148, 0.008)]), 128)
bm = bmesh.new()
bm.from_mesh(rim)
bpy.data.meshes.remove(rim)
for i in range(3):
    arm = bmesh.new()
    v_, f_ = box(-0.006, 0.006, 0.0, 0.16, -0.004, 0.004)
    vs = [arm.verts.new(p) for p in v_]
    for ff in f_:
        arm.faces.new([vs[j] for j in ff])
    arm_me = bpy.data.meshes.new('arm')
    arm.to_mesh(arm_me)
    arm_me.transform(Matrix.Rotation(tau * i / 3, 4, 'Z'))
    bm.from_mesh(arm_me)
    bpy.data.meshes.remove(arm_me)
for i in range(12):
    a = tau * i / 12
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.007, radius2=0.007, depth=0.016,
                          matrix=Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((0.178, 0, 0)) @ Matrix.Rotation(pi / 2, 4, 'Y'))
mesh_object('balance_wheel', bm_to_mesh('balance_wheel', bm), M['gold_mvt'], spin_balance, sharp=40)
spiral = [((0.025 + 0.085 * t) * cos(t * 9 * tau), (0.025 + 0.085 * t) * sin(t * 9 * tau), -0.006) for t in np.linspace(0, 1, 900)]
mesh_object('hairspring', tube_mesh('hairspring', spiral, 0.0018, 4), M['blued'], spin_balance, sharp=None)
jewel_set('balance', [(0.5, -0.42)], -0.176, part_bridges)

# Rotor: Côtes de Genève plate with a heavy gold rim weight, on a central bearing.
part_rotor = empty('part_rotor', root)
spin_rotor = empty('spin_rotor', part_rotor, (0, 0, -0.205))
a0, a1 = radians(14), radians(166)
outline = [(x, y, 0.0) for x, y in arc(0, 0, 0.94, a0, a1, 64)] + [(x, y, 0.0) for x, y in arc(0, 0, 0.19, a1, a0 + tau, 40)]
for i in (0, 64, 65, len(outline) - 1):
    outline[i] = (*outline[i][:2], 0.05)
rotor = mesh_object('rotor', curve_mesh('rotor', [fillet(outline, steps=6), circle(0, 0, 0.06, 32)], 0.018, bevel_depth=0.004), M['cotes'], spin_rotor, sharp=40)
planar_uv(rotor)
weight = [(x, y, 0.0) for x, y in arc(0, 0, 0.945, a0 + 0.02, a1 - 0.02, 64)] + [(x, y, 0.0) for x, y in arc(0, 0, 0.84, a1 - 0.02, a0 + 0.02, 64)]
for i in (0, 64, 65, len(weight) - 1):
    weight[i] = (*weight[i][:2], 0.02)
weight_me = curve_mesh('rotor_weight', [fillet(weight, steps=4)], 0.03, bevel_depth=0.005)
weight_me.transform(Matrix.Translation((0, 0, -0.006)))
mesh_object('rotor_weight', weight_me, M['gold_mvt'], spin_rotor, sharp=40)
hub = lathe('rotor_hub', fillet([(0.03, -0.012), (0.085, -0.012, 0.004), (0.085, 0.026, 0.004), (0.03, 0.026, 0.004)]), 96)
mesh_object('rotor_hub', hub, M['case'], spin_rotor)
mesh_object('rotor_screws', merge_copies('rotor_screws', screw_me, [
    Matrix.Translation((0.058 * cos(a), 0.058 * sin(a), -0.012)) @ flip @ Matrix.Rotation(a * 2, 4, 'Z') for a in (0.5, 0.5 + tau / 3, 0.5 + 2 * tau / 3)
]), M['blued'], spin_rotor, sharp=40)

# Exhibition caseback: screwed ring with a sapphire window.
part_caseback = empty('part_caseback', root)
back_profile = fillet([(0.74, -0.27, 0.006), (1.12, -0.27, 0.03), (1.13, -0.2, 0.01), (0.74, -0.2, 0.006)], steps=6)
mesh_object('caseback_ring', lathe('caseback_ring', back_profile, 192), M['case'], part_caseback)
glass_profile = fillet([(0.0, -0.248), (0.765, -0.248, 0.006), (0.765, -0.228, 0.006), (0.0, -0.228)], closed=False)
mesh_object('caseback_glass', lathe('caseback_glass', [(p[0], p[1]) for p in glass_profile], 128, closed=False), M['sapphire'], part_caseback, sharp=60)
mesh_object('caseback_screws', merge_copies('caseback_screws', screw_me, [
    Matrix.Translation((0.93 * cos(a), 0.93 * sin(a), -0.27)) @ flip @ Matrix.Rotation(a * 3, 4, 'Z') for a in np.linspace(0, tau, 7)[:-1] + pi / 6
]), M['case'], part_caseback, sharp=40)

# Bracelet. The links follow a wrist-shaped path (flatter on top, deeper than
# wide) that starts at the spring bar between the lug tips. Link positions are
# exported as slot_* empties, so the site places links exactly where Blender does.
WRIST = [(1.50, -0.04), (1.78, -0.25), (1.98, -0.70), (2.02, -1.30), (1.85, -1.95), (1.35, -2.45), (0.65, -2.70), (0.0, -2.76)]
WRIST_PTS = catmull_rom(WRIST)
WRIST_LEN = [0.0]
for a, b in zip(WRIST_PTS, WRIST_PTS[1:]):
    WRIST_LEN.append(WRIST_LEN[-1] + (b - a).length)
PITCH = 0.215
CLASP_HALF = 0.42


def wrist_at(s):
    """Point and unit tangent (y, z) at arc length s along the wrist path."""
    for i in range(len(WRIST_LEN) - 1):
        if WRIST_LEN[i + 1] >= s:
            a, b = WRIST_PTS[i], WRIST_PTS[i + 1]
            f = (s - WRIST_LEN[i]) / max(WRIST_LEN[i + 1] - WRIST_LEN[i], 1e-9)
            return a.lerp(b, f), (b - a).normalized()
    return WRIST_PTS[-1], (WRIST_PTS[-1] - WRIST_PTS[-2]).normalized()


def wrist_z(y):
    best = min(WRIST_PTS, key=lambda p: abs(p.x - y))
    return best.y


def end_link_mesh():
    secs = []
    for y in np.linspace(1.18, 1.5, 16):
        u = (y - 1.18) / 0.32
        secs.append((y, rounded_rect(0, 0.035 - 0.075 * u ** 1.4, 0.9, 0.15 - 0.03 * u, 0.035)))
    return loft('end_link', secs)


for side, label in ((1, 'top'), (-1, 'bottom')):
    part = empty(f'part_bracelet_{label}', root)
    me = end_link_mesh()
    if side < 0:
        me.transform(Matrix.Scale(-1, 4, (0, 1, 0)))
        me.flip_normals()
    end = mesh_object(f'end_link_{label}', me, M['brushed'], part, sharp=50)
    planar_uv(end, scale=2.0)

    i = 0
    while True:
        p, t = wrist_at(PITCH * (i + 0.5))
        if p.x < CLASP_HALF + PITCH / 2:
            break
        last_link_y = p.x
        X = Vector((side, 0, 0))
        Y = Vector((0, side * t.x, t.y))
        Z = X.cross(Y)  # points away from the wrist on both sides
        slot = empty(f'slot_{label}_{i:02d}', part)
        slot.matrix_basis = Matrix.Translation((0, side * p.x, p.y)) @ Matrix((X, Y, Z)).transposed().to_4x4()
        i += 1

# Folding clasp under the wrist: brushed cover, engraved logo, polished pushers.
# Sized to meet the last links with the same gap as between links.
CLASP_HALF = last_link_y - 0.1 - (PITCH - 0.2)
part = bpy.data.objects['part_bracelet_bottom']
clasp_z = wrist_z(0.0) - 0.005
secs = [(y, rounded_rect(0, wrist_z(abs(y)) - 0.005, 0.96, 0.15, 0.04)) for y in np.linspace(-CLASP_HALF, CLASP_HALF, 25)]
clasp = mesh_object('clasp', loft('clasp', secs), M['brushed'], part, sharp=50)
planar_uv(clasp, scale=2.0)
logo = text_mesh('MERIDIAN', FONT_SERIF, 0.085, 0.0, 1.3)
logo.transform(Matrix.Translation((0, 0, clasp_z - 0.075 - 0.0004)) @ Matrix.Rotation(pi, 4, 'Y') @ Matrix.Translation((0, 0, -PRINT_Z)))
mesh_object('clasp_logo', logo, M['polished'], part, sharp=30)
bm = bmesh.new()
for sx in (-1, 1):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.042, radius2=0.036, depth=0.05,
                          matrix=Matrix.Translation((sx * 0.495, 0, clasp_z)) @ Matrix.Rotation(sx * pi / 2, 4, 'Y'))
mesh_object('clasp_pushers', bm_to_mesh('clasp_pushers', bm), M['polished'], part, sharp=40)

# Bracelet link prototypes; the site lays them around the wrist.
proto = empty('proto_links', root)
v, f = box(0.19, 0.465, -0.1, 0.1, -0.06, 0.06)
outer_r = pydata_mesh('link_outer_r', v, f)
outer = merge_copies('link_outer', outer_r, [Matrix.Identity(4), Matrix.Scale(-1, 4, (1, 0, 0))])
link_outer = mesh_object('link_outer', outer, [M['brushed'], M['polished']], proto, sharp=None)
bevel(link_outer, 0.028, segments=4, angle=40, material=1)
planar_uv(link_outer, scale=2.0)
v, f = box(-0.17, 0.17, -0.1, 0.1, -0.072, 0.072)
v = [(x, y, z + (0.012 if z > 0 and abs(x) < 0.1 else 0)) for x, y, z in v]
link_center = mesh_object('link_center', pydata_mesh('link_center', v, f), M['polished'], proto, sharp=None)
bevel(link_center, 0.045, segments=5, angle=25)


# ---------------------------------------------------------------- export

def export_glb():
    bpy.ops.object.select_all(action='DESELECT')
    for ob in WATCH.all_objects:
        ob.select_set(True)
    os.makedirs(os.path.join(ROOT, 'blender', 'out'), exist_ok=True)
    path = os.path.join(ROOT, 'blender', 'out', 'watch_raw.glb')  # compressed into public/models by npm run model
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_yup=False,
        export_apply=False,
        export_image_format='NONE',
        export_materials='EXPORT',
        export_tangents=False,
    )
    print(f'Exported {path} ({os.path.getsize(path) / 1024:.0f} KB)')


export_glb()


# ---------------------------------------------------------------- reference renders

def bracelet_preview():
    for slot in [o for o in WATCH.all_objects if o.name.startswith('slot_')]:
        for src in (link_outer, link_center):
            ob = bpy.data.objects.new(f'{src.name}_{slot.name}', src.data)
            ob.matrix_world = slot.matrix_world
            STUDIO.objects.link(ob)
    proto.hide_render = True
    for ob in proto.children:
        ob.hide_render = True


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def area(name, size, loc, energy, color=(1, 1, 1)):
    light = bpy.data.lights.new(name, 'AREA')
    light.shape = 'RECTANGLE'
    light.size, light.size_y = size
    light.energy = energy
    light.color = color
    ob = bpy.data.objects.new(name, light)
    ob.location = loc
    look_at(ob, (0, 0, 0))
    STUDIO.objects.link(ob)


def studio():
    world = bpy.data.worlds.new('studio')
    world.color = (0.003, 0.003, 0.003)
    scene.world = world
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.004, 0.0035, 0.003, 1)
    area('key', (5, 3), (-4.5, -3.5, 7), 3000, (1, 0.96, 0.9))
    area('strip_l', (0.5, 9), (-6, 1, 2.5), 2200)
    area('strip_r', (0.5, 9), (6, -1, 3.5), 1800, (0.95, 0.97, 1))
    area('top', (9, 9), (0, 0, 10), 500)
    area('rim', (6, 1), (0, 7, -3), 2500, (1, 0.85, 0.65))
    area('under', (6, 6), (0, -2, -8), 600)


def render(name, cam_loc, target, lens=75):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 8
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = cam_loc
    look_at(cam, target)
    cam_data.dof.focus_distance = (Vector(target) - Vector(cam_loc)).length
    STUDIO.objects.link(cam)
    scene.camera = cam
    scene.render.filepath = os.path.join(RENDER_DIR, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('Rendered', scene.render.filepath)


if RENDER:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    for name, frac in (('hour', (10 + 10 / 60) / 12), ('minute', 10 / 60), ('second', 35 / 60)):
        bpy.data.objects[f'spin_{name}'].rotation_euler.z = -frac * tau
    bracelet_preview()
    studio()
    render('front', (1.8, -2.9, 8.6), (0.05, 0.1, 0.0))
    render('back', (-2.4, 2.2, -8.6), (0.0, -0.05, -0.15))
    render('macro_dial', (0.9, -1.4, 3.6), (0.15, 0.1, 0.12), lens=90)
    render('side', (7.5, -3.2, 1.2), (0.0, 0.0, -1.0), lens=60)
    render('clasp', (2.6, -2.4, -7.5), (0.0, 0.0, -2.6), lens=70)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'meridian_watch.blend'))
print('Done')
