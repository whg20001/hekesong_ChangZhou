"""Build editable Rick and Morty reference props in Blender 5.2.

Run: blender --background --factory-startup --python build_portal_lab.py
All generated assets remain in this folder. No existing projects are changed.
"""
import bpy
import math
import random
import os
import json
from math import sin, cos, pi
from mathutils import Vector, Quaternion

OUT = os.path.dirname(os.path.abspath(__file__))
random.seed(137)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.adaptive_threshold = .025
scene.cycles.max_bounces = 10
scene.cycles.transmission_bounces = 8
scene.render.resolution_x = 2000
scene.render.resolution_y = 1500
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 120
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -.25
scene.render.film_transparent = False
bpy.context.preferences.filepaths.save_version = 0
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    gpu = [d for d in prefs.devices if d.type == 'OPTIX']
    for d in prefs.devices:
        d.use = d in gpu
    scene.cycles.device = 'GPU' if gpu else 'CPU'
    print('RENDER_DEVICE', [(d.name, d.type) for d in gpu], flush=True)
except Exception as e:
    print('GPU_FALLBACK', str(e), flush=True)


def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


def move(obj, col, parent=None):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    if parent:
        obj.parent = parent
    return obj


def empty(name, col, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    col.objects.link(o)
    o.location = loc
    o.empty_display_type = 'PLAIN_AXES'
    o.empty_display_size = .3
    if parent:
        o.parent = parent
    return o


def material(name, color, rough=.4, metal=0, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m


def mesh(name, verts, faces, mat, col, parent=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    o = bpy.data.objects.new(name, data)
    col.objects.link(o)
    if mat:
        o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def bevel(o, amount=.035, segments=3):
    mod = o.modifiers.new('Soft cartoon edges', 'BEVEL')
    mod.width = amount
    mod.segments = segments
    o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o


def box(name, loc, dim, mat, col, parent=None, amount=.025):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = move(bpy.context.object, col, parent)
    o.name = name
    o.location = loc
    o.dimensions = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if amount:
        bevel(o, amount)
    return o


def uv_sphere(name, loc, scale, mat, col, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    o = move(bpy.context.object, col, parent)
    o.name = name
    o.location = loc
    o.scale = scale
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def cylinder(name, loc, radius, depth, mat, col, parent=None, edge=.01):
    bpy.ops.mesh.primitive_cylinder_add(vertices=72, radius=radius, depth=depth)
    o = move(bpy.context.object, col, parent)
    o.name = name
    o.location = loc
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    if edge:
        bevel(o, edge)
    return o


def curve(name, points, thickness, mat, col, parent=None, cyclic=False):
    d = bpy.data.curves.new(name, 'CURVE')
    d.dimensions = '3D'
    d.resolution_u = 2
    d.bevel_depth = thickness
    d.bevel_resolution = 3
    s = d.splines.new('POLY')
    s.points.add(len(points) - 1)
    for p, xyz in zip(s.points, points):
        p.co = (*xyz, 1)
    s.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, d)
    col.objects.link(o)
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


def lathe(name, profile, mat, col, parent=None, loc=(0, 0, 0)):
    n = 80
    verts = [(r * cos(2*pi*k/n), r * sin(2*pi*k/n), z)
             for r, z in profile for k in range(n)]
    faces = []
    for j in range(len(profile) - 1):
        for k in range(n):
            a = j*n + k
            b = j*n + (k+1) % n
            faces.append((a, b, b+n, a+n))
    o = mesh(name, verts, faces, mat, col, parent)
    o.location = loc
    for p in o.data.polygons:
        p.use_smooth = True
    return o


FONT = bpy.data.fonts.load('C:/Windows/Fonts/bahnschrift.ttf')


def text(name, body, loc, size, mat, col, parent=None, rotation=(pi/2, 0, 0)):
    d = bpy.data.curves.new(name, 'FONT')
    d.body = body
    d.font = FONT
    d.size = size
    d.align_x = 'CENTER'
    d.extrude = .0005
    o = bpy.data.objects.new(name, d)
    col.objects.link(o)
    o.location = loc
    o.rotation_euler = rotation
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    return o


PORTAL = collection('01 | PORTAL - editable energy geometry')
GUN = collection('02 | PORTAL GUN - body, button and vial')
STAGE = collection('03 | DISPLAY - removable studio')
LIGHTS = collection('04 | LIGHTING AND CAMERAS')
root = empty('PORTAL | move the whole portal here', PORTAL, (-1.75, .65, 2.65))
root.rotation_euler = (pi/2, 0, 0)
root.scale = (1.32, 2.42, 1)
root['Description'] = 'Organic oval energy portal. No rigid frame; all ribbons and sparks are editable.'
root['Animation'] = '120-frame seamless material swirl; frame 121 matches frame 1.'
gun = empty('PORTAL GUN | move the whole prop here', GUN, (1.70, -.40, 1.42))
gun.rotation_euler[2] = math.radians(-12)
gun['Reference'] = 'Flat pale-grey handheld body, square red button and upright green cartridge; no pistol grip.'

ink = material('Outline | deep graphite', (.014, .020, .013), .48)
shell = material('Gun | warm pale grey shell', (.57, .62, .58), .31, .12)
top = material('Gun | off-white top plate', (.73, .77, .71), .32, .04)
edge = material('Gun | darker grey lower edge', (.24, .29, .25), .42, .15)
red = material('Button | classic saturated red', (.63, .016, .008), .27)
red_side = material('Button | dark red bevel', (.25, .008, .004), .4)
green_dark = material('Portal | dark green ink', (.007, .085, .001), .6, emission=.8)
green = material('Portal | vivid slime green', (.105, .66, .002), .35, emission=1.5)
lime = material('Portal | acid lime', (.37, 1.0, .018), .35, emission=2.1)
yellow_green = material('Portal | yellow-green edge', (.58, .93, .035), .35, emission=1.5)
white = material('Portal | pale animated flecks', (.73, 1.0, .49), .32, emission=3)
fluid_green = material('Vial | glowing green fluid', (.18, .75, .008), .22, emission=.75)
fluid_dark = material('Vial | deeper green swirl', (.035, .26, .003), .32, emission=.45)
glass = material('Vial | clear green-tinted glass', (.72, .95, .56), .09)
gp = glass.node_tree.nodes.get('Principled BSDF')
gp.inputs['Transmission Weight'].default_value = 1
gp.inputs['IOR'].default_value = 1.35
gp.inputs['Coat Weight'].default_value = .35
glass_highlight = material('Vial | soft white illustrated reflection', (.77, 1.0, .67), .21, emission=.5)

# The surface uses a genuine polar spiral shader, rather than an image plane.
surface = bpy.data.materials.new('PORTAL | animated polar vortex - edit green color ramp')
surface.use_nodes = True
n, l = surface.node_tree.nodes, surface.node_tree.links
n.clear()
out = n.new('ShaderNodeOutputMaterial'); out.location = (1050, 50)
em = n.new('ShaderNodeEmission'); em.location = (850, 50); em.inputs['Strength'].default_value = 1.4
coord = n.new('ShaderNodeTexCoord'); coord.location = (-1100, 0)
sep = n.new('ShaderNodeSeparateXYZ'); sep.location = (-900, 120)
l.new(coord.outputs['Object'], sep.inputs[0])


def mathnode(op, a=None, b=None, loc=(0, 0)):
    q = n.new('ShaderNodeMath'); q.operation = op; q.location = loc
    for i, v in enumerate((a, b)):
        if v is not None:
            if isinstance(v, (float, int)):
                q.inputs[i].default_value = v
            else:
                l.new(v, q.inputs[i])
    return q.outputs[0]


x2 = mathnode('MULTIPLY', sep.outputs['X'], sep.outputs['X'], (-700, 220))
y2 = mathnode('MULTIPLY', sep.outputs['Y'], sep.outputs['Y'], (-700, 60))
sum2 = mathnode('ADD', x2, y2, (-520, 200))
radius = mathnode('SQRT', sum2, None, (-350, 240))
ang = mathnode('ARCTAN2', sep.outputs['Y'], sep.outputs['X'], (-700, -140))
ang3 = mathnode('MULTIPLY', ang, 2, (-520, -140))
twist = mathnode('MULTIPLY', radius, 15, (-170, 240))
phase = mathnode('ADD', ang3, twist, (0, 80))
time = n.new('ShaderNodeValue'); time.name = 'ANIMATION | 3 spiral turns / loop'; time.label = 'Animated swirl phase'; time.location = (-160, -150)
time.outputs[0].default_value = 0
time.outputs[0].keyframe_insert('default_value', frame=1)
time.outputs[0].default_value = 2*pi*3
time.outputs[0].keyframe_insert('default_value', frame=121)
phase = mathnode('SUBTRACT', phase, time.outputs[0], (170, 50))
noise = n.new('ShaderNodeTexNoise'); noise.location = (-700, -430)
noise.inputs['Scale'].default_value = 4.0
noise.inputs['Detail'].default_value = 3
noise.inputs['Roughness'].default_value = .65
l.new(coord.outputs['Object'], noise.inputs['Vector'])
warping = mathnode('MULTIPLY', noise.outputs['Fac'], 3.3, (-340, -350))
phase = mathnode('ADD', phase, warping, (340, 70))
wave = mathnode('SINE', phase, None, (500, 50))
wave = mathnode('MULTIPLY_ADD', wave, .5, (500, -150))
# MULTIPLY_ADD's third input maps sine [-1,1] to [0,1].
n[-1].inputs[2].default_value = .5
ramp = n.new('ShaderNodeValToRGB'); ramp.location = (650, 120)
cr = ramp.color_ramp
cr.interpolation = 'EASE'
colors = [(0, (.002, .025, .0003, 1)), (.23, (.006, .10, .0005, 1)),
          (.45, (.022, .32, .001, 1)), (.64, (.12, .66, .004, 1)),
          (.82, (.32, .9, .018, 1)), (1, (.028, .24, .001, 1))]
cr.elements.remove(cr.elements[1])
cr.elements[0].position, cr.elements[0].color = colors[0]
for pos, color in colors[1:]:
    e = cr.elements.new(pos); e.color = color
l.new(wave, ramp.inputs[0]); l.new(ramp.outputs[0], em.inputs['Color']); l.new(em.outputs[0], out.inputs[0])


def outline_radius(a):
    tip = .052 * math.exp(-((a-pi/2)/.13)**2)
    return 1 + .018*sin(3*a+.2) + .012*sin(7*a+.4) + .013*sin(13*a+1.1) + .006*sin(25*a) + tip


N, R = 256, 36
verts = [(0, 0, -.015)]
for j in range(1, R+1):
    rr = j/R
    for i in range(N):
        a = 2*pi*i/N
        r = rr * outline_radius(a)
        verts.append((r*cos(a), r*sin(a), -.045*(1-rr)**2))
faces = [(0, 1+i, 1+(i+1) % N) for i in range(N)]
for j in range(R-1):
    for i in range(N):
        a = 1+j*N+i; b = 1+j*N+(i+1) % N
        faces.append((a, a+N, b+N, b))
disk = mesh('Portal | polar vortex surface', verts, faces, surface, PORTAL, root)
for p in disk.data.polygons:
    p.use_smooth = True


def annulus(name, inner, outer, mat, z, irregular=1):
    vs = []
    for i in range(N):
        a = 2*pi*i/N
        r = outline_radius(a) if irregular else 1
        vs.extend([(inner*r*cos(a), inner*r*sin(a), z),
                   (outer*r*cos(a), outer*r*sin(a), z)])
    fs = [(2*i, 2*i+1, 2*((i+1) % N)+1, 2*((i+1) % N)) for i in range(N)]
    return mesh(name, vs, fs, mat, PORTAL, root)


annulus('Portal | organic dark silhouette', .95, 1.045, green_dark, -.016)
annulus('Portal | living green outer skin', .92, 1.018, green, .006)
annulus('Portal | thin acid-lime rim', .970, .994, yellow_green, .014)

# Broad, tapered flowing ribbons supply visible geometry when editing the portal.
def spiral_ribbon(name, phase0, turns, width, mat, z):
    vs = []
    steps = 340
    for i in range(steps+1):
        t = i/steps
        r = .055 + .89*t
        a = phase0 + turns*2*pi*(1-t) + .035*sin(t*23+phase0)
        w = width * sin(pi*t)**.65 * (.55+.45*t)
        for rr in (r-w, r+w):
            vs.append((rr*cos(a), rr*sin(a), z+.003*sin(t*20)))
    fs = [(2*i, 2*i+1, 2*i+3, 2*i+2) for i in range(steps)]
    return mesh(name, vs, fs, mat, PORTAL, root)


for i in range(2):
    spiral_ribbon('Portal | flowing emerald arm %02d' % (i+1), i*pi+.35, 1.02, .040, green_dark, .019)
    spiral_ribbon('Portal | acid-green arm highlight %02d' % (i+1), i*pi+.43, 1.02, .009, lime, .024)

# Broken bright streaks around the edge, as in the cartoon reference.
for i in range(48):
    a = random.uniform(0, 2*pi)
    rr = random.uniform(.80, .985)
    da = random.uniform(.013, .060)
    pts = []
    for k in range(10):
        t = k/9; aa = a+da*(t-.5)
        r = rr + .004*sin(t*pi)
        pts.append((r*cos(aa), r*sin(aa), .034))
    curve('Portal | white edge streak %02d' % i, pts, random.uniform(.003, .008), white if i % 4 else lime, PORTAL, root)

for i in range(38):
    a = random.uniform(0, 2*pi); rr = random.uniform(.30, .94)
    uv_sphere('Portal | suspended luminous droplet %02d' % i,
              (rr*cos(a), rr*sin(a), .037),
              (random.uniform(.005, .015), random.uniform(.005, .014), .008),
              lime if i % 3 else white, PORTAL, root)

for i in range(12):
    a = 2*pi*i/12 + random.uniform(-.12, .12)
    pts = []
    for k in range(24):
        t = k/23
        rr = 1.006 + .065*t + .008*sin(t*pi*3)
        aa = a+.035*sin(t*pi*1.6)
        pts.append((rr*cos(aa), rr*sin(aa), .015))
    curve('Portal | escaping energy tendril %02d' % i, pts, .0045, lime, PORTAL, root)

# GUN: low, flat rectangular silhouette; the cartridge and red button sit on top.
body = box('Gun | graphite outline beneath shell', (0, 0, .09), (2.06, .76, .23), ink, GUN, gun, .05)
box('Gun | main pale-grey rounded rectangular body', (0, 0, .135), (2.00, .715, .245), shell, GUN, gun, .045)
box('Gun | lower grey lip', (0, -.004, .025), (2.035, .735, .065), edge, GUN, gun, .025)
box('Gun | black top plate seam', (-.015, 0, .259), (1.925, .655, .035), ink, GUN, gun, .023)
box('Gun | off-white top plate', (-.015, 0, .280), (1.89, .625, .030), top, GUN, gun, .021)
box('Button | recessed charcoal square bezel', (-.61, -.045, .302), (.36, .32, .035), ink, GUN, gun, .018)
box('Button | red button dark sidewall', (-.61, -.045, .326), (.285, .25, .043), red_side, GUN, gun, .012)
box('Button | raised red activation key', (-.61, -.045, .350), (.274, .239, .034), red, GUN, gun, .012)

vx, vy = .31, .015
cylinder('Cartridge | graphite socket outline', (vx, vy, .315), .313, .052, ink, GUN, gun, .008)
cylinder('Cartridge | broad grey seating collar', (vx, vy, .353), .287, .052, edge, GUN, gun, .012)
cylinder('Cartridge | off-white collar top', (vx, vy, .382), .264, .023, top, GUN, gun, .007)
cylinder('Cartridge | lower green gasket', (vx, vy, .407), .241, .025, green_dark, GUN, gun, .004)
profile = [(.218, .407), (.235, .428), (.237, .50), (.237, 1.03), (.230, 1.115),
           (.210, 1.170), (.165, 1.205), (.08, 1.224), (0, 1.226)]
vial = lathe('Cartridge | rounded transparent glass envelope', profile, glass, GUN, gun, (vx, vy, 0))
solid = vial.modifiers.new('Physical thin glass wall', 'SOLIDIFY'); solid.thickness = .009
cylinder('Cartridge | contained luminous green liquid', (vx, vy, .75), .205, .625, fluid_green, GUN, gun, .018)
uv_sphere('Cartridge | curved liquid meniscus', (vx, vy, 1.063), (.205, .205, .035), fluid_green, GUN, gun)
for i in range(3):
    pts = []
    for k in range(100):
        t = k/99; a = i*2*pi/3 + 2*pi*1.25*t
        pts.append((vx+.208*cos(a), vy+.208*sin(a), .46+.56*t))
    curve('Cartridge | swirling darker green filament %02d' % i, pts, .021 if i == 0 else .013,
          fluid_dark if i != 1 else lime, GUN, gun)
for i in range(15):
    a = random.uniform(0, 2*pi); z = random.uniform(.49, 1.035)
    r = random.uniform(.017, .043)
    uv_sphere('Cartridge | green suspended bubble %02d' % i,
              (vx+.181*cos(a), vy+.181*sin(a), z), (r, r, r),
              lime if i % 3 else fluid_dark, GUN, gun)
# Deliberate thin illustrated highlights, visible even in a material preview.
for j, a in enumerate((-pi/2-.57, -pi/2+.45)):
    pts = [(vx+.242*cos(a+.025*sin(t*pi)), vy+.242*sin(a+.025*sin(t*pi)), .52+.57*t)
           for t in [k/30 for k in range(31)]]
    curve('Cartridge | long glass reflection %02d' % j, pts, .008 if j == 0 else .004, glass_highlight, GUN, gun)
pts = [(vx+.227*cos(a), vy+.227*sin(a), 1.105+.018*sin(a*2))
       for a in [-2.7+k/40*1.2 for k in range(41)]]
curve('Cartridge | curved shoulder highlight', pts, .006, glass_highlight, GUN, gun)

# Small unobtrusive casing details retain the reference's clean silhouette.
for i in range(3):
    box('Gun | three side ventilation slots %02d' % i, (.56+i*.095, -.359, .145),
        (.040, .008, .075), ink, GUN, gun, .008)
text('Gun | small C-137 casing mark', 'C-137', (-.40, -.363, .095), .085, ink, GUN, gun)
for x in (-.90, .90):
    s = cylinder('Gun | top plate recessed fastener', (x, .23, .300), .019, .006, edge, GUN, gun, .001)
    box('Gun | fastener slot', (x, .23, .304), (.022, .004, .003), ink, GUN, gun, 0)
# A shallow front emitter is flush with the body rather than a protruding barrel.
nozzle = cylinder('Gun | flush circular emitter dark rim', (1.005, 0, .14), .087, .014, ink, GUN, gun, .006)
nozzle.rotation_euler[1] = pi/2
nozzle = cylinder('Gun | flush green emitter lens', (1.016, 0, .14), .062, .012, green_dark, GUN, gun, .005)
nozzle.rotation_euler[1] = pi/2

# Studio display is independent from both prop collections and can be hidden.
floor_mat = material('Studio | midnight charcoal', (.025, .037, .035), .37, .15)
plinth_mat = material('Studio | satin graphite plinth', (.06, .085, .075), .35, .3)
label_mat = material('Studio | subtle pale-green type', (.38, .52, .40), .5, emission=.15)
box('Studio | ground', (0, 0, -.16), (200, 200, .25), floor_mat, STAGE, amount=.02)
cylinder('Studio | gun display plinth', (1.70, -.35, .55), 1.36, 1.13, plinth_mat, STAGE, edge=.05)
cylinder('Studio | plinth top green pinstripe', (1.70, -.35, 1.121), 1.27, .012, green_dark, STAGE, edge=.004)
stand = cylinder('Studio | discreet gun support', (1.70, -.40, 1.27), .075, .30, ink, STAGE, edge=.01)
text('Studio | portal identification', '01 / PORTAL', (-1.75, -.02, .004), .16, label_mat, STAGE, rotation=(0, 0, 0))
text('Studio | gun plinth label', '02 / PORTAL GUN', (1.70, -1.711, .58), .14, label_mat, STAGE)

world = bpy.data.worlds.new('Studio | dark desaturated green environment')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.10, .15, .12, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .22


def area(name, loc, target, power, color, size, size_y=None):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = power; d.color = color
    d.shape = 'RECTANGLE' if size_y else 'DISK'; d.size = size
    if size_y:
        d.size_y = size_y
    o = bpy.data.objects.new(name, d); LIGHTS.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z', 'Y').to_euler()
    return o


area('Key | broad softbox', (1.5, -6, 8.5), (0, 0, 1.9), 1500, (.85, 1, .87), 5)
area('Rim | cool neutral softbox', (4, 3.2, 6), (1, 0, 2), 1800, (.60, .78, .85), 4)
area('Front | soft shell fill', (-.5, -7, 3.2), (1.7, -.4, 1.8), 450, (1, .96, .83), 3)
area('Portal | green spill on the ground', (-1.7, .25, 2.6), (-1.7, -.2, 0), 130, (.30, 1, .015), 2, 3)


def camera(name, loc, target, lens=50, ortho=None):
    d = bpy.data.cameras.new(name)
    o = bpy.data.objects.new(name, d)
    LIGHTS.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z', 'Y').to_euler()
    d.lens = lens; d.clip_end = 300
    if ortho:
        d.type = 'ORTHO'; d.ortho_scale = ortho
    return o


hero = camera('CAM 01 | both props - presentation', (7.6, -15.5, 7.5), (-.25, .2, 2.35), 70)
portal_cam = camera('CAM 02 | portal face and organic rim', (-1.75, -10.5, 3.8), (-1.75, .65, 2.63), 55, 6.10)
gun_cam = camera('CAM 03 | gun reference three-quarter', (5.1, -5.7, 4.6), (1.70, -.4, 2.02), 63, 3.45)

# Blender 5 compositor glow remains editable in the saved node group.
ng = bpy.data.node_groups.new('Portal | restrained emission bloom', 'CompositorNodeTree')
scene.compositing_node_group = ng
ng.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new('CompositorNodeRLayers'); rl.location = (0, 0)
gl = ng.nodes.new('CompositorNodeGlare'); gl.location = (220, 0)
gl.inputs['Type'].default_value = 'Fog Glow'
gl.inputs['Quality'].default_value = 'High'
gl.inputs['Threshold'].default_value = 1.4
gl.inputs['Strength'].default_value = .25
output = ng.nodes.new('NodeGroupOutput'); output.location = (450, 0)
ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
ng.links.new(gl.outputs['Image'], output.inputs['Image'])

# Linear interpolation makes a constant-speed, mathematically seamless loop.
if surface.node_tree.animation_data and surface.node_tree.animation_data.action:
    action = surface.node_tree.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag = strip.channelbag(slot)
                if bag:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'

scene.camera = hero
scene.frame_set(1)
scene['Assets'] = 'Editable reference-inspired portal and portal gun. All effects are procedural or mesh geometry.'
scene['Controls'] = 'Move PORTAL and PORTAL GUN root empties. Hide collection 03 for clean models. Cameras 01/02/03.'
scene['Animation'] = '24 fps; frames 1-120 loop. Portal polar shader phase animated, endpoint at frame 121.'
scene['Reference'] = 'The two user-provided Rick and Morty screenshots; modelled from scratch in Blender.'

for o in bpy.context.selected_objects:
    o.select_set(False)
gun.select_set(True)
bpy.context.view_layer.objects.active = gun
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type == 'VIEW_3D':
            a.spaces.active.region_3d.view_perspective = 'CAMERA'
            a.spaces.active.overlay.show_overlays = False
            a.spaces.active.shading.type = 'MATERIAL'
            a.spaces.active.shading.use_scene_world = True
            a.spaces.active.shading.use_scene_lights = True

bpy.ops.file.pack_all()
blend_path = os.path.join(OUT, 'Rick_Portal_and_Gun.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print('MODEL_SAVED', blend_path, flush=True)

views = [(hero, 2000, 1500, '01_Portal_and_Gun.png'),
         (portal_cam, 1400, 1700, '02_Portal_Closeup.png'),
         (gun_cam, 1800, 1500, '03_Portal_Gun_Closeup.png')]
for cam, width, height, filename in views:
    PORTAL.hide_render = cam == gun_cam
    GUN.hide_render = cam == portal_cam
    for o in STAGE.objects:
        o.hide_render = cam == portal_cam and o.name not in ('Studio | ground', 'Studio | portal identification')
        if cam == gun_cam and o.name == 'Studio | portal identification':
            o.hide_render = True
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.filepath = os.path.join(OUT, filename)
    print('RENDER_START', filename, flush=True)
    bpy.ops.render.render(write_still=True)
    print('RENDER_DONE', filename, flush=True)

PORTAL.hide_render = False
GUN.hide_render = False
for o in STAGE.objects:
    o.hide_render = False
scene.camera = hero
scene.render.resolution_x, scene.render.resolution_y = 2000, 1500
scene.render.filepath = os.path.join(OUT, '01_Portal_and_Gun.png')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
report = {'blender': bpy.app.version_string, 'file': blend_path,
          'portal_objects': len(PORTAL.objects), 'gun_objects': len(GUN.objects),
          'animation_frames': [1, 120], 'fps': 24,
          'cameras': [c.name for c, _, _, _ in views], 'previews': [f for _, _, _, f in views],
          'external_images': [i.filepath for i in bpy.data.images if i.source == 'FILE' and not i.packed_file]}
with open(os.path.join(OUT, 'asset_info.json'), 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print('ASSETS_COMPLETE', json.dumps(report, ensure_ascii=False), flush=True)
