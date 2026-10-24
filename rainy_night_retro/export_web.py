"""把 After_Hours_Rainy_Room.blend 导出为网页可用的 web/room.glb（不改动原 .blend）。
运行（在本文件所在文件夹）：
  & 'D:\\blender\\blender.exe' --background '.\\After_Hours_Rainy_Room.blend' --python '.\\export_web.py'
做的事：
  1. 删除灯光、相机和带动画的雨丝（灯光在网页里重建，雨在网页里重新做动画）
  2. 曲线 / 文字转为网格，应用全部修改器
  3. 按集合合并网格，减少网页端的绘制次数；屏幕、台灯等可交互物体单独保留
  4. 导出 Draco 压缩的 GLB
"""
import bpy, os, json

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
os.makedirs(OUT, exist_ok=True)
# 需要在网页里单独点击 / 控制的物体，不参与合并
KEEP = {
    'CRT blue convex display': 'screen',
    'Copper lampshade': 'lampshade',
}
DROP_COLLECTIONS = ('09 •',)            # 带动画的雨丝

bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None

# 1. 删除灯光、相机、空物体和动画雨丝
hidden = []
for o in list(bpy.data.objects):
    drop = o.type in ('LIGHT', 'CAMERA', 'EMPTY', 'LIGHT_PROBE')
    # 渲染里看不到的辅助物体（例如 refine_scene.py 留下的“Lamp pivot”大球）不导出
    if o.hide_render or o.hide_viewport or o.hide_get() or o.name.startswith('Lamp pivot'):
        drop = True; hidden.append(o.name)
    if any(c.name.startswith(DROP_COLLECTIONS) for c in o.users_collection):
        drop = True
    if drop:
        bpy.data.objects.remove(o, do_unlink=True)

# 2. 曲线 / 文字转网格（转成带修改器结果的独立网格）
dg = bpy.context.evaluated_depsgraph_get()
for o in list(bpy.data.objects):
    if o.type in ('CURVE', 'FONT', 'SURFACE', 'META', 'MESH'):
        ev = o.evaluated_get(dg)
        try:
            me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        except Exception:
            continue
        if o.type == 'MESH':
            o.modifiers.clear()
            o.data = me
        else:
            new = bpy.data.objects.new(o.name, me)
            new.matrix_world = o.matrix_world.copy()
            for c in o.users_collection:
                c.objects.link(new)
            bpy.data.objects.remove(o, do_unlink=True)

# 清掉父子关系（保留世界变换），合并时不受影响
for o in bpy.data.objects:
    if o.parent:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw

# 2b. 程序化颜色（噪波 → 色带）导不进 glTF，会变成白色；改为色带的平均色写回底色
baked = 0
for m in bpy.data.materials:
    if not (m.use_nodes and m.node_tree):
        continue
    for n in m.node_tree.nodes:
        if n.bl_idname != 'ShaderNodeBsdfPrincipled':
            continue
        for key in ('Base Color', 'Roughness'):
            inp = n.inputs.get(key)
            if not inp or not inp.is_linked:
                continue
            src = inp.links[0].from_node
            if src.bl_idname == 'ShaderNodeValToRGB':
                els = src.color_ramp.elements
                avg = [sum(e.color[i] for e in els) / len(els) for i in range(4)]
                if key == 'Base Color':
                    inp.default_value = avg
                else:
                    inp.default_value = sum(avg[:3]) / 3
            elif key == 'Base Color':
                inp.default_value = (*m.diffuse_color[:3], 1)
            for l in list(inp.links):
                m.node_tree.links.remove(l)
            baked += 1

# 3. 按集合合并
stats = {}
for col in bpy.data.collections:
    meshes = [o for o in col.objects if o.type == 'MESH' and o.name not in KEEP and len(o.data.polygons)]
    if len(meshes) < 2:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    meshes[0].name = 'MERGED ' + col.name
    stats[col.name] = len(meshes)
for name, tag in KEEP.items():
    o = bpy.data.objects.get(name)
    if o:
        o.name = 'KEEP_' + tag

# 4. 导出
path = os.path.join(OUT, 'room.glb')
bpy.ops.export_scene.gltf(
    filepath=path, export_format='GLB', use_selection=False,
    export_apply=True, export_yup=True, export_lights=False, export_cameras=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
    export_animations=False, export_texcoords=True, export_normals=True,
)
info = {'skipped_hidden': hidden[:20], 'file': path, 'size_mb': round(os.path.getsize(path) / 1048576, 2), 'merged': stats,
        'objects': len([o for o in bpy.data.objects if o.type == 'MESH'])}
with open(os.path.join(OUT, 'export_info.json'), 'w', encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=1)
print('EXPORT_DONE', json.dumps(info, ensure_ascii=False))
