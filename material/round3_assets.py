"""Detailed museum bust, baked bronze, timber beams, and picture lights.

Pure Blender geometry. Helpers are shared with build_models.py. The incremental
round-three updater uses these functions without rebuilding existing objects.
"""
import bpy
import bmesh
import math
import struct
import zlib
from pathlib import Path
from math import sin,cos,pi,exp
from mathutils import Vector


def activate(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True);bpy.context.view_layer.objects.active=o


def finish(g,o,p=None,smooth=True,weighted=False):
    activate(o)
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free();o.data.update()
    for f in o.data.polygons:f.use_smooth=smooth
    if weighted:
        mod=o.modifiers.new('Applied weighted surface normals','WEIGHTED_NORMAL')
        mod.keep_sharp=True;mod.weight=35
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if p is not None:g.origin(o,p)
    o['preserve_part']=True
    o['revision']='round3'
    return o


def round_edges(o,segments=3):
    for m in o.modifiers:
        if m.type=='BEVEL':m.segments=segments
    return o


def smooth_path(points,steps=5):
    points=[Vector(p) for p in points];out=[]
    for i in range(len(points)-1):
        a=points[max(i-1,0)];b=points[i];c=points[i+1];d=points[min(i+2,len(points)-1)]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out+[points[-1]]


def interpolate(profile,t):
    i=min(int(t),len(profile)-2);u=t-i
    a=Vector(profile[max(i-1,0)]);b=Vector(profile[i]);c=Vector(profile[i+1]);d=Vector(profile[min(i+2,len(profile)-1)])
    return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)


def oval_loft(g,name,profile,n=48,rows=None,deform=None):
    if rows:
        profile=[interpolate(profile,(len(profile)-1)*i/(rows-1)) for i in range(rows)]
    verts=[];faces=[]
    for w,d,y,z in profile:
        for i in range(n):
            a=2*pi*i/n
            p=(w*cos(a),y+d*sin(a),z)
            verts.append(deform(p,a,w,d) if deform else p)
    for j in range(len(profile)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces += [tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))]
    return g.mesh(name,verts,faces,'sculpture')


def facial_head(g):
    profile=[(.024,.032,5.485,1.627),(.075,.071,5.485,1.646),(.112,.094,5.483,1.675),
      (.133,.106,5.480,1.716),(.141,.115,5.480,1.760),(.140,.118,5.480,1.805),
      (.141,.116,5.480,1.845),(.137,.113,5.482,1.882),(.123,.101,5.485,1.921),
      (.088,.074,5.485,1.951),(.025,.024,5.485,1.968)]
    def deform(p,a,w,d):
        x,y,z=p
        # A subtly squared jaw and broad forehead, with actual orbital recesses.
        x=w*math.copysign(abs(cos(a))**.86,cos(a))
        y=5.48+d*math.copysign(abs(sin(a))**.88,sin(a))
        f=max(0,-sin(a))**5
        sockets=sum(.012*exp(-((x-s*.060)/.034)**2-((z-1.804)/.021)**2) for s in (-1,1))
        cheeks=sum(.010*exp(-((x-s*.085)/.04)**2-((z-1.752)/.035)**2) for s in (-1,1))
        brows=sum(.009*exp(-((x-s*.06)/.040)**2-((z-1.834)/.018)**2) for s in (-1,1))
        muzzle=.010*exp(-(x/.053)**2-((z-1.695)/.032)**2)
        return (x,y+f*(sockets-cheeks-brows-muzzle),z)
    parts=[oval_loft(g,'Sculpt_head_anatomy',profile,64,44,deform)]
    # A fused bridge, rounded tip, and two alae, rather than a triangular nose.
    nose=[(.008,.006,5.357,1.821),(.014,.013,5.350,1.796),(.017,.022,5.338,1.766),
          (.025,.025,5.329,1.747),(.020,.014,5.342,1.735)]
    parts.append(oval_loft(g,'Sculpt_nasal_bridge',nose,28,15))
    for s in (-1,1):
        parts.append(g.ellipsoid('Sculpt_nose_ala',(s*.024,5.341,1.742),(.016,.018,.012),'sculpture',24,12))
        parts.append(g.ellipsoid('Sculpt_ear_base',(s*.144,5.486,1.785),(.025,.024,.056),'sculpture',24,16))
    head=g.join(parts,'Sculpt_fused_head')
    activate(head);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    mod=head.modifiers.new('Sculpted union','REMESH');mod.mode='VOXEL';mod.voxel_size=.0024
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=head.modifiers.new('Sculpt polish','SMOOTH');mod.factor=.38;mod.iterations=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    head.data.calc_loop_triangles();count=len(head.data.loop_triangles)
    if count>6500:
        mod=head.modifiers.new('Controlled face density','DECIMATE');mod.ratio=6500/count
        bpy.ops.object.modifier_apply(modifier=mod.name)
    finish(g,head,None,True)
    return head


