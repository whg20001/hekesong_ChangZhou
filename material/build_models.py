"""Build the seven museum asset packages with Blender 5.x.

  & 'D:\blender\blender.exe' --background --python material/build_models.py
Optional: -- --only S3_tea (or comma-separated names); -- --skip-render; -- --assemble-only
No external packages, textures, downloaded assets, or procedural shader nodes.
"""
import bpy
import bmesh
import math
import json
import os
import sys
from pathlib import Path
from math import sin, cos, pi
from mathutils import Vector

OUT = Path(__file__).resolve().parent
if str(OUT) not in sys.path:sys.path.insert(0,str(OUT))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SKIP_RENDER = '--skip-render' in ARGS
ONLY = ARGS[ARGS.index('--only') + 1] if '--only' in ARGS else None
SCENE = None
COL = None
ITEM = ''
M = {}
PIVOTS = {}
REPORT = {}
NAMES = ['S0_shell', 'S1_lobby', 'S2_shop', 'S3_tea', 'S4_factory', 'S5_exit', 'S6_common']
BUDGETS = {
 'S0-1':2000, 'S0-2':6000, 'S0-3':3000, 'S0-4':2000, 'S0-5':1500,
 'S0-6':1500, 'S0-7':9000, 'S0-8':400, 'S0-9':2000,
 'S1-1':21500, 'S1-2':2000, 'S1-3':800, 'S1-4':1500, 'S1-5':4000, 'S1-6':500, 'S1-7':2000, 'S1-8':2500,
 'S2-1':5000, 'S2-2':2000, 'S2-3':2000, 'S2-4':4000, 'S2-5':2000,
 'S2-6':800, 'S2-7':1000, 'S2-8':900, 'S2-9':1000, 'S2-10':300,
 'S3-1':3000, 'S3-2':1500, 'S3-3':2000, 'S3-4':2000, 'S3-5':1500,
 'S3-6':1600, 'S3-7':600, 'S3-8':1000, 'S3-9':300, 'S3-10':800,
 'S3-11':600, 'S3-12':300,
 'S4-1':3000, 'S4-2':4000, 'S4-3':2000, 'S4-4':800, 'S4-5':1000,
 'S4-6':1500, 'S4-7':3000, 'S4-8':2500, 'S4-9':300,
 'S5-1':4000, 'S5-2':1000, 'S5-3':500,
 'S6-1':200, 'S6-2':300, 'S6-3':400, 'S6-4':50, 'S6-5':1000,
}
REQUIRED = {
 'S0_shell':['INT_exitDoor_L','INT_exitDoor_R','EMIT_exitPortal','SIGN_exit','EMIT_exitSign_01','EMIT_exitSign_02','EMIT_spot_21','EMIT_spot_22','Ceiling_timber_beams'],
 'S1_lobby':['SIGN_statue'] + [f'SIGN_timeline_{i:02d}' for i in range(1,7)] + ['SIGN_brochure','SIGN_hallTitle','SIGN_vitrine_01','SIGN_vitrine_02','Statue_bronze_bust','Statue_spectacles','Statue_pedestal','Statue_plaque_brass_frame'] + [f'EMIT_picLight_{i:02d}' for i in range(1,7)],
 'S2_shop':['SIGN_shopName','INT_counter','SIGN_ledgerL','SIGN_ledgerR','EMIT_oilLamp','SIGN_label_shop']
   + [f'ANIM_bead_{i:02d}_{j}' for i in range(1,14) for j in range(1,8)] + [f'SIGN_customer_{i:02d}' for i in range(1,4)],
 'S3_tea':['INT_stove','EMIT_fire','INT_kettle','ANIM_kettleLid','INT_teapot','ANIM_potLid',
   'INT_caddy','ANIM_caddyLid','ANIM_hourHand','ANIM_minHand','SIGN_gantt','EMIT_pendant','SIGN_label_tea']
   + [f'INT_cup_{i}' for i in range(1,5)],
 'S4_factory':['ANIM_furnaceDoor','EMIT_furnaceGlow','INT_dial','INT_testBtn','SIGN_tempReadout',
   'ANIM_needle','SIGN_dial','SIGN_board','SIGN_notebook','SIGN_label_factory','EMIT_highWindow']
   + [f'ANIM_sample_{i}' for i in range(1,9)] + [f'ANIM_gear_{i}' for i in range(1,4)],
 'S5_exit':[f'ANIM_fib_{i}' for i in range(1,9)] + ['SIGN_guestbook','SIGN_epilogue'],
 'S6_common':['SIGN_card','SIGN_label','Common_stanchion','Common_rope'],
}


def srgb(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4


def material(name, color, rough=.48, metal=0, alpha=1, emit=0):
    rgb = tuple(srgb(int(color[i:i+2],16)/255) for i in (0,2,4))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb,1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Alpha'].default_value = alpha
    p.inputs['Transmission Weight'].default_value = 0
    if emit:
        p.inputs['Emission Color'].default_value = (*rgb,1)
        p.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = (*rgb,alpha)
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
    return m


def reset(name):
    global SCENE, M, PIVOTS
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SCENE = bpy.context.scene
    SCENE.name = name
    SCENE.unit_settings.system = 'METRIC'
    SCENE.unit_settings.scale_length = 1
    SCENE['design'] = 'Fictional Hua Luogeng mathematics museum; not a real building reconstruction.'
    SCENE['coordinates'] = 'Meters. Blender Z up, ground Z=0; GLB standard Y up.'
    PIVOTS = {}
    colors = {
      'walnut':('6B4129',.47,0), 'wood':('9A6A43',.46,0), 'woodLight':('AF8053',.5,0),
      'woodDark':('583623',.53,0), 'ivory':('E9DFCB',.7,0), 'paper':('F3E8CD',.86,0),
      'green':('2F5D50',.56,0), 'greenLight':('517764',.53,0), 'brick':('A9432F',.67,0),
      'brickLight':('BD6247',.68,0), 'mortar':('775E4D',.85,0),
      'copper':('B87333',.36,.6), 'bronzeDark':('80502E',.43,.6), 'brass':('C9A24A',.32,.7),
      'night':('1B2A4A',.65,0), 'iron':('1D1D1B',.42,.45), 'ink':('31342E',.66,0),
      'red':('8B302C',.82,0), 'ceramic':('DFD9BA',.28,0), 'tea':('754830',.49,0),
      'leaf':('3C6B48',.6,0), 'leafLight':('658458',.6,0), 'soil':('31271D',.9,0),
      'chalk':('F0EBD9',.84,0), 'blue':('6893AB',.36,0),
    }
    M = {k:material(k,*v) for k,v in colors.items()}
    M['glass'] = material('Cold glass - alpha only','8FB3D9',.22,0,.26)
    M['collision'] = material('Collision - invisible alpha','FFFFFF',1,0,0)
    M['warm'] = material('Warm luminous glass','FFD18A',.28,0,1,3)
    M['fire'] = material('Orange fire emitter','FF872E',.36,0,1,4)
    M['glow'] = material('Furnace emitter','FF662C',.4,0,1,5)
    M['cool'] = material('Cold blue window emitter','8FB3D9',.35,0,.7,.9)
    M['portal'] = material('Ivory portal emitter','FFEAC0',.48,0,1,3)
    M['exit'] = material('Green exit emitter','72C09B',.5,0,1,1.8)


def item(code):
    global COL, ITEM
    ITEM = code
    COL = bpy.data.collections.new(code)
    SCENE.collection.children.link(COL)


def place(o,name,mat=None):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    COL.objects.link(o)
    o.name = name
    o['item'] = ITEM
    if mat:
        o.data.materials.append(M[mat] if isinstance(mat,str) else mat)
    return o


def bevel(o,width=.004):
    if width:
        m=o.modifiers.new('Rounded miniature edges','BEVEL')
        m.width=width
        m.segments=1
    return o


def box(name,loc,dims,mat='wood',b=.004):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=place(bpy.context.object,name,mat)
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return bevel(o,min(b,min(dims)*.22))


def cyl(name,loc,r,depth,mat='iron',n=16,rot=None,b=.003):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=depth,location=loc)
    o=place(bpy.context.object,name,mat)
    if rot:o.rotation_euler=rot
    return bevel(o,min(b,depth*.18,r*.1))


def ellipsoid(name,loc,scale,mat='copper',n=20,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=n,ring_count=rings,location=loc)
    o=place(bpy.context.object,name,mat)
    o.scale=scale
    for p in o.data.polygons:p.use_smooth=True
    return o


def mesh(name,verts,faces,mat='wood'):
    d=bpy.data.meshes.new(name)
    d.from_pydata(verts,[],faces)
    d.update()
    o=bpy.data.objects.new(name,d)
    COL.objects.link(o)
    o['item']=ITEM
    d.materials.append(M[mat] if isinstance(mat,str) else mat)
    return o


def rod(name,a,b,r,mat='iron',n=10):
    a,b=Vector(a),Vector(b)
    o=cyl(name,(a+b)/2,r,(b-a).length,mat,n,b=0)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o


def tube(name,pts,r,mat='brass',sides=6,closed=False):
    pts=[Vector(p) for p in pts]
    tangents=[]
    for i,p in enumerate(pts):
        t=pts[(i+1)%len(pts)]-pts[i-1] if closed else pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]
        tangents.append(t.normalized())
    # A stable frame avoids 180-degree flips at vertical bends (lamp handles,
    # eyeglasses, and the Fibonacci arcs). All main paths lie in one plane.
    normal=None
    for t in tangents[1:]:
        candidate=tangents[0].cross(t)
        if candidate.length>.001:
            normal=candidate.normalized();break
    if normal is None:
        normal=Vector((0,0,1)) if abs(tangents[0].z)<.9 else Vector((0,1,0))
    verts=[]
    for i,p in enumerate(pts):
        t=tangents[i]
        v=(normal-t*normal.dot(t)).normalized()
        u=t.cross(v).normalized()
        verts += [tuple(p+r*(cos(2*pi*j/sides)*u+sin(2*pi*j/sides)*v)) for j in range(sides)]
    faces=[]
    for i in range(len(pts) if closed else len(pts)-1):
        for j in range(sides):
            faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%len(pts))*sides+(j+1)%sides,((i+1)%len(pts))*sides+j))
    if not closed:
        faces += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+j for j in range(sides))]
    return mesh(name,verts,faces,mat)


