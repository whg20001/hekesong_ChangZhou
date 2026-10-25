"""Incremental round-three revision; preserves every out-of-scope object.

Blender --background --python material/revise_round3.py
Options: -- --only S1_lobby --no-bake --skip-render --skip-assemble
"""
import bpy
import json
import sys
import hashlib
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import build_models as g
import round3_assets as assets

ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
TARGETS=ARGS[ARGS.index('--only')+1].split(',') if '--only' in ARGS else ['S0_shell','S1_lobby']
BASELINE=ROOT/'round3_preservation_baseline.json'


def fingerprint(o):
    values={'name':o.name,'type':o.type,'matrix':[list(r) for r in o.matrix_world],
       'vertices':[list(v.co) for v in o.data.vertices],
       'faces':[list(p.vertices) for p in o.data.polygons],
       'smooth':[p.use_smooth for p in o.data.polygons],
       'uv':[[list(uv.uv) for uv in layer.data] for layer in o.data.uv_layers],
       'materials':[m.name for m in o.data.materials],
       'material_indices':[p.material_index for p in o.data.polygons]}
    return hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest()


def is_protected(name,o):
    if name=='S0_shell':return o.get('item')!='S0-9'
    return o.get('item') not in ('S1-1','S1-8') or o.name in ('SIGN_statue','COL_statue')


