import bpy, os, math
from mathutils import Vector
OUT=os.path.dirname(os.path.abspath(__file__))
s=bpy.context.scene
city=bpy.data.collections['14 • Midnight city / editable architecture']
# Compress only distant architecture to reveal sky above the busy foreground.
def remap(co):
    v=co.copy()
    if v.y>18:
        factor=.48 if v.y>30 else .65
        v.z=-4.4+(v.z+4.4)*factor
    return v
for o in city.objects:
    if o.name.startswith(('Neon sign','Neon lettering')):continue
    if o.type=='MESH':
        inv=o.matrix_world.inverted()
        for v in o.data.vertices:v.co=inv@remap(o.matrix_world@v.co)
    elif o.type=='CURVE':
        if o.location.y>18:o.location=remap(o.location)
# Lower the far sign to the altered rooftop.
for o in city.objects:
    if ('MIDNIGHT' in o.name):o.location.z-=1.9
for i,power in enumerate([1.25,1.55,1.0,.06,.85]):
    p=bpy.data.materials['Window light '+str(i)].node_tree.nodes['Principled BSDF']
    p.inputs['Emission Strength'].default_value=power
# Add a slender neon tower toward the edge, giving the skyline a distinct silhouette.
mat=bpy.data.materials['Night concrete 2']
light=bpy.data.materials['Neon cyan']
def block(name,loc,dim,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection):c.objects.unlink(o)
    city.objects.link(o);o.data.materials.append(material);return o
block('Distant signature tower',(-7.4,31,1.5),(1.1,1.1,7.4),mat)
block('Distant tower crown',(-7.4,31,5.5),(.64,.64,.6),mat)
block('Distant tower antenna',(-7.4,31,6.6),(.035,.035,1.6),light)
for x in [-7.87,-6.93]:block('Distant tower illuminated edge',(x,30.44,1.5),(.018,.018,7.4),light)
# The lamp pivot has a softer metal finish to avoid a bulb-like specular hotspot.
m=bpy.data.materials.new('Lamp pivot / brushed copper');m.use_nodes=True
p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.21,.07,.025,1);p.inputs['Metallic'].default_value=.45;p.inputs['Roughness'].default_value=.55
o=bpy.data.objects.get('Lamp pivot')
if o:o.data.materials.clear();o.data.materials.append(m)
# A more generous desk portrait; the whole room remains on CAM 02.
hero=bpy.data.objects['CAM 01 • Rain at the window']
hero.rotation_euler=(Vector((0,2.18,1.76))-hero.location).to_track_quat('-Z','Y').to_euler()
hero.data.dof.aperture_fstop=8
s.camera=hero;s.render.resolution_x=2560;s.render.resolution_y=1440;s.render.resolution_percentage=45
s.cycles.samples=64;s.cycles.adaptive_threshold=.03
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
s.cycles.device='GPU'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'After_Hours_Rainy_Room.blend'))
s.render.filepath=os.path.join(OUT,'preview_refined.png');bpy.ops.render.render(write_still=True)
s.camera=bpy.data.objects['CAM 02 • Personal room'];s.render.resolution_x=1800;s.render.resolution_y=1200;s.render.resolution_percentage=50
s.render.filepath=os.path.join(OUT,'preview_room.png');bpy.ops.render.render(write_still=True)
print('REFINEMENT PREVIEWS COMPLETE',flush=True)