def make_hair(g):
    parts=[];verts=[];faces=[];n=56;rows=15
    for j in range(rows):
        t=.012+(1-.012)*j/(rows-1)
        for i in range(n):
            a=2*pi*i/n;p=t*(1.73+.28*sin(a)+.035*sin(9*a)+.022*cos(5*a))
            ripple=.0035*(.5+.5*cos(9*a+2.7*t))*sin(p)**.7
            x=(.145+ripple)*sin(p)*cos(a)
            y=5.48+(.121+ripple)*sin(p)*sin(a)
            z=1.866+(.131+ripple)*cos(p)
            part=.004*exp(-((x-(.043+.015*cos(p)))/.008)**2)*max(0,cos(p))
            verts.append((x,y,z-part))
    for j in range(rows-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    faces += [tuple(reversed(range(n))),tuple((rows-1)*n+i for i in range(n))]
    parts.append(g.mesh('Sculpt_hair_foundation',verts,faces,'sculpture'))
    # Broad swept locks are raised, tapered solids, separated by visible grooves.
    for i,x in enumerate((-.122,-.097,-.072,-.047,-.022,.003,.028,.074,.103)):
        pts=[]
        for j in range(25):
            t=j/24
            u=x/.145*(1-.24*sin(pi*t))+.11*sin(pi*t)
            v=-.982*math.sqrt(max(.001,1-u*u))*cos(pi*t)
            nz=math.sqrt(max(.001,1-u*u-v*v))
            normal=Vector((u/.145,v/.121,nz/.131)).normalized()
            pts.append(Vector((.145*u,5.48+.121*v,1.866+.131*nz))+normal*.0035)
        vs=[];fs=[];sides=8
        for j,p in enumerate(pts):
            tangent=(pts[min(j+1,len(pts)-1)]-pts[max(0,j-1)]).normalized()
            normal=Vector((p.x/.145,(p.y-5.48)/.121,(p.z-1.866)/.131)).normalized()
            u=tangent.cross(normal).normalized();v=u.cross(tangent).normalized()
            taper=.35+.65*sin(pi*j/(len(pts)-1))**.6
            for k in range(sides):
                a=2*pi*k/sides
                vs.append(tuple(p+taper*(.0125*cos(a)*u+.007*sin(a)*v)))
        for j in range(len(pts)-1):
            for k in range(sides):
                a=j*sides+k;b=j*sides+(k+1)%sides;fs.append((a,b,b+sides,a+sides))
        fs += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+k for k in range(sides))]
        parts.append(g.mesh('Sculpt_swept_hair_lock',vs,fs,'sculpture'))
    return parts


