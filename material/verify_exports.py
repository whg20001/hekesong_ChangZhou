"""Verify Blender sources, GLB payloads, and actual Draco import round trips.
Run with Blender --background --python material/verify_exports.py.
"""
import bpy
import json
import struct
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
NAMES=['S0_shell','S1_lobby','S2_shop','S3_tea','S4_factory','S5_exit','S6_common']
REPORT={'checks':[],'feedback_checks':[],'errors':[]}


def require(test,message):
    if not test:REPORT['errors'].append(message)


def read_glb(path):
    raw=path.read_bytes()
    magic,version,length=struct.unpack_from('<4sII',raw,0)
    require(magic==b'glTF' and version==2 and length==len(raw),path.name+': invalid GLB header')
    size,kind=struct.unpack_from('<I4s',raw,12)
    require(kind==b'JSON',path.name+': missing JSON chunk')
    return json.loads(raw[20:20+size])


def world_bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return [min(v[k] for v in points) for k in range(3)],[max(v[k] for v in points) for k in range(3)]


def center(o):
    low,high=world_bounds([o])
    return Vector([(a+b)/2 for a,b in zip(low,high)])


def no_overlap_xy(a,b):
    al,ah=world_bounds(a);bl,bh=world_bounds(b)
    return any(min(ah[k],bh[k])-max(al[k],bl[k])<=.0001 for k in (0,1))