def ring(name,center,radius,mat='brass',thick=.008,normal='Y',n=24,sides=6):
    x,y,z=center
    pts=[]
    for i in range(n):
        a=2*pi*i/n
        pts.append((x+radius*cos(a),y,z+radius*sin(a)) if normal=='Y' else (x+radius*cos(a),y+radius*sin(a),z))
    return tube(name,pts,thick,mat,sides,True)


def lathe(name,loc,profile,mat='ceramic',n=16):
    x,y,z=loc
    verts=[(x+r*cos(2*pi*i/n),y+r*sin(2*pi*i/n),z+h) for r,h in profile for i in range(n)]
    faces=[]
    for j in range(len(profile)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces += [tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))]
    o=mesh(name,verts,faces,mat)
    for p in o.data.polygons:p.use_smooth=True
    return o


def origin(o,p):
    bpy.context.view_layer.update()
    if o.type=='MESH':
        delta=o.matrix_world.inverted()@Vector(p)
        for v in o.data.vertices:v.co-=delta
        o.location=Vector(p)
    else:
        SCENE.cursor.location=p
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o


def pivot(o,p,kind='hinge',axis='Z'):
    PIVOTS[o.name]=(tuple(p),kind,axis)
    o['pivot_role']=kind
    o['rotation_axis_blender']=axis
    return o


def join(parts,name,p=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o=bpy.context.object
    o.name=name
    o['item']=ITEM
    if p is not None:pivot(o,p,'prop bottom')
    return o


def collision(name,loc,dims):
    o=box('COL_'+name,loc,dims,'collision',0)
    o.display_type='WIRE'
    o['collision']=True
    o['runtime_visibility']='Set visible=false in Three.js; keep for physics.'
    return o


def front_sign(name,loc,w,h,mat='paper',facing='south'):
    dims=(w,.004,h) if facing=='south' else (.004,w,h)
    o=box(name,loc,dims,mat,0)
    o['surface_front_blender']='-Y' if facing=='south' else ('+X' if facing=='east' else '-X')
    o['blank_surface']=True
    return o


def plaque(name,loc=(0,0,0)):
    x,y,z=loc
    box(name+'_foot',(x,y,z+.035),(.48,.38,.07),'iron')
    rod(name+'_stem',(x,y,z+.06),(x,y,z+.9),.027,'brass')
    board=box(name+'_rim',(x,y,z+1.02),(.8,.34,.045),'brass')
    board.rotation_euler.x=math.radians(22)
    face=box('SIGN_'+name,(x,y-.003,z+1.046),(.758,.3,.004),'paper',0)
    face.rotation_euler.x=math.radians(22)
    face['blank_surface']=True
    return face


def table(name,x,y,w,d,h,mat='walnut'):
    parts=[box(name+'_top',(x,y,h-.035),(w,d,.07),mat,.008)]
    for dx in (-1,1):
        for dy in (-1,1):
            parts.append(box(name+'_leg',(x+dx*(w/2-.08),y+dy*(d/2-.07),(h-.07)/2),(.07,.07,h-.07),mat))
    for dy in (-1,1):parts.append(box(name+'_apron',(x,y+dy*(d/2-.07),h-.15),(w-.1,.035,.15),mat))
    o=join(parts,name,(x,y,0))
    collision(name,(x,y,h/2),(w,d,h))
    return o


def plant(name,x,y,h):
    r=h*.145
    parts=[lathe(name+'_pot',(x,y,0),[(r*.7,0),(r*.72,.02),(r,h*.25),(r*1.02,h*.27),(r*.83,h*.27),(r*.78,h*.23)],'brick',12),
           cyl(name+'_soil',(x,y,h*.24),r*.82,.015,'soil',12,b=0)]
    for i in range(9):
        a=i*2.4
        ex=x+cos(a)*h*(.18+.025*(i%3));ey=y+sin(a)*h*(.18+.025*(i%3));ez=h*(.52+.05*i)
        parts.append(rod(name+'_stem',(x,y,h*.24),(ex,ey,ez),h*.006,'leaf',6))
        v=Vector((cos(a),sin(a),.25));side=Vector((-sin(a),cos(a),0))
        base=Vector((ex,ey,ez-h*.07));tip=base+v*h*.24
        mid=(base+tip)/2+Vector((0,0,h*.035))
        verts=[tuple(base),tuple(mid+side*h*.07),tuple(tip),tuple(mid-side*h*.07),tuple(mid+Vector((0,0,h*.018)))]
        parts.append(mesh(name+'_leaf',verts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],'leafLight' if i%3==0 else 'leaf'))
    return join(parts,name,(x,y,0))


def book(name,x,y,z,w=.3,d=.22):
    box(name+'_cover',(x,y,z+.012),(w+.015,d+.012,.024),'red')
    box(name+'_pages',(x,y,z+.029),(w,d,.018),'paper',0)
    for suffix,dx in [('L',-w/4),('R',w/4)]:
        o=box('SIGN_'+name+suffix,(x+dx,y,z+.040),(w/2-.009,d-.012,.003),'paper',0)
        o['blank_surface']=True
    rod(name+'_spine',(x,y-d/2,z+.037),(x,y+d/2,z+.037),.003,'brass',6)


def rope_post(name,x,y,h=.95):
    return [lathe(name,(x,y,0),[(.115,0),(.115,.025),(.065,.045),(.032,.12),(.023,h-.09),(.04,h-.055),(.027,h-.01),(.012,h)],'brass',10)]


def rope(name,a,b):
    a,b=Vector(a),Vector(b)
    pts=[tuple(a.lerp(b,i/9)-Vector((0,0,.12*sin(pi*i/9)))) for i in range(10)]
    return tube(name,pts,.018,'red',6)


def floor(name,bounds,wood=False):
    x0,x1,y0,y1=bounds
    box(name,((x0+x1)/2,(y0+y1)/2,-.09),(x1-x0,y1-y0,.18),'woodDark' if wood else 'ivory',0)
    # Actual geometry colour blocks; no shader noise or external images.
    verts=[];faces=[];colors=[]
    step=.38 if wood else 1.0
    rows=math.ceil((y1-y0)/step)
    for j in range(rows):
        ya=y0+j*step;yb=min(y1,ya+step)
        stride=2.0 if wood else 1.0
        xa=x0
        if j%2 and wood:
            stops=[x0,min(x1,x0+1)] + [x0+1+i*stride for i in range(1,20) if x0+1+i*stride<x1] + [x1]
        else:stops=[x0+i*stride for i in range(math.ceil((x1-x0)/stride))]+[x1]
        for i in range(len(stops)-1):
            xa,xb=stops[i],stops[i+1]
            if xb-xa<.01:continue
            k=len(verts);gap=.008 if wood else .006
            verts += [(xa+gap,ya+gap,.001),(xb-gap,ya+gap,.001),(xb-gap,yb-gap,.001),(xa+gap,yb-gap,.001)]
            faces.append((k,k+1,k+2,k+3));colors.append((i+j)%3)
    o=mesh(name+'_surface',verts,faces,'wood' if wood else 'ivory')
    if wood:
        o.data.materials.append(M['woodDark']);o.data.materials.append(M['walnut'])
        for p,i in zip(o.data.polygons,colors):p.material_index=i


