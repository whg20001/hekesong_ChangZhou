"""Create a warm retro version of the editable rainy room with local Blender.
Run: blender --background --python build_retro.py
"""
import bpy, math, random, os, sys, json
from mathutils import Vector
from math import sin, cos, pi

OUT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(os.path.dirname(OUT), 'rainy_night_room', '雨夜私室_Rainy_Night_Room.blend')
bpy.ops.wm.open_mainfile(filepath=SOURCE)
scene = bpy.context.scene
random.seed(108)
COL = None

def collection(name):
    global COL
    COL = bpy.data.collections.new(name); scene.collection.children.link(COL)
    return COL
def move(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    COL.objects.link(o); return o
def mat(name, color, rough=.5, metal=0, emission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m
def cube(name,loc,dim,m,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=move(bpy.context.object);o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if m:o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('Soft edges','BEVEL');b.width=bevel;b.segments=4
        o.modifiers.new('Surface normals','WEIGHTED_NORMAL')
    return o
def sphere(name,loc,scale,m,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    o=move(bpy.context.object);o.name=name;o.scale=scale;o.data.materials.append(m)
    for p in o.data.polygons:p.use_smooth=True
    return o
def cyl(name,loc,r,depth,m,vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc)
    o=move(bpy.context.object);o.name=name;o.data.materials.append(m)
    b=o.modifiers.new('Rounded edge','BEVEL');b.width=min(.008,r*.12,depth*.2);b.segments=3
    o.modifiers.new('Surface normals','WEIGHTED_NORMAL');return o
def rod(name,a,b,r,m):
    v=Vector(b)-Vector(a);o=cyl(name,(Vector(a)+Vector(b))/2,r,v.length,m,16)
    o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return o
def mesh(name,verts,faces,m):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);COL.objects.link(o)
    if m:d.materials.append(m)
    return o
def curve(name,paths,r,m):
    d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=12;d.bevel_depth=r;d.bevel_resolution=2
    for points in paths:
        s=d.splines.new('POLY');s.points.add(len(points)-1)
        for p,co in zip(s.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,d);COL.objects.link(o);d.materials.append(m);return o
def lathe(name,loc,profile,m,steps=64):
    vs=[];fs=[]
    for r,z in profile:
        for i in range(steps):
            t=2*pi*i/steps;vs.append((loc[0]+r*cos(t),loc[1]+r*sin(t),loc[2]+z))
    for j in range(len(profile)-1):
        for i in range(steps):
            a=j*steps+i;b=j*steps+(i+1)%steps;fs.append((a,b,b+steps,a+steps))
    o=mesh(name,vs,fs,m)
    for p in o.data.polygons:p.use_smooth=True
    return o
FONT=bpy.data.fonts.load('C:/Windows/Fonts/segoeui.ttf')
MONO=bpy.data.fonts.load('C:/Windows/Fonts/DejaVuSansMono_0.ttf')
def text(name,body,loc,size,m,rot=(pi/2,0,0),align='LEFT',font=FONT):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size;d.font=font;d.align_x=align
    o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc;o.rotation_euler=rot;d.materials.append(m);return o
def area(name,loc,target,power,color,size,size_y=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color
    d.shape='RECTANGLE' if size_y else 'DISK';d.size=size
    if size_y:d.size_y=size_y
    o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    o.visible_glossy=False;o.visible_transmission=False;return o
def delete_prefix(prefixes):
    for o in list(bpy.data.objects):
        if any(o.name.startswith(p) for p in prefixes):bpy.data.objects.remove(o,do_unlink=True)
def recolor_noise(name,a,b):
    m=bpy.data.materials.get(name)
    if m:
        for n in m.node_tree.nodes:
            if n.type=='VALTORGB':
                n.color_ramp.elements[0].color=(*a,1);n.color_ramp.elements[1].color=(*b,1)

paper=bpy.data.materials['Warm ivory book paper']
ink=bpy.data.materials['Printed charcoal ink']
brass=bpy.data.materials['Brushed aged brass']
walnut=bpy.data.materials['Walnut / long open grain']
black=bpy.data.materials['Soft black polymer']
linen=bpy.data.materials['Natural woven linen']
cream=bpy.data.materials['Ivory ceramic']
terracotta=bpy.data.materials['Earthenware']
soil=bpy.data.materials['Potting soil']
leafmat=bpy.data.materials['Leaves / jade']
leaflight=bpy.data.materials['Leaves / young sage']
warm=bpy.data.materials['Warm opal light']
enamel=mat('Burnished copper enamel',(.38,.105,.045),.27,.62)
shell=mat('Retro computer / charcoal plastic',(.045,.046,.042),.37,.08)
beige=mat('Retro computer / warm beige',(.47,.43,.33),.51)
blue=mat('Phosphor / deep cobalt',(.014,.035,.28),.34,emission=.8)
white=mat('Phosphor / warm white',(.66,.84,1),.5,emission=1.3)
cyan=mat('Phosphor / soft cyan',(.12,.55,.73),.5,emission=1.5)
scan=mat('CRT scan line',(.009,.015,.06),.6,emission=.1)
bookcolors=[mat('Cloth book / '+n,c,.8) for n,c in [('navy',(.03,.065,.13)),('coral',(.48,.12,.065)),('sage',(.16,.27,.18)),('ivory',(.67,.59,.41)),('ochre',(.52,.29,.075)),('wine',(.20,.04,.055))]]

print('RETRO: room and window',flush=True)
recolor_noise('Blue slate limewash',(.28,.20,.135),(.48,.365,.25))
recolor_noise('Heavy oatmeal curtain',(.42,.35,.25),(.72,.63,.47))
recolor_noise('Walnut / long open grain',(.085,.037,.017),(.32,.16,.063))
frame=mat('Window / painted warm ivory',(.44,.37,.26),.51)
for o in bpy.data.objects:
    if o.name.startswith(('Window outer','Window slender')):
        o.data.materials.clear();o.data.materials.append(frame)
        if o.name.startswith('Window slender'):o.scale.x=1.6
delete_prefix(['Monitor base','Monitor upright','Monitor housing','Display glass','Screen ','Editor title','Window control','Explorer','Code line','On-screen','Preview label','Status bar','Monitor power','Reference book','Reference pages','Reference spine','Spine title','Gilt book','Bookend','Design reference','Light monograph','Small desk notebook','Notebook label'])
# Replace the desk lamp, preserving the base room.
delete_prefix(['Lamp ','Green enamel lamp shade','Ivory shade interior','Warm desk lamp','Monitor cable'])
# A foreground chair would obscure the desk in the near-frontal composition.
for o in bpy.data.collections['05 • Upholstered desk chair'].objects:o.location.x-=1.0;o.location.y-=.45
# Compact original keyboard, with a visibly wider space key.
for o in bpy.data.objects:
    if o.name.startswith(('Mechanical keyboard','Keyboard key','Space bar')):o.location.y-=.08
for o in bpy.data.objects:
    if o.name.startswith(('Hand-thrown tea mug','Tea surface','Cork coaster')):o.location.x-=2.43;o.location.y-=.25
# Handle was an unnamed torus: identify its original position.
for o in bpy.data.objects:
    if o.type=='MESH' and abs(o.location.x-1.777)<.01 and abs(o.location.y-1.91)<.01:o.location.x-=2.43;o.location.y-=.25

collection('11 • Retro CRT computer')
cube('Desktop computer main unit',(-.15,2.26,.975),(1.16,.66,.18),beige,.028)
cube('Desktop dark faceplate',(-.15,1.923,.982),(1.10,.018,.133),shell,.012)
cube('Disk drive opening',(.15,1.910,1.005),(.31,.006,.017),black,.003)
cube('Disk eject button',(.33,1.901,.971),(.045,.012,.016),beige,.003)
text('Computer model','ATELIER   /   PERSONAL COMPUTER',(-.66,1.899,.96),.016,paper,font=MONO)
sphere('Power LED',(-.61,1.894,1.012),(.006,.003,.006),cyan,12,8)
for i in range(9):cube('Computer front vents',(-.40+i*.032,1.908,1.013),(.018,.005,.021),black,.002)
cube('CRT swivel foot',(-.15,2.28,1.10),(.49,.40,.08),shell,.04)
cube('CRT deep case',(-.15,2.40,1.54),(1.02,.64,.87),shell,.085)
cube('CRT front bezel',(-.15,2.065,1.55),(1.045,.10,.90),shell,.065)
cube('CRT inner screen recess',(-.15,2.005,1.592),(.908,.025,.688),black,.048)
cube('CRT blue convex display',(-.15,1.985,1.595),(.857,.025,.626),blue,.045)
for i in range(142):
    z=1.298+i*.00415
    cube('CRT fine scanline',(-.15,1.968,z),(.798,.001,.0008),scan)
cube('Terminal header line',(-.15,1.963,1.819),(.74,.001,.002),white)
text('Terminal title','RAINY NIGHT  /  PERSONAL SPACE',(-.51,1.960,1.845),.023,white,font=MONO)
text('Terminal main','AFTER HOURS',(-.15,1.960,1.708),.068,white,align='CENTER',font=MONO)
text('Terminal subtitle','a quiet place to think',(-.15,1.960,1.657),.024,cyan,align='CENTER',font=MONO)
text('Terminal status','> reading, making, dreaming_',(-.50,1.960,1.540),.023,white,font=MONO)
for i in range(25):cube('Terminal progress',(-.49+i*.028,1.960,1.465),(.021,.001,.025),white if i<17 else scan)
text('Terminal footer','OCT 23    RAIN: ON     23:48',(-.50,1.960,1.346),.022,white,font=MONO)
text('CRT badge','ATELIER',(-.57,2.003,1.157),.026,paper,font=MONO)
text('CRT model','COLOR DISPLAY  14',(.02,2.003,1.157),.013,paper,font=MONO)
for i in range(3):
    knob=cyl('CRT adjustment knob',(.24+i*.051,1.998,1.205),.013,.014,beige,24);knob.rotation_euler[0]=pi/2
sphere('CRT green LED',(.34,1.981,1.164),(.004,.002,.004),cyan,12,8)
for i in range(12):cube('CRT right cooling vent',(.365,2.28+i*.024,1.60),(.005,.012,.23),black,.003)
curve('Computer power cable',[[(-.16,2.71,1.2),(-.23,2.76,.9),(-.48,2.76,.7),(-.44,2.6,.2)]],.008,black)
area('CRT blue glow',(-.15,1.92,1.59),(-.1,1.15,.9),5,(.22,.36,1),.75,.55)

collection('12 • Copper reading lamp')
lx,ly=-1.11,2.10
cyl('Copper lamp weighted base',(lx,ly,.913),.17,.06,enamel)
cyl('Lamp base inset',(lx,ly,.945),.139,.009,brass)
rod('Lamp upright',(lx,ly,.95),(lx+.04,ly,1.58),.013,brass)
sphere('Lamp pivot',(lx+.04,ly,1.58),(.033,.033,.033),enamel)
rod('Lamp upper arm',(lx+.04,ly,1.58),(lx+.11,ly+.025,1.75),.014,brass)
lathe('Copper lampshade',(lx+.11,ly+.025,1.68),[(.232,-.055),(.235,-.04),(.214,.02),(.166,.14),(.089,.24),(.045,.26),(.035,.25)],enamel)
lathe('Warm ivory shade lining',(lx+.11,ly+.025,1.68),[(.226,-.054),(.225,-.035),(.203,.02),(.157,.14),(.083,.23)],cream)
lathe('Polished lampshade lip',(lx+.11,ly+.025,1.68),[(.232,-.057),(.237,-.05),(.236,-.04),(.231,-.037)],brass)
sphere('Lamp warm bulb',(lx+.11,ly+.025,1.69),(.04,.04,.055),warm)
area('Tungsten pool on desk',(lx+.10,ly+.015,1.64),(-.45,1.8,.87),48,(1,.55,.25),.24)
area('Lamp soft shade bounce',(lx+.10,ly,1.66),(-1.5,3.2,1.35),9,(1,.45,.16),.4)
curve('Lamp black cord',[[(lx,ly+.05,.90),(lx-.2,2.4,.89),(-1.8,2.5,.87),(-1.8,2.5,.2)]],.005,black)
cyl('Lamp switch',(lx+.08,ly-.07,.955),.013,.012,black)

collection('13 • Books, analog objects and desk details')
def flat_book(name,loc,w,d,h,cover,title):
    x,y,z=loc
    cube(name+' paper',(x,y,z+h/2),(w-.014,d-.019,h-.014),paper,.005)
    for zz in [z+.003,z+h-.003]:cube(name+' cover',(x,y,zz),(w,d,.009),cover,.004)
    cube(name+' spine',(x,y-d/2,z+h/2),(w,.02,h),cover,.004)
    text(name+' title',title,(x-w*.43,y-d/2-.012,z+h*.30),min(.025,h*.38),paper,font=MONO)
    for j in range(4):cube(name+' fine page edges',(x+w/2-.008,y,z+.015+j*(h-.03)/4),(.002,d-.025,.0008),linen)
    for xx in [x-w*.45,x+w*.44]:cube(name+' spine detail',(xx,y-d/2-.012,z+h/2),(.003,.003,h*.6),brass)
titles=['COMPUTER GRAPHICS','THE ART OF CODE','DESIGN PATTERNS','PYTHON / NOTES','LIGHT & SPACE','CREATIVE SYSTEMS']
z=.886
for i,title in enumerate(titles):
    h=[.065,.075,.06,.055,.07,.055][i]
    flat_book('Stack / '+title,(1.22+random.uniform(-.04,.04),2.28+random.uniform(-.035,.035),z),[.64,.69,.60,.65,.62,.56][i],.35,h,bookcolors[i],title);z+=h+.002
flat_book('Left book / film',(-1.52,2.31,.887),.43,.30,.055,bookcolors[2],'WAYS OF SEEING')
flat_book('Left book / field',(-1.51,2.31,.944),.40,.28,.045,bookcolors[3],'A FIELD GUIDE')
flat_book('Foreground notebook',(-1.34,1.69,.89),.37,.36,.025,bookcolors[1],'')
cube('Notebook loose paper',(-1.33,1.68,.906),(.32,.31,.004),paper,.002)
text('Notebook handwritten heading','THINGS TO MAKE',(-1.46,1.76,.910),.018,ink,rot=(0,0,0),font=MONO)
for i in range(7):curve('Notebook pencil line',[[(-1.45,1.72-i*.025,.911),(-1.26+random.uniform(-.04,.06),1.72-i*.025,.911)]],.0006,ink)
rod('Writing pencil',(-1.19,1.56,.924),(-1.12,1.86,.924),.005,brass)
rod('Graphite point',(-1.12,1.86,.924),(-1.115,1.88,.924),.003,ink)
# Ceramic pencil cup with individual pencils.
lathe('Pencil cup',(-1.77,1.83,.885),[(.065,0),(.071,.015),(.078,.19),(.070,.195),(.064,.18),(.058,.02)],cream)
for i in range(5):
    x=-1.77+random.uniform(-.045,.045);y=1.83+random.uniform(-.04,.04)
    rod('Pencil in cup',(x,y,.91),(x+(i-2)*.014,y+.025,1.19+random.uniform(-.04,.05)),.004,bookcolors[i])
# Pocket radio and its speaker grille.
cube('Small tabletop radio',(1.72,2.32,1.04),(.26,.15,.30),beige,.03)
cube('Radio face',(1.72,2.238,1.04),(.224,.012,.26),shell,.018)
cube('Radio tuning window',(1.72,2.227,1.13),(.182,.008,.037),black,.004)
text('Radio dial','FM  98.6',(1.635,2.22,1.122),.018,paper,font=MONO)
for j in range(8):curve('Radio grille',[[ (1.63,2.224,.94+j*.016),(1.81,2.224,.94+j*.016)]],.0025,black)
knob=cyl('Radio volume',(1.79,2.215,1.085),.016,.012,brass,24);knob.rotation_euler[0]=pi/2
rod('Radio telescopic antenna',(1.80,2.32,1.19),(1.87,2.34,1.58),.0035,brass)
# A cassette on top of the stack.
cube('Audio cassette',(1.23,2.27,1.300),(.24,.155,.025),black,.01)
cube('Cassette paper label',(1.23,2.27,1.314),(.211,.114,.001),paper,.006)
text('Mixtape label','NIGHT / SIDE A',(1.23,2.30,1.317),.017,ink,rot=(0,0,0),align='CENTER',font=MONO)
for xx in [1.18,1.28]:
    cyl('Cassette spool',(xx,2.25,1.317),.020,.003,shell,24)
    cyl('Cassette spool centre',(xx,2.25,1.319),.008,.003,paper,16)
# Digital clock at the foot of the book stack.
cube('Digital clock walnut body',(.72,2.14,.954),(.30,.14,.135),walnut,.021)
cube('Digital clock glass',(.72,2.064,.954),(.263,.012,.100),black,.012)
text('Digital clock display','23:48',(.72,2.056,.938),.047,cyan,align='CENTER',font=MONO)
# Reading glasses resting across the open book, with folded temples.
paths=[]
for xx in [.80,1.00]:paths.append([(xx+.081*cos(t*2*pi/64),1.81+.056*sin(t*2*pi/64),.969) for t in range(65)])
paths.append([(.881,1.81,.969),(.90,1.825,.972),(.919,1.81,.969)])
paths.extend([[(.72,1.81,.969),(.73,1.95,.981),(.83,1.99,.978)],[(1.08,1.81,.969),(1.07,1.95,.981),(.98,1.99,.978)]])
curve('Reading glasses thin bronze frames',paths,.0025,brass)
# Keyboard key legends, all geometry.
for row,line in enumerate(['ZXCVBNM,./','ASDFGHJKL;','QWERTYUIOP','1234567890']):
    for j,ch in enumerate(line):text('Key legend '+ch,ch,(-.70+j*.058,1.707+row*.05,.973),.011,ink,rot=(0,0,0),align='CENTER',font=MONO)
curve('Keyboard coiled cord',[[(-.75+.014*cos(i*.7),2.00+i*.0018,.905+.014*sin(i*.7)) for i in range(100)]],.0035,black)

def plant(name,loc,height=.85,r=.16):
    x,y,z=loc
    lathe(name+' pot',loc,[(r*.7,0),(r*.86,.02),(r,height*.25),(r*1.04,height*.27),(r*.90,height*.28),(r*.87,height*.245)],terracotta)
    cyl(name+' soil',(x,y,z+height*.245),r*.86,.014,soil)
    for k in range(16):
        a=k*2.399;h=height*(.44+.56*k/15);reach=height*(.19+.08*sin(k))
        tip=(x+reach*cos(a),y+reach*sin(a),z+h)
        curve(name+' stem',[[(x,y,z+height*.23),(x+reach*.4*cos(a),y+reach*.4*sin(a),z+h*.8),tip]],.003,leafmat)
        direction=Vector((cos(a)*.8,sin(a)*.8,.12));side=Vector((-sin(a),cos(a),0));origin=Vector(tip)
        vs=[];fs=[];L=height*.3;W=height*.10
        for j in range(17):
            t=j/16;c=origin+direction*L*t+Vector((0,0,.035*sin(pi*t)-.08*t*t))
            for s in [-1,0,1]:vs.append(c+side*s*W*sin(pi*t)+Vector((0,0,-abs(s)*.013*sin(pi*t))))
        for j in range(16):
            for i in range(2):a0=j*3+i;fs.append((a0,a0+1,a0+4,a0+3))
        o=mesh(name+' leaf',vs,fs,leafmat if k%4 else leaflight)
        for p in o.data.polygons:p.use_smooth=True
        cpoints=[origin+direction*L*j/16+Vector((0,0,.036*sin(pi*j/16)-.08*(j/16)**2)) for j in range(17)]
        curve(name+' leaf vein',[cpoints],.0009,leaflight)
plant('Desk pothos',(-1.73,2.48,.887),.77,.15)

print('RETRO: skyline and rain',flush=True)
city=bpy.data.collections.get('08 • City / buildings, neon & wet streets')
for o in list(city.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections.remove(city)
collection('14 • Midnight city / editable architecture')
facades=[mat('Night concrete '+str(i),(.019+i*.007,.031+i*.007,.052+i*.008),.5,.16) for i in range(5)]
lit=[mat('Window light '+str(i),c,.4,emission=e) for i,(c,e) in enumerate([((1,.60,.28),2.0),((1,.82,.52),2.4),((.32,.59,.80),1.6),((.03,.065,.10),.1),((.70,.37,.14),1.3)])]
batches=[([],[]) for m in lit]
def quad(batch,pts):
    vs,fs=batch;n=len(vs);vs.extend(pts);fs.append((n,n+1,n+2,n+3))
def building(x,y,w,d,h,base,idx):
    cube('City tower %02d'%idx,(x,y,base+h/2),(w,d,h),facades[idx%5],.018)
    cube('City rooftop parapet',(x,y,base+h),(w+.06,d+.06,.10),facades[(idx+2)%5],.01)
    cols=max(3,int(w/.31));rows=int(h/.37)
    for j in range(rows):
        z=base+.24+j*.37
        if j%6==0:cube('Facade floor belt',(x,y-d/2-.006,z-.14),(w,.02,.025),facades[(idx+3)%5])
        for k in range(cols):
            xx=x-w/2+.18+k*(w-.36)/max(1,cols-1);yy=y-d/2-.02
            n=random.choices(range(5),[.18,.23,.12,.38,.09])[0];ww=.095 if idx%4 else .14;hh=.20
            quad(batches[n],[(xx-ww/2,yy,z-hh/2),(xx+ww/2,yy,z-hh/2),(xx+ww/2,yy,z+hh/2),(xx-ww/2,yy,z+hh/2)])
        for k in range(max(2,int(d/.35))):
            yy=y-d/2+.18+k*.35;xx=x+w/2+.012;n=random.choices(range(5),[.2,.2,.1,.4,.1])[0]
            quad(batches[n],[(xx,yy-.05,z-.10),(xx,yy+.05,z-.10),(xx,yy+.05,z+.1),(xx,yy-.05,z+.1)])
    if idx%3==0:
        cube('Rooftop mechanical room',(x,y,base+h+.2),(w*.4,d*.4,.4),facades[idx%5],.01)
        rod('Rooftop aerial',(x,y,base+h+.2),(x,y,base+h+.9),.014,black)
        sphere('Aviation beacon',(x,y,base+h+.9),(.023,.023,.03),red,12,8)
red=mat('Neon coral',(1,.05,.04),.4,emission=3)
neon=mat('Neon cyan',(.12,.58,.75),.4,emission=3)
gold=mat('Neon warm white',(1,.70,.30),.4,emission=3)
idx=0
for row,(yy,spacing,count) in enumerate([(13.8,2.65,6),(23,3.2,8),(37,3.9,10)]):
    for i in range(-count,count+1):
        h=random.uniform(4.4,7) if row==0 else random.uniform(7,12) if row==1 else random.uniform(10,16)
        if row==0 and i in [-1,0,1]:h=[5.4,4.8,5.9][i+1]
        building(i*spacing+random.uniform(-.3,.3),yy+random.uniform(-.4,.4),random.uniform(1.9,2.45) if row==0 else random.uniform(2.3,3.1),2.0+row*.4,h,-4.4,idx);idx+=1
for i,b in enumerate(batches):mesh('City windows / batch '+str(i),b[0],b[1],lit[i])
for x,y,z,label,mm in [(-3.7,12.2,1.65,'HOTEL',red),(3.0,12.1,2.0,'METRO',gold),(-1.3,21.2,4.0,'MIDNIGHT',neon),(6.2,12.2,2.9,'24 / 7',neon)]:
    vertical=label=='HOTEL';w=.45 if vertical else 1.45;h=1.5 if vertical else .46
    cube('Neon sign / '+label,(x,y,z),(w,.09,h),black,.018)
    text('Neon lettering / '+label,'H\nO\nT\nE\nL' if vertical else label,(x,y-.052,z-.58 if vertical else z-.10),.235 if vertical else .25,mm,align='CENTER',font=FONT)
    curve('Neon sign border',[[(x-w/2+.035,y-.055,z-h/2+.035),(x+w/2-.035,y-.055,z-h/2+.035),(x+w/2-.035,y-.055,z+h/2-.035),(x-w/2+.035,y-.055,z+h/2-.035),(x-w/2+.035,y-.055,z-h/2+.035)]],.006,mm)
wet=mat('Wet city asphalt',(.02,.027,.037),.16,.5)
cube('Rain-wet street',(0,10,-4.45),(80,50,.08),wet)
for i in range(-25,26):
    x=i*.92;y=random.choice([8.2,9.4]);cube('City traffic',(x,y,-4.20),(.55,.24,.24),facades[i%5],.04)
    for yoff in [-.085,.085]:sphere('Traffic light',(x-.28,y+yoff,-4.17),(.018,.018,.021),gold if y<9 else red,8,6)
for x in range(-24,25,3):
    rod('City street lamp',(x,10,-4.4),(x,10,-2.5),.017,black)
    rod('City street lamp arm',(x,10,-2.5),(x,9.65,-2.5),.015,black)
    sphere('City street lamp glow',(x,9.65,-2.51),(.06,.06,.03),gold,12,8)
# Refine the scale of rain streaks and add small droplets to the pane.
rain=bpy.data.objects.get('Falling rain • looping 48 frames')
if rain:rain.data.bevel_depth=.00085
collection('15 • Fine rain on window')
dropmat=bpy.data.materials['Water drops / clear']
vs=[];fs=[]
for i in range(850):
    x=random.uniform(-2.50,2.76);z=random.uniform(1.10,3.09);r=random.uniform(.0012,.0045);start=len(vs)
    for j in range(6):
        p=pi*j/5
        for k in range(8):
            t=2*pi*k/8;vs.append((x+r*sin(p)*cos(t),3.315+r*.55*sin(p)*sin(t),z+r*1.6*cos(p)))
    for j in range(5):
        for k in range(8):
            a=start+j*8+k;b=start+j*8+(k+1)%8;fs.append((a,b,b+8,a+8))
o=mesh('850 fine beads of water',vs,fs,dropmat)
for p in o.data.polygons:p.use_smooth=True

print('RETRO: lights, cameras and save',flush=True)
for name,power in [('Soft warm room bounce',65),('Bed and wall gentle fill',35),('Cool sky through the window',35),('Monitor soft blue cast',0),('Lamp amber reflection on wall',0)]:
    if name in bpy.data.objects:bpy.data.objects[name].data.energy=power
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.16
scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.65
collection('16 • Portrait and room cameras')
area('Soft front amber fill',(-.7,-.8,2.7),(0,2.2,1.0),38,(1,.72,.48),3.0)
def camera(name,loc,target,lens,fstop):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=300
    d.dof.use_dof=True;d.dof.focus_distance=(Vector((-.15,2.07,1.45))-o.location).length;d.dof.aperture_fstop=fstop
    return o
hero=camera('CAM 01 • Rain at the window',(.10,-3.60,2.15),(0,2.18,1.67),49,7.1)
wide=camera('CAM 02 • Personal room',(4.65,-5.80,3.25),(-.26,1.36,1.53),43,9)
wide.data.shift_y=-.018
detail=camera('CAM 03 • Lamp and reading',(2.8,-1.6,2.35),(-.20,2.1,1.40),49,6.3)
scene.camera=hero
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.035
scene.cycles.max_bounces=10;scene.cycles.transmission_bounces=8
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
scene.cycles.device='GPU'
scene.render.resolution_x=2400;scene.render.resolution_y=1500;scene.render.resolution_percentage=45
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
scene.frame_set(12)
ng=scene.compositing_node_group
for n in ng.nodes:
    if n.type=='GLARE':
        n.inputs['Threshold'].default_value=1.4;n.inputs['Strength'].default_value=.18
scene['Description']='雨落之后 / AFTER HOURS — retro personal room with real 3D city, rain, a copper desk lamp and a CRT computer.'
scene['Cameras']='CAM 01: near-frontal window desk; CAM 02: whole room; CAM 03: desk detail.'
scene['Rain animation']='48 frames, 24 fps, seamlessly looping falling rain; static glass droplets and trails.'
for o in bpy.context.selected_objects:o.select_set(False)
hero.select_set(True);bpy.context.view_layer.objects.active=hero
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False
            a.spaces.active.shading.type='MATERIAL';a.spaces.active.shading.use_scene_world=True;a.spaces.active.shading.use_scene_lights=True
bpy.ops.file.pack_all()
scene.render.filepath=os.path.join(OUT,'preview.png')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'After_Hours_Rainy_Room.blend'))
bpy.ops.render.render(write_still=True)
print('PREVIEW COMPLETE',flush=True)
