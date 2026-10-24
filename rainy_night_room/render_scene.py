"""Render the saved scene with Blender in background mode.

blender --background <project.blend> --python render_scene.py -- final
blender --background <project.blend> --python render_scene.py -- detail
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector
out=os.path.dirname(os.path.abspath(__file__))
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'final'
s=bpy.context.scene
pages=bpy.data.objects.get('Open book / curved pages')
if pages and pages.data.polygons[0].normal.z<0:
    bm=bmesh.new();bm.from_mesh(pages.data)
    bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(pages.data);bm.free();pages.data.update()
for ob in bpy.data.objects:
    if ob.name.startswith('Spine title / '):ob.rotation_euler=(math.pi/2,-math.pi/2,0)
lamp=bpy.data.objects['Warm desk lamp • 2700 K']
lamp.data.energy=65
lamp.rotation_euler=(Vector((0,1.84,.84))-lamp.location).to_track_quat('-Z','Y').to_euler()
p=bpy.context.preferences.addons['cycles'].preferences
p.compute_device_type='OPTIX';p.get_devices()
for d in p.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU';s.cycles.use_denoising=True
s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
s.render.image_settings.color_mode='RGB'
if mode=='detail':
    cam=s.camera.copy();cam.data=s.camera.data.copy();s.collection.objects.link(cam)
    cam.name='Camera • desk detail';cam.location=(2.9,-1.6,2.45)
    cam.rotation_euler=(Vector((-.12,2.12,1.34))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=48;cam.data.dof.aperture_fstop=5.6;s.camera=cam
    s.render.resolution_x=1800;s.render.resolution_y=1350
    s.cycles.samples=192;s.cycles.adaptive_threshold=.018
    s.render.filepath=os.path.join(out,'雨夜私室_书桌特写.png')
else:
    s.render.resolution_x=2400;s.render.resolution_y=1600
    s.cycles.samples=256;s.cycles.adaptive_threshold=.012
    s.render.filepath=os.path.join(out,'雨夜私室_最终渲染.png')
    s.render.image_settings.color_depth='8'
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'雨夜私室_Rainy_Night_Room.blend'))
bpy.ops.render.render(write_still=True)
print('RENDER COMPLETE:',s.render.filepath,flush=True)