def shell():
    item('S0-1')
    for name,bounds,wood in [('lobby',(-4,4,0,8),False),('shop',(-12,-4,0,8),True),
       ('tea',(-12,-2,8,16),True),('factory',(-2,12,8,16),True),('exit',(4,12,0,8),False)]:
        floor('Floor_'+name,bounds,wood)
    item('S0-2')
    walls=[]
    def wall(name,axis,fixed,a,b,mat='ivory',z0=0,z1=4.2):
        loc=(fixed,(a+b)/2,(z0+z1)/2) if axis=='X' else ((a+b)/2,fixed,(z0+z1)/2)
        dims=(.2,b-a,z1-z0) if axis=='X' else (b-a,.2,z1-z0)
        o=box(name,loc,dims,mat,.004);walls.append((name,axis,fixed,a,b,z0,z1))
        collision(name,loc,dims)
        return o
    wall('Wall_west','X',-12,0,16,'green')
    wall('Wall_north','Y',16,-12,12,'ivory')
    wall('Wall_south_left','Y',0,-12,-1)
    wall('Wall_south_right','Y',0,1,12)
    wall('Wall_south_header','Y',0,-1,1,z0=2.8)
    wall('Wall_east_lower','X',12,0,3)
    wall('Wall_east_upper','X',12,5,16)
    wall('Wall_east_header','X',12,3,5,z0=2.8)
    wall('Wall_shop_south','X',-4,0,2,'green')
    wall('Wall_shop_north','X',-4,4,8,'green')
    wall('Wall_shop_header','X',-4,2,4,'green',2.8)
    wall('Wall_lobby_exit','X',4,0,8,'green')
    wall('Wall_cross_west','Y',8,-12,-9)
    wall('Wall_cross_middle','Y',8,-7,7)
    wall('Wall_cross_east','Y',8,9,12)
    wall('Wall_cross_shop_header','Y',8,-9,-7,z0=2.8)
    wall('Wall_cross_exit_header','Y',8,7,9,z0=2.8)
    wall('Wall_tea_factory_south','X',-2,8,11,'green')
    wall('Wall_tea_factory_north','X',-2,13,16,'green')
    wall('Wall_tea_factory_header','X',-2,11,13,'green',2.8)
    # Brass portal surrounds clarify the route through each two-meter opening.
    for axis,fixed,a,b in [('X',-4,2,4),('Y',8,-9,-7),('X',-2,11,13),('Y',8,7,9)]:
        for edge in (a-.025,b+.025):
            box('Doorway_vertical', (fixed,edge,1.4) if axis=='X' else (edge,fixed,1.4),
                (.24,.055,2.8) if axis=='X' else (.055,.24,2.8),'walnut')
        box('Doorway_lintel',(fixed,(a+b)/2,2.81) if axis=='X' else ((a+b)/2,fixed,2.81),
            (.24,b-a+.1,.09) if axis=='X' else (b-a+.1,.24,.09),'brass')
    item('S0-3')
    # A grid with real roof openings at lobby and workshop.
    xs=[-12,-2,2,3,7,12];ys=[0,2.5,5.5,10.5,13.5,16]
    for i in range(len(xs)-1):
        for j in range(len(ys)-1):
            a,b=xs[i],xs[i+1];c,d=ys[j],ys[j+1]
            if (a>=-2 and b<=2 and c>=2.5 and d<=5.5) or (a>=3 and b<=7 and c>=10.5 and d<=13.5):continue
            box('Ceiling_panel',((a+b)/2,(c+d)/2,4.25),(b-a,d-c,.1),'ivory',0)
    for x,y in [(0,4),(5,12)]:
        box('Skylight_glass',(x,y,4.24),(4,3,.025),'glass',0)
        box('Skylight_night_backdrop',(x,y,4.5),(4,3,.035),'night',0)
        for dx in (-2,0,2):box('Skylight_mullion',(x+dx,y,4.24),(.065,3.12,.12),'iron')
        for dy in (-1.5,0,1.5):box('Skylight_crossbar',(x,y+dy,4.24),(4.1,.065,.12),'iron')
    item('S0-4')
    for name,axis,fixed,a,b,z0,z1 in walls:
        if z0>0:continue
        # Trim both wall faces so interior partitions read correctly from either room.
        for offset in (-.105,.105):
            for z,height in [(.07,.14),(4.08,.09)]:
                loc=(fixed+offset,(a+b)/2,z) if axis=='X' else ((a+b)/2,fixed+offset,z)
                dims=(.035,b-a,height) if axis=='X' else (b-a,.035,height)
                box('Trim_'+name,loc,dims,'walnut',0)
    item('S0-5')
    parts=[]
    for x in (-.5,.5):
        parts.append(box('Entrance_glass',(x,.015,1.38),(.88,.024,2.64),'glass',0))
        for dx in (-.47,.47):parts.append(box('Entrance_stile',(x+dx,0,1.4),(.055,.09,2.8),'green'))
        for z in (.07,1.08,2.74):parts.append(box('Entrance_rail',(x,0,z),(1,.09,.08),'green'))
        parts.append(rod('Entrance_handle',(x*.25,-.09,1.1),(x*.25,-.09,1.42),.013,'brass'))
    join(parts,'Entrance_double_door',(0,0,0))
    collision('entrance',(0,0,1.4),(2,.14,2.8))
    box('Entrance_dark_exterior',(0,-.14,1.4),(2,.025,2.8),'night',0)
    item('S0-6')
    for side,y,hinge_y in [('L',3.5,3),('R',4.5,5)]:
        parts=[]
        parts.append(box('Exit_leaf',(11.97,y,1.36),(.09,.96,2.72),'green'))
        parts.append(box('Exit_inset',(11.91,y,1.56),(.016,.73,1.72),'night'))
        parts.append(rod('Exit_pushbar',(11.86,y-.34,1.1),(11.86,y+.34,1.1),.018,'brass'))
        door=join(parts,'INT_exitDoor_'+side)
        pivot(door,(12,hinge_y,0),'door hinge','Z')
        door['closed_rotation_radians']=0.0
    for y in (2.95,5.05):box('Exit_frame',(12,y,1.4),(.23,.11,2.8),'brass')
    box('Exit_lintel',(12,4,2.84),(.23,2.2,.14),'walnut')
    box('EMIT_exitPortal',(12.08,4,1.38),(.008,1.88,2.72),'portal',0)
    front_sign('SIGN_exit',(11.86,4,3.12),1.55,.29,'paper','west')
    item('S0-7')
    k=0
    for x0,y0 in [(0,4),(-8,4),(-7,12),(5,12),(8,4)]:
        box('Ceiling_track',(x0,y0,4.04),(4.6,.065,.06),'iron',.002)
        for dx in (-1.8,-.6,.6,1.8):
            k+=1;x=x0+dx
            rod('Spot_stem',(x,y0,4.04),(x,y0,3.9),.016,'iron',8)
            o=cyl('Spot_housing',(x,y0-.04,3.8),.075,.21,'copper',10,b=.003)
            o.rotation_euler.x=math.radians(22)
            lens=cyl(f'EMIT_spot_{k:02d}',(x,y0-.078,3.702),.061,.006,'warm',10,b=0)
            lens.rotation_euler.x=math.radians(22)
    for k,x,y0 in [(21,0,13.9),(22,9.5,13.6)]:
        box('Ceiling_track_extra',(x,y0,4.04),(.7,.065,.06),'iron',.002)
        rod('Spot_stem_extra',(x,y0,4.04),(x,y0,3.9),.016,'iron',8)
        housing=cyl('Spot_housing_extra',(x,y0-.04,3.8),.075,.21,'copper',10,b=.003)
        housing.rotation_euler.x=math.radians(22)
        lens=cyl(f'EMIT_spot_{k:02d}',(x,y0-.078,3.702),.061,.006,'warm',10,b=0)
        lens.rotation_euler.x=math.radians(22)
    item('S0-8')
    for i,loc,dims in [(1,(0,.125,3.12),(.5,.04,.18)),(2,(11.875,4,3.53),(.04,.5,.18))]:
        box('Exit_sign_frame',loc,tuple(d+.025 for d in dims),'iron')
        center=(loc[0],loc[1]+.025,loc[2]) if i==1 else (loc[0]-.025,loc[1],loc[2])
        box(f'EMIT_exitSign_{i:02d}',center,dims,'exit',0)


def lobby():
    item('S1-1')
    x,y=0,5.5
    box('Statue_pedestal',(x,y,.55),(.8,.8,1.1),'green',.008)
    box('Statue_base_plinth',(x,y,.055),(.91,.91,.11),'walnut',.006)
    box('Statue_pedestal_cap',(x,y,1.08),(.85,.85,.045),'brass')
    front_sign('SIGN_statue',(x,y-.406,.67),.48,.27,'paper')
    # Stylized sculpted bust: shoulders, Zhongshan collar, side part, round spectacles.
    parts=[]
    parts.append(lathe('Bust_foot',(x,y,1.1),[(.22,0),(.24,.025),(.22,.06),(.18,.09)],'copper',20))
    verts=[];faces=[];n=24
    for w,d,z in [(.22,.13,1.18),(.31,.15,1.26),(.33,.145,1.39),(.28,.12,1.49),(.105,.095,1.56)]:
        for i in range(n):
            a=2*pi*i/n;verts.append((x+w*cos(a),y+d*sin(a),z))
    for j in range(4):
        for i in range(n):a=j*n+i;b=j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
    faces += [tuple(reversed(range(n))),tuple(4*n+i for i in range(n))]
    parts.append(mesh('Bust_jacket',verts,faces,'copper'))
    parts.append(cyl('Bust_neck',(x,y,1.576),.077,.13,'copper',20,b=0))
    parts.append(ellipsoid('Bust_head',(x,y-.012,1.76),(.14,.119,.202),'copper',28,18))
    parts.append(ellipsoid('Bust_chin',(x,y-.062,1.649),(.09,.077,.065),'copper',16,10))
    for side in (-1,1):
        parts.append(ellipsoid('Bust_ear',(x+side*.142,y-.005,1.752),(.026,.022,.051),'copper',12,8))
        parts.append(ellipsoid('Bust_cheek',(x+side*.071,y-.095,1.738),(.058,.036,.063),'copper',16,10))
        parts.append(ellipsoid('Bust_eye',(x+side*.062,y-.123,1.792),(.031,.012,.015),'bronzeDark',12,8))
        parts.append(tube('Bust_brow',[(x+side*.025,y-.119,1.832),(x+side*.064,y-.129,1.838),(x+side*.098,y-.11,1.826)],.008,'bronzeDark',6))
        parts.append(ring('Bust_round_glasses',(x+side*.063,y-.143,1.793),.043,'brass',.0045,n=24,sides=6))
        parts.append(tube('Bust_spectacle_arm',[(x+side*.105,y-.142,1.795),(x+side*.149,y-.075,1.799),(x+side*.15,y+.015,1.79)],.0035,'brass',6))
    parts.append(rod('Bust_glasses_bridge',(x-.018,y-.151,1.797),(x+.018,y-.151,1.797),.004,'brass',8))
    parts.append(ellipsoid('Bust_nose_bridge',(x,y-.131,1.761),(.021,.027,.054),'copper',16,10))
    parts.append(ellipsoid('Bust_nose_tip',(x,y-.155,1.736),(.033,.027,.02),'copper',16,10))
    parts.append(tube('Bust_mouth',[(x-.039,y-.129,1.694),(x,y-.14,1.689),(x+.038,y-.129,1.694)],.0035,'bronzeDark',6))
    # A closed upper-head cap, a visible parting groove, and broad swept hair locks.
    hv=[];hf=[]
    for row in range(7):
        t=(pi/2)*row/6
        for i in range(28):
            a=2*pi*i/28
            hv.append((x+.143*sin(t)*cos(a),y-.009+.123*sin(t)*sin(a),1.838+.138*cos(t)))
    for j in range(6):
        for i in range(28):a=j*28+i;b=j*28+(i+1)%28;hf.append((a,b,b+28,a+28))
    hf.append(tuple(reversed([6*28+i for i in range(28)])))
    parts.append(mesh('Bust_side_parted_hair',hv,hf,'bronzeDark'))
    for i in range(6):
        xx=-.108+i*.031
        parts.append(tube('Bust_swept_hair',[(x+xx,y-.105,1.867),(x+xx+.025,y-.08,1.923),(x+xx+.04,y-.015,1.965),(x+xx+.032,y+.07,1.922)],.007,'copper',5))
    for side in (-1,1):
        collar=box('Bust_standing_collar',(x+side*.05,y-.091,1.541),(.09,.028,.062),'bronzeDark',.005)
        collar.rotation_euler.y=side*math.radians(-16)
        parts.append(collar)
        parts.append(box('Bust_breast_pocket',(x+side*.17,y-.138,1.377),(.095,.014,.069),'bronzeDark',.004))
        parts.append(box('Bust_pocket_flap',(x+side*.17,y-.149,1.415),(.108,.012,.018),'copper',.003))
    parts.append(box('Bust_jacket_seam',(x,y-.15,1.362),(.014,.014,.24),'bronzeDark',.002))
    for z in (1.28,1.355,1.43):parts.append(ellipsoid('Bust_button',(x,y-.166,z),(.011,.007,.011),'brass',10,6))
    join(parts,'Hua_Luogeng_stylized_bronze_bust',(x,y,1.1))
    collision('statue',(x,y,1),(.84,.84,2))
    item('S1-2')
    box('Timeline_green_wall',(3.77,4,1.4),(.08,6.5,2.8),'green')
    for i in range(6):
        yy=1.48+i*1.01
        box('Timeline_brass_frame',(3.71,yy,1.83),(.035,.96,1.26),'brass')
        front_sign(f'SIGN_timeline_{i+1:02d}',(3.685,yy,1.83),.9,1.2,'paper','west')
        cyl('Timeline_node',(3.665,yy,1.05),.045,.012,'brass',12,(0,pi/2,0),0)
    rod('Timeline_brass_rule',(3.68,1,1.05),(3.68,7,1.05),.012,'brass')
    item('S1-3')
    parts=[]
    # The west wall now holds vitrines. Move the bench to the north wall.
    for i in range(4):parts.append(box('Bench_slat',(-1.1,7.25+(i-1.5)*.115,.425),(2,.105,.05),'walnut',.006))
    for xx in (-1.85,-.35):
        parts.append(box('Bench_iron_leg',(xx,7.25,.205),(.055,.42,.41),'iron'))
    join(parts,'Lobby_bench',(-1.1,7.25,0))
    collision('lobby_bench',(-1.1,7.25,.225),(2,.5,.45))
    item('S1-4')
    box('Reception_body',(2.35,.85,.5),(1.6,.6,1),'green',.008)
    box('Reception_top',(2.35,.85,1.025),(1.68,.66,.05),'walnut',.006)
    for x in (1.75,2.05,2.35,2.65,2.95):box('Reception_flute',(x,.542,.5),(.018,.018,.8),'brass',.002)
    for i in range(4):box('Brochure_stack',(2.6,.85,1.06+i*.012),(.24,.3,.01),'paper',0)
    o=box('SIGN_brochure',(2.6,.85,1.11),(.23,.29,.002),'paper',0);o['blank_surface']=True
    collision('reception',(2.35,.85,.53),(1.68,.66,1.06))
    item('S1-5')
    plant('Lobby_plant_A',-2.3,6.5,1.6)
    plant('Lobby_plant_B',2.7,7.15,1.6)
    item('S1-6')
    box('Hall_title_brass_frame',(0,7.86,3),(3.10,.045,.90),'brass')
    front_sign('SIGN_hallTitle',(0,7.833,3),3,.8,'ivory')
    item('S1-7')
    for i,y in enumerate((5.15,6.75),1):
        x=-3.4
        box('Vitrine_wood_pedestal',(x,y,.35),(.56,1.16,.7),'walnut',.008)
        box('Vitrine_lower_plinth',(x,y,.045),(.60,1.20,.09),'green',.006)
        box('Vitrine_top_tray',(x,y,.72),(.6,1.2,.04),'wood',.006)
        box('Vitrine_glass_top',(x,y,1.094),(.6,1.2,.012),'glass',0)
        for dx in (-.294,.294):
            box('Vitrine_glass_side',(x+dx,y,.914),(.012,1.2,.348),'glass',0)
        for dy in (-.594,.594):
            box('Vitrine_glass_end',(x,y+dy,.914),(.588,.012,.348),'glass',0)
        for dx in (-.288,.288):
            for dy in (-.588,.588):
                rod('Vitrine_corner',(x+dx,y+dy,.743),(x+dx,y+dy,1.088),.006,'brass',6)
        page=box(f'SIGN_vitrine_{i:02d}',(x,y,.746),(.43,.9,.004),'paper',0)
        page['blank_surface']=True
        collision(f'vitrine_{i:02d}',(x,y,.55),(.6,1.2,1.1))


