"""An editable, self-contained Blender scene. Run with Blender 5.x --background --python."""
import bpy, math, random, os, sys
from mathutils import Vector
from math import sin, cos, pi

random.seed(23)
OUT = os.path.dirname(os.path.abspath(__file__))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in list(bpy.data.collections):
    if block.name != 'Collection': bpy.data.collections.remove(block)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.adaptive_threshold = .035
scene.cycles.max_bounces = 10
scene.cycles.transmission_bounces = 8
scene.cycles.transparent_max_bounces = 8
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for dev in prefs.devices: dev.use = dev.type == 'OPTIX'
    scene.cycles.device = 'GPU'
except Exception as exc: print('GPU setup:', exc)
scene.render.resolution_x = 2400
scene.render.resolution_y = 1600
scene.render.resolution_percentage = 45
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
scene.render.film_transparent = False
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 48
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = .35
world = bpy.data.worlds.new('Midnight blue atmosphere')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.065, .105, .21, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .18

COL = None
def collection(name):
    global COL
    COL = bpy.data.collections.new(name)
    scene.collection.children.link(COL)
    return COL

def move(obj):
    for co in list(obj.users_collection): co.objects.unlink(obj)
    COL.objects.link(obj)
    return obj

def mat(name, color, rough=.5, metal=0, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

def noise_mat(name, c1, c2, rough=.7, scale=(1,1,1), detail=3, bump=.06):
    m = mat(name,c1,rough)
    n = m.node_tree.nodes; l = m.node_tree.links; p = n.get('Principled BSDF')
    t = n.new('ShaderNodeTexCoord')
    v = n.new('ShaderNodeVectorMath'); v.operation='MULTIPLY'; v.inputs[1].default_value=scale
    l.new(t.outputs['Generated'],v.inputs[0])
    tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=5; tex.inputs['Detail'].default_value=detail
    l.new(v.outputs['Vector'],tex.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.2; ramp.color_ramp.elements[1].position=.8
    ramp.color_ramp.elements[0].color=(*c1,1); ramp.color_ramp.elements[1].color=(*c2,1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]); l.new(ramp.outputs[0],p.inputs['Base Color'])
    b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=bump; b.inputs['Distance'].default_value=.025
    l.new(tex.outputs['Fac'],b.inputs['Height']); l.new(b.outputs[0],p.inputs['Normal'])
    return m

def cube(name,loc,dim,m,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=move(bpy.context.object); o.name=name; o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if m: o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('Soft manufactured edges','BEVEL'); b.width=bevel; b.segments=3
        b=o.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
    return o

def sphere(name,loc,scale,m,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    o=move(bpy.context.object);o.name=name;o.scale=scale;o.data.materials.append(m)
    for p in o.data.polygons:p.use_smooth=True
    return o

def cyl(name,loc,r,depth,m,vertices=40):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc)
    o=move(bpy.context.object);o.name=name;o.data.materials.append(m)
    b=o.modifiers.new('Rounded rim','BEVEL'); b.width=min(.012,r*.15,depth*.2);b.segments=3
    o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def rod(name,a,b,r,m):
    d=Vector(b)-Vector(a);o=cyl(name,(Vector(a)+Vector(b))/2,r,d.length,m,24)
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o

def mesh(name,verts,faces,m):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);COL.objects.link(ob)
    if m:data.materials.append(m)
    return ob

def curve(name,paths,r,m):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=16
    data.bevel_depth=r;data.bevel_resolution=3
    for points in paths:
        s=data.splines.new('POLY');s.points.add(len(points)-1)
        for p,co in zip(s.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,data);COL.objects.link(o);data.materials.append(m);return o

def lathe(name,loc,profile,m,steps=64):
    verts=[];faces=[]
    for r,z in profile:
        for i in range(steps):
            t=2*pi*i/steps;verts.append((loc[0]+r*cos(t),loc[1]+r*sin(t),loc[2]+z))
    for j in range(len(profile)-1):
        for i in range(steps):
            a=j*steps+i;b=j*steps+(i+1)%steps
            faces.append((a,b,b+steps,a+steps))
    o=mesh(name,verts,faces,m)
    for p in o.data.polygons:p.use_smooth=True
    return o

FONT = bpy.data.fonts.load('C:/Windows/Fonts/segoeui.ttf')
MONO = bpy.data.fonts.load('C:/Windows/Fonts/DejaVuSansMono_0.ttf')
def text(name,body,loc,size,m,rot=(pi/2,0,0),align='LEFT',font=FONT):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size;d.align_x=align;d.font=font
    d.space_character=1.1;d.extrude=0
    o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc;o.rotation_euler=rot;d.materials.append(m)
    return o

def area(name,loc,target,power,color,size,size_y=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color
    if size_y:d.shape='RECTANGLE';d.size=size;d.size_y=size_y
    else:d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc
    o.visible_glossy=False
    o.visible_transmission=False
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o

walnut=noise_mat('Walnut / long open grain',(.055,.021,.011),(.27,.12,.047),.36,(1,35,6),3,.13)
oak=noise_mat('Honey oak',(.16,.072,.027),(.39,.23,.105),.48,(1,30,4),3,.11)
wall=noise_mat('Blue slate limewash',(.045,.10,.105),(.085,.16,.155),.88,(2,2,2),4,.045)
dark=mat('Graphite powder coat',(.018,.028,.034),.33,.5)
black=mat('Soft black polymer',(.009,.015,.019),.56)
brass=mat('Brushed aged brass',(.37,.215,.075),.29,.8)
paper=mat('Warm ivory book paper',(.8,.76,.62),.75)
ink=mat('Printed charcoal ink',(.055,.07,.07),.8)
linen=noise_mat('Natural woven linen',(.45,.41,.31),(.76,.72,.58),.94,(100,100,100),2,.24)
teal=noise_mat('Petrol blue cotton',(.018,.08,.09),(.055,.20,.21),.92,(75,75,75),2,.23)
ochre=noise_mat('Saffron wool throw',(.24,.095,.023),(.55,.30,.09),.95,(85,85,85),2,.28)
green=mat('Forest green enamel',(.035,.13,.095),.24,.35)
cream=mat('Ivory ceramic',(.65,.64,.50),.25)
terracotta=noise_mat('Earthenware',(.21,.065,.032),(.41,.16,.075),.82,(4,4,4),3,.08)
leafmat=mat('Leaves / jade',(.026,.16,.07),.43)
leaflight=mat('Leaves / young sage',(.13,.25,.085),.5)
soil=mat('Potting soil',(.023,.014,.008),1)
warm_glow=mat('Warm opal light', (1,.63,.25),.3,emission=5)
screen_bg=mat('Screen / midnight blue',(.012,.035,.06),.5,emission=.8)
screen_panel=mat('Screen / pane',(.025,.06,.085),.5,emission=.7)
screen_white=mat('Screen / text',(.52,.76,.81),.6,emission=1)
screen_mint=mat('Screen / mint',(.16,.69,.49),.6,emission=1.2)
screen_gold=mat('Screen / amber',(.83,.45,.16),.6,emission=1)
book_mats=[mat('Book cover / '+n,c,.7) for n,c in [('rust',(.32,.078,.035)),('sea',(.035,.16,.18)),('cream',(.57,.49,.32)),('indigo',(.043,.065,.15)),('olive',(.16,.22,.10))]]

print('BUILD: architecture',flush=True)
collection('01 • Room architecture')
cube('Subfloor',(0,.1,-.09),(6.7,6.7,.16),dark)
floor_mats=[noise_mat('Oak flooring %02d'%i,(.085+i*.009,.04+i*.004,.017+i*.002),(.24+i*.012,.12+i*.008,.045+i*.004),.45,(35,1,4),3,.09) for i in range(5)]
for ix in range(24):
    x=-3.3+ix*.278
    for iy in range(5):
        y=-3.17+iy*1.5+(ix%3)*.49
        if y>3.3:continue
        lo=max(-3.22,y-.745);hi=min(3.32,y+.745)
        cube('Individual oak plank',(x,(lo+hi)/2,0),(.272,hi-lo,.055),random.choice(floor_mats),.008)
cube('Left plaster wall',(-3.38,.13,1.7),(.16,6.5,3.4),wall,.025)
cube('Back wall / beneath window',(0,3.35,.49),(6.9,.18,1.0),wall,.02)
cube('Back wall / lintel',(0,3.35,3.3),(6.9,.18,.28),wall,.02)
cube('Back wall / left pier',(-2.99,3.35,2.1),(.78,.18,2.2),wall,.02)
cube('Back wall / right pier',(3.12,3.35,2.1),(.5,.18,2.2),wall,.02)
cube('Left skirting',(-3.25,.1,.12),(.06,6.4,.20),walnut,.012)
cube('Back skirting',(0,3.21,.12),(6.6,.06,.2),walnut,.012)
cube('Top wall trim',(-3.27,.1,3.31),(.08,6.5,.09),walnut,.01)
ceiling_mat=mat('Ceiling / warm grey plaster',(.22,.26,.24),.9)
cube('Room ceiling',(1.0,-.9,3.49),(9.0,8.6,.12),ceiling_mat)
cube('Back upper crown',(0,3.30,3.40),(6.8,.17,.09),walnut,.01)
cube('Left upper crown',(-3.31,.1,3.40),(.14,6.5,.09),walnut,.01)

collection('02 • Window, curtains & wet glass')
for x in [-2.58,2.84]:cube('Window outer jamb',(x,3.28,2.09),(.095,.16,2.2),dark,.012)
for z in [1.03,3.15]:cube('Window outer rail',(.13,3.28,z),(5.5,.16,.095),dark,.012)
for x in [-.8,1.02]:cube('Window slender mullion',(x,3.275,2.1),(.045,.12,2.05),dark,.007)
cube('Deep walnut windowsill',(.13,3.13,.975),(5.68,.46,.10),walnut,.028)
for x in [-.74,1.08]:
    cube('Window latch',(x,3.18,1.78),(.025,.035,.15),brass,.01)
glass=mat('Clear rain-covered window',(.88,.95,1),.045)
gp=glass.node_tree.nodes['Principled BSDF'];gp.inputs['Transmission Weight'].default_value=1;gp.inputs['IOR'].default_value=1.45
cube('Glass panes',(.13,3.305,2.09),(5.31,.008,2.04),glass)
rod('Curtain rail',(-2.95,3.03,3.27),(3.13,3.03,3.27),.025,brass)
curtain_mat=noise_mat('Heavy oatmeal curtain',(.28,.27,.22),(.51,.48,.38),.95,(55,55,55),2,.2)
for cx,width in [(-2.57,.57),(2.80,.63)]:
    verts=[];faces=[];nx=44;nz=26
    for j in range(nz+1):
        v=j/nz;z=.93+2.27*v
        for i in range(nx+1):
            u=i/nx;x=cx+(u-.5)*width*(1+.11*sin(v*pi))
            y=3.00+.085*cos(u*10*pi)+.025*sin(v*4+u*3)
            verts.append((x,y,z+.018*cos(u*10*pi)*(1-v)))
    for j in range(nz):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    ob=mesh('Pleated linen curtain',verts,faces,curtain_mat)
    for p in ob.data.polygons:p.use_smooth=True
    sol=ob.modifiers.new('Fabric thickness','SOLIDIFY');sol.thickness=.006
    for i in range(8):
        bpy.ops.mesh.primitive_torus_add(major_radius=.035,minor_radius=.006,location=(cx-width*.45+i*width*.9/7,3.03,3.25),rotation=(0,pi/2,0))
        move(bpy.context.object).data.materials.append(brass)

print('BUILD: writing desk and computer',flush=True)
collection('03 • Walnut desk & computer')
cube('Solid walnut desktop',(.08,2.07,.83),(3.94,1.03,.095),walnut,.035)
for x in [-1.65,1.82]:
    for y in [1.7,2.44]:cube('Desk tapered frame leg',(x,y,.41),(.065,.065,.78),dark,.012)
    cube('Desk side stretcher',(x,2.07,.20),(.055,.78,.045),brass,.009)
cube('Desk rear brace',(.08,2.45,.67),(3.5,.045,.065),dark,.008)
cube('Shallow desk drawer',(1.35,2.05,.705),(.83,.84,.16),walnut,.018)
cube('Drawer brass pull',(1.35,1.615,.705),(.22,.025,.018),brass,.005)
cube('Desk leather mat',(-.33,1.99,.884),(1.72,.62,.012),mat('Espresso leather',(.034,.042,.039),.83),.055)
cyl('Monitor base',(-.35,2.30,.902),.18,.035,dark)
cube('Monitor upright',(-.35,2.32,1.13),(.06,.045,.43),dark,.01)
cube('Monitor housing',(-.35,2.30,1.49),(1.27,.065,.78),black,.033)
cube('Display glass',(-.35,2.263,1.505),(1.20,.008,.686),screen_bg,.018)
cube('Screen top bar',(-.35,2.256,1.808),(1.16,.003,.062),screen_panel,.003)
text('Editor title','STUDIO  /  rainy-evening.py',(-.9,2.251,1.794),.026,screen_white,font=MONO)
for i,m in enumerate([book_mats[0],screen_gold,screen_mint]):sphere('Window control',(-.897+i*.033,2.247,1.825),(.008,.002,.008),m,12,8)
cube('Screen left rail',(-.845,2.255,1.475),(.18,.003,.57),screen_panel)
text('Explorer','FILES\n\nscene.py\nlights.py\nnotes.md\n\nassets /',(-.923,2.248,1.71),.021,screen_white,font=MONO)
code=[('#  a quiet place',screen_mint),('import light',screen_gold),('',screen_white),('room = Scene()',screen_white),('room.time = "23:48"',screen_gold),('room.weather = RAIN',screen_white),('',screen_white),('with desk.lamp:',screen_mint),('    warmth = 2700',screen_gold),('    read(book)',screen_white),('',screen_white),('render(evening)',screen_mint)]
for i,(line,m) in enumerate(code):text('Code line %02d'%i,line,(-.712,2.248,1.709-i*.036),.023,m,font=MONO)
cube('Screen right preview',(.084,2.252,1.49),(.28,.003,.52),screen_panel,.01)
sphere('On-screen moon',(.085,2.247,1.62),(.064,.001,.064),screen_gold,40,24)
for k in range(8):
    h=random.uniform(.04,.15)
    cube('On-screen skyline',(-.034+k*.033,2.246,1.335+h/2),(.025,.001,h),screen_mint)
text('Preview label','NIGHT\n23:48',(-.02,2.245,1.72),.023,screen_white,font=MONO)
text('Status bar','Python 3      UTF-8                  saved',(-.9,2.246,1.183),.019,screen_mint,font=MONO)
sphere('Monitor power LED',(.218,2.26,1.127),(.004,.002,.004),screen_mint,12,8)
cube('Mechanical keyboard',(-.40,1.843,.925),(.85,.29,.055),dark,.022)
keymat=mat('Keycaps / warm grey',(.33,.36,.33),.63)
for row in range(5):
    for col in range(14):
        x=-.783+col*.058;y=1.731+row*.05
        cube('Keyboard key %02d %02d'%(row,col),(x,y,.96),(.050,.041,.019),keymat if (col+row)%9 else cream,.005)
cube('Space bar',(-.40,1.73,.965),(.31,.042,.02),cream,.006)
cube('Mouse pad',(.27,1.85,.896),(.33,.36,.01),teal,.035)
sphere('Mouse',(.28,1.84,.934),(.064,.10,.034),black)
curve('Mouse seam',[[ (.28,1.79,.967),(.28,1.845,.97)]],.0018,brass)
for x in [-1.13,.60]:
    cube('Desktop speaker',(x,2.39,1.05),(.16,.15,.31),walnut,.018)
    sp=cyl('Speaker driver',(x,2.309,1.045),.057,.007,black);sp.rotation_euler[0]=pi/2
    sp=cyl('Speaker tweeter',(x,2.303,1.145),.024,.009,brass);sp.rotation_euler[0]=pi/2
cube('Compact computer tower',(1.40,2.25,.31),(.28,.40,.55),dark,.025)
for i in range(9):cube('PC ventilation grille',(1.4,2.042,.15+i*.034),(.20,.004,.009),black,.003)
sphere('PC power indicator',(1.40,2.039,.52),(.005,.002,.005),screen_mint,12,8)
curve('Monitor cable',[[(-.35,2.34,1.12),(-.35,2.47,.90),(-.35,2.49,.55),(.4,2.49,.52),(1.4,2.43,.52)]],.009,black)

collection('04 • Lamp, books & personal objects')
lx,ly=-1.42,1.99
cyl('Lamp heavy brass foot',(lx,ly,.908),.16,.055,brass)
cyl('Lamp green base inset',(lx,ly,.941),.127,.015,green)
rod('Lamp lower brass stem',(lx,ly,.95),(lx,ly,1.32),.015,brass)
sphere('Lamp hinge',(lx,ly,1.33),(.038,.038,.038),brass)
rod('Lamp angled arm',(lx,ly,1.33),(lx+.15,ly+.01,1.62),.014,brass)
shade_center=(lx+.15,ly+.01,1.58)
lathe('Green enamel lamp shade',shade_center,[(.224,-.09),(.226,-.075),(.21,-.02),(.16,.07),(.08,.15),(.031,.165)],green)
lathe('Ivory shade interior',shade_center,[(.219,-.09),(.217,-.075),(.20,-.02),(.15,.065),(.073,.143),(.027,.15)],cream)
lathe('Lamp polished rim',shade_center,[(.223,-.092),(.229,-.091),(.229,-.082),(.223,-.08)],brass)
sphere('Lamp glowing bulb',(lx+.15,ly+.01,1.56),(.042,.042,.052),warm_glow)
area('Warm desk lamp • 2700 K',(lx+.15,ly,1.51),(0,1.84,.84),65,(1,.61,.28),.27)
rod('Lamp switch',(lx+.075,ly-.045,.95),(lx+.075,ly-.045,.973),.009,black)
curve('Lamp cord',[[(lx,ly+.03,.91),(lx-.15,2.23,.895),(-1.67,2.43,.88),(-1.72,2.48,.65),(-1.71,2.50,.13)]],.006,black)

def flat_book(name,loc,w,d,h,cover,title):
    x,y,z=loc
    cube(name+' / page block',(x,y,z+h/2),(w-.015,d-.018,h-.013),paper,.005)
    for zz in [z+.003,z+h-.003]:cube(name+' / cover',(x,y,zz),(w,d,.009),cover,.005)
    cube(name+' / spine',(x,y-d/2,z+h/2),(w,.015,h),cover,.005)
    text(name+' / title',title,(x-w*.43,y-d/2-.008,z+h*.27),min(.025,h*.46),paper)
    for j in range(3):cube(name+' / leaf edges',(x,y+d/2-.008,z+.018+j*max(.005,(h-.03)/3)),(w-.025,.003,.001),linen)

flat_book('Design reference',(-1.41,2.39,.884),.48,.30,.055,book_mats[1],'THE DESIGN OF EVERYDAY THINGS')
flat_book('Light monograph',(-1.40,2.38,.941),.44,.29,.045,book_mats[2],'LIGHT / SPACE')
for i,(title,h,w) in enumerate([('BLENDER',.34,.072),('PYTHON',.30,.064),('DESIGN',.38,.078),('ARCHITECTURE',.35,.069)]):
    x=1.17+i*.082
    cube('Reference book / '+title,(x,2.36,.887+h/2),(w,.22,h),book_mats[i],.006)
    cube('Reference pages',(x,2.365,.887+h/2),(w-.014,.207,h-.018),paper,.003)
    cube('Reference spine',(x,2.245,.887+h/2),(w,.018,h),book_mats[i],.004)
    text('Spine title / '+title,title,(x-w*.20,2.233,.927),.023,paper,rot=(pi/2,-pi/2,0))
    for z in [.915,.887+h-.031]:cube('Gilt book band',(x,2.234,z),(w*.75,.003,.006),brass)
cube('Bookend',(1.54,2.36,1.02),(.026,.26,.27),brass,.008)

# An open book: shaped page surfaces, real lines and chapter headings.
bx,by,bz=.93,1.84,.9
cube('Open book fabric cover',(bx,by,bz),(.72,.45,.016),book_mats[0],.01)
for side in [-1,1]:
    verts=[];faces=[];nx=24;ny=4
    for j in range(ny+1):
        yy=by-.213+j*.426/ny
        for i in range(nx+1):
            u=i/nx;xx=bx+side*(.012+u*.337)
            zz=bz+.018+.026*sin(u*pi)+.008*(1-u)
            verts.append((xx,yy,zz))
    for j in range(ny):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    if side == -1: faces=[tuple(reversed(f)) for f in faces]
    ob=mesh('Open book / curved pages',verts,faces,paper);sol=ob.modifiers.new('Page block','SOLIDIFY');sol.thickness=.022
    for p in ob.data.polygons:p.use_smooth=True
    for line in range(15):
        yy=by-.145+line*.018
        if line>11:continue
        start=.048;end=.305-random.uniform(0,.055)
        pts=[]
        for k in range(14):
            u=(start+(end-start)*k/13)/.337
            pts.append((bx+side*(.012+u*.337),yy,bz+.019+.026*sin(u*pi)+.008*(1-u)))
        curve('Book typeset line',[pts],.00065,ink)
    text('Book chapter','LIGHT & SPACE' if side==-1 else 'THE QUIET HOURS',(bx+side*.18,by+.14,bz+.052),.020,ink,rot=(0,0,0),align='CENTER')
curve('Cloth bookmark',[[(bx,by+.20,bz+.027),(bx,by-.23,bz+.027),(bx+.03,by-.29,bz-.01)]],.006,book_mats[0])
rod('Brass pen',(.50,1.64,.906),(.60,1.99,.906),.006,brass)
rod('Pen ink tip',(.60,1.99,.906),(.604,2.005,.906),.003,ink)

mx,my=1.70,1.91
lathe('Hand-thrown tea mug',(mx,my,.88),[(.053,0),(.067,.009),(.069,.12),(.065,.137),(.058,.14),(.055,.13),(.054,.025)],cream)
cyl('Tea surface',(mx,my,.989),.055,.002,mat('Black tea',(.07,.025,.008),.19))
bpy.ops.mesh.primitive_torus_add(major_radius=.043,minor_radius=.012,location=(mx+.077,my,.954),rotation=(pi/2,0,0))
move(bpy.context.object).data.materials.append(cream)
cyl('Cork coaster',(mx,my,.884),.093,.01,oak)
cube('Small desk notebook',(1.79,2.36,.902),(.25,.34,.025),teal,.012)
text('Notebook label','IDEAS',(1.79,2.37,.918),.032,paper,rot=(0,0,0),align='CENTER')

print('BUILD: chair and bedroom furniture',flush=True)
collection('05 • Upholstered desk chair')
cx,cy=-.34,.91
cyl('Chair central spindle',(cx,cy,.29),.042,.37,dark)
for i in range(5):
    t=2*pi*i/5;end=(cx+.34*cos(t),cy+.34*sin(t),.115)
    rod('Chair five-star base',(cx,cy,.18),end,.022,dark)
    wheel=cyl('Chair caster',(end[0],end[1],.078),.052,.04,black,24);wheel.rotation_euler[0]=pi/2
cube('Chair bentwood seat shell',(cx,cy,.485),(.68,.61,.08),walnut,.10)
cube('Chair linen seat cushion',(cx,cy,.545),(.64,.59,.12),linen,.10)
cube('Chair curved low back frame',(cx,cy-.275,.855),(.68,.085,.57),walnut,.075)
cube('Chair upholstered back',(cx,cy-.218,.867),(.61,.10,.49),linen,.075)
for x in [cx-.35,cx+.35]:
    rod('Chair arm support',(x,cy+.12,.50),(x,cy+.11,.75),.015,brass)
    cube('Chair wooden armrest',(x,cy,.76),(.065,.44,.055),walnut,.025)

collection('06 • Bed, textiles & bedside details')
cube('Rug woven base',(.13,.35,.045),(2.85,2.35,.023),linen,.09)
for x in [-1.20,1.46]:
    for offset in [0,.06]:cube('Rug border',(x+offset*(1 if x<0 else -1),.35,.059),(.018,2.20,.002),ochre,.002)
for i in range(95):
    x=-1.24+i*.029
    for y in [-.86,1.56]:curve('Rug fringe',[[(x,y,.05),(x+.005*sin(i),y+(-.08 if y<0 else .08),.045)]],.002,linen)
cube('Oak bed base',(-2.43,-.17,.26),(1.48,2.19,.27),walnut,.06)
for x in [-3.02,-1.83]:
    for y in [-1.09,.69]:cyl('Bed feet',(x,y,.14),.05,.26,dark)
cube('Upholstered headboard',(-2.43,.91,.76),(1.55,.12,1.12),teal,.08)
cube('Mattress',(-2.43,-.17,.49),(1.40,2.10,.24),linen,.12)

def textile(name,xmin,xmax,ymin,ymax,z,m,drop=.22):
    nx,ny=60,64;verts=[];faces=[]
    for j in range(ny+1):
        v=j/ny;y=ymin+(ymax-ymin)*v
        for i in range(nx+1):
            u=i/nx;x=xmin+(xmax-xmin)*u
            edge=max(0,(abs(u-.5)-.40)/.10)
            zz=z-drop*edge**1.4+.018*sin(u*pi)+.006*sin(u*31+v*9)+.004*sin(v*47+u*13)
            verts.append((x,y,zz))
    for j in range(ny):
        for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    ob=mesh(name,verts,faces,m)
    for p in ob.data.polygons:p.use_smooth=True
    sol=ob.modifiers.new('Soft cloth thickness','SOLIDIFY');sol.thickness=.015
    return ob
textile('Linen duvet with soft folds',-3.19,-1.66,-1.24,.48,.653,linen,.20)
textile('Ochre throw over foot of bed',-3.23,-1.61,-1.20,-.52,.68,ochre,.30)
for x in [-2.78,-2.09]:
    p=cube('Soft linen pillow',(x,.54,.735),(.62,.42,.16),linen,.15);p.rotation_euler[2]=random.uniform(-.08,.08)
cube('Bedside floating shelf',(-1.48,.77,.48),(.34,.52,.07),walnut,.02)
flat_book('Bedside book',(-1.48,.77,.52),.23,.32,.035,book_mats[1],'READ SLOWLY')

collection('07 • Shelves, art & plants')
# Shelves on the left side wall, facing the desk.
for z in [1.51,2.18,2.85]:
    cube('Floating oak wall shelf',(-3.10,1.48,z),(.44,1.52,.055),walnut,.014)
    for y in [.86,2.12]:cube('Shelf brass bracket',(-3.12,y,z-.09),(.30,.025,.16),brass,.004)
for level,z in enumerate([1.55,2.22]):
    for i in range(9):
        y=.89+i*.10;h=random.uniform(.24,.40)
        cube('Shelf book',(-3.08,y,z+h/2),(.26,.075,h),random.choice(book_mats),.005)
        for zz in [z+.035,z+h-.035]:cube('Shelf book gold band',(-2.943,y,zz),(.004,.055,.007),brass)
lathe('Shelf ceramic vase',(-3.06,1.85,2.89),[(.06,0),(.105,.06),(.09,.17),(.044,.23),(.043,.30)],cream)
curve('Vase dry branches',[[(-3.06,1.85,3.10),(-3.10,1.82,3.28),(-3.04,1.78,3.42)],[(-3.06,1.85,3.10),(-3,1.90,3.28),(-3.03,1.94,3.39)]],.003,oak)
cube('Framed print / walnut',(-3.25,-.57,2.10),(.055,1.01,1.28),walnut,.015)
cube('Framed print / paper',(-3.214,-.57,2.10),(.008,.92,1.19),paper)
# Abstract sun and hills in the framed print, all editable geometry.
sun=cyl('Print terracotta sun',(-3.204,-.55,2.31),.23,.003,book_mats[0],64);sun.rotation_euler[1]=pi/2
for k,(z,mm) in enumerate([(1.85,teal),(1.76,green),(1.66,ochre)]):
    verts=[(-3.197+k*.003,-1.0,z-.11),(-3.197+k*.003,-.14,z-.11)]
    for i in range(30,-1,-1):
        u=i/30;verts.append((-3.197+k*.003,-1.0+.86*u,z+.11*sin(u*pi*1.2+k*.7)))
    mesh('Print rolling hill',verts,[tuple(range(len(verts)))],mm)

def plant(name,loc,height=1.2,r=.22):
    x,y,z=loc
    lathe(name+' pot',(x,y,z),[(r*.70,0),(r*.9,.03),(r,height*.24),(r*1.02,height*.27),(r*.91,height*.28),(r*.88,height*.24)],terracotta)
    cyl(name+' soil',(x,y,z+height*.245),r*.86,.015,soil)
    for k in range(13):
        angle=k*2.399;h=height*(.46+.54*k/12);reach=height*(.22+.09*sin(k))
        tip=(x+reach*cos(angle),y+reach*sin(angle),z+h)
        start=(x,y,z+height*.23)
        mid=(x+reach*.34*cos(angle),y+reach*.34*sin(angle),z+h*.76)
        curve(name+' stem',[[start,mid,tip]],.0045,leafmat)
        direction=Vector((cos(angle)*.75,sin(angle)*.75,.22));side=Vector((-sin(angle),cos(angle),0))
        origin=Vector(tip);verts=[];faces=[];length=height*.27;width=height*.095
        for j in range(13):
            t=j/12;center=origin+direction*length*t+Vector((0,0,.075*sin(pi*t)-.12*t*t))
            for s in [-1,0,1]:verts.append(center+side*s*width*sin(pi*t)+Vector((0,0,-abs(s)*.018*sin(pi*t))))
        for j in range(12):
            for i in range(2):a=j*3+i;faces.append((a,a+1,a+4,a+3))
        ob=mesh(name+' leaf',verts,faces,leafmat if k%3 else leaflight)
        for p in ob.data.polygons:p.use_smooth=True
        sol=ob.modifiers.new('Leaf thickness','SOLIDIFY');sol.thickness=.0015
plant('Window rubber plant',(2.61,2.45,.04),1.55,.24)
plant('Little shelf plant',(-3.06,1.96,1.55),.49,.085)
plant('Sill plant',(1.98,3.07,1.035),.38,.08)

print('BUILD: layered city skyline',flush=True)
collection('08 • City / buildings, neon & wet streets')
building_mats=[mat('City facade '+str(i),(.012+.007*i,.021+.007*i,.04+.009*i),.40,.35) for i in range(5)]
window_mats=[mat('City window / '+n,c,.35,emission=e) for n,c,e in [('amber',(1,.55,.18),3.5),('ivory',(1,.78,.43),2.7),('ice',(.25,.62,.85),2),('dark',(.02,.06,.10),.12),('gold',(.75,.32,.10),1.8)]]
window_batches=[([],[]) for _ in window_mats]
def quad_batch(batch,points):
    vs,fs=batch;a=len(vs);vs.extend(points);fs.append((a,a+1,a+2,a+3))
def building(x,y,w,d,h,base=-4.5,idx=0):
    cube('Tower %02d / mass'%idx,(x,y,base+h/2),(w,d,h),random.choice(building_mats),.035)
    cube('Tower %02d / rooftop'%idx,(x,y,base+h+.045),(w+.08,d+.08,.09),dark,.015)
    # Window strips on the facade and visible right return.
    cols=max(3,int(w/.33));rows=max(3,int(h/.43))
    for row in range(rows):
        z=base+.26+row*.43
        if z>base+h-.2:continue
        for col in range(cols):
            xx=x-w/2+.18+col*(w-.32)/max(1,cols-1)
            material=random.choices(range(5),[.17,.13,.09,.51,.10])[0]
            ww=.09 if idx%3==0 else .14;hh=.23 if idx%4 else .30
            yy=y-d/2-.006
            quad_batch(window_batches[material],[(xx-ww/2,yy,z-hh/2),(xx+ww/2,yy,z-hh/2),(xx+ww/2,yy,z+hh/2),(xx-ww/2,yy,z+hh/2)])
        for col in range(max(2,int(d/.4))):
            yy=y-d/2+.20+col*.38;xx=x+w/2+.006
            material=random.choices(range(5),[.16,.15,.10,.48,.11])[0]
            quad_batch(window_batches[material],[(xx,yy-.07,z-.115),(xx,yy+.07,z-.115),(xx,yy+.07,z+.115),(xx,yy-.07,z+.115)])
    if idx%3==0:
        cube('Tower rooftop equipment',(x,y,base+h+.23),(w*.4,d*.45,.36),dark,.02)
        rod('Tower antenna',(x,y,base+h+.3),(x,y,base+h+1.1),.022,dark)
        red=mat('Aviation light %02d'%idx,(1,.03,.012),.3,emission=4)
        sphere('Red rooftop beacon',(x,y,base+h+1.11),(.036,.036,.045),red,12,8)

idx=0
for row,(yy,spacing,range_x) in enumerate([(13,3.6,range(-7,6)),(23,4.1,range(-8,7)),(38,4.8,range(-9,8))]):
    for i in range_x:
        xx=i*spacing+random.uniform(-.38,.38)
        h=random.uniform(5.2,8.6) if row==0 else random.uniform(7,15.5)
        if row==0 and i in [-1,0,1]:h=random.uniform(4.8,6.8)
        building(xx,yy+random.uniform(-.7,.7),random.uniform(2.1,2.9),random.uniform(2.2,3.8),h,idx=idx);idx+=1
neon_cyan=mat('Neon / pale cyan',(.08,.65,1),.25,emission=5)
neon_pink=mat('Neon / muted coral',(1,.10,.16),.25,emission=4)
neon_gold=mat('Neon / amber',(1,.38,.08),.25,emission=4)
for xx,yy,zz,word,mm in [(-5.3,10.95,3.9,'HOTEL',neon_pink),(-12.6,11.1,1.7,'NOVA',neon_cyan),(2.7,10.75,2.6,'24 / 7',neon_gold),(-1.8,21.0,8.4,'MIDNIGHT',neon_cyan)]:
    cube('Neon sign backing',(xx,yy,zz),(.82,.10,1.7 if word=='HOTEL' else .48),dark,.025)
    text('City sign '+word,'H\nO\nT\nE\nL' if word=='HOTEL' else word,(xx,yy-.061,zz-.65 if word=='HOTEL' else zz-.09),.25 if word=='HOTEL' else .22,mm,align='CENTER')
for i,batch in enumerate(window_batches):mesh('Batched city windows / '+str(i),batch[0],batch[1],window_mats[i])
wet=mat('Rain-wet asphalt',(.014,.022,.03),.18,.35)
cube('City street ground',(0,18,-4.56),(100,65,.1),wet)
for i in range(-28,22):
    x=i*1.25
    cube('Street lane marking',(x,8,-4.499),(.5,.055,.004),paper)
for i in range(45):
    x=random.uniform(-35,24);y=random.choice([6.9,8.7])+random.uniform(-.10,.10)
    cube('Distant car',(x,y,-4.23),(.74,.31,.29),random.choice(building_mats),.06)
    for yy in [-.105,.105]:sphere('Traffic light',(x-.38,y+yy,-4.19),(.025,.025,.028),neon_gold if y<8 else neon_pink,8,6)
for x in range(-28,25,4):
    rod('Street light post',(x,9.6,-4.5),(x,9.6,-2.4),.024,dark)
    rod('Street light arm',(x,9.6,-2.4),(x,9.0,-2.4),.025,dark)
    cube('Street lamp light',(x,9,-2.41),(.19,.28,.035),warm_glow,.01)

for city_object in COL.objects:
    city_object.location.z -= 10.3

collection('09 • Rain / animated streaks & droplets')
rainmat=mat('Rain / silver-blue glints',(.28,.47,.62),.14,.25,emission=.15)
rp=rainmat.node_tree.nodes['Principled BSDF'];rp.inputs['Transmission Weight'].default_value=.60;rp.inputs['IOR'].default_value=1.333
paths=[]
for i in range(280):
    x=random.uniform(-5,4);y=random.uniform(3.6,9);base_z=random.uniform(0,2.8)
    length=random.uniform(.065,.21)
    for j in range(4):
        z=base_z+j*2.8-2.8
        paths.append([(x,y,z),(x+.017,y+.005,z-length)])
rain=curve('Falling rain • looping 48 frames',paths,.0017,rainmat)
rain.location.z=0;rain.keyframe_insert(data_path='location',frame=1)
rain.location.z=-2.8;rain.keyframe_insert(data_path='location',frame=49)
if rain.animation_data and rain.animation_data.action:
    act=rain.animation_data.action
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for kp in fc.keyframe_points:kp.interpolation='LINEAR'
                    fc.modifiers.new('CYCLES')
scene.frame_set(12)
# Individual drops flattened onto the outside face of the glass.
dropmat=mat('Water drops / clear',(.86,.96,1),.075)
dp=dropmat.node_tree.nodes['Principled BSDF'];dp.inputs['Transmission Weight'].default_value=.96;dp.inputs['IOR'].default_value=1.333
verts=[];faces=[]
for i in range(430):
    x=random.uniform(-2.51,2.77);z=random.uniform(1.09,3.09);r=random.uniform(.0035,.012)
    elong=random.uniform(1.1,2.6);start=len(verts);segs=10;rings=7
    for j in range(rings+1):
        phi=pi*j/rings
        for k in range(segs):
            theta=2*pi*k/segs
            verts.append((x+r*sin(phi)*cos(theta),3.313+r*.40*sin(phi)*sin(theta),z+r*elong*cos(phi)))
    for j in range(rings):
        for k in range(segs):
            a=start+j*segs+k;b=start+j*segs+(k+1)%segs;faces.append((a,b,b+segs,a+segs))
dr=mesh('430 beads of rain on glass',verts,faces,dropmat)
for p in dr.data.polygons:p.use_smooth=True
trails=[]
for i in range(32):
    x=random.uniform(-2.45,2.70);z=random.uniform(1.4,3.08);length=random.uniform(.08,.4)
    trails.append([(x+.003*sin(k*1.6+i),3.316,z-length*k/16) for k in range(17)])
curve('Rainwater rivulets on glass',trails,.0018,dropmat)

print('BUILD: cinematic lighting and camera',flush=True)
collection('10 • Lighting & cameras')
area('Cool sky through the window',(0,3.10,2.7),(-.2,.3,.7),65,(.29,.48,1),4.4,1.7)
area('Soft warm room bounce',(1.7,-1.2,3.25),(-.8,1,.6),48,(1,.72,.43),4)
area('Bed and wall gentle fill',(-2,-.5,3.3),(-2.4,.2,.7),24,(1,.66,.37),2.2)
area('Monitor soft blue cast',(-.35,2.20,1.5),(-.35,1,.7),5,(.26,.70,1),1.0,.6)
area('City cool facade wash',(-4,5,8),(-3,15,2),1200,(.20,.34,.75),12)
area('City second facade wash',(7,8,9),(2,22,4),1800,(.18,.30,.63),15)
area('Lamp amber reflection on wall',(-1.44,2.2,1.35),(-2,3.15,1.25),8,(1,.47,.17),.4)

bpy.ops.object.camera_add(location=(4.65,-5.80,3.25))
cam=move(bpy.context.object);cam.name='Camera • quiet rainy evening'
target=Vector((-.26,1.36,1.53));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.lens=43;cam.data.sensor_width=36
scene.camera=cam
focus=bpy.data.objects.new('Camera focus • open book',None);COL.objects.link(focus);focus.location=(.15,2,1.18)
cam.data.dof.use_dof=True;cam.data.dof.focus_object=focus;cam.data.dof.aperture_fstop=9
cam.data.shift_y=-.018
cam.data.clip_end=250

# Subtle optical bloom; Blender 5 uses a compositing node group.
ng=bpy.data.node_groups.new('Rainy evening • restrained bloom','CompositorNodeTree')
scene.compositing_node_group=ng
ng.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
rl=ng.nodes.new('CompositorNodeRLayers')
gl=ng.nodes.new('CompositorNodeGlare')
gl.inputs['Type'].default_value='Fog Glow';gl.inputs['Quality'].default_value='High'
try:gl.inputs['Threshold'].default_value=2;gl.inputs['Strength'].default_value=.14
except Exception:pass
out=ng.nodes.new('NodeGroupOutput');ng.links.new(rl.outputs['Image'],gl.inputs['Image']);ng.links.new(gl.outputs['Image'],out.inputs['Image'])

# Keep the initial project view useful when opened on the user's computer.
for ob in bpy.context.selected_objects:ob.select_set(False)
cam.select_set(True);bpy.context.view_layer.objects.active=cam
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA'
            a.spaces.active.overlay.show_overlays=False
            a.spaces.active.shading.type='MATERIAL'
            a.spaces.active.shading.use_scene_world=True
            a.spaces.active.shading.use_scene_lights=True
scene['Description']='雨夜私室 / A quiet room above the city. Editable geometry, procedural materials, animated rain.'
scene['Rain animation']='48-frame loop at 24 fps. Still image uses frame 12.'
scene['Lighting']='Warm 2700 K desk lamp, blue window fill, emissive city windows.'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'雨夜私室_Rainy_Night_Room.blend'))
scene.render.filepath=os.path.join(OUT,'preview.png')
print('RENDER: preview',flush=True)
bpy.ops.render.render(write_still=True)
print('DONE: preview and editable project saved.',flush=True)