def record_baseline():
    if BASELINE.exists():return json.loads(BASELINE.read_text(encoding='utf-8'))
    result={'revision':'round3','protected_objects':{},'untouched_files':{}}
    for name in ('S0_shell','S1_lobby'):
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/(name+'.blend')))
        result['protected_objects'][name]={o.name:fingerprint(o) for o in bpy.context.scene.objects if is_protected(name,o)}
    for name in g.NAMES[2:]:
        for ext in ('.blend','.glb','.png','.audit.json'):
            path=ROOT/(name+ext)
            result['untouched_files'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    BASELINE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def bind_scene():
    g.SCENE=bpy.context.scene;g.PIVOTS={}
    aliases={'glass':'Cold glass - alpha only','collision':'Collision - invisible alpha','warm':'Warm luminous glass',
       'fire':'Orange fire emitter','glow':'Furnace emitter','cool':'Cold blue window emitter',
       'portal':'Ivory portal emitter','exit':'Green exit emitter'}
    g.M={m.name:m for m in bpy.data.materials}
    for k,v in aliases.items():
        if v in bpy.data.materials:g.M[k]=bpy.data.materials[v]
    if 'warm' not in g.M:g.M['warm']=g.material('Warm luminous glass','FFD18A',.28,0,1,3)
    if 'night' not in g.M:g.M['night']=g.material('night','1B2A4A',.65,0)


def collect_audit(name):
    objects=[];items={};components={'bust':0,'pedestal':0};errors=[]
    for o in g.SCENE.objects:
        if o.type!='MESH':errors.append('Non-mesh '+o.name);continue
        o.data.calc_loop_triangles();tri=len(o.data.loop_triangles)
        item=o['item'];items[item]=items.get(item,0)+tri
        if item=='S1-1':
            component='bust' if o.get('component')=='bust' else 'pedestal'
            components[component]+=tri
        if o.modifiers:errors.append('Unapplied modifier '+o.name)
        if o.hide_render or o.hide_viewport or o.hide_get():errors.append('Hidden '+o.name)
        if any(abs(v-1)>1e-5 for v in o.scale) or any(abs(v)>1e-5 for v in o.rotation_euler):errors.append('Transform '+o.name)
        if any(p.area<=1e-12 for p in o.data.polygons):errors.append('Degenerate face '+o.name)
        objects.append({'name':o.name,'item':item,'triangles':tri,
          'origin':[round(v,6) for v in o.matrix_world.translation],
          'dimensions':[round(v,6) for v in o.dimensions],
          'pivot_role':o.get('pivot_role','bottom center'),'rotation_axis':o.get('rotation_axis_blender',''),
          'translation_axis':o.get('translation_axis_blender',''),'stretch_axis':o.get('stretch_axis_blender',''),
          'component':o.get('component',''),'blank_surface':o.name.startswith('SIGN_'),'collision':o.name.startswith('COL_')})
    used={m for o in g.SCENE.objects for m in o.data.materials if m}
    images=set()
    for mat in used:
        if not mat.use_nodes:errors.append('Material without nodes '+mat.name);continue
        for node in mat.node_tree.nodes:
            if node.type not in ('OUTPUT_MATERIAL','BSDF_PRINCIPLED','TEX_IMAGE'):errors.append('Procedural material '+mat.name)
            if node.type=='TEX_IMAGE' and node.image:images.add(node.image)
        p=mat.node_tree.nodes.get('Principled BSDF')
        if p and p.inputs['Transmission Weight'].default_value!=0:errors.append('Transmission '+mat.name)
    if len(images)>1:errors.append('More than one image texture')
    if any(max(im.size)>1024 or not im.packed_file for im in images):errors.append('Image too large or unpacked')
    if name=='S1_lobby':
        if components['bust']>20000:errors.append('Bust exceeds 20000 triangles')
        if components['pedestal']>1500:errors.append('Pedestal exceeds 1500 triangles')
    missing=[node for node in g.REQUIRED[name] if node not in g.SCENE.objects]
    if missing:errors.append('Missing nodes '+str(missing))
    for code,tri in items.items():
        if tri>g.BUDGETS[code]:errors.append('Over budget '+code)
    report={'file':name,'revision':'round3','objects':len(objects),'triangles':sum(items.values()),
      'items':items,'budget_limits':{i:g.BUDGETS[i] for i in items},'required_nodes':len(g.REQUIRED[name]),
      'missing_nodes':missing,'errors':errors,'object_manifest':objects,
      'image_textures':[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file)} for i in images]}
    if name=='S1_lobby':report['statue_components']={'triangles':components,'limits':{'bust':20000,'pedestal':1500}}
    (ROOT/(name+'.audit.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors:raise RuntimeError(str(errors))
    return report


def verify_preservation(baseline,name):
    errors=[];expected=baseline['protected_objects'][name]
    for node,digest in expected.items():
        o=g.SCENE.objects.get(node)
        if o is None or fingerprint(o)!=digest:errors.append(node)
    if errors:raise RuntimeError('Protected objects changed: '+str(errors))
    return len(expected)


def closeup():
    g.item('PREVIEW_STATUE_ONLY');g.setup_render()
    scene=g.SCENE;scene.cycles.samples=64
    scene.render.resolution_x=1400;scene.render.resolution_y=1600
    # Render from a natural slightly off-center visitor angle, no text overlays.
    d=bpy.data.cameras.new('Statue closeup camera');o=bpy.data.objects.new('Statue closeup camera',d)
    g.COL.objects.link(o);o.location=(1.25,2.65,2.22)
    target=Vector((0,5.48,1.59));o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='ORTHO';d.ortho_scale=1.18;scene.camera=o
    hidden=[]
    for obj in list(scene.objects):
        if obj.get('item') and obj.get('item') not in ('S1-1','PREVIEW_STATUE_ONLY') or obj.name.startswith('COL_'):
            obj.hide_render=True;hidden.append(obj)
    g.light('Statue warm softbox',(-1.4,3.5,3.6),target,320,(1,.78,.56),2)
    g.light('Statue cool rim',(1.3,6.2,2.7),target,220,(.55,.72,1),1.4)
    g.light('Statue frontal fill',(.2,3.0,1.7),target,65,(1,.91,.78),1.6)
    # A matte dark background isolates the bronze; these are preview-only objects.
    g.box('Closeup backdrop',(0,6.4,1.7),(5,.05,5),'night',0)
    scene.render.filepath=str(ROOT/'S1_statue_detail.png');bpy.ops.render.render(write_still=True)
    for obj in hidden:obj.hide_render=False
    for obj in list(g.COL.objects):bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(g.COL);scene.camera=None


def summary():
    reports=[json.loads((ROOT/(n+'.audit.json')).read_text(encoding='utf-8')) for n in g.NAMES]
    data={'blender':bpy.app.version_string,'revision':'round3-A1-B1-B2',
      'total_triangles_including_common':sum(r['triangles'] for r in reports),'scene_limit':250000,
      'total_objects':sum(r['objects'] for r in reports),'all_items':sum(len(r['items']) for r in reports),
      'errors':[e for r in reports for e in r['errors']],
      'packages':[{k:r[k] for k in ('file','objects','triangles','items')} for r in reports]}
    (ROOT/'validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('ROUND3_DONE',data['total_triangles_including_common'],flush=True)


def main():
    baseline=record_baseline();checks={}
    for name in TARGETS:
        print('ROUND3_BUILD',name,flush=True)
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/(name+'.blend')));bind_scene()
        if name=='S0_shell':assets.add_timber_beams(g)
        elif name=='S1_lobby':
            assets.make_statue(g,bake='--no-bake' not in ARGS);assets.add_picture_lights(g)
        else:raise ValueError('This revision only changes S0_shell and S1_lobby')
        checks[name]=verify_preservation(baseline,name)
        collect_audit(name);g.save_export(name)
        if '--skip-render' not in ARGS:
            g.preview(name)
            if name=='S1_lobby':closeup()
    if '--skip-assemble' not in ARGS:g.assemble()
    untouched={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==digest for f,digest in baseline['untouched_files'].items()}
    result={'protected_object_counts':checks,'untouched_packages':untouched,'passed':all(untouched.values())}
    (ROOT/'round3_preservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    summary()
    if not result['passed']:raise RuntimeError('Out-of-scope package changed')


if __name__=='__main__':main()