def shop():
    item('S2-1')
    # Facade is a six-meter frontage along Y, one meter deep along X, facing +X.
    box('Shop_facade_back',(-11.68,4,1.55),(.22,6,3.1),'walnut',.006)
    for yy in (1.05,2.9,5.1,6.95):
        box('Shop_front_post',(-11.33,yy,1.6),(.18,.15,3.2),'wood')
        box('Shop_post_foot',(-11.33,yy,.16),(.26,.25,.32),'iron')
    for yy in (2,6):
        box('Shop_window_recess',(-11.53,yy,1.95),(.025,1.6,1.5),'night',0)
        for dy in (-.72,-.36,0,.36,.72):box('Shop_window_vertical',(-11.47,yy+dy,1.95),(.065,.035,1.5),'woodLight')
        for zz in (1.23,1.59,1.95,2.31,2.67):box('Shop_window_lattice',(-11.44,yy,zz),(.065,1.5,.035),'woodLight')
    for i in range(8):box('Shop_door_plank',(-11.49,3.18+i*.235,1.36),(.08,.22,2.65),'wood' if i%2 else 'walnut')
    for yy in (3.85,4.15):cyl('Shop_door_pull',(-11.42,yy,1.35),.035,.05,'brass',12,(0,pi/2,0),0)
    box('Shop_sign_frame',(-11.22,4,2.9),(.15,3.2,.48),'brass')
    front_sign('SIGN_shopName',(-11.132,4,2.9),3.04,.34,'green','east')
    # Two slopes of low-poly roof tiles, each tile is a folded shell.
    for row in range(2):
        xx=-11.72+row*.4;zz=3.38-row*.13
        box('Shop_eave_slope',(xx,4,zz),(.45,6.25,.07),'night')
        for i in range(26):
            yy=.93+i*.238
            tube('Shop_roof_tile',[(xx-.19,yy,zz+.03),(xx,yy,zz+.07),(xx+.19,yy,zz+.03)],.035,'iron',5)
    box('Shop_eave_front',(-11.11,4,3.18),(.09,6.35,.14),'wood')
    collision('shop_facade',(-11.55,4,1.6),(.75,6.25,3.2))
    item('S2-2')
    parts=[box('Counter_body',(-8.8,4,.48),(.64,2.54,.96),'wood',.008),
           box('Counter_top',(-8.8,4,.975),(.7,2.6,.05),'walnut',.008)]
    for yy in (2.78,3.59,4.41,5.22):parts.append(box('Counter_front_stile',(-8.464,yy,.48),(.025,.055,.83),'walnut'))
    for zz in (.1,.83):parts.append(box('Counter_panel_rail',(-8.458,4,zz),(.025,2.5,.055),'walnut'))
    parts.append(box('Counter_rim',(-9.13,4,1.017),(.035,2.6,.034),'brass'))
    join(parts,'INT_counter',(-8.8,4,0))
    collision('counter',(-8.8,4,.5),(.7,2.6,1))
    item('S2-3')
    x,y=-10.89,4
    parts=[]
    for yy in (y-1.06,y+1.06):parts.append(box('Shelf_side',(x,yy,1.1),(.45,.08,2.2),'walnut'))
    parts.append(box('Shelf_back',(x-.21,y,1.1),(.035,2.2,2.2),'woodDark'))
    for z in (.12,.8,1.48,2.16):parts.append(box('Shelf_board',(x,y,z),(.45,2.2,.06),'wood'))
    join(parts,'Shop_three_tier_shelf',(x,y,0))
    collision('shop_shelf',(x,y,1.1),(.45,2.2,2.2))
    item('S2-4')
    for i,h in enumerate((.3,.25,.21)):
        yy=3.24+i*.38
        lathe('Ceramic_goods_jar',(-10.82,yy,.83),[(.09,0),(.12,.04),(.13,h*.6),(.1,h*.85),(.07,h),(.06,h)],'ceramic' if i%2 else 'tea',14)
        cyl('Jar_lid',(-10.82,yy,.83+h+.012),.078,.025,'walnut',14,b=.002)
    for i in range(4):
        yy=3.18+i*.45
        box('Paper_goods_package',(-10.83,yy,1.64),(.27,.32,.23),'paper' if i%2 else 'woodLight',.006)
        box('Paper_package_twine',(-10.83,yy,1.759),(.008,.33,.003),'red',0)
        box('Paper_package_twine_cross',(-10.83,yy,1.761),(.28,.008,.003),'red',0)
    for i in range(4):box('Matchbox',(-10.8,4.75,.87+i*.04),(.1,.16,.036),'brick' if i%2 else 'paper',.002)
    ellipsoid('Salt_bag',(-10.8,4.2,.97),(.13,.14,.15),'paper',12,8)
    cyl('Salt_bag_tie',(-10.8,4.2,1.11),.037,.03,'red',10,b=0)
    lathe('Oil_bottle',(-10.81,4.75,1.51),[(.07,0),(.08,.025),(.08,.18),(.033,.23),(.03,.31)],'green',12)
    cyl('Oil_bottle_stop',(-10.81,4.75,1.83),.033,.04,'wood',12,b=0)
    for i in range(2):
        o=cyl('Cloth_roll',(-10.81,3.5+i*.62,2.29),.105,.46,'blue' if i else 'red',14,(pi/2,0,0),.002)
        cyl('Cloth_roll_core',(-10.81,3.26+i*.62,2.29),.035,.008,'paper',10,(pi/2,0,0),0)
    item('S2-5')
    # 13 rods along +Y, each with two far-side upper beads and five near-side lower beads.
    x,y,z=-8.75,4.25,1.02
    for dx in (-.077,.077):box('Abacus_long_frame',(x+dx,y,z+.015),(.018,.45,.03),'walnut',.002)
    for dy in (-.22,.22):box('Abacus_end_frame',(x,y+dy,z+.015),(.15,.018,.03),'walnut',.002)
    beam_x=x+.020
    box('Abacus_divider',(beam_x,y,z+.014),(.009,.43,.022),'brass',.001)
    for i in range(13):
        yy=y-.195+i*.0325
        rod('Abacus_wire',(x-.064,yy,z+.015),(x+.064,yy,z+.015),.0016,'brass',6)
        for j,xx in enumerate((.0325,.050,.0075,-.008,-.0235,-.039,-.0545),1):
            vs=[(x+xx-.007,yy,z+.018),(x+xx+.007,yy,z+.018)]
            vs += [(x+xx,yy+.0105*cos(2*pi*j/8),z+.018+.007*sin(2*pi*j/8)) for j in range(8)]
            fs=[(0,2+j,2+(j+1)%8) for j in range(8)]+[(1,2+(j+1)%8,2+j) for j in range(8)]
            bead=mesh(f'ANIM_bead_{i+1:02d}_{j}',vs,fs,'woodDark')
            pivot(bead,(x+xx,yy,z+.018),'bead center','')
            bead['translation_axis_blender']='X'
            bead['abacus_rod']=i+1;bead['bead_index']=j
            bead['bead_group']='upper' if j<=2 else 'lower'
            bead['beam_x_blender']=beam_x
    item('S2-6')
    x,y,z=-8.76,3.35,1.005
    box('Ledger_cover',(x,y,z+.012),(.22,.30,.024),'red')
    box('Ledger_page_block',(x,y,z+.029),(.22,.30,.018),'paper',0)
    for side,dy in [('L',.075),('R',-.075)]:
        page=box('SIGN_ledger'+side,(x,y+dy,z+.040),(.22,.15,.003),'paper',0)
        page['blank_surface']=True
        page['uv_u_axis_blender']='-Y';page['uv_v_axis_blender']='+X'
    rod('Ledger_spine',(x-.11,y,z+.037),(x+.11,y,z+.037),.003,'brass',6)
    box('Inkstone',(-8.70,3.78,1.027),(.11,.13,.045),'iron',.006)
    box('Ink_pool',(-8.70,3.78,1.052),(.075,.085,.005),'ink',0)
    rod('Brush_handle',(-8.88,3.57,1.05),(-8.71,3.71,1.05),.004,'woodLight',8)
    rod('Brush_tip',(-8.71,3.71,1.05),(-8.68,3.735,1.05),.006,'ink',8)
    item('S2-7')
    x,y,z=-8.78,4.99,1.005
    lathe('Oil_lamp_base',(x,y,z),[(.07,0),(.075,.02),(.06,.055),(.04,.09),(.045,.105)],'copper',16)
    lathe('EMIT_oilLamp',(x,y,z+.105),[(.04,0),(.06,.05),(.052,.14),(.032,.20),(.025,.21)],'warm',16)
    lathe('Oil_lamp_cap',(x,y,z+.315),[(.03,0),(.05,.008),(.037,.026),(.017,.035)],'iron',16)
    tube('Oil_lamp_handle',[(x-.065,y,z+.11),(x-.074,y,z+.3),(x,y,z+.345),(x+.074,y,z+.3),(x+.065,y,z+.11)],.005,'iron',6)
    item('S2-8')
    for i,yy in enumerate((2.5,4.2,5.9),1):
        x=-6.95
        # Thick die-cut silhouette, with UVs on its complete front face.
        contour=[(-.27,0),(.27,0),(.25,.78),(.36,1.01),(.25,1.2),(.13,1.27),(.16,1.44),(.11,1.57),
                 (0,1.6),(-.11,1.57),(-.16,1.44),(-.13,1.27),(-.25,1.2),(-.36,1.01),(-.25,.78)]
        verts=[(x+depth,yy+u,h+.035) for depth in (-.012,.012) for u,h in contour]
        n=len(contour);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        o=mesh(f'SIGN_customer_{i:02d}',verts,faces,'paper');o['blank_surface']=True;o['surface_front_blender']='+X'
        box('Customer_stand',(x,yy,.025),(.42,.5,.05),'green')
    item('S2-9')
    pts=[(-6.35,1.7),(-6.35,3.3),(-6.35,4.9),(-6.35,6.5)]
    for x,y in pts:rope_post('Shop_barrier_post',x,y)
    for a,b in zip(pts,pts[1:]):rope('Shop_barrier_rope',(*a,.9),(*b,.9))
    item('S2-10')
    plaque('label_shop',(-5.15,5.8,0))