def make_torso(g):
    profiles=[(.215,.105,5.5,1.205),(.274,.129,5.5,1.29),(.310,.140,5.5,1.36),
      (.322,.137,5.5,1.425),(.305,.124,5.5,1.477),(.258,.105,5.5,1.524),(.117,.080,5.5,1.573)]
    def cloth(p,a,w,d):
        x,y,z=p;f=max(0,-sin(a))**7
        # Arced lower truncation, shoulder mass, and quiet diagonal cloth folds.
        if z<1.29:z+=.073*(abs(x)/.215)**2*max(0,1-(z-1.205)/.085)
        line=.115+(1.5-z)*.7
        ridges=sum(.006*exp(-((x-s*line)/.018)**2) for s in (-1,1))
        y-=f*ridges*exp(-((z-1.405)/.105)**2)
        return x,y,z
    parts=[oval_loft(g,'Sculpt_jacket_with_shoulders',profiles,64,26,cloth),
           g.cyl('Sculpt_short_neck_support',(0,5.5,1.164),.16,.118,'sculpture',40,b=.006),
           g.ellipsoid('Sculpt_neck',(0,5.49,1.594),(.078,.073,.086),'sculpture',32,16)]
    # Standing collar with visible top thickness and a small front opening.
    n=44;vs=[];fs=[]
    for w,d,z in [(.101,.087,1.551),(.103,.087,1.608),(.091,.075,1.608),(.089,.075,1.553)]:
        for i in range(n):
            a=-pi/2+.1+(2*pi-.2)*i/(n-1);vs.append((w*cos(a),5.49+d*sin(a),z))
    for j in range(4):
        for i in range(n-1):
            a=j*n+i;b=j*n+i+1;c=((j+1)%4)*n+i+1;d=((j+1)%4)*n+i
            fs.append((a,b,c,d))
    fs += [(0,n,2*n,3*n),(n-1,4*n-1,3*n-1,2*n-1)]
    collar=g.mesh('Sculpt_thick_mandarin_collar',vs,fs,'sculpture');g.bevel(collar,.002);round_edges(collar,2)
    parts.append(collar)
    # Front placket follows the chest surface rather than floating as a box.
    vs=[];fs=[]
    for z,y in [(1.27,5.369),(1.34,5.353),(1.42,5.353),(1.49,5.377),(1.556,5.403)]:
        vs.extend([(-.014,y,z),(.014,y,z)])
    for j in range(4):fs.append((2*j,2*j+1,2*j+3,2*j+2))
    placket=g.mesh('Sculpt_placket',vs,fs,'sculpture')
    m=placket.modifiers.new('Fabric thickness','SOLIDIFY');m.thickness=.006
    g.bevel(placket,.002);round_edges(placket,2);parts.append(placket)
    for z,y in [(1.305,5.354),(1.389,5.342),(1.478,5.365)]:
        parts.append(round_edges(g.cyl('Sculpt_uniform_button',(0,y,z),.009,.007,'sculpture',20,(pi/2,0,0),.0015),2))
    for s in (-1,1):
        x=s*.146
        # Curved pocket panels, thick folded flaps, and softly raised seams.
        pocket=round_edges(g.box('Sculpt_chest_pocket',(x,5.370,1.359),(.112,.012,.086),'sculpture',.004),3)
        parts.append(pocket)
        vs=[(x-.061,5.356,1.419),(x+.061,5.356,1.419),(x+.059,5.352,1.394),
            (x,5.348,1.385),(x-.059,5.352,1.394)]
        flap=g.mesh('Sculpt_folded_pocket_flap',vs,[(0,1,2,3,4)],'sculpture')
        m=flap.modifiers.new('Fold thickness','SOLIDIFY');m.thickness=.006
        g.bevel(flap,.002);round_edges(flap,2);parts.append(flap)
        pts=smooth_path([(s*.098,5.424,1.546),(s*.167,5.414,1.518),(s*.248,5.432,1.481),(s*.282,5.456,1.455)],4)
        parts.append(g.tube('Sculpt_shoulder_seam',pts,.003,'sculpture',6))
    return parts


