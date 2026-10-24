"""Render final views of the saved project, using the local NVIDIA GPU."""
import bpy, os, sys, json
OUT=os.path.dirname(os.path.abspath(__file__))
scene=bpy.context.scene
# Typography corrections on the distant signs.
hotel=bpy.data.objects.get('Neon lettering / HOTEL')
if hotel:hotel.location.z=2.16
joint=bpy.data.objects.get('Lamp pivot')
if joint:joint.hide_render=True;joint.hide_viewport=True
note=bpy.data.objects.get('Notebook loose paper')
if note:note.location.z=.920
heading=bpy.data.objects.get('Notebook handwritten heading')
if heading:heading.location.z=.923
for o in bpy.data.objects:
    if o.name.startswith('Notebook pencil line'):o.location.z=.013
for o in bpy.data.objects:
    if o.name.startswith('Neon sign border') and o.type=='CURVE':
        if o.data.splines and o.data.splines[0].points[0].co.y>18:o.location.z=-1.9
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
scene.cycles.device='GPU';scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGB'
scene.cycles.samples=256;scene.cycles.adaptive_threshold=.012
views=[('hero','CAM 01 • Rain at the window',2560,1440,'雨落之后_窗前书桌.png'),
       ('room','CAM 02 • Personal room',2400,1600,'雨落之后_房间全景.png')]
for key,cam,w,h,filename in views:
    if mode not in ['all',key]:continue
    scene.camera=bpy.data.objects[cam]
    scene.render.resolution_x=w;scene.render.resolution_y=h
    scene.render.filepath=os.path.join(OUT,filename)
    print('RENDER VIEW:',key,flush=True)
    bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['CAM 01 • Rain at the window']
scene.render.resolution_x=2560;scene.render.resolution_y=1440
scene.render.filepath=os.path.join(OUT,'雨落之后_窗前书桌.png')
scene.render.resolution_percentage=100
bpy.ops.file.pack_all()
scene.render.fps=24;scene.frame_start=1;scene.frame_end=48
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'After_Hours_Rainy_Room.blend'))
report={'blender':bpy.app.version_string,'objects':len(scene.objects),'cameras':[o.name for o in scene.objects if o.type=='CAMERA'],'external_unpacked_images':[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file],'rain_frames':[scene.frame_start,scene.frame_end],'engine':scene.render.engine,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':scene.cycles.samples}
with open(os.path.join(OUT,'scene_info.json'),'w',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print('ALL REQUESTED VIEWS SAVED',flush=True)