def tea():
    item('S3-1')
    box('Tea_wall',(-7,15.66,1.6),(6,.3,3.2),'ivory')
    box('Tea_wainscot',(-7,15.48,.48),(6,.055,.96),'walnut')
    for x in (-9.9,-8.9,-7.9,-6.9,-5.9,-4.9,-4.1):box('Tea_wainscot_batten',(x,15.438,.48),(.042,.03,.9),'wood')
    for x in (-8.8,-5.2):
        box('Tea_window_recess',(x,15.477,2.12),(1.55,.018,1.55),'night',0)
        box('Tea_window_glass',(x,15.454,2.12),(1.49,.01,1.49),'glass',0)
        for dx in (-.78,-.39,0,.39,.78):box('Tea_window_vertical',(x+dx,15.405,2.12),(.045,.055,1.62),'wood')
        for dz in (-.78,-.39,0,.39,.78):box('Tea_window_horizontal',(x,15.403,2.12+dz),(1.62,.055,.045),'wood')
        # Geometric cut-paper rosette with open negative space; contains no text.
        for j in range(8):
            a=j*pi/4
            v=[(x+.09*cos(a-.36),15.365,2.12+.09*sin(a-.36)),(x+.3*cos(a),15.365,2.12+.3*sin(a)),
               (x+.09*cos(a+.36),15.365,2.12+.09*sin(a+.36)),(x+.16*cos(a),15.365,2.12+.16*sin(a))]
            mesh('Red_paper_window_flower',v,[(0,1,3),(1,2,3)],'red')
        ring('Paper_flower_ring',(x,15.363,2.12),.105,'red',.012,n=16,sides=4)
    collision('tea_background',(-7,15.66,1.6),(6,.3,3.2))
    item('S3-2')
    table('Tea_table',-7,13.1,1.6,.8,.8)
    box('Tea_tray',(-6.67,13.1,.82),(.62,.34,.035),'woodLight',.006)
    for dx in (-.3,.3):box('Tea_tray_edge',(-6.67+dx,13.1,.848),(.018,.34,.032),'walnut',.002)
    for dy in (-.16,.16):box('Tea_tray_edge',(-6.67,13.1+dy,.848),(.6,.018,.032),'walnut',.002)
    item('S3-3')
    x,y=-8.25,13.1
    parts=[lathe('Stove_body',(x,y,.07),[(.17,0),(.195,.03),(.195,.37),(.18,.48),(.195,.51)],'iron',16)]
    for dx in (-.14,.14):
        for dy in (-.14,.14):parts.append(box('Stove_foot',(x+dx,y+dy,.065),(.045,.045,.13),'iron'))
    parts.append(box('Stove_fire_opening',(x,y-.191,.29),(.23,.016,.18),'ink'))
    for xx in (-.08,-.04,0,.04,.08):parts.append(rod('Stove_grate',(x+xx,y-.21,.21),(x+xx,y-.21,.37),.008,'iron',6))
    for dx in (-.14,.14):parts.append(box('Stove_top_support',(x+dx,y,.59),(.035,.31,.02),'iron',.002))
    join(parts,'INT_stove',(x,y,0))
    box('EMIT_fire',(x,y-.203,.29),(.21,.004,.15),'fire',0)
    collision('stove',(x,y,.3),(.4,.4,.6))
    item('S3-4')
    x,y,z=-7.48,13.1,.8
    parts=[lathe('Kettle_body',(x,y,z),[(.085,0),(.11,.025),(.115,.09),(.105,.15),(.075,.18),(.066,.185)],'copper',20)]
    parts.append(tube('Kettle_spout',[(x+.077,y,z+.065),(x+.125,y,z+.105),(x+.151,y,z+.17)],.025,'copper',8))
    pts=[(x-.095*cos(a),y,z+.17+.11*sin(a)) for a in [i*pi/12 for i in range(13)]]
    parts.append(tube('Kettle_handle',pts,.012,'iron',8))
    kettle=join(parts,'INT_kettle',(x,y,z))
    lidparts=[lathe('Kettle_lid',(x,y,z+.18),[(.07,0),(.075,.008),(.046,.026),(.012,.028)],'copper',20),
              cyl('Kettle_lid_knob',(x,y,z+.22),.018,.024,'iron',12,b=.002)]
    lid=join(lidparts,'ANIM_kettleLid');pivot(lid,(x,y+.067,z+.185),'lid rear hinge','X')
    item('S3-5')
    x,y,z=-6.72,13.13,.84
    parts=[lathe('Teapot_body',(x,y,z),[(.045,0),(.067,.026),(.072,.077),(.055,.121),(.043,.130)],'tea',18)]
    parts.append(tube('Teapot_spout',[(x+.052,y,z+.055),(x+.096,y,z+.103),(x+.119,y,z+.143)],.016,'tea',8))
    parts.append(tube('Teapot_handle',[(x-.053,y,z+.03),(x-.09,y,z+.035),(x-.103,y,z+.105),
       (x-.095,y,z+.145),(x-.08,y,z+.15),(x-.065,y,z+.145),(x-.055,y,z+.12)],.01,'tea',8))
    join(parts,'INT_teapot',(x,y,z))
    parts=[lathe('Teapot_lid',(x,y,z+.129),[(.044,0),(.05,.006),(.025,.018),(.008,.021)],'tea',18),
           ellipsoid('Teapot_lid_finial',(x,y,z+.15),(.014,.014,.01),'brass',12,6)]
    lid=join(parts,'ANIM_potLid');pivot(lid,(x,y+.044,z+.132),'lid rear hinge','X')
    item('S3-6')
    for i,(dx,dy) in enumerate([(-.15,-.08),(.06,-.08),(-.15,.08),(.06,.08)],1):
        xx,yy=-6.59+dx,13.1+dy
        lathe(f'INT_cup_{i}',(xx,yy,.84),[(.025,0),(.03,.005),(.04,.064),(.04,.07),(.034,.07),(.028,.014)],'ceramic',16)
    item('S3-7')
    x,y,z=-7.02,13.36,.8
    lathe('INT_caddy',(x,y,z),[(.045,0),(.05,.012),(.05,.125),(.044,.134)],'green',16)
    lid=cyl('ANIM_caddyLid',(x,y,z+.142),.052,.016,'brass',16,b=.002)
    pivot(lid,(x,y+.045,z+.134),'lid rear hinge','X')
    item('S3-8')
    x,y,z=-7,15.37,2.6
    cyl('Clock_case',(x,y,z),.25,.085,'walnut',32,(pi/2,0,0),.003)
    cyl('Clock_blank_face',(x,y-.049,z),.225,.008,'paper',32,(pi/2,0,0),0)
    ring('Clock_bezel',(x,y-.06,z),.232,'brass',.008,n=32,sides=5)
    for i in range(12):
        a=i*pi/6
        rod('Clock_tick',(x+.185*sin(a),y-.057,z+.185*cos(a)),(x+.208*sin(a),y-.057,z+.208*cos(a)),.0035,'walnut',4)
    h=box('ANIM_hourHand',(x-.032,y-.07,z+.043),(.014,.008,.12),'iron',.002)
    h.rotation_euler.y=-.6;pivot(h,(x,y-.07,z),'clock axis','Y')
    m=box('ANIM_minHand',(x+.045,y-.082,z+.063),(.008,.006,.17),'brass',.001)
    m.rotation_euler.y=.62;pivot(m,(x,y-.082,z),'clock axis','Y')
    cyl('Clock_center_pin',(x,y-.09,z),.014,.012,'copper',12,(pi/2,0,0),0)
    item('S3-9')
    box('Gantt_frame',(-11.68,12.4,2.1),(.08,2.4,1.4),'brass')
    front_sign('SIGN_gantt',(-11.631,12.4,2.1),2.32,1.32,'green','east')
    collision('gantt_board',(-11.68,12.4,2.1),(.08,2.4,1.4))
    item('S3-10')
    for i,xx in enumerate((-7.55,-6.35),1):table(f'Tea_stool_{i}',xx,12.15,.4,.4,.45,'wood')
    item('S3-11')
    rod('Pendant_cord',(-7,13.1,4),(-7,13.1,3.06),.008,'iron',8)
    lathe('Pendant_shade',(-7,13.1,2.9),[(.175,0),(.174,.016),(.06,.18),(.03,.19)],'green',20)
    cyl('Pendant_brass_rim',(-7,13.1,2.905),.177,.018,'brass',20,b=.002)
    ellipsoid('EMIT_pendant',(-7,13.1,2.89),(.055,.055,.045),'warm',16,8)
    item('S3-12')
    plaque('label_tea',(-4.1,10.1,0))


