"""把 Rick_Portal_and_Gun.blend 里的传送枪导出成网页用的 ../rainy_night_retro/web/portal_gun.glb（不改动原 .blend）。
运行（在本文件所在文件夹）：
  & 'D:\\blender\\blender.exe' --background '.\\Rick_Portal_and_Gun.blend' --python '.\\export_gun_web.py'
传送门本身是程序化旋涡材质，导不进网页，网页里用着色器重做，这里只导出枪。
"""
import bpy, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'rainy_night_retro', 'web', 'portal_gun.glb')
GUN = next(c for c in bpy.data.collections if c.name.startswith('02 | PORTAL GUN'))

if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
objs = [o for o in GUN.all_objects if o.type in ('MESH', 'CURVE', 'FONT') and not o.hide_render]
for o in objs:
    o.hide_set(False); o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
# 曲线、文字转网格，同时应用倒角、加厚等修改器
bpy.ops.object.convert(target='MESH')
objs = [o for o in bpy.context.selected_objects]
for o in objs:   # 清掉父子关系（保留世界变换），网页里按整体移动
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw

# 玻璃：Transmission 导进网页太贵，记下来交给网页端改成半透明；发光液体保留自发光
info = {'objects': len(objs), 'materials': {}}
for o in objs:
    for s in o.material_slots:
        m = s.material
        if not m or m.name in info['materials']:
            continue
        b = next((n for n in m.node_tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None) if m.use_nodes else None
        if b:
            info['materials'][m.name] = {
                'transmission': round(b.inputs['Transmission Weight'].default_value, 2) if 'Transmission Weight' in b.inputs else None,
                'alpha': round(b.inputs['Alpha'].default_value, 2),
                'emission': round(b.inputs['Emission Strength'].default_value, 2) if 'Emission Strength' in b.inputs else None,
            }

bpy.ops.export_scene.gltf(
    filepath=OUT, export_format='GLB', use_selection=True,
    export_apply=True, export_yup=True, export_lights=False, export_cameras=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
    export_animations=False,
)
info['file'] = OUT; info['size_kb'] = round(os.path.getsize(OUT) / 1024, 1)
print('EXPORT_DONE', json.dumps(info, ensure_ascii=False))