def face_details(g):
    parts=[]
    for s in (-1,1):
        x=s*.060
        parts.append(g.ellipsoid('Sculpt_eye',(x,5.363,1.805),(.026,.013,.010),'sculpture',20,10))
        for upper in (True,False):
            pts=[]
            for i in range(17):
                a=pi*i/16
                pts.append((x+.027*cos(a),5.349-.002*sin(a),1.805+(.011 if upper else -.008)*sin(a)))
            parts.append(g.tube('Sculpt_eyelid',pts,.0014,'sculpture',6))
        parts.append(g.ring('Sculpt_iris',(x,5.349,1.805),.0055,'sculpture',.0008,n=20,sides=4))
        # Complete helix, antihelix and ear lobe, all backed by fused ear volume.
        pts=[]
        for i in range(32):
            a=2*pi*i/32
            pts.append((s*(.160+.006*sin(a)),5.486+.018*cos(a),1.785+.049*sin(a)))
        parts.append(g.tube('Sculpt_ear_helix',pts,.0045,'sculpture',6,True))
        pts=smooth_path([(s*.166,5.493,1.754),(s*.169,5.481,1.773),(s*.170,5.488,1.798),(s*.163,5.493,1.814)],3)
        parts.append(g.tube('Sculpt_ear_antihelix',pts,.003,'sculpture',6))
        # Short philtrum ridges and the curved rim of each nostril.
        parts.append(g.tube('Sculpt_philtrum',[(s*.006,5.355,1.724),(s*.008,5.353,1.716),(s*.01,5.352,1.711)],.0015,'sculpture',6))
        pts=[(s*.023+.007*cos(a),5.326,1.738+.003*sin(a)) for a in [pi+pi*i/12 for i in range(13)]]
        parts.append(g.tube('Sculpt_nostril_rim',pts,.0018,'sculpture',6))
        pts=smooth_path([(s*.030,5.359,1.835),(s*.061,5.349,1.842),(s*.093,5.365,1.830)],5)
        parts.append(g.tube('Sculpt_brow',pts,.004,'sculpture',6))
    for upper in (True,False):
        pts=[]
        for i in range(21):
            x=-.042+.084*i/20
            smile=1.693+.005*(abs(x)/.042)**1.8
            cupid=.002*cos(2*pi*x/.07)*exp(-(x/.035)**2)
            pts.append((x,5.352+.011*(abs(x)/.042)**1.5,smile+(cupid+.002 if upper else -.005)))
        parts.append(g.tube('Sculpt_upper_lip' if upper else 'Sculpt_lower_lip',pts,.0025 if upper else .003,'sculpture',8))
    return parts


def make_spectacles(g):
    parts=[]
    for s in (-1,1):
        parts.append(g.ring('Spectacle_round_rim',(s*.060,5.328,1.805),.040,'spectacle',.0027,n=48,sides=8))
        pts=smooth_path([(s*.100,5.328,1.808),(s*.137,5.369,1.817),(s*.161,5.435,1.818),
                        (s*.166,5.494,1.809),(s*.158,5.515,1.785)],4)
        parts.append(g.tube('Spectacle_temple_on_ear',pts,.0022,'spectacle',8))
        parts.append(g.ellipsoid('Spectacle_nose_pad',(s*.017,5.327,1.790),(.0045,.0025,.007),'spectacle',12,8))
    pts=smooth_path([(-.020,5.327,1.806),(-.011,5.316,1.812),(0,5.312,1.815),(.011,5.316,1.812),(.020,5.327,1.806)],3)
    parts.append(g.tube('Spectacle_bridge',pts,.0023,'spectacle',8))
    o=g.join(parts,'Statue_spectacles')
    finish(g,o,(0,5.5,1.1),True,True)
    o['component']='bust';o['lens_geometry']='None: open rims'
    return o


def png_rgb(path,rgb):
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    h,w=rgb.shape[:2]
    scan=b''.join(b'\x00'+rgb[h-1-j].tobytes() for j in range(h))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan,8))+chunk(b'IEND',b''))