def gear(name,x,y,z,r,teeth):
    verts=[];faces=[];n=teeth*4
    for depth in (-.028,.028):
        for i in range(n):
            a=2*pi*i/n;rr=r*(1 if i%4 in (1,2) else .84)
            verts.append((x+rr*cos(a),y+depth,z+rr*sin(a)))
        for i in range(n):
            a=2*pi*i/n;verts.append((x+r*.3*cos(a),y+depth,z+r*.3*sin(a)))
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),
                  (i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)]
    o=mesh(name,verts,faces,'brass')
    pivot(o,(x,y,z),'gear shaft','Y')
    return o


def factory():
    item('S4-1')
    box('Factory_wall',(5,15.64,2),(8,.3,4),'mortar')
    # Brick faces are shallow mesh quads, leaving actual mortar gaps.
    verts=[];faces=[]
    for j in range(13):
        z=.04+j*.2;start=1.03-(.3 if j%2 else 0)
        for i in range(15):
            a=max(1.025,start+i*.6);b=min(8.975,start+(i+1)*.6-.025)
            if b-a<.02:continue
            k=len(verts);verts += [(a,15.478,z),(b,15.478,z),(b,15.478,z+.175),(a,15.478,z+.175)]
            faces.append((k,k+1,k+2,k+3))
    bricks=mesh('Factory_brick_faces',verts,faces,'brick')
    bricks.data.materials.append(M['brickLight'])
    for p in bricks.data.polygons:p.material_index=1 if p.index%11==0 else 0
    windows=[]
    for xx in (2.1,4.03,5.96,7.89):
        box('Factory_window_recess',(xx,15.463,3.18),(1.7,.02,1.1),'iron',0)
        windows.append(box('High_window_glass',(xx,15.438,3.18),(1.57,.012,.97),'cool',0))
        for dx in (-.82,0,.82):box('High_window_mullion',(xx+dx,15.41,3.18),(.04,.07,1.12),'iron',.002)
        for dz in (-.54,0,.54):box('High_window_rail',(xx,15.409,3.18+dz),(1.7,.07,.04),'iron',.002)
    join(windows,'EMIT_highWindow')
    rod('Factory_wall_pipe',(8.65,15.36,.15),(8.65,15.36,3.9),.045,'iron',12)
    rod('Factory_wall_pipe_upper',(1.2,15.36,3.88),(8.65,15.36,3.88),.045,'iron',12)
    collision('factory_background',(5,15.64,2),(8,.3,4))
    item('S4-2')
    x,y=3.4,13.8
    box('Furnace_hearth',(x,y,.075),(1.48,1.08,.15),'iron',.008)
    box('Furnace_body',(x,y,.83),(1.4,1,1.5),'brick',.008)
    box('Furnace_iron_top',(x,y,1.57),(1.44,1.04,.08),'iron',.006)
    for zz in (.25,.55,.85,1.15,1.45):box('Furnace_mortar',(x,y-.503,zz),(1.38,.008,.012),'mortar',0)
    for zz in (.4,1.0,1.3):
        for dx in (-.43,.1):box('Furnace_vertical_joint',(x+dx,y-.508,zz),(.012,.005,.28),'mortar',0)
    box('Furnace_iron_aperture',(x,y-.518,.7),(.86,.05,.68),'iron')
    box('EMIT_furnaceGlow',(x,y-.549,.7),(.71,.008,.53),'glow',0)
    # Closed at rotation zero; one explicit hinge origin drives the whole iron leaf.
    parts=[box('Furnace_door_leaf',(x,y-.59,.7),(.81,.07,.61),'iron',.007),
           box('Furnace_door_inset',(x,y-.633,.7),(.63,.02,.43),'bronzeDark',.006)]
    for dx in (-.3,.3):
        for dz in (-.22,.22):parts.append(cyl('Furnace_door_rivet',(x+dx,y-.655,.7+dz),.018,.015,'brass',8,(pi/2,0,0),0))
    parts.append(rod('Furnace_door_handle',(x+.24,y-.69,.62),(x+.24,y-.69,.8),.014,'brass',8))
    door=join(parts,'ANIM_furnaceDoor')
    hinge=Vector((x-.42,y-.59,.7))
    pivot(door,hinge,'furnace door hinge','Z')
    door['closed_rotation_radians']=0.0
    cyl('Furnace_flue',(x+.43,y+.12,1.69),.12,.22,'iron',16,b=.003)
    cyl('Furnace_flue_rim',(x+.43,y+.12,1.79),.15,.04,'iron',16,b=.003)
    collision('furnace',(x,y,.9),(1.5,1.1,1.8))
    item('S4-3')
    x,y=4.92,13.45
    box('Control_cabinet',(x,y,.45),(.9,.5,.9),'green',.008)
    for dx in (-.35,.35):box('Control_foot',(x+dx,y,.035),(.12,.4,.07),'iron')
    # Sloped console: front z=.92, rear z=1.10, depth=.5.
    v=[(x-.45,y-.25,.88),(x+.45,y-.25,.88),(x+.45,y+.25,.88),(x-.45,y+.25,.88),
       (x-.45,y-.25,.92),(x+.45,y-.25,.92),(x+.45,y+.25,1.1),(x-.45,y+.25,1.1)]
    mesh('Console_sloped_top',v,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],'iron')
    angle=math.atan2(.18,.5)
    dial=cyl('INT_dial',(x-.22,y-.035,1.036),.095,.046,'brass',24,b=.004)
    dial.rotation_euler.x=angle
    marker=box('Dial_pointer',(x-.22,y-.089,1.064),(.012,.05,.012),'ivory',.002)
    dial=join([dial,marker],'INT_dial');pivot(dial,(x-.22,y-.035,1.036),'sloped knob shaft','0,-0.339,0.941')
    btn=cyl('INT_testBtn',(x+.19,y-.12,1.005),.043,.04,'red',16,b=.003)
    btn.rotation_euler.x=angle;pivot(btn,(x+.19,y-.12,1.005),'button travel','0,-0.339,0.941')
    screen=box('SIGN_tempReadout',(x+.12,y+.1,1.059),(.34,.15,.005),'night',0)
    screen.rotation_euler.x=angle;screen['blank_surface']=True
    box('Control_door_seam',(x,y-.254,.49),(.72,.01,.64),'greenLight')
    cyl('Control_keyhole',(x+.23,y-.267,.56),.016,.015,'brass',10,(pi/2,0,0),0)
    collision('control_console',(x,y,.55),(.9,.5,1.1))
    item('S4-4')
    x,y,z=3.4,13.26,1.30
    cyl('Furnace_temperature_gauge',(x,y,z),.2,.06,'brass',28,(pi/2,0,0),.003)
    front=cyl('SIGN_dial',(x,y-.036,z),.178,.006,'paper',28,(pi/2,0,0),0)
    front['blank_surface']=True;front['surface_front_blender']='-Y'
    for i in range(11):
        a=(-.8+i*.16)*pi
        rod('Temperature_tick',(x+.145*sin(a),y-.042,z+.145*cos(a)),(x+.164*sin(a),y-.042,z+.164*cos(a)),.002,'iron',4)
    needle=rod('ANIM_needle',(x,y-.05,z),(x-.11,y-.05,z+.09),.005,'red',6)
    pivot(needle,(x,y-.05,z),'gauge shaft','Y')
    cyl('Gauge_center',(x,y-.06,z),.013,.014,'iron',12,(pi/2,0,0),0)
    item('S4-5')
    x,y=7.3,13.5
    for dx in (-.78,.78):
        box('Blackboard_upright',(x+dx,y,.9),(.055,.07,1.8),'walnut')
        box('Blackboard_foot',(x+dx,y,.03),(.12,.5,.06),'walnut')
    box('Blackboard_frame',(x,y,1.26),(1.8,.075,1.28),'walnut',.006)
    front_sign('SIGN_board',(x,y-.044,1.26),1.66,1.13,'green')
    box('Blackboard_chalk_trough',(x,y-.105,.62),(1.76,.16,.055),'wood')
    for i in range(4):cyl('Chalk_piece',(x-.5+i*.14,y-.12,.661),.008,.072,'chalk',8,(0,pi/2,0),0)
    collision('blackboard',(x,y,.95),(1.8,.5,1.9))
    item('S4-6')
    x,y=9.5,13.6
    for dx in (-.47,.47):
        for dy in (-.12,.12):box('Sample_rack_leg',(x+dx,y+dy,.6),(.035,.035,1.2),'iron',.002)
    for z in (.44,1.03):box('Sample_rack_shelf',(x,y,z),(1,.3,.035),'iron',.002)
    for i in range(8):
        dx=(i%4-1.5)*.22;z=.44 if i<4 else 1.03
        o=box(f'ANIM_sample_{i+1}',(x+dx,y,z+.082),(.15,.15,.13),'blue' if i%2 else 'copper',.005)
        pivot(o,(x+dx,y,z+.0175),'sample bottom')
    collision('sample_rack',(x,y,.6),(1,.3,1.2))
    item('S4-7')
    for i,(x,z,r,n) in enumerate([(5.65,2.53,.25,12),(6.3,2.66,.4,16),(7.55,2.15,.6,20)],1):
        gear(f'ANIM_gear_{i}',x,15.32,z,r,n)
        cyl('Gear_shaft',(x,15.34,z),r*.18,.16,'iron',12,(pi/2,0,0),0)
    item('S4-8')
    table('Factory_workbench',.05,13.9,2,.8,.9,'wood')
    # Tool silhouettes, crafted as real simple meshes.
    rod('Wrench_handle',(-.6,13.8,.93),(-.22,13.8,.93),.018,'iron',8)
    tube('Wrench_open_jaw',[(-.64,13.73,.93),(-.71,13.76,.93),(-.71,13.84,.93),(-.64,13.87,.93)],.023,'iron',6)
    ring('Wrench_ring',(-.20,13.8,.93),.046,'iron',.012,'Z',12,5)
    box('Workbench_ruler',(.37,13.75,.915),(.53,.045,.016),'brass',.002)
    for i in range(12):box('Ruler_tick',(.13+i*.043,13.735,.925),(.003,.013,.002),'ink',0)
    box('Notebook_cover',(.25,14.07,.921),(.29,.24,.04),'green')
    o=box('SIGN_notebook',(.25,14.07,.943),(.26,.21,.003),'paper',0);o['blank_surface']=True
    item('S4-9')
    plaque('label_factory',(3.0,10.2,0))


