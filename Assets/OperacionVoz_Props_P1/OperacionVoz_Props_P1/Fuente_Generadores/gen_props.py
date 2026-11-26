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



# ============================================================================ PROPS
PN = ['olive', 'olive_dark', 'tan', 'metal_dark', 'metal_light', 'rubber', 'led_green', 'led_red', 'led_amber', 'stencil_yellow',
      'stencil_white', 'rust', 'wood', 'canvas', 'canvas_dark', 'black', 'screen_dark', 'key_gray', 'copper', 'red', 'glass']
def K(n): return dict(cell=PN.index(n))
T_ = os.path.join(OUT, 'Textures')
M_PROPS = mat_bc('M_Props', os.path.join(T_, 'T_Props_BC.png'), True)
P_PROPS = mat_pbr('prv_Props', os.path.join(T_, 'T_Props_BC.png'), os.path.join(T_, 'T_Props_ORM.png'), None, True)
M_SCR = mat_bc('M_Terminal_Pantalla', os.path.join(T_, 'T_Terminal_Pantalla_Activa.png'))
# emisiva en la vista previa
def make_emissive(m, img_path, strength):
    nt = m.node_tree; bs = nt.nodes['Principled BSDF']; t = nt.nodes.new('ShaderNodeTexImage'); t.image = load_img(img_path)
    nt.links.new(t.outputs['Color'], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = strength
make_emissive(P_PROPS, os.path.join(T_, 'T_Props_E.png'), 4.0)
P_SCR = mat_bc('prv_Pantalla', os.path.join(T_, 'T_Terminal_Pantalla_Activa.png')); make_emissive(P_SCR, os.path.join(T_, 'T_Terminal_Pantalla_Activa.png'), 1.5)
P_SCR.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0, 0, 0, 1)


def quad(b, cx, cz, w, h, y, rot=(0, 0, 0), loc=(0, 0, 0), mat=1):
    """Plano con UV 0-1 (cara hacia -Y)."""
    bm = b.bm; M = MX(loc, rot)
    pts = [(-w / 2, y, -h / 2), (w / 2, y, -h / 2), (w / 2, y, h / 2), (-w / 2, y, h / 2)]
    vs = [bm.verts.new(M @ Vector(p)) for p in pts]
    f = bm.faces.new(vs); f[b.pid] = 1; f.material_index = mat
    for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[b.uv].uv = uv