def bake_bronze(g,o):
    import numpy as np
    activate(o)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004,area_weight=.15,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    mat=g.M['sculpture'];o.data.materials.clear();o.data.materials.append(mat)
    for p in o.data.polygons:p.material_index=0
    image=bpy.data.images.new('Temporary AO bake',1024,1024,alpha=False,float_buffer=True)
    image.colorspace_settings.name='Non-Color'
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    mat.node_tree.nodes.active=node
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        if any(d.type!='CPU' for d in prefs.devices):
            for d in prefs.devices:d.use=d.type!='CPU'
            scene.cycles.device='GPU'
    except Exception:pass
    scene.render.bake.margin=8
    bpy.ops.object.bake(type='AO',margin=8,use_clear=True)
    ao=np.array(image.pixels[:],dtype=np.float32).reshape(1024,1024,4)[:,:,:3].mean(axis=2)
    cavity=np.clip((.94-ao)/.7,0,1)**1.35
    copper=np.array([184,115,51],dtype=np.float32)
    verdigris=np.array([48,89,71],dtype=np.float32)
    mix=.68*cavity[:,:,None]
    rgb=(copper*(1-mix)+verdigris*mix)*(.69+.31*np.clip(ao,0,1))[:,:,None]
    rgb=np.clip(rgb,0,255).astype(np.uint8)
    folder=g.OUT/'textures';folder.mkdir(exist_ok=True)
    path=folder/'Hua_Bust_BaseColor_1024.png';png_rgb(path,rgb)
    baked=bpy.data.images.load(str(path),check_existing=False);baked.name='Hua_Bust_AO_Verdigris_BaseColor'
    baked.colorspace_settings.name='sRGB';baked.pack();baked.filepath='//textures/'+path.name
    node.image=baked;node.label='Baked AO and verdigris - 1024 square'
    p=mat.node_tree.nodes.get('Principled BSDF')
    mat.node_tree.links.new(node.outputs['Color'],p.inputs['Base Color'])
    bpy.data.images.remove(image)
    o['base_color_texture']='Hua_Bust_BaseColor_1024.png'
    o['texture_method']='Cycles AO bake; cavity-dependent verdigris, baked to Base Color PNG'
    o['texture_resolution']='1024x1024'
    print('BAKE_COMPLETE',float(ao.min()),float(ao.max()),flush=True)


def make_statue(g,bake=True):
    g.ITEM='S1-1';g.COL=bpy.data.collections.get('S1-1')
    # Only A1 geometry is replaced. SIGN_statue and COL_statue are untouched.
    for o in list(g.SCENE.objects):
        if o.get('item')=='S1-1' and o.name not in ('SIGN_statue','COL_statue'):
            bpy.data.objects.remove(o,do_unlink=True)
    g.M['sculpture']=g.material('Statue bronze - baked AO and verdigris','B87333',.35,.85)
    g.M['spectacle']=g.material('Statue dark metal spectacles','2A2A28',.34,.6)
    pieces=[facial_head(g)]+make_torso(g)+make_hair(g)+face_details(g)
    bust=g.join(pieces,'Statue_bronze_bust')
    finish(g,bust,(0,5.5,1.1),True,True)
    bust.data.calc_loop_triangles()
    if len(bust.data.loop_triangles)>16500:
        activate(bust);mod=bust.modifiers.new('Final bust budget','DECIMATE');mod.ratio=16500/len(bust.data.loop_triangles)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        finish(g,bust,(0,5.5,1.1),True,True)
    bust['component']='bust'
    spectacles=make_spectacles(g)
    if bake:bake_bronze(g,bust)
    # Same .8 x .8 x 1.1 pedestal envelope, with stone-colored mouldings.
    pedestal=[]
    pedestal.append(round_edges(g.box('Pedestal_stone_shaft',(0,5.5,.55),(.76,.76,1.04),'green',.012),3))
    for z,w,h in [(.035,.8,.07),(.083,.77,.03),(1.055,.78,.03),(1.09,.8,.02)]:
        pedestal.append(round_edges(g.box('Pedestal_cap_or_plinth',(0,5.5,z),(w,w,h),'green',.005),3))
    pedestal=g.join(pedestal,'Statue_pedestal')
    finish(g,pedestal,(0,5.5,0),True,True);pedestal['component']='pedestal'
    # A separate, open brass border. The protected sign does not move.
    frame=[]
    for x in (-.249,.249):frame.append(round_edges(g.box('Plaque_vertical_border',(x,5.089,.67),(.012,.012,.30),'brass',.002),2))
    for z in (.526,.814):frame.append(round_edges(g.box('Plaque_horizontal_border',(0,5.089,z),(.51,.012,.012),'brass',.002),2))
    frame=g.join(frame,'Statue_plaque_brass_frame')
    finish(g,frame,(0,5.089,.52),True,True);frame['component']='pedestal'
    return bust,spectacles,pedestal,frame


