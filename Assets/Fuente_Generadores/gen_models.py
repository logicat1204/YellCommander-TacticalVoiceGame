# -*- coding: utf-8 -*-
import bpy, bmesh, math, random, sys, os, shutil, zipfile, csv, addon_utils
from mathutils import Vector, Matrix, Euler, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

OUT = sys.argv[1]          # raiz de salida
PREV = sys.argv[2]         # carpeta de previews
TEX = os.path.join(OUT, 'Textures')
os.makedirs(PREV, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable('io_scene_fbx', default_set=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0


# ----------------------------------------------------------------------------- materiales
def load_img(p, nc=False):
    im = bpy.data.images.load(p, check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if nc else 'sRGB'
    return im


def mat_bc(name, bc, closest=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = load_img(bc)
    if closest:
        t.interpolation = 'Closest'
    nt.links.new(t.outputs['Color'], bs.inputs['Base Color'])
    return m


def mat_pbr(name, bc, orm=None, nrm=None, closest=False):
    m = mat_bc(name, bc, closest)
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    if orm:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = load_img(orm, True)
        if closest:
            t.interpolation = 'Closest'
        sp = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t.outputs['Color'], sp.inputs['Color'])
        nt.links.new(sp.outputs['Green'], bs.inputs['Roughness'])
        nt.links.new(sp.outputs['Blue'], bs.inputs['Metallic'])
    if nrm:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = load_img(nrm, True)
        sp = nt.nodes.new('ShaderNodeSeparateColor'); cm = nt.nodes.new('ShaderNodeCombineColor')
        iv = nt.nodes.new('ShaderNodeMath'); iv.operation = 'SUBTRACT'; iv.inputs[0].default_value = 1.0
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(t.outputs['Color'], sp.inputs['Color'])
        nt.links.new(sp.outputs['Red'], cm.inputs['Red'])
        nt.links.new(sp.outputs['Green'], iv.inputs[1])
        nt.links.new(iv.outputs['Value'], cm.inputs['Green'])
        nt.links.new(sp.outputs['Blue'], cm.inputs['Blue'])
        nt.links.new(cm.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    return m


def tt(n):
    return os.path.join(TEX, 'Tileable', f'T_{n}_%s.png')


TILE = {}
for n_ in ('Concreto', 'Tierra', 'Saco', 'Roca', 'Metal'):
    TILE[n_] = dict(exp=mat_bc('M_' + n_, tt(n_) % 'BC'),
                    prv=mat_pbr('prv_' + n_, tt(n_) % 'BC', tt(n_) % 'ORM', tt(n_) % 'N'))
SOLD = {v: dict(exp=mat_bc('M_Soldado', os.path.join(TEX, 'Soldado', f'T_Soldado_{v}_BC.png'), True),
                prv=mat_pbr('prv_Sold_' + v, os.path.join(TEX, 'Soldado', f'T_Soldado_{v}_BC.png'),
                            os.path.join(TEX, 'Soldado', 'T_Soldado_ORM.png'), None, True)) for v in PALETTES}
WEAP = dict(exp=mat_bc('M_Armas', os.path.join(TEX, 'Armas', 'T_Armas_BC.png'), True),
            prv=mat_pbr('prv_Armas', os.path.join(TEX, 'Armas', 'T_Armas_BC.png'),
                        os.path.join(TEX, 'Armas', 'T_Armas_ORM.png'), None, True))


# ----------------------------------------------------------------------------- constructor de mallas
def MX(loc=(0, 0, 0), rot=(0, 0, 0), sc=(1, 1, 1)):
    return Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((sc[0], sc[1], sc[2], 1.0))


class B:
    def __init__(s):
        s.bm = bmesh.new()
        s.uv = s.bm.loops.layers.uv.new('UVMap')
        s.pid = s.bm.faces.layers.int.new('pid')

    def _b(s):
        pass

    def newf(s):
        return [f for f in s.bm.faces if f[s.pid] == 0]

    def _e(s, mat=0, cell=None, box=None, bevel=0.0, fcell=None):
        bm = s.bm
        new = s.newf()
        if bevel > 0 and new:
            edges = list({e for f in new for e in f.edges})
            try:
                bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=1, affect='EDGES', profile=0.5, clamp_overlap=True)
            except Exception:
                pass
            new = s.newf()
        bm.normal_update()
        for f in new:
            f[s.pid] = 1
            f.material_index = mat
            c = fcell(f.calc_center_median()) if fcell else cell
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                if c is not None:
                    l[s.uv].uv = cell_uv(c)
                else:
                    p = l.vert.co
                    u, v = ((p.x, p.y), (p.x, p.z), (p.y, p.z))[{2: 0, 1: 1, 0: 2}[ax]]
                    l[s.uv].uv = (u / box, v / box)

    def box(s, size, loc=(0, 0, 0), rot=(0, 0, 0), **k):
        s._b(); bmesh.ops.create_cube(s.bm, size=1.0, matrix=MX(loc, rot, size)); s._e(**k)

    def sph(s, r, loc, rot=(0, 0, 0), seg=(12, 8), **k):
        rr = (r, r, r) if isinstance(r, (int, float)) else r
        s._b(); bmesh.ops.create_uvsphere(s.bm, u_segments=seg[0], v_segments=seg[1], radius=1.0, matrix=MX(loc, rot, rr)); s._e(**k)

    def cyl(s, r1, r2, h, loc, rot=(0, 0, 0), seg=12, sc=(1, 1, 1), **k):
        s._b(); bmesh.ops.create_cone(s.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=h, matrix=MX(loc, rot, sc)); s._e(**k)

    def loft(s, rings, seg=14, matrix=None, caps=True, **k):
        s._b(); bm = s.bm; vr = []
        for (z, rx, ry, cx, cy) in rings:
            vr.append([bm.verts.new((cx + rx * math.cos(2 * math.pi * i / seg), cy + ry * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
        fs = []
        for a, b_ in zip(vr[:-1], vr[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                fs.append(bm.faces.new((a[i], a[j], b_[j], b_[i])))
        if caps:
            fs.append(bm.faces.new(vr[0])); fs.append(bm.faces.new(vr[-1]))
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        if matrix is not None:
            bmesh.ops.transform(bm, matrix=matrix, verts=[v for r in vr for v in r])
        s._e(**k)

    def ring(s, z0, z1, rx, ry, seg=16, cy=0.0, **k):
        s.loft([(z0, rx, ry, 0, cy), (z1, rx, ry, 0, cy)], seg, **k)

    def tube(s, p0, p1, radii, seg=12, **k):
        p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0; L = d.length
        rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        rings = [(t * L, r[1], r[-1], 0, 0) for r in radii for t in (r[0],)]
        s.loft(rings, seg, matrix=Matrix.Translation(p0) @ rot, **k)

    def dome(s, c, rx, ry, hz, n=7, seg=24, **k):
        rings = []
        for i in range(n):
            ph = math.radians(88.0 * i / (n - 1))
            rings.append((c[2] + hz * math.sin(ph), max(rx * math.cos(ph), 0.002), max(ry * math.cos(ph), 0.002), c[0], c[1]))
        s.loft(rings, seg, **k)

    def prism(s, pts, x0, x1, axis='x', **k):
        """Extrusion de un perfil (offset,z) a lo largo de un eje. pts: [(off,z)...] en orden."""
        s._b(); bm = s.bm
        mk = (lambda o, z, t: (t, o, z)) if axis == 'x' else (lambda o, z, t: (o, t, z))
        a = [bm.verts.new(mk(o, z, x0)) for o, z in pts]
        b_ = [bm.verts.new(mk(o, z, x1)) for o, z in pts]
        fs = [bm.faces.new((a[i], a[(i + 1) % len(a)], b_[(i + 1) % len(a)], b_[i])) for i in range(len(a))]
        fs += [bm.faces.new(a), bm.faces.new(b_)]
        bmesh.ops.recalc_face_normals(bm, faces=fs)
        s._e(**k)

    def finish(s, name, mats, sharp=40):
        bm = s.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        thr = math.radians(sharp)
        for e in bm.edges:
            e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > thr)
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me); bm.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        scene.collection.objects.link(ob)
        return ob


def ucx_box(base, i, size, loc, rot=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=MX(loc, rot, size))
    me = bpy.data.meshes.new(f'UCX_{base}_{i:02d}'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f'UCX_{base}_{i:02d}', me); scene.collection.objects.link(ob); return ob


def ucx_hull(base, i, pts):
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs)
    try:
        bmesh.ops.delete(bm, geom=list(res.get('geom_interior', [])) + list(res.get('geom_unused', [])), context='VERTS')
    except Exception:
        pass
    me = bpy.data.meshes.new(f'UCX_{base}_{i:02d}'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f'UCX_{base}_{i:02d}', me); scene.collection.objects.link(ob); return ob


STATS = []
ALL = {}       # nombre -> (ob, ucx[], grupo)


def reg(ob, ucx, group, slots):
    me = ob.data
    me.calc_loop_triangles()
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    dim = ob.dimensions
    STATS.append([ob.name, group, len(me.loop_triangles), len(me.vertices), round(dim.x, 2), round(dim.y, 2), round(dim.z, 2)])
    ALL[ob.name] = (ob, ucx, group, slots)


def export(ob, ucx, path, ue=True):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [ob] + list(ucx):
        o.select_set(True)
    bpy.context.view_layer.objects.active = ob
    kw = dict(filepath=path, check_existing=False, use_selection=True, object_types={'MESH'}, use_mesh_modifiers=True,
              mesh_smooth_type='EDGE', add_leaf_bones=False, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
              bake_space_transform=False, bake_anim=False)
    if ue:
        kw.update(axis_forward='-Y', axis_up='Z', path_mode='STRIP')
    else:
        kw.update(axis_forward='-Z', axis_up='Y', path_mode='STRIP', embed_textures=False)
    bpy.ops.export_scene.fbx(**kw)


# ============================================================================ SOLDADOS
def K(n):
    return dict(cell=CI[n])


def soldier(kind):
    b = B()
    enemy = kind == 'Enemigo'
    medic = kind == 'Medico'
    HAND = 'skin_dark' if enemy else 'glove'
    # --- torso (lofts elipticos)
    b.loft([(0.84, .150, .095, 0, 0), (0.93, .165, .105, 0, 0), (1.02, .152, .097, 0, 0)], 16, **K('uniform_dark'))
    b.loft([(1.00, .152, .096, 0, 0), (1.12, .146, .092, 0, 0), (1.24, .166, .105, 0, 0)], 16, **K('uniform'))
    b.loft([(1.22, .166, .105, 0, 0), (1.34, .186, .116, 0, 0), (1.46, .176, .108, 0, 0), (1.50, .075, .065, 0, 0)], 16, **K('uniform'))
    # --- piernas
    for sx in (-1, 1):
        hip = (.085 * sx, 0, .93); knee = (.115 * sx, -.005, .50); ank = (.14 * sx, .005, .095)
        b.tube(hip, knee, [(0, .092), (.5, .078), (1, .062)], 12, **K('uniform'))
        b.sph(.064, knee, **K('uniform'))
        b.tube(knee, ank, [(0, .060), (.4, .058), (1, .044)], 12, **K('uniform'))
        b.tube((ank[0], ank[1], .20), (ank[0], ank[1], .06), [(0, .052), (1, .060)], 12, **K('boots'))
        b.sph((.054, .135, .046), (ank[0], -.045, .052), seg=(12, 8), **K('boots'))
        b.box((.114, .288, .024), (ank[0], -.045, .012), bevel=.009, **K('sole'))
        b.box((.12, .055, .12), (knee[0], knee[1] - .062, .50), bevel=.02, **K('vest' if not enemy else 'pouch'))
        b.box((.036, .09, .13), (.19 * sx, 0, .74), bevel=.008, **K('pouch'))
    if not enemy:
        b.box((.03, .06, .16), (-.195, 0, .80), bevel=.006, **K('holster'))
        b.box((.026, .05, .03), (-.195, .012, .895), **K('metal'))
    # --- brazos (T-pose, horizontales)
    for sx in (-1, 1):
        sh = (.19 * sx, 0, 1.44); el = (.50 * sx, 0, 1.44); wr = (.76 * sx, 0, 1.44)
        b.sph(.064, sh, **K('uniform'))
        b.tube(sh, el, [(0, .060), (1, .050)], 12, **K('uniform'))
        b.sph(.05, el, **K('uniform'))
        b.tube(el, wr, [(0, .048), (1, .037)], 12, **K('uniform'))
        b.tube((.335 * sx, 0, 1.44), (.395 * sx, 0, 1.44), [(0, .0665), (1, .0665)], 14, **K('accent'))
        b.tube((.585 * sx, 0, 1.44), (.74 * sx, 0, 1.44), [(0, .045), (1, .040)], 12, **K('skin'))
        b.box((.095, .082, .030), (.808 * sx, 0, 1.44), bevel=.007, **K(HAND))
        for (yo, ln) in ((-.027, .074), (-.009, .084), (.009, .078), (.027, .062)):
            b.box((ln, .0165, .021), (sx * (.8555 + ln / 2), yo, 1.44), bevel=.004, **K(HAND))
        th = math.atan2(-math.sin(math.radians(38)), sx * math.cos(math.radians(38)))
        b.box((.062, .019, .022), (.790 * sx + math.cos(th) * .03, -.048 + math.sin(th) * .03, 1.435), (0, 0, th), bevel=.004, **K(HAND))
    # --- cuello y cabeza
    b.tube((0, .01, 1.50), (0, .005, 1.60), [(0, .054), (1, .048)], 12, **K('skin' if not enemy else 'mask'))
    b.sph((.082, .098, .108), (0, 0, 1.665), seg=(16, 12), **K('skin' if not enemy else 'mask'))
    b.sph((.071, .086, .066), (0, -.012, 1.600), seg=(14, 10), **K('skin' if not enemy else 'mask'))
    b.sph((.014, .021, .022), (0, -.104, 1.648), **K('skin_dark' if not enemy else 'mask'))
    for sx in (-1, 1):
        b.sph((.012, .02, .03), (.086 * sx, .005, 1.66), **K('skin_dark' if not enemy else 'mask'))
        b.sph((.011, .007, .011), (.033 * sx, -.094, 1.676), **K('frame'))
    if enemy:
        b.box((.150, .014, .030), (0, -.092, 1.676), bevel=.006, **K('skin'))
        b.sph((.012, .006, .011), (-.033, -.1, 1.676), **K('frame')); b.sph((.012, .006, .011), (.033, -.1, 1.676), **K('frame'))
    # casco
    if not enemy:
        b.dome((0, .012, 1.69), .118, .136, .110, 7, 24,
               fcell=lambda c: CI['accent'] if (abs(c.x) < .019 and c.z > 1.70) else CI['helmet'])
        b.loft([(1.676, .124, .142, 0, .012), (1.692, .119, .137, 0, .012)], 24, **K('helmet'))
        for sx in (-1, 1):
            b.box((.062, .024, .036), (.040 * sx, -.140, 1.712), bevel=.007, **K('lens'))
            b.box((.076, .016, .046), (.040 * sx, -.134, 1.712), bevel=.007, **K('frame'))
            b.box((.012, .012, .07), (.098 * sx, -.02, 1.625), **K('strap'))
        b.box((.048, .03, .04), (0, -.142, 1.768), bevel=.006, **K('metal'))
        b.ring(1.705, 1.722, .123, .141, 24, cy=.012, **K('strap'))
    else:
        b.dome((0, .012, 1.672), .126, .144, .124, 7, 24,
               fcell=lambda c: CI['helmet'])
        b.loft([(1.664, .131, .150, 0, .012), (1.682, .127, .146, 0, .012)], 24, **K('helmet'))
        b.ring(1.700, 1.724, .1262, .1442, 24, cy=.012, **K('accent'))
        for sx in (-1, 1):
            b.box((.012, .012, .07), (.105 * sx, -.02, 1.62), **K('strap'))
    # --- equipo
    if not enemy:
        b.box((.285, .062, .335), (0, -.142, 1.31), bevel=.014, **K('vest'))
        b.box((.22, .016, .262), (0, -.178, 1.32), bevel=.006, **K('plate'))
        b.box((.285, .062, .335), (0, .142, 1.31), bevel=.014, **K('vest'))
        for sx in (-1, 1):
            b.box((.072, .24, .024), (.118 * sx, 0, 1.488), (0, 0, 0), bevel=.008, **K('vest'))
            b.box((.10, .15, .03), (.165 * sx, 0, 1.497), bevel=.01, **K('vest'))
        b.loft([(1.06, .172, .108, 0, 0), (1.19, .175, .111, 0, 0)], 16, **K('vest'))
        for x in (-.085, 0, .085):
            b.box((.072, .046, .11), (x, -.138, 1.13), bevel=.009, **K('pouch'))
    else:
        b.box((.345, .07, .22), (0, -.145, 1.27), bevel=.012, **K('vest'))
        for x in (-.12, -.04, .04, .12):
            b.box((.065, .04, .10), (x, -.19, 1.27), bevel=.008, **K('pouch'))
        for sx in (-1, 1):
            b.box((.07, .16, .03), (.165 * sx, 0, 1.495), bevel=.01, **K('vest'))
        b.loft([(1.06, .170, .107, 0, 0), (1.17, .172, .109, 0, 0)], 16, **K('belt'))
    b.loft([(1.00, .158, .101, 0, 0), (1.045, .158, .101, 0, 0)], 16, **K('belt'))
    b.box((.04, .012, .036), (0, -.104, 1.023), **K('metal'))
    # mochila
    if medic:
        b.box((.36, .18, .42), (0, .21, 1.285), bevel=.035, **K('pack'))
        b.box((.36, .185, .06), (0, .212, 1.49), bevel=.02, **K('accent'))
        b.box((.25, .012, .25), (0, .306, 1.30), **K('cross_white'))
        b.box((.17, .014, .05), (0, .312, 1.30), **K('cross_red')); b.box((.05, .014, .17), (0, .312, 1.30), **K('cross_red'))
        b.box((.075, .012, .075), (-.09, -.18, 1.40), **K('cross_white'))
        b.box((.05, .014, .016), (-.09, -.186, 1.40), **K('cross_red')); b.box((.016, .014, .05), (-.09, -.186, 1.40), **K('cross_red'))
    elif enemy:
        b.box((.27, .13, .30), (0, .20, 1.26), bevel=.03, **K('pack'))
        b.cyl(.07, .07, .34, (0, .20, 1.46), (0, math.pi / 2, 0), 12, **K('cloth'))
        b.box((.27, .134, .028), (0, .20, 1.415), bevel=.008, **K('accent'))
    else:
        b.box((.30, .15, .36), (0, .20, 1.27), bevel=.03, **K('pack'))
        b.box((.30, .156, .075), (0, .203, 1.475), bevel=.02, **K('accent'))
        for sx in (-1, 1):
            b.box((.07, .12, .20), (.18 * sx, .20, 1.21), bevel=.012, **K('pouch'))
        b.box((.055, .04, .13), (.12, .285, 1.40), bevel=.006, **K('metal'))
        b.tube((.12, .285, 1.465), (.12, .29, 1.70), [(0, .0045), (1, .003)], 6, **K('strap'))
    ob = b.finish('SK_Soldado_' + kind, [SOLD['Alpha' if kind == 'Aliado' else kind]['exp']])
    return ob


# ============================================================================ ARMAS
def KW(n):
    return dict(cell=WCI[n])


def rifle():
    b = B()
    b.box((.042, .15, .075), (0, -.03, 0), bevel=.005, **KW('gunmetal'))
    b.box((.045, .25, .055), (0, -.10, .062), bevel=.005, **KW('gunmetal'))
    b.box((.024, .34, .013), (0, -.15, .0985), **KW('sight'))
    b.box((.02, .025, .035), (0, .02, .112), **KW('sight'))
    b.box((.012, .014, .045), (0, -.52, .105), **KW('sight'))
    b.cyl(.0285, .0285, .30, (0, -.35, .058), (math.pi / 2, 0, 0), 14, **KW('poly_tan'))
    b.cyl(.009, .009, .20, (0, -.60, .058), (math.pi / 2, 0, 0), 10, **KW('steel'))
    b.cyl(.015, .015, .07, (0, -.715, .058), (math.pi / 2, 0, 0), 10, **KW('gunmetal'))
    b.box((.03, .055, .14), (0, -.065, -.10), (math.radians(-8), 0, 0), bevel=.006, **KW('poly_black'))
    b.box((.034, .052, .115), (0, .035, -.07), (math.radians(18), 0, 0), bevel=.008, **KW('poly_black'))
    b.box((.011, .075, .012), (0, -.005, -.04), **KW('gunmetal'))
    b.cyl(.022, .022, .20, (0, .17, .055), (math.pi / 2, 0, 0), 12, **KW('poly_black'))
    b.box((.046, .15, .105), (0, .275, .02), (math.radians(-6), 0, 0), bevel=.01, **KW('poly_black'))
    b.box((.012, .09, .06), (0, .35, .0), bevel=.004, **KW('rubber'))
    b.box((.034, .07, .028), (0, -.13, .105), bevel=.004, **KW('gunmetal'))
    b.cyl(.021, .021, .13, (0, -.13, .14), (math.pi / 2, 0, 0), 12, **KW('poly_black'))
    b.cyl(.0185, .0185, .006, (0, -.197, .14), (math.pi / 2, 0, 0), 12, **KW('lens'))
    b.cyl(.0185, .0185, .006, (0, -.063, .14), (math.pi / 2, 0, 0), 12, **KW('lens'))
    b.box((.006, .035, .02), (.0235, -.05, .068), **KW('brass'))
    b.box((.01, .045, .02), (-.0235, -.12, .062), **KW('accent_o'))
    for v in b.bm.verts:
        v.co *= 0.80
    return b.finish('SM_Rifle_Asalto', [WEAP['exp']], 35)


def pistol():
    b = B()
    b.box((.03, .17, .036), (0, -.07, .045), bevel=.004, **KW('gunmetal'))
    b.box((.028, .15, .03), (0, -.05, .005), bevel=.004, **KW('poly_black'))
    b.box((.032, .046, .098), (0, .018, -.045), (math.radians(14), 0, 0), bevel=.007, **KW('poly_black'))
    b.box((.01, .06, .012), (0, -.03, -.022), **KW('poly_black'))
    b.cyl(.007, .007, .03, (0, -.163, .045), (math.pi / 2, 0, 0), 8, **KW('steel'))
    b.box((.008, .012, .014), (0, .01, .07), **KW('sight')); b.box((.006, .01, .012), (0, -.15, .07), **KW('sight'))
    return b.finish('SM_Pistola', [WEAP['exp']], 35)


# ============================================================================ BUNKER
def concrete(): return dict(mat=0, box=2.0)
def metalk(): return dict(mat=1, box=1.0)


def bunker(state):
    b = B(); rnd = random.Random(11)
    C = dict(mat=0, box=2.0); M = dict(mat=1, box=1.0)
    zb = .4
    b.box((9.0, 7.0, .4), (0, 0, .2), bevel=.04, **C)
    if state == 'Destruido':
        for (x, y, w, d, h) in [(0, 2.95, 8.0, .7, .9), (-3.65, 0.0, .7, 5.2, 1.3), (3.65, 1.6, .7, 2.0, .6), (-3.15, -2.95, 1.7, .7, 1.2),
                                (3.15, -2.95, 1.7, .7, .5), (0, -2.95, 2.6, .7, .45)]:
            b.box((w, d, h), (x, y, zb + h / 2), (0, 0, rnd.uniform(-.04, .04)), bevel=.03, **C)
        for i in range(10):
            w, d, h = rnd.uniform(.4, 1.1), rnd.uniform(.3, .8), rnd.uniform(.3, .9)
            b.box((w, d, h), (rnd.uniform(-3.8, 3.8), rnd.uniform(-3, 3), zb + h / 2), (rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), rnd.uniform(0, 6)), bevel=.03, **C)
        b.box((8.2, 6.4, .4), (.4, -.3, zb + .85), (math.radians(14), math.radians(-9), math.radians(8)), bevel=.04, **C)
        for i in range(34):
            s = rnd.uniform(.15, .5)
            b.box((s, s * rnd.uniform(.6, 1.3), s * rnd.uniform(.5, 1)), (rnd.uniform(-4.6, 4.6), rnd.uniform(-4, 4), zb + s * .3 + (0 if abs(i) % 3 else .15)),
                  (rnd.uniform(-.7, .7), rnd.uniform(-.7, .7), rnd.uniform(0, 6)), bevel=.02, **C)
        for i in range(9):
            x, y = rnd.uniform(-3.5, 3.5), rnd.uniform(-2.8, 2.8)
            b.tube((x, y, zb + .5), (x + rnd.uniform(-.4, .4), y + rnd.uniform(-.4, .4), zb + rnd.uniform(1.0, 1.7)), [(0, .014), (1, .014)], 6, **M)
        ucx = [ucx_box('SM_Bunker_Enemigo_Destruido', 0, (9.0, 7.0, 1.4), (0, 0, .7))]
        return b.finish('SM_Bunker_Enemigo_Destruido', [TILE['Concreto']['exp'], TILE['Metal']['exp']], 50), ucx
    dam = state == 'Danado'
    b.box((8.0, .7, 2.8), (0, 2.95, zb + 1.4), bevel=.03, **C)
    b.box((.7, 5.2, 2.8), (-3.65, 0, zb + 1.4), bevel=.03, **C)
    b.box((.7, 2.0, 2.8), (3.65, -1.6, zb + 1.4), bevel=.03, **C)
    b.box((.7, 2.0, 2.8), (3.65, 1.6, zb + 1.4), bevel=.03, **C)
    b.box((.7, 1.2, .9), (3.65, 0, zb + 2.35), bevel=.03, **C)
    b.box((.12, 1.2, 1.9), (3.55, 0, zb + .95), **M)
    b.box((.2, .12, .12), (3.46, .45, zb + .95), **M)
    b.box((8.0, .7, 1.0), (0, -2.95, zb + .5), bevel=.03, **C)
    for (x, w) in ((-3.15, 1.7), (0, 1.8), (3.15, 1.7)):
        b.box((w, .7, .45), (x, -2.95, zb + 1.225), bevel=.02, **C)
    if not dam:
        b.box((8.0, .7, 1.35), (0, -2.95, zb + 2.125), bevel=.03, **C)
    else:
        b.box((4.6, .7, 1.35), (-1.7, -2.95, zb + 2.125), bevel=.03, **C)
        b.box((1.5, .7, .6), (3.2, -2.95, zb + 1.8), (0, 0, 0), bevel=.03, **C)
    if not dam:
        b.box((9.0, 7.2, .4), (0, 0, zb + 3.0), bevel=.04, **C)
        b.box((9.0, .25, .3), (0, -3.5, zb + 3.35), bevel=.03, **C)
    else:
        b.box((4.6, 7.2, .4), (-2.2, 0, zb + 3.0), bevel=.04, **C)
        b.box((4.6, 7.0, .4), (2.6, 0, zb + 2.55), (math.radians(4), math.radians(15), 0), bevel=.04, **C)
        b.box((4.4, .25, .3), (-2.3, -3.5, zb + 3.35), bevel=.03, **C)
        for i in range(16):
            s = rnd.uniform(.15, .55)
            b.box((s, s * rnd.uniform(.6, 1.3), s * rnd.uniform(.5, 1)), (rnd.uniform(2.5, 5.2), rnd.uniform(-4.2, -2.2), zb + s * .4),
                  (rnd.uniform(-.6, .6), rnd.uniform(-.6, .6), rnd.uniform(0, 6)), bevel=.02, **C)
        for i in range(6):
            x, y = rnd.uniform(2.0, 3.8), rnd.uniform(-3.3, -2.7)
            b.tube((x, y, zb + 2.5), (x + rnd.uniform(-.3, .3), y - rnd.uniform(.2, .5), zb + rnd.uniform(3.0, 3.5)), [(0, .015), (1, .015)], 6, **M)
    b.box((1.0, 1.0, .14), (-2.2, 1.6, zb + 3.27), **M)
    b.cyl(.16, .16, .45, (2.6, 1.8, zb + 3.4), seg=10, **M)
    b.cyl(.16, .16, .45, (1.9, 1.8, zb + 3.4), seg=10, **M)
    b.tube((-3.4, 2.8, zb + 3.2), (-3.4, 2.8, zb + 5.6), [(0, .035), (1, .025)], 8, **M)
    b.box((.6, 1.2, 2.2), (-4.3, 2.7, zb + 1.1), bevel=.03, **C)
    b.box((.6, 1.2, 2.2), (4.3, 2.7, zb + 1.1), bevel=.03, **C)
    b.box((.5, 2.8, 2.4), (5.3, 0, zb + 1.2), bevel=.03, **C)
    b.box((1.6, 1.8, .16), (4.6, 0, .08), bevel=.02, **C)
    name = 'SM_Bunker_Enemigo_' + state
    ucx = [ucx_box(name, 0, (9.0, 7.0, 3.8 if not dam else 3.3), (0, 0, 1.9 if not dam else 1.65)), ucx_box(name, 1, (.5, 2.8, 2.8), (5.3, 0, 1.4))]
    return b.finish(name, [TILE['Concreto']['exp'], TILE['Metal']['exp']], 50), ucx


# ============================================================================ TRINCHERA
def trench(kind):
    b = B(); T = dict(mat=0, box=2.0)
    prof = [(1.0, .15), (1.0, 1.65), (1.5, 1.72), (2.4, .15)]

    def wall(axis, side, s0, s1):
        pts = [(side * o, z) for o, z in prof]
        if side < 0:
            pts = pts[::-1]
        b.prism(pts, s0, s1, axis, **T)
    b.box((4.0, 4.8, .15), (0, 0, .075), **T) if kind != 'Esquina' else b.box((4.0, 4.0, .15), (0, 0, .075), **T)
    if kind == 'Recta':
        wall('x', 1, -2, 2); wall('x', -1, -2, 2)
        b.box((4.0, .5, .4), (0, -.75, .35), bevel=.03, **T)
        ucx = [ucx_box('SM_Trinchera_Recta_4m', 0, (4.0, 1.4, 1.7), (0, 1.7, .85)), ucx_box('SM_Trinchera_Recta_4m', 1, (4.0, 1.4, 1.7), (0, -1.7, .85)),
               ucx_box('SM_Trinchera_Recta_4m', 2, (4.0, 3.0, .15), (0, 0, .075))]
        nm = 'SM_Trinchera_Recta_4m'
    elif kind == 'Esquina':
        wall('x', -1, -2, 2.4)      # exterior norte
        wall('y', 1, -2.4, 2)       # exterior este
        wall('x', 1, -2, -1.0)      # interior sur
        wall('y', -1, 1.0, 2)       # interior oeste
        ucx = [ucx_box('SM_Trinchera_Esquina', 0, (4.4, 1.4, 1.7), (.2, -1.7, .85)), ucx_box('SM_Trinchera_Esquina', 1, (1.4, 4.4, 1.7), (1.7, -.2, .85)),
               ucx_box('SM_Trinchera_Esquina', 2, (1.4, 1.4, 1.7), (-1.7, 1.7, .85)), ucx_box('SM_Trinchera_Esquina', 3, (4.0, 4.0, .15), (0, 0, .075))]
        nm = 'SM_Trinchera_Esquina'
    else:
        wall('x', 1, -2, 2); wall('x', -1, -2, 2)
        b.box((.9, 4.8, 1.55), (1.55, 0, .925), bevel=.04, **T)
        ucx = [ucx_box('SM_Trinchera_Final', 0, (4.0, 1.4, 1.7), (0, 1.7, .85)), ucx_box('SM_Trinchera_Final', 1, (4.0, 1.4, 1.7), (0, -1.7, .85)),
               ucx_box('SM_Trinchera_Final', 2, (.9, 4.8, 1.7), (1.55, 0, .85)), ucx_box('SM_Trinchera_Final', 3, (4.0, 3.0, .15), (0, 0, .075))]
        nm = 'SM_Trinchera_Final'
    rnd = random.Random(3)
    for v in b.bm.verts:   # irregularidad de la tierra (sin tocar los bordes de union)
        if abs(v.co.x) < 1.95 and abs(v.co.y) < 1.95 and v.co.z > .3:
            v.co += Vector((rnd.uniform(-.03, .03), rnd.uniform(-.03, .03), rnd.uniform(-.03, .03)))
    return b.finish(nm, [TILE['Tierra']['exp']], 55), ucx


# ============================================================================ SACOS
def sandbag(b, loc, rz, rng, sz=(.50, .30, .16)):
    bmesh.ops.create_uvsphere(b.bm, u_segments=10, v_segments=7, radius=1.0)
    vs = list({v for f in b.newf() for v in f.verts})
    sc = (sz[0] * rng.uniform(.95, 1.06) / 2, sz[1] * rng.uniform(.95, 1.06) / 2, sz[2] * rng.uniform(.92, 1.08) / 2)
    R = Euler((rng.uniform(-.04, .04), rng.uniform(-.04, .04), rz)).to_matrix()
    for v in vs:
        p = v.co
        q = Vector([math.copysign(abs(c) ** .62, c) for c in p])
        q.z *= 1.0 - .22 * (abs(q.x) ** 2)           # extremos mas planos
        q = Vector((q.x * sc[0], q.y * sc[1], q.z * sc[2]))
        v.co = R @ q + Vector(loc)
    b._e(mat=0, box=.8)


def sandwall(name, rows, length=2.0, corner=False):
    b = B(); rng = random.Random(21 + rows)
    sz = (.50, .30, .17)

    def row(k, axis_y=False):
        if axis_y:
            off = .25 if k % 2 else 0
            for i in range(3):
                sandbag(b, (.78, .42 + i * .5 + off, .085 + k * .155), math.pi / 2 + rng.uniform(-.06, .06), rng, sz)
            return
        n = int(length / .5)
        off = 0 if k % 2 == 0 else .25
        for i in range(n + (1 if off else 0)):
            x = -length / 2 + .25 + i * .5 - (.25 if off else 0) + (off if False else 0)
            if off:
                x = -length / 2 + i * .5
                if i == 0 or i == n:
                    continue
            if axis_y:
                sandbag(b, (0, x, .085 + k * .155), math.pi / 2 + rng.uniform(-.06, .06), rng, sz)
            else:
                sandbag(b, (x, 0, .085 + k * .155), rng.uniform(-.06, .06), rng, sz)
    for k in range(rows):
        row(k)
    nm = name
    hh = .17 + (rows - 1) * .155
    if not corner:
        ucx = [ucx_box(nm, 0, (length + .05, .34, hh), (0, 0, hh / 2))]
    else:
        for k in range(rows):
            row(k, True)
        ucx = [ucx_box(nm, 0, (length + .05, .34, hh), (0, 0, hh / 2)),
               ucx_box(nm, 1, (.34, 1.75, hh), (.78, 1.3, hh / 2))]
    return b.finish(nm, [TILE['Saco']['exp']], 60), ucx


def single_sandbag():
    b = B(); sandbag(b, (0, 0, .085), 0, random.Random(5), (.50, .30, .17))
    ob = b.finish('SM_Saco_Arena', [TILE['Saco']['exp']], 60)
    return ob, [ucx_box('SM_Saco_Arena', 0, (.5, .3, .17), (0, 0, .085))]


# ============================================================================ ROCAS
def rock(name, seed, size, rough=.5, nplanes=7, flat=.35, sub=4, hullpts=22):
    rng = random.Random(seed)
    b = B(); bm = b.bm; bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    off = Vector((rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(0, 100)))
    planes = [(Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, .7))).normalized(), rng.uniform(.6, .82)) for _ in range(nplanes)]
    for v in bm.verts:
        p = v.co.copy()
        p *= 1 + rough * noise.fractal(p * 1.5 + off, 1.0, 2.1, 5)
        for (nn, dd) in planes:
            ex = p.dot(nn) - dd
            if ex > 0:
                p -= nn * ex
        v.co = Vector((p.x * size[0] / 2, p.y * size[1] / 2, p.z * size[2] / 2))
    zlim = -.35 * size[2] / 2 * (flat / .35)
    for v in bm.verts:
        if v.co.z < zlim:
            v.co.z = zlim
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    b._e(mat=0, box=2.2)
    pts = [v.co.copy() for v in b.bm.verts]
    sel = [max(pts, key=lambda p: p.z)]
    while len(sel) < hullpts:
        sel.append(max(pts, key=lambda p: min((p - q).length for q in sel)))
    ob = b.finish(name, [TILE['Roca']['exp']], 55)
    return ob, [ucx_hull(name, 0, [tuple(p) for p in sel])]


# ============================================================================ CONSTRUCCION Y EXPORTACION
UE = os.path.join(OUT, 'Models', 'UE5_StaticMeshes')
MX_DIR = os.path.join(OUT, 'Models', 'Mixamo_Upload')
for d_ in (UE, MX_DIR):
    os.makedirs(d_, exist_ok=True)

# soldados -> Mixamo (T-pose)
for kind, tex in (('Aliado', 'Alpha'), ('Medico', 'Medico'), ('Enemigo', 'Enemigo')):
    ob = soldier(kind)
    reg(ob, [], 'Soldado', None)
    if kind == 'Aliado':
        SOLDOBJ = ob
    ALL[ob.name] = (ob, [], 'Soldado', tex)
    fb = os.path.join(MX_DIR, ob.name, ob.name + '_TPose.fbx')
    os.makedirs(os.path.dirname(fb), exist_ok=True)
    # el export usa la paleta correspondiente
    ob.data.materials[0] = SOLD[tex]['exp']
    export(ob, [], fb, ue=False)
    zp = os.path.join(MX_DIR, ob.name + '_Mixamo.zip')
    texsrc = os.path.join(TEX, 'Soldado', f'T_Soldado_{tex}_BC.png')
    shutil.copy(texsrc, os.path.join(os.path.dirname(fb), os.path.basename(texsrc)))
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(fb, os.path.basename(fb))
        z.write(texsrc, os.path.basename(texsrc))
    ob.data.materials[0] = SOLD[tex]['prv']

# armas, bunker, trinchera, sacos, rocas -> UE5
items = []
for fn in (rifle, pistol):
    ob = fn(); items.append((ob, [], 'Arma', WEAP))
for st in ('Intacto', 'Danado', 'Destruido'):
    ob, u = bunker(st); items.append((ob, u, 'Bunker', None))
for k in ('Recta', 'Esquina', 'Final'):
    ob, u = trench(k); items.append((ob, u, 'Trinchera', None))
ob, u = single_sandbag(); items.append((ob, u, 'Sacos', None))
ob, u = sandwall('SM_Sacos_Muro_2m_Bajo', 3); items.append((ob, u, 'Sacos', None))
ob, u = sandwall('SM_Sacos_Muro_2m_Alto', 5); items.append((ob, u, 'Sacos', None))
ob, u = sandwall('SM_Sacos_Esquina_Bajo', 3, 2.0, True); items.append((ob, u, 'Sacos', None))
for (nm, seed, size, rough) in (('SM_Rocas_PuertaNorte_01', 4, (6.0, 5.0, 6.5), .45), ('SM_Rocas_PuertaNorte_02', 9, (5.0, 7.0, 4.5), .5),
                                ('SM_Rocas_PuertaNorte_03', 14, (4.0, 3.5, 3.0), .5), ('SM_Rocas_PuertaNorte_Muro', 17, (13.0, 4.0, 5.5), .55)):
    ob, u = rock(nm, seed, size, rough); items.append((ob, u, 'Roca', None))
for ob, u, g, _ in items:
    reg(ob, u, g, None)
    export(ob, u, os.path.join(UE, ob.name + '.fbx'), ue=True)

# materiales de previsualizacion
PRV = {'Concreto': TILE['Concreto']['prv'], 'Metal': TILE['Metal']['prv']}
for name, (ob, ucx, g, tex) in ALL.items():
    if g == 'Bunker':
        ob.data.materials[0] = TILE['Concreto']['prv']; ob.data.materials[1] = TILE['Metal']['prv']
    elif g == 'Trinchera':
        ob.data.materials[0] = TILE['Tierra']['prv']
    elif g == 'Sacos':
        ob.data.materials[0] = TILE['Saco']['prv']
    elif g == 'Roca':
        ob.data.materials[0] = TILE['Roca']['prv']
    elif g == 'Arma':
        ob.data.materials[0] = WEAP['prv']
    for u in ucx:
        bpy.data.objects.remove(u, do_unlink=True)

# estadisticas
os.makedirs(os.path.join(OUT, 'Docs'), exist_ok=True)
with open(os.path.join(OUT, 'Docs', 'Estadisticas_Modelos.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['Asset', 'Grupo', 'Triangulos', 'Vertices', 'Ancho_m(X)', 'Largo_m(Y)', 'Alto_m(Z)'])
    w.writerows(STATS)
for s_ in STATS:
    print(s_)

if os.environ.get('NOPREV'):
    sys.exit(0)
# ============================================================================ PREVIEWS
def place(name, x, y, z=0, rz=0, mat=None):
    ob = ALL[name][0]; ob.location = (x, y, z); ob.rotation_euler = (0, 0, rz)
    if mat:
        ob.data.materials[0] = mat
    return ob


# copias de soldados con otras paletas
def dup(name, newname, variant, x, y):
    src = ALL[name][0]
    ob = src.copy(); ob.data = src.data.copy(); ob.name = newname
    scene.collection.objects.link(ob); ob.data.materials[0] = SOLD[variant]['prv']; ob.location = (x, y, 0); return ob


place('SK_Soldado_Aliado', -3.0, 0); place('SK_Soldado_Medico', 0.0, 0); place('SK_Soldado_Enemigo', 3.0, 0)
dup('SK_Soldado_Aliado', 'prv_bravo', 'Bravo', -1.5, 0)
for nme, v in (('SK_Soldado_Aliado', 'Alpha'), ('SK_Soldado_Medico', 'Medico'), ('SK_Soldado_Enemigo', 'Enemigo')):
    ALL[nme][0].data.materials[0] = SOLD[v]['prv']
place('SM_Rifle_Asalto', 0, 14, 0, 0); ALL['SM_Rifle_Asalto'][0].location = (-2.2, 14, .5); ALL['SM_Rifle_Asalto'][0].rotation_euler = (0, 0, math.radians(90))
place('SM_Pistola', -1.2, 14, .5, math.radians(90))
place('SM_Saco_Arena', 0.0, 14); place('SM_Sacos_Muro_2m_Bajo', 1.6, 14); place('SM_Sacos_Muro_2m_Alto', 4.2, 14); place('SM_Sacos_Esquina_Bajo', 7.2, 14)
place('SM_Trinchera_Recta_4m', 3.0, 19, 0, 0); place('SM_Trinchera_Esquina', 8.5, 19); place('SM_Trinchera_Final', 14, 19)
place('SM_Bunker_Enemigo_Intacto', 0, 52); place('SM_Bunker_Enemigo_Danado', 16, 52); place('SM_Bunker_Enemigo_Destruido', 32, 52)
for i, nme in enumerate(('SM_Rocas_PuertaNorte_01', 'SM_Rocas_PuertaNorte_02', 'SM_Rocas_PuertaNorte_03', 'SM_Rocas_PuertaNorte_Muro')):
    place(nme, -14 + i * 12 + (4 if i == 3 else 0), 90)

# suelo, luz, camara
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=160, matrix=Matrix.Translation((10, 50, -.01)))
gme = bpy.data.meshes.new('ground'); bm.to_mesh(gme); bm.free()
gob = bpy.data.objects.new('ground', gme); scene.collection.objects.link(gob)
gm = bpy.data.materials.new('prv_ground'); gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.20, .22, .14, 1); gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
gme.materials.append(gm)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
sun.data.energy = 4.0; sun.data.angle = math.radians(5); sun.rotation_euler = (math.radians(50), 0, math.radians(35))
wd = bpy.data.worlds.new('w'); wd.use_nodes = True; scene.world = wd
bgn = wd.node_tree.nodes['Background']; bgn.inputs['Color'].default_value = (.55, .65, .80, 1); bgn.inputs['Strength'].default_value = 1.0
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 40
try:
    scene.cycles.use_denoising = True
except Exception:
    pass
scene.render.resolution_x = 1400; scene.render.resolution_y = 700; scene.cycles.samples = 32


def shot(name, loc, target, lens=50):
    cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(PREV, name)
    bpy.ops.render.render(write_still=True)


shot('prev_soldados.png', (0, -8.8, 1.1), (0, 0, .95), 40)
shot('prev_soldados_3q.png', (4.5, -5.5, 2.0), (0, 0, 1.0), 45)
shot('prev_props.png', (3.5, 5.0, 4.5), (3.6, 14.6, .3), 40)
shot('prev_trinchera.png', (8.5, 6.0, 15.0), (8.5, 19.0, .5), 34)
shot('prev_bunkers.png', (14, 20, 11), (16, 52, 1.5), 40)
shot('prev_rocas.png', (0, 62, 14), (0, 90, 2.5), 38)
print('previews OK')