def terminal():
    b = B(); P = K
    # mesa de campana
    b.box((1.0, .62, .04), (0, 0, .78), bevel=.008, **P('olive'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((.04, .04, .76), (sx * .46, sy * .27, .38), **P('metal_dark'))
    b.box((.92, .03, .03), (0, .27, .25), **P('metal_dark')); b.box((.92, .03, .03), (0, -.27, .25), **P('metal_dark'))
    b.box((.03, .5, .03), (.46, 0, .25), **P('metal_dark')); b.box((.03, .5, .03), (-.46, 0, .25), **P('metal_dark'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((.07, .07, .015), (sx * .46, sy * .27, .008), **P('rubber'))
    # bateria bajo la mesa
    b.box((.34, .22, .2), (-.18, 0, .12 + .03), bevel=.01, **P('olive_dark')); b.box((.2, .005, .06), (-.18, -.112, .15), **P('stencil_yellow'))
    b.box((.04, .04, .03), (-.27, 0, .27), **P('metal_light')); b.box((.04, .04, .03), (-.09, 0, .27), **P('metal_light'))
    # caja del terminal
    zt = .80; cx = -.12
    b.box((.54, .40, .075), (cx, 0, zt + .0375), bevel=.012, **P('olive_dark'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((.05, .05, .08), (cx + sx * .26, sy * .185, zt + .04), bevel=.006, **P('metal_dark'))
    b.box((.44, .22, .006), (cx, -.045, zt + .078), **P('black'))
    for r in range(4):
        for c in range(8):
            b.box((.04, .03, .008), (cx - .175 + c * .05, -.115 + r * .036, zt + .083), **P('key_gray'))
    b.box((.2, .03, .008), (cx, -.01, zt + .083), **P('key_gray')) if False else None
    b.box((.14, .075, .006), (cx, -.165, zt + .081), **P('black'))
    # tapa con pantalla
    tilt = math.radians(14); hy = .185; lh = .36
    lc = (cx, hy + math.sin(tilt) * lh / 2, zt + .075 + math.cos(tilt) * lh / 2)
    b.box((.54, .04, lh), lc, (-tilt, 0, 0), bevel=.01, **P('olive_dark'))
    fy = -.0215
    quad(b, 0, 0, .46, .288, fy, rot=(-tilt, 0, 0), loc=lc, mat=1)
    b.box((.5, .006, .035), (lc[0], lc[1] - .0195 - math.sin(tilt) * 0 - .0, lc[2] - lh / 2 + .02), (-tilt, 0, 0), **P('black')) if False else None
    for sx in (-1, 1):
        b.box((.045, .03, .045), (cx + sx * .22, hy + .01, zt + .095), bevel=.006, **P('metal_dark'))
    # luces de estado y boton de llamada
    for i, n in enumerate(('led_green', 'led_amber', 'led_red')):
        b.box((.022, .022, .014), (cx - .22 + i * .035, .0, zt + .082) if False else (.24 + i * .0, -.15 + i * .04, 0) if False else (cx + .2, -.155 + i * .034, zt + .083), **P(n))
    b.cyl(.04, .04, .03, (cx + .27 + .02, -.02, zt + .045), (0, math.radians(90), 0), seg=14, **P('metal_dark'))
    b.cyl(.026, .026, .02, (cx + .27 + .04, -.02, zt + .045), (0, math.radians(90), 0), seg=14, **P('led_red'))
    # antena y microfono
    b.tube((cx + .24, .16, zt + .06), (cx + .24, .2, zt + .72), [(0, .012), (1, .006)], 8, **P('metal_light'))
    b.sph(.012, (cx + .24, .2, zt + .72), seg=(8, 6), **P('led_amber'))
    b.box((.07, .05, .12), (.4, -.1, zt + .06), (0, 0, math.radians(8)), bevel=.012, **P('olive_dark'))   # microfono de mano
    b.tube((.4, -.1, zt + .12), (.37, -.04, zt + .13), [(0, .004), (1, .004)], 6, **P('rubber'))
    # cable
    b.tube((cx + .25, -.1, zt + .02), (.46, -.3, .55), [(0, .006), (1, .006)], 6, **P('rubber'))
    ob = b.finish('SM_Terminal_Refuerzos', [M_PROPS, M_SCR], 40)
    return ob, [ucx_box('SM_Terminal_Refuerzos', 0, (1.0, .62, .84), (0, 0, .42)), ucx_box('SM_Terminal_Refuerzos', 1, (.56, .3, .42), (cx, .08, 1.06))]


def crate(b, loc, rz=0.0, open_=False):
    P = K; r = (0, 0, rz); M = Matrix.Translation(Vector(loc)) @ Euler(r).to_matrix().to_4x4()
    def bx(size, l, mat, bevel=0.0):
        b.box(size, tuple(M @ Vector(l)), r, bevel=bevel, **P(mat))
    bx((.60, .30, .20), (0, 0, .10), 'olive_dark', .008)
    bx((.62, .32, .03), (0, 0, .205), 'olive_dark', .006)
    bx((.34, .12, .004), (0, 0, .222), 'stencil_yellow')
    for s in (-1, 1):
        bx((.03, .34, .06), (s * .22, 0, .12), 'metal_dark')
        bx((.10, .02, .04), (s * .1, -.165, .08), 'metal_dark')
        bx((.06, .012, .035), (s * .24, .155, .17), 'metal_light')


def cajas():
    b = B()
    crate(b, (-.31, -.17, 0.0)); crate(b, (.31, -.17, 0.0)); crate(b, (-.31, .17, .0 + .0)) if False else None
    crate(b, (0, .2, 0.0), math.radians(3)); crate(b, (-.30, -.17, .245), math.radians(-2)); crate(b, (.30, -.17, .245), math.radians(2))
    crate(b, (.0, .2, .245), math.radians(90)); crate(b, (0, -.17, .49), math.radians(6))
    ob = b.finish('SM_Cajas_Municion_Pila', [M_PROPS], 40)
    return ob, [ucx_box('SM_Cajas_Municion_Pila', 0, (1.25, .75, .70), (0, 0, .35))]


def barril():
    b = B(); P = K
    b.cyl(.29, .29, .86, (0, 0, .45), seg=18, **P('red'))
    b.cyl(.30, .30, .035, (0, 0, .22), seg=18, **P('red')); b.cyl(.30, .30, .035, (0, 0, .66), seg=18, **P('red'))
    b.cyl(.30, .30, .045, (0, 0, .03), seg=18, **P('olive_dark')); b.cyl(.30, .30, .045, (0, 0, .87), seg=18, **P('olive_dark'))
    b.cyl(.2915, .2915, .13, (0, 0, .44), seg=18, **P('stencil_white'))
    b.cyl(.04, .04, .03, (.1, .08, .895), seg=10, **P('metal_light')); b.cyl(.03, .03, .03, (-.12, -.06, .895), seg=10, **P('metal_dark'))
    ob = b.finish('SM_Barril_Combustible', [M_PROPS], 40)
    return ob, [ucx_box('SM_Barril_Combustible', 0, (.6, .6, .9), (0, 0, .45))]


def mastil():
    b = B(); P = K
    b.box((.7, .7, .06), (0, 0, .03), bevel=.01, **P('metal_dark'))
    b.tube((0, 0, .06), (0, 0, 5.0), [(0, .06), (.45, .05), (1, .035)], 10, **P('metal_light'))
    for z in (1.5, 3.0, 4.2):
        b.cyl(.065, .065, .06, (0, 0, z), seg=10, **P('metal_dark'))
    for z, L_ in ((3.9, 1.1), (4.5, .7)):
        b.tube((-L_ / 2, 0, z), (L_ / 2, 0, z), [(0, .016), (1, .016)], 8, **P('metal_light'))
    b.tube((0, 0, 5.0), (0, 0, 6.2), [(0, .012), (1, .004)], 8, **P('metal_light'))
    b.sph(.045, (0, 0, 6.2), seg=(8, 6), **P('led_red'))
    b.box((.5, .34, .34), (.65, .0, .17), bevel=.01, **P('olive_dark')); b.box((.3, .005, .1), (.65, -.172, .2), **P('stencil_yellow'))
    for i, c in enumerate(('led_green', 'led_amber', 'led_red')):
        b.box((.03, .02, .03), (.52 + i * .06, -.172, .3), **P(c))
    b.tube((.4, 0, .22), (.04, 0, .1), [(0, .012), (1, .012)], 6, **P('rubber'))
    for k in range(3):
        a = math.radians(90 + k * 120); ex, ey = 2.3 * math.cos(a), 2.3 * math.sin(a)
        b.tube((0, 0, 3.4), (ex, ey, .12), [(0, .007), (1, .007)], 5, **P('metal_dark'))
        b.box((.08, .08, .5), (ex, ey, .2), (0, math.radians(20), a), **P('metal_dark'))
    ob = b.finish('SM_Mastil_Radio', [M_PROPS], 40)
    return ob, [ucx_box('SM_Mastil_Radio', 0, (.7, .7, 5.0), (0, 0, 2.5)), ucx_box('SM_Mastil_Radio', 1, (.5, .34, .34), (.65, 0, .17))]


def tienda():
    b = B(); P = K
    b.prism([(-1.5, 0), (1.5, 0), (1.5, 1.0), (0, 2.15), (-1.5, 1.0)], -2.0, 2.0, 'x', **P('canvas'))
    b.box((.04, 1.1, 1.65), (2.012, 0, .83), **P('canvas_dark')); b.box((.03, .5, 1.45), (2.02, 0, .76), **P('black'))
    b.box((.03, .06, 1.7), (2.025, -.55, .85), **P('wood')); b.box((.03, .06, 1.7), (2.025, .55, .85), **P('wood'))
    b.tube((-2.25, 0, 2.15), (2.25, 0, 2.15), [(0, .025), (1, .025)], 8, **P('wood'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ex, ey = sx * 2.9, sy * 2.1
            b.tube((sx * 2.0, sy * 1.5, 1.0), (ex, ey, .05), [(0, .006), (1, .006)], 5, **P('tan'))
            b.box((.06, .06, .3), (ex, ey, .12), (0, 0, 0), **P('wood'))
    for sy in (-1, 1):
        b.box((4.04, .05, .05), (0, sy * 1.5, .03), **P('canvas_dark'))
    ob = b.finish('SM_Tienda_Militar', [M_PROPS], 40)
    return ob, [ucx_box('SM_Tienda_Militar', 0, (4.0, 3.0, 1.0), (0, 0, .5)), ucx_box('SM_Tienda_Militar', 1, (4.0, 1.9, 2.1), (0, 0, 1.05))]


def alambrada():
    b = B(); P = K; rnd = random.Random(2)
    for x in (-2.0, 0.0, 2.0):
        b.box((.08, .08, 1.15), (x, 0, .575), (0, 0, rnd.uniform(-.05, .05)), bevel=.006, **P('wood'))
        b.box((.12, .12, .02), (x, 0, .0), **P('rust'))
    for z in (.3, .62, .95):
        b.tube((-2.0, -.045, z), (2.0, -.045, z), [(0, .005), (1, .005)], 5, **P('metal_dark'))
        for k in range(15):
            x = -1.9 + k * .27 + rnd.uniform(-.03, .03)
            b.box((.035, .012, .012), (x, -.045, z), (0, 0, 0), **P('metal_dark')); b.box((.012, .012, .035), (x, -.045, z), **P('metal_dark'))
    b.tube((-2.0, -.045, .3), (0, -.045, .95), [(0, .004), (1, .004)], 4, **P('metal_dark'))
    b.tube((0, -.045, .3), (2.0, -.045, .95), [(0, .004), (1, .004)], 4, **P('metal_dark'))
    ob = b.finish('SM_Alambrada_4m', [M_PROPS], 40)
    return ob, [ucx_box('SM_Alambrada_4m', 0, (4.1, .14, 1.15), (0, 0, .575))]


# ============================================================================ EXPORTACION
UE = os.path.join(OUT, 'Models', 'UE5_StaticMeshes'); os.makedirs(UE, exist_ok=True)
items = [terminal(), cajas(), barril(), mastil(), tienda(), alambrada()]
for ob, u in items:
    reg(ob, u, 'Props', None); export(ob, u, os.path.join(UE, ob.name + '.fbx'), ue=True)
os.makedirs(os.path.join(OUT, 'Docs'), exist_ok=True)
with open(os.path.join(OUT, 'Docs', 'Estadisticas_Props.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['Asset', 'Grupo', 'Triangulos', 'Vertices', 'Ancho_m(X)', 'Largo_m(Y)', 'Alto_m(Z)']); w.writerows(STATS)
for s_ in STATS: print(s_)
for ob, u in items:
    ob.data.materials[0] = P_PROPS
    if len(ob.data.materials) > 1: ob.data.materials[1] = P_SCR
    for x in u: bpy.data.objects.remove(x, do_unlink=True)
if os.environ.get('NOPREV'): sys.exit(0)

pos = {'SM_Terminal_Refuerzos': (0, 0), 'SM_Cajas_Municion_Pila': (2.2, 0), 'SM_Barril_Combustible': (3.7, 0), 'SM_Mastil_Radio': (6.5, 0.5),
       'SM_Tienda_Militar': (6.0, 7.5), 'SM_Alambrada_4m': (-1.5, 4.0)}
for ob, u in items:
    ob.location = (*pos[ob.name], 0)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=80, matrix=Matrix.Translation((5, 4, -.001)))
gme = bpy.data.meshes.new('ground'); bm.to_mesh(gme); bm.free(); gob = bpy.data.objects.new('ground', gme); scene.collection.objects.link(gob)
gm = bpy.data.materials.new('g'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.20, .22, .14, 1); gme.materials.append(gm)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
sun.data.energy = 4.0; sun.data.angle = math.radians(5); sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
wd = bpy.data.worlds.new('w'); wd.use_nodes = True; scene.world = wd
wd.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .65, .80, 1)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 32
try: scene.cycles.use_denoising = True
except Exception: pass
scene.render.resolution_x = 1400; scene.render.resolution_y = 800
os.makedirs(PREV, exist_ok=True)
def shot(name, loc, target, lens=50):
    cam.location = loc; cam.data.lens = lens; cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(PREV, name); bpy.ops.render.render(write_still=True)
shot('prev_terminal.png', (.9, -1.9, 1.5), (-.1, 0, .98), 42)
shot('prev_props.png', (3.2, -4.2, 2.4), (3.0, 0.2, .5), 38)
shot('prev_exterior.png', (-3.0, -6.5, 4.2), (4.5, 4.5, 1.2), 34)
print('previews OK')