def feedback_checks(name,objects,stage):
    """Acceptance checks use physical geometry/UVs, independent of the build audit."""
    prefix=name+' '+stage+': '
    def check(code,fn):
        before=len(REPORT['errors'])
        try:fn()
        except (KeyError,ValueError) as e:require(False,prefix+code+' '+str(e))
        REPORT['feedback_checks'].append({'item':code,'stage':stage,'passed':len(REPORT['errors'])==before})
    if name=='S0_shell':
        def doors():
            require('INT_exitDoor' not in objects,prefix+'old combined exit door remains')
            for side,p,y0,y1 in [('L',(12,3,0),3,4),('R',(12,5,0),4,5)]:
                o=objects['INT_exitDoor_'+side];lo,hi=world_bounds([o])
                require((o.matrix_world.translation-Vector(p)).length<.0001,prefix+'incorrect '+side+' exit hinge')
                require(lo[1]>=y0-.001 and hi[1]<=y1+.001,prefix+'exit leaf crosses the center seam')
                require(all(abs(v)<1e-5 for v in o.rotation_euler),prefix+'exit not at zero rotation')
                largest=max(o.data.polygons,key=lambda p:p.area)
                normal=(o.matrix_world.to_3x3()@largest.normal).normalized()
                require(abs(normal.x)>.9999,prefix+'exit door is baked open')
                require(o.get('rotation_axis_blender')=='Z',prefix+'exit hinge axis incorrect')
        check('A1',doors)
        def extra_spots():
            for number,x,y in [(21,0,13.9),(22,9.5,13.6)]:
                p=center(objects[f'EMIT_spot_{number}'])
                require(abs(p.x-x)<.02 and abs(p.y-y)<.15 and p.z>3.5,prefix+'extra spotlight misplaced')
        check('B2',extra_spots)
    if name=='S1_lobby':
        def lobby():
            title=objects['SIGN_hallTitle'];p=center(title)
            require(abs(title.dimensions.x-3)<.001 and abs(title.dimensions.z-.8)<.001,prefix+'hall title size')
            require(abs(p.y-7.85)<.04 and 2.6<=p.z<=3.4,prefix+'hall title placement')
            for i in (1,2):
                manuscript=objects[f'SIGN_vitrine_{i:02d}']
                case=objects[f'COL_vitrine_{i:02d}'];p=center(case)
                require(max(abs(a-b) for a,b in zip(case.dimensions,(.6,1.2,1.1)))<.001,prefix+'vitrine size')
                require(p.x<-3 and 5<=p.y<=7.5,prefix+'vitrine placement')
                low,high=world_bounds([case])
                require(low[1]>4.25,prefix+'vitrine obstructs west doorway')
                require(no_overlap_xy([case],[objects['COL_lobby_bench']]),prefix+'bench overlaps vitrine')
                require(low[0]<center(manuscript).x<high[0] and low[1]<center(manuscript).y<high[1],prefix+'manuscript outside case')
        check('B1',lobby)
    if name=='S2_shop':
        def ledger():
            left=objects['SIGN_ledgerL'];right=objects['SIGN_ledgerR']
            require(center(left).y>center(right).y,prefix+'ledger left/right are swapped')
            require(abs(center(left).x-center(right).x)<.001,prefix+'pages are arranged along X')
            for o in (left,right):
                require(abs(o.dimensions.x-.22)<.001 and abs(o.dimensions.y-.15)<.001,prefix+'ledger page dimensions')
                low,high=world_bounds([o]);uv=o.data.uv_layers.active
                for poly in o.data.polygons:
                    for li in poly.loop_indices:
                        p=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co
                        expected=((high[1]-p.y)/(high[1]-low[1]),(p.x-low[0])/(high[0]-low[0]))
                        actual=uv.data[li].uv
                        require(max(abs(a-b) for a,b in zip(actual,expected))<.0003,prefix+'ledger UV must have U=-Y, V=+X')
            low,high=world_bounds([left,right])
            require(abs(high[0]-low[0]-.22)<.001 and abs(high[1]-low[1]-.30)<.001,prefix+'ledger spread size')
            # The handle has its own woodLight material; inkstone uses iron.
            static=objects['S2_6_static']
            for matname in ('woodLight','iron'):
                verts=[]
                for poly in static.data.polygons:
                    if static.data.materials[poly.material_index].name.split('.')[0]==matname:
                        verts += [static.matrix_world@static.data.vertices[i].co for i in poly.vertices]
                require(bool(verts),prefix+'writing tool missing '+matname)
                al=[min(p[k] for p in verts) for k in range(2)];ah=[max(p[k] for p in verts) for k in range(2)]
                for other in ([left,right],[o for o in objects.values() if o.get('item')=='S2-5']):
                    bl,bh=world_bounds(other)
                    require(any(min(ah[k],bh[k])-max(al[k],bl[k])<=.0001 for k in (0,1)),prefix+'writing tool overlaps book/abacus')
        check('A3',ledger)
        def abacus():
            names={f'ANIM_bead_{i:02d}_{j}' for i in range(1,14) for j in range(1,8)}
            actual={n for n in objects if n.startswith('ANIM_bead_')}
            require(actual==names,prefix+'expected 91 individually named beads')
            require(not any(n.startswith('ANIM_beads_') for n in objects),prefix+'old grouped beads remain')
            previous_y=-float('inf')
            for i in range(1,14):
                beads=[objects[f'ANIM_bead_{i:02d}_{j}'] for j in range(1,8)]
                xs=[o.matrix_world.translation.x for o in beads];ys=[o.matrix_world.translation.y for o in beads]
                require(max(ys)-min(ys)<.0001 and ys[0]>previous_y,prefix+'bead rod order must increase along +Y')
                previous_y=ys[0];beam=-8.75+.020
                require(beam<xs[0]<xs[1],prefix+'upper beads not on +X side in correct order')
                require(beam>xs[2]>xs[3]>xs[4]>xs[5]>xs[6],prefix+'lower bead order is incorrect')
                for o in beads:
                    o.data.calc_loop_triangles()
                    require(len(o.data.loop_triangles)<=24,prefix+'bead over 24 triangles')
                    require((o.matrix_world.translation-center(o)).length<.0001,prefix+'bead origin is not centered')
                    require(o.get('translation_axis_blender')=='X',prefix+'bead travel axis is missing')
        check('A5',abacus)
    if name=='S3_tea':
        def teapot():
            pot=objects['INT_teapot'];lid=objects['ANIM_potLid']
            require(abs(pot.dimensions.z-.16)<.001,prefix+'teapot mesh height is not .16 m')
            low,high=world_bounds([pot,lid])
            require(abs(high[2]-low[2]-.16)<.001,prefix+'teapot plus lid exceeds .16 m')
        check('B3',teapot)
    if name=='S4_factory':
        def furnace():
            o=objects['ANIM_furnaceDoor']
            require((o.matrix_world.translation-Vector((2.98,13.21,.7))).length<.0001,prefix+'furnace hinge changed')
            require(all(abs(v)<1e-5 for v in o.rotation_euler),prefix+'furnace default rotation not zero')
            largest=max(o.data.polygons,key=lambda p:p.area)
            normal=(o.matrix_world.to_3x3()@largest.normal).normalized()
            require(abs(normal.y)>.9999,prefix+'furnace closed panel is not parallel to XZ')
            back=[p for p in o.data.polygons if p.area>.1 and o.data.materials[p.material_index].name.split('.')[0]=='iron']
            require(len(back)>=2,prefix+'furnace door panel missing')
            require(max(abs((o.matrix_world@p.center).y-13.21) for p in back)<.037,prefix+'furnace door not at closed face')
        check('A2',furnace)
    if name=='S6_common':
        def rope():
            post=objects['Common_stanchion'];cord=objects['Common_rope']
            require('S6_3_static' not in objects,prefix+'rope and post still merged')
            require(abs(cord.dimensions.x-1)<.0001,prefix+'rope X length is not exactly 1 m')
            local=[v.co.x for v in cord.data.vertices]
            require(abs(min(local))<.0001 and abs(max(local)-1)<.0001,prefix+'rope must extend from hook along +X')
            require((cord.matrix_world.translation-Vector((1.05,0,.9))).length<.0001,prefix+'rope hook origin')
            low,high=world_bounds([post])
            require(abs(post.matrix_world.translation.z-low[2])<.0001,prefix+'stanchion origin not at base')
            require(abs(post.matrix_world.translation.x-(low[0]+high[0])/2)<.0001,prefix+'stanchion origin not centered')
        check('A4',rope)