def exit_hall():
    item('S5-1')
    # Exact contiguous Fibonacci square tiling (1,1,2,3,5,8,13,21), turned clockwise.
    squares=[(0,0,1),(1,0,1),(0,1,2),(-3,0,3),(-3,-5,5),(2,-5,8),(-3,3,13),(-24,-5,21)]
    xmin=min(x for x,z,s in squares);xmax=max(x+s for x,z,s in squares)
    zmin=min(z for x,z,s in squares);zmax=max(z+s for x,z,s in squares)
    scale=3/(xmax-xmin);cx=(xmin+xmax)/2
    colors=['paper','woodLight','greenLight','wood','green','brick','night','walnut']
    for i,(x,z,s) in enumerate(squares,1):
        xx=8+(x+s/2-cx)*scale;zz=.3+(z+s/2-zmin)*scale
        o=box(f'ANIM_fib_{i}',(xx,4.7,zz),(s*scale-.004,.12,s*scale-.004),colors[i-1],.002)
        pivot(o,(xx,4.7,zz),'square center')
    # Eight tangent quarter-circle arcs, with exactly the matching Fibonacci radii.
    # This is the familiar Fibonacci approximation to a golden logarithmic spiral.
    centers=[(1,1),(1,1),(0,1),(0,0),(2,0),(2,3),(-3,3),(-3,-5)]
    starts=[pi,1.5*pi,0,pi/2,pi,1.5*pi,0,pi/2]
    pts=[]
    for i,((ax,az),start,(_,_,radius)) in enumerate(zip(centers,starts,squares)):
        for j in range(21):
            if i and j==0:continue
            a=start+j*pi/40
            pts.append((8+(ax+radius*cos(a)-cx)*scale,4.795,.3+(az+radius*sin(a)-zmin)*scale))
    tube('Golden_spiral_brass',pts,.009,'brass',6)
    for xx in (6.62,9.38):box('Spiral_stand',(xx,4.7,.14),(.12,.3,.28),'iron')
    collision('golden_spiral',(8,4.7,1.1),(3,.3,2.2))
    item('S5-2')
    table('Guestbook_desk',10.6,1.9,1.2,.6,1,'walnut')
    book('guestbook',10.6,1.9,1,.45,.3)
    # Guestbook is one full surface for an application-owned spread texture.
    left=bpy.data.objects['SIGN_guestbookL'];right=bpy.data.objects['SIGN_guestbookR']
    o=join([left,right],'SIGN_guestbook');o['blank_surface']=True
    rod('Guestbook_pen',(10.93,1.78,1.06),(10.93,2.02,1.06),.006,'brass',8)
    item('S5-3')
    box('Epilogue_wall',(7.4,.22,1.2),(4,.1,2.4),'green')
    box('Epilogue_frame',(7.4,.285,1.4),(3.7,.025,1.65),'brass')
    front_sign('SIGN_epilogue',(7.4,.305,1.4),3.56,1.51,'paper')
    # This south-wall panel faces north into the room.
    bpy.data.objects['SIGN_epilogue']['surface_front_blender']='+Y'
    collision('epilogue',(7.4,.22,1.2),(4,.1,2.4))


def common():
    item('S6-1')
    # Slightly curved, thick cardstock; front/back grid supports straight UV mapping.
    verts=[];faces=[]
    for side in (-1,1):
        for i in range(7):
            x=-.125+i*.25/6;y=.013*(x/.125)**2+side*.002
            verts.extend([(x,y,.3-.175),(x,y,.3+.175)])
    for i in range(6):
        a=2*i;faces.extend([(a,a+2,a+3,a+1),(14+a+1,14+a+3,14+a+2,14+a)])
        faces.extend([(a,14+a,14+a+2,a+2),(a+1,a+3,14+a+3,14+a+1)])
    faces.extend([(0,1,15,14),(12,26,27,13)])
    o=mesh('SIGN_card',verts,faces,'paper');o['blank_surface']=True
    pivot(o,(0,.0065,.3),'card center')
    item('S6-2')
    plaque('label',(-1.25,0,0))
    item('S6-3')
    parts=rope_post('Common_stanchion',1.05,0)
    post=join(parts,'Common_stanchion',(1.05,0,0))
    # Keep cross sections in YZ so the mesh's X length is exactly 1 m,
    # even with the hanging curve. X=0 is the fixed hook for runtime stretching.
    verts=[];faces=[];rings=10;sides=6
    for i in range(rings):
        t=i/(rings-1)
        for j in range(sides):
            a=2*pi*j/sides
            verts.append((1.05+t,.018*cos(a),.9-.12*sin(pi*t)+.018*sin(a)))
    for i in range(rings-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces += [tuple(reversed(range(sides))),tuple((rings-1)*sides+j for j in range(sides))]
    cord=mesh('Common_rope',verts,faces,'red')
    pivot(cord,(1.05,0,.9),'rope hook','')
    cord['stretch_axis_blender']='X';cord['rest_length_m']=1.0
    item('S6-4')
    x,y=-.1,-.9
    mesh('Common_floor_arrow',[(x-.075,y-.3,.002),(x+.075,y-.3,.002),(x+.075,y+.045,.002),
        (x+.3,y+.045,.002),(x,y+.3,.002),(x-.3,y+.045,.002),(x-.075,y+.045,.002)],
        [(0,1,2,3,4,5,6)],'brass')
    item('S6-5')
    plant('Common_small_plant',.1,.95,.5)


def bake_and_audit(name):
    # Bake all bevels, rotations and scales, leaving positions in museum coordinates.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    # Merge only static pieces of the same listed item. Preserve all runtime nodes.
    for col in list(SCENE.collection.children):
        static=[o for o in col.objects if not o.name.startswith(('INT_','ANIM_','SIGN_','EMIT_','COL_'))
                and o.name not in {'Common_stanchion','Common_rope'} and not o.get('preserve_part')]
        if len(static)>1:
            global ITEM
            ITEM=col.name
            join(static,col.name.replace('-','_')+'_static')
    errors=[];items={};objects=[]
    for o in SCENE.objects:
        if o.type!='MESH':errors.append('Unexpected type: '+o.name);continue
        # Recalculate closed mesh orientation, retaining intentional open sign faces.
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(o.data);bm.free();o.data.update()
        if o.name in PIVOTS:
            p,role,axis=PIVOTS[o.name]
            origin(o,p)
        else:
            vs=[o.matrix_world@Vector(v) for v in o.bound_box]
            origin(o,((min(v.x for v in vs)+max(v.x for v in vs))/2,
                      (min(v.y for v in vs)+max(v.y for v in vs))/2,min(v.z for v in vs)))
        # Assign explicit UVs to every sign after final vertex positions are established.
        if o.name.startswith('SIGN_'):
            if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
            coords=[v.co for v in o.data.vertices]
            ranges=[max(v[k] for v in coords)-min(v[k] for v in coords) for k in range(3)]
            axes=sorted(range(3),key=lambda k:ranges[k],reverse=True)[:2]
            if 2 in axes:axes=[next(a for a in axes if a!=2),2]
            else:axes=sorted(axes)
            ledger=o.name in ('SIGN_ledgerL','SIGN_ledgerR')
            if ledger:axes=[1,0]
            low=[min(v[k] for v in coords) for k in axes]
            front=o.get('surface_front_blender','')
            for poly in o.data.polygons:
                for li in poly.loop_indices:
                    v=o.data.vertices[o.data.loops[li].vertex_index].co
                    u=(v[axes[0]]-low[0])/max(ranges[axes[0]],1e-8)
                    vv=(v[axes[1]]-low[1])/max(ranges[axes[1]],1e-8)
                    if front in ('-X','+Y'):u=1-u
                    if ledger:u=1-u
                    o.data.uv_layers.active.data[li].uv=(u,vv)
            o['uv_note']='UVMap: U=-Y, V=+X, viewed from the counter behind (-X).' if ledger else 'UVMap: normalized full surface, upright from surface_front_blender.'
        o.data.calc_loop_triangles()
        tri=len(o.data.loop_triangles)
        code=o['item'];items[code]=items.get(code,0)+tri
        if any(abs(v-1)>1e-5 for v in o.scale) or any(abs(v)>1e-5 for v in o.rotation_euler):errors.append('Unapplied transform '+o.name)
        objects.append({'name':o.name,'item':code,'triangles':tri,'origin':[round(v,6) for v in o.location],
          'dimensions':[round(v,6) for v in o.dimensions],
          'pivot_role':o.get('pivot_role','bottom center'),'rotation_axis':o.get('rotation_axis_blender',''),
          'translation_axis':o.get('translation_axis_blender',''),'stretch_axis':o.get('stretch_axis_blender',''),
          'blank_surface':o.name.startswith('SIGN_'),'collision':o.name.startswith('COL_')})
    for m in bpy.data.materials:
        if not m.use_nodes:continue
        bad=[n.type for n in m.node_tree.nodes if n.type not in ('BSDF_PRINCIPLED','OUTPUT_MATERIAL','TEX_IMAGE')]
        if bad:errors.append('Unsupported material '+m.name+':'+str(bad))
        p=m.node_tree.nodes.get('Principled BSDF')
        if p and p.inputs['Transmission Weight'].default_value!=0:errors.append('Transmission '+m.name)
    missing=[n for n in REQUIRED[name] if n not in SCENE.objects]
    if missing:errors.append('Missing nodes '+str(missing))
    over={k:{'triangles':v,'limit':BUDGETS[k]} for k,v in items.items() if v>BUDGETS[k]}
    if over:errors.append('Over budget '+str(over))
    report={'file':name,'objects':len(objects),'triangles':sum(items.values()),'items':items,
            'budget_limits':{k:BUDGETS[k] for k in items},'required_nodes':len(REQUIRED[name]),
            'missing_nodes':missing,'errors':errors,'object_manifest':objects}
    (OUT/(name+'.audit.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors:raise RuntimeError(name+': '+str(errors))
    return report


def save_export(name):
    # A picked-up vessel carries its independently animated lid with it.
    for child_name,parent_name in [('ANIM_kettleLid','INT_kettle'),('ANIM_potLid','INT_teapot'),('ANIM_caddyLid','INT_caddy')]:
        child=SCENE.objects.get(child_name);parent=SCENE.objects.get(parent_name)
        if child and parent:
            bpy.context.view_layer.update()
            world=child.matrix_world.copy()
            child.parent=parent
            child.matrix_world=world
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='SELECT')
    SCENE.camera=None
    # Open in a useful material-colored solid view without adding camera/light objects.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.shading.color_type='MATERIAL'
                area.spaces.active.clip_end=200
                area.spaces.active.clip_start=.01
                if name in VIEWS:
                    eye,target,scale,_=VIEWS[name]
                    region=area.spaces.active.region_3d
                    region.view_location=target
                    region.view_rotation=(Vector(target)-Vector(eye)).to_track_quat('-Z','Y')
                    region.view_distance=scale*1.25
                    region.view_perspective='ORTHO'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')),compress=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,
        export_apply=True,export_yup=True,export_lights=False,export_cameras=False,
        export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
        export_animations=False,export_extras=True,export_normals=True,export_texcoords=True)


VIEWS={
 'S0_shell':((30,-31,32),(0,8,0),33,(-12,12,0,16)),
 'S1_lobby':((-8,-7,6.7),(.2,4,1),11.2,(-4,4,0,8)),
 'S2_shop':((-.3,-2.2,5.4),(-8.8,4.1,1.4),10.4,(-12,-4,0,8)),
 'S3_tea':((.5,5.7,6.2),(-7.6,12.8,1.4),11.2,(-12,-2,8,16)),
 'S4_factory':((15,4,7.2),(4.6,13.3,1.65),12,(-2,12,8,16)),
 'S5_exit':((15,11,5.7),(8,3.4,1.1),9.6,(4,12,0,8)),
 'S6_common':((4,-6,3.7),(.15,.15,.5),4.7,(-2.2,2.3,-1.6,1.6)),
}


def setup_render():
    SCENE.render.engine='CYCLES'
    SCENE.cycles.samples=40
    SCENE.cycles.use_denoising=True
    SCENE.cycles.max_bounces=6
    SCENE.cycles.transparent_max_bounces=8
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        gpus=[d for d in prefs.devices if d.type!='CPU']
        if gpus:
            for d in prefs.devices:d.use=d.type!='CPU'
            SCENE.cycles.device='GPU'
    except Exception as e:print('GPU fallback:',str(e),flush=True)
    SCENE.render.resolution_x=1440;SCENE.render.resolution_y=1000;SCENE.render.resolution_percentage=100
    SCENE.render.image_settings.file_format='PNG'
    SCENE.world=bpy.data.worlds.new('Preview night world')
    SCENE.world.use_nodes=True
    SCENE.world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.075,.13,1)
    SCENE.world.node_tree.nodes['Background'].inputs[1].default_value=.4
    SCENE.view_settings.view_transform='AgX'
    SCENE.render.film_transparent=False