def add_picture_lights(g):
    for o in list(g.SCENE.objects):
        if o.get('item')=='S1-8':bpy.data.objects.remove(o,do_unlink=True)
    if bpy.data.collections.get('S1-8') is None:g.item('S1-8')
    else:g.COL=bpy.data.collections['S1-8'];g.ITEM='S1-8'
    static=[]
    for i in range(6):
        y=1.48+i*1.01
        static.append(round_edges(g.box('Picture_light_mount',(3.711,y,2.66),(.026,.066,.08),'brass',.004),2))
        static.append(g.rod('Picture_light_arm',(3.71,y,2.66),(3.46,y,2.66),.009,'brass',12))
        static.append(g.rod('Picture_light_drop',(3.46,y,2.66),(3.43,y,2.611),.008,'brass',10))
        verts=[];faces=[];n=17
        for yy in (y-.2,y+.2):
            for j in range(n):
                a=pi*j/(n-1);verts.append((3.43+.045*cos(a),yy,2.594+.045*sin(a)))
        for j in range(n-1):faces.append((j,j+1,n+j+1,n+j))
        faces += [tuple(reversed(range(n))),tuple(n+j for j in range(n))]
        shade=g.mesh('Picture_light_half_cylinder',verts,faces,'brass')
        static.append(shade)
        emitter=g.box(f'EMIT_picLight_{i+1:02d}',(3.43,y,2.598),(.018,.34,.006),'warm',0)
        finish(g,emitter,(3.43,y,2.595),False)
    housing=g.join(static,'Timeline_picture_light_housings')
    finish(g,housing,None,True,True)


def add_timber_beams(g):
    for o in list(g.SCENE.objects):
        if o.get('item')=='S0-9':bpy.data.objects.remove(o,do_unlink=True)
    if bpy.data.collections.get('S0-9') is None:g.item('S0-9')
    else:g.COL=bpy.data.collections['S0-9'];g.ITEM='S0-9'
    pieces=[]
    for y in (1.4,5.7,7.3):pieces.append(g.box('Ceiling_shop_beam',(-8,y,4.05),(7.6,.2,.25),'walnut',.005))
    for x in (-10.5,-7,-3.5):
        if x==-7:
            # A real underside notch passes the existing rail at y=12 without contact.
            for a,b in [(8.2,11.9),(12.1,15.8)]:
                pieces.append(g.box('Ceiling_tea_notched_beam',(x,(a+b)/2,4.05),(.2,b-a,.25),'walnut',.005))
            pieces.append(g.box('Ceiling_tea_notch_bridge',(x,12,4.1325),(.2,.2,.085),'walnut',.004))
        else:pieces.append(g.box('Ceiling_tea_beam',(x,12,4.05),(.2,7.6,.25),'walnut',.005))
    for x in (-.8,2.3,7.7,10.7):
        pieces.append(g.box('Ceiling_factory_beam',(x,12,4.05),(.2,7.6,.25),'walnut',.005))
    beams=g.join(pieces,'Ceiling_timber_beams')
    finish(g,beams,None,False,True)
    # Match the generic source convention: bottom-center object origin.
    coords=[beams.matrix_world@v.co for v in beams.data.vertices]
    g.origin(beams,((min(p.x for p in coords)+max(p.x for p in coords))/2,
                    (min(p.y for p in coords)+max(p.y for p in coords))/2,min(p.z for p in coords)))
    beams['beam_counts']='shop=3, tea=3, factory=4'
    beams['cross_section_m']='0.20 x 0.25'
    beams['clearance']='Tea middle beam has a physical underside notch at the original lighting rail.'
    return beams