for name in NAMES:
    info=json.loads((ROOT/(name+'.audit.json')).read_text(encoding='utf-8'))
    expected={o['name']:o for o in info['object_manifest']}
    gltf=read_glb(ROOT/(name+'.glb'))
    nodes={n['name']:n for n in gltf.get('nodes',[])}
    require(set(nodes)==set(expected),name+': exported node name mismatch')
    require(not gltf.get('cameras'),name+': camera found')
    require(not gltf.get('animations'),name+': animation found')
    require('KHR_lights_punctual' not in gltf.get('extensionsUsed',[]),name+': lights found')
    require(not gltf.get('images'),name+': unexpected texture image')
    require(not gltf.get('buffers',[{}])[0].get('uri'),name+': external binary buffer')
    primitives=[p for m in gltf['meshes'] for p in m['primitives']]
    require(all('KHR_draco_mesh_compression' in p.get('extensions',{}) for p in primitives),name+': uncompressed mesh')
    glbtris=sum(gltf['accessors'][p['indices']]['count']//3 for p in primitives)
    require(glbtris==info['triangles'],name+': triangle count changed in export')
    for n in gltf['nodes']:
        if 'mesh' in n:
            require('item' in n.get('extras',{}),name+': metadata missing '+n['name'])
    for m in gltf.get('materials',[]):
        require('KHR_materials_transmission' not in m.get('extensions',{}),name+': transmission material')
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/(name+'.blend')))
    require(len(bpy.context.scene.objects)==len(expected),name+': source object count mismatch')
    require(all(o.type=='MESH' for o in bpy.context.scene.objects),name+': non-mesh source object')
    require(all(not o.hide_render and not o.hide_viewport and not o.hide_get() for o in bpy.context.scene.objects),name+': hidden source object')
    require(all(not o.modifiers for o in bpy.context.scene.objects),name+': unapplied modifier')
    require(all(not o.animation_data for o in bpy.context.scene.objects),name+': animated source')
    require(all(o.data.uv_layers for o in bpy.context.scene.objects if o.name.startswith('SIGN_')),name+': sign UV missing')
    bounds={'S1_lobby':(-4,4,0,8),'S2_shop':(-12,-4,0,8),'S3_tea':(-12,-2,8,16),
            'S4_factory':(-2,12,8,16),'S5_exit':(4,12,0,8)}.get(name)
    for o in bpy.context.scene.objects:
        require(all(p.area>1e-12 for p in o.data.polygons),name+': degenerate face '+o.name)
        if o.name.startswith('COL_'):
            require(len(o.data.polygons)==6,name+': collider is not a simple box '+o.name)
        if bounds:
            x0,x1,y0,y1=bounds
            for v in o.bound_box:
                p=o.matrix_world@Vector(v)
                require(x0-.2<=p.x<=x1+.2 and y0-.2<=p.y<=y1+.2 and -.01<=p.z<=4.21,
                        name+': object outside assigned exhibit '+o.name)
    if name=='S3_tea':
        for child,parent in [('ANIM_kettleLid','INT_kettle'),('ANIM_potLid','INT_teapot'),('ANIM_caddyLid','INT_caddy')]:
            require(bpy.context.scene.objects[child].parent==bpy.context.scene.objects[parent],name+': lid parent missing '+child)
    feedback_checks(name,{o.name:o for o in bpy.context.scene.objects},'blend')
    # Actual importer decodes Draco and restores the standard glTF Y-up to Z-up.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/(name+'.glb')))
    imported={o.name:o for o in bpy.context.scene.objects}
    feedback_checks(name,imported,'glb_roundtrip')
    require(set(expected)==set(imported),name+': import node mismatch')
    max_pivot_error=0
    max_dim_error=0
    for node,e in expected.items():
        if node not in imported:continue
        o=imported[node]
        error=(o.matrix_world.translation-Vector(e['origin'])).length
        max_pivot_error=max(max_pivot_error,error)
        require(error<.0001,name+': pivot moved '+node)
        dim_error=max(abs(float(a)-float(b)) for a,b in zip(o.dimensions,e['dimensions']))
        max_dim_error=max(max_dim_error,dim_error)
        # Draco quantization can shift full-size museum meshes by a few millimeters.
        require(dim_error<.008,name+': dimensions changed '+node+' '+str(dim_error))
    REPORT['checks'].append({'package':name,'nodes':len(nodes),'triangles':glbtris,
        'glb_bytes':(ROOT/(name+'.glb')).stat().st_size,'all_meshes_draco':True,
        'max_origin_roundtrip_error_m':round(max_pivot_error,8),
        'max_dimension_roundtrip_error_m':round(max_dim_error,8)})