def light(name,loc,target,power,color,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);COL.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o


def preview(name):
    if SKIP_RENDER:return
    item('PREVIEW_ONLY')
    setup_render()
    eye,target,scale,bounds=VIEWS[name]
    x0,x1,y0,y1=bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
    hidden=[]
    # Collision meshes stay in every delivered file, but are deliberately absent
    # from beauty renders (the runtime also sets their visibility to false).
    for o in list(SCENE.objects):
        if o.name.startswith('COL_'):
            o.hide_render=True;hidden.append(o)
    if name=='S0_shell':
        # Static pieces merged by item; hide roof and trim in a documented cutaway.
        for o in list(SCENE.objects):
            if o.get('item') in ('S0-3','S0-4'):
                o.hide_render=True;hidden.append(o)
        # Shell source remains complete. South/east walls are omitted ONLY in preview.
        shellmesh=SCENE.objects.get('S0_2_static')
        if shellmesh:
            shellmesh.hide_render=True;hidden.append(shellmesh)
            # Build a clean north/west/partition cutaway from original geometry bounds.
            for o in list(SCENE.objects):
                if o.name.startswith('COL_Wall') and not any(k in o.name for k in ('south_left','south_right','south_header','east_lower','east_upper','east_header')):
                    p=o.location+Vector((0,0,o.dimensions.z/2))
                    box('Preview_wall',p,o.dimensions,'green' if 'shop' in o.name or 'tea_factory' in o.name else 'ivory')
    else:
        box('Preview_room_floor',(cx,cy,-.085),(x1-x0,y1-y0,.15),'walnut' if name in ('S2_shop','S3_tea','S4_factory') else 'ivory',.006)
    box('Preview_diorama_base',(cx,cy,-.24),(x1-x0+.14,y1-y0+.14,.28),'night',.008)
    box('Preview_ground',(cx,cy,-.43),(200,200,.08),'night',0)
    light('Preview_warm_key',(cx-3,cy-4,8),(cx,cy,0),2300 if name!='S0_shell' else 6500,(1,.74,.46),7)
    light('Preview_cool_rim',(cx+3,cy+4,7),(cx,cy,1),1800 if name!='S0_shell' else 6000,(.48,.67,1),6)
    light('Preview_front_fill',(cx+6,cy-3,4),(cx,cy,1),850 if name!='S0_shell' else 4000,(1,.9,.73),5)
    d=bpy.data.cameras.new('Preview camera');cam=bpy.data.objects.new('Preview camera',d);COL.objects.link(cam)
    cam.location=eye;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO';d.ortho_scale=scale;d.lens=48;SCENE.camera=cam
    SCENE.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    for o in hidden:o.hide_render=False
    for o in list(COL.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(COL)
    SCENE.camera=None


def assemble():
    reset('Hua_Museum')
    for name in NAMES[:6]:
        with bpy.data.libraries.load(str(OUT/(name+'.blend')),link=False) as (src,dst):
            dst.collections=src.collections
        for col in dst.collections:
            if col and not col.name.startswith('PREVIEW'):SCENE.collection.children.link(col)
    # Identical plain materials can share datablocks in the assembled source.
    for o in SCENE.objects:
        for slot in o.material_slots:
            if slot.material:
                base=slot.material.name.split('.')[0]
                if base in bpy.data.materials:slot.material=bpy.data.materials[base]
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Hua_Museum.blend'),compress=True)
    if not SKIP_RENDER:
        VIEWS['Hua_Museum']=((31,-32,34),(0,8,.5),33,(-12,12,0,16))
        # Render master as a cutaway by using the S0 preview rules.
        shellcopy=OUT/'S0_shell.preview.png'
        if not shellcopy.exists() and (OUT/'S0_shell.png').exists():
            import shutil
            shutil.copyfile(OUT/'S0_shell.png',shellcopy)
        preview('S0_shell')
        os.replace(OUT/'S0_shell.png',OUT/'Hua_Museum.png')
        # Restore the standalone shell image without re-rendering.
        shellcopy=OUT/'S0_shell.preview.png'
        if shellcopy.exists():os.replace(shellcopy,OUT/'S0_shell.png')


def main():
    functions=[shell,lobby,shop,tea,factory,exit_hall,common]
    if '--assemble-only' not in ARGS:
        for name,fn in zip(NAMES,functions):
            if ONLY and name not in ONLY.split(','):continue
            print('BUILD_START',name,flush=True)
            reset(name);fn()
            if name in ('S0_shell','S1_lobby'):
                import round3_assets
                context=sys.modules[__name__]
                if name=='S0_shell':round3_assets.add_timber_beams(context)
                else:
                    round3_assets.make_statue(context)
                    round3_assets.add_picture_lights(context)
            report=bake_and_audit(name)
            save_export(name)
            preview(name)
            if name=='S0_shell' and not SKIP_RENDER:
                import shutil
                shutil.copyfile(OUT/'S0_shell.png',OUT/'S0_shell.preview.png')
            REPORT[name]={k:report[k] for k in ('objects','triangles','items','errors')}
            print('BUILD_COMPLETE',name,report['triangles'],'triangles',flush=True)
    if not ONLY and all((OUT/(name+'.blend')).exists() for name in NAMES):assemble()
    allreports=[json.loads((OUT/(name+'.audit.json')).read_text(encoding='utf-8')) for name in NAMES if (OUT/(name+'.audit.json')).exists()]
    total=sum(r['triangles'] for r in allreports)
    summary={'blender':bpy.app.version_string,'revision':'review-1-A1-A5-B1-B3','total_triangles_including_common':total,'scene_limit':250000,
        'total_objects':sum(r['objects'] for r in allreports),'all_items':sum(len(r['items']) for r in allreports),
        'errors':[e for r in allreports for e in r['errors']],
        'packages':[{k:r[k] for k in ('file','objects','triangles','items')} for r in allreports]}
    if total>250000:raise RuntimeError('Total triangle budget exceeded')
    (OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('ALL_DONE',json.dumps({k:v for k,v in summary.items() if k!='packages'}),flush=True)


if __name__=='__main__':main()