# Layout checks on the complete, camera/light-free source.
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Hua_Museum.blend'))
scene=bpy.context.scene
require(all(o.type=='MESH' for o in scene.objects),'Master source contains non-mesh object')
require(len(scene.objects)==sum(c['nodes'] for c in REPORT['checks'][:6]),'Master source count mismatch')
require(all(not o.hide_render and not o.hide_viewport for o in scene.objects),'Master contains hidden objects')
# Probe each intended route opening at standing and eye heights against wall boxes.
wallboxes=[o for o in scene.objects if o.name.startswith('COL_Wall')]
def blocked(point):
    p=Vector(point)
    for o in wallboxes:
        q=o.matrix_world.inverted()@p
        bounds=[v.co for v in o.data.vertices]
        if all(min(v[k] for v in bounds)-1e-5<=q[k]<=max(v[k] for v in bounds)+1e-5 for k in range(3)):
            return True
    return False
for x,y in [(0,0),(-4,3),(-8,8),(-2,12),(8,8),(12,4)]:
    for z in (.2,1.6,2.7):require(not blocked((x,y,z)),'Blocked route opening '+str((x,y,z)))
require(blocked((4,4,1.6)),'Lobby/exit dividing wall missing')
REPORT['layout_openings']=6
REPORT['total_glb_bytes']=sum(c['glb_bytes'] for c in REPORT['checks'])
REPORT['total_triangles']=sum(c['triangles'] for c in REPORT['checks'])
REPORT['passed']=not REPORT['errors']
(ROOT/'export_validation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
print('EXPORT_VALIDATION',json.dumps(REPORT,ensure_ascii=False),flush=True)
if REPORT['errors']:raise RuntimeError('Export checks failed')
