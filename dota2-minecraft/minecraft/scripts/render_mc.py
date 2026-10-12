import bpy, numpy as np, sys, math, os, time
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:]
out,res,spp,mode=a[0],int(a[1]),int(a[2]),a[3]
D='/home/user/dota_work/mc/rend/'
T=time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
d=np.load(D+'mesh.npz'); V,F,UV,M=d['V'],d['F'],d['UV'],d['M']
me=bpy.data.meshes.new('mc'); nv=len(V); nf=len(F)
me.vertices.add(nv); me.vertices.foreach_set('co',V.ravel())
me.loops.add(nf*4); me.loops.foreach_set('vertex_index',F.ravel())
me.polygons.add(nf); me.polygons.foreach_set('loop_start',np.arange(0,nf*4,4,dtype=np.int32)); me.polygons.foreach_set('loop_total',np.full(nf,4,np.int32))
me.polygons.foreach_set('material_index',M.astype(np.int32))
me.polygons.foreach_set('use_smooth',np.zeros(nf,bool))
uvl=me.uv_layers.new(name='uv'); uvl.data.foreach_set('uv',UV.ravel())
me.update(calc_edges=False); me.validate(verbose=False)
ob=bpy.data.objects.new('mc',me); bpy.context.scene.collection.objects.link(ob)
print('mesh built',time.time()-T,flush=True)
img=bpy.data.images.load(D+'atlas.png')
def mat(name,kind):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; N=nt.nodes; L=nt.links
    bs=N['Principled BSDF']; o=N['Material Output']
    tx=N.new('ShaderNodeTexImage'); tx.image=img; tx.interpolation='Closest'
    L.new(tx.outputs['Color'],bs.inputs['Base Color']); bs.inputs['Roughness'].default_value=0.85
    if 'Specular IOR Level' in bs.inputs: bs.inputs['Specular IOR Level'].default_value=0.2
    if kind in (1,4):
        L.new(tx.outputs['Alpha'],bs.inputs['Alpha'])
    if kind==2:
        bs.inputs['Roughness'].default_value=0.05; bs.inputs['Alpha'].default_value=0.75
        if 'Specular IOR Level' in bs.inputs: bs.inputs['Specular IOR Level'].default_value=0.6
    if kind==3:
        L.new(tx.outputs['Color'],bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value=3.0
    if kind==4:
        L.new(tx.outputs['Color'],bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value=2.0
    return m
for i in range(5): me.materials.append(mat('m%d'%i,i))
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=spp; sc.cycles.use_denoising=False
sc.cycles.max_bounces=4; sc.cycles.transparent_max_bounces=16
sc.render.resolution_percentage=100
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; nt=w.node_tree
sky=nt.nodes.new('ShaderNodeTexSky'); sky.sky_type='NISHITA'; sky.sun_elevation=math.radians(45); sky.sun_rotation=math.radians(210)
bg=nt.nodes['Background']; bg.inputs['Strength'].default_value=0.3
nt.links.new(sky.outputs['Color'],bg.inputs['Color'])
sun=bpy.data.lights.new('sun','SUN'); sun.energy=4.0; sun.angle=math.radians(1.0)
so=bpy.data.objects.new('sun',sun); so.rotation_euler=(math.radians(42),0,math.radians(30)); sc.collection.objects.link(so)
cd=bpy.data.cameras.new('cam'); co=bpy.data.objects.new('cam',cd); sc.collection.objects.link(co); sc.camera=co
def look(cam,target):
    d=Vector(target)-Vector(cam); co.location=cam; co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
if mode=='top':
    cd.type='ORTHO'; cd.ortho_scale=1010; co.location=(478,-502,400); co.rotation_euler=(0,0,0)
    sc.render.resolution_x=res; sc.render.resolution_y=res
else:
    vals=[float(v) for v in os.environ['CAM'].split(',')]
    look(vals[:3],vals[3:6]); cd.lens=vals[6] if len(vals)>6 else 30
    sc.render.resolution_x=res; sc.render.resolution_y=int(res*9/16)
cd.clip_end=5000
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Punchy'; sc.view_settings.exposure=float(os.environ.get('EXP','-0.6'))
sc.render.filepath=out; sc.render.image_settings.file_format='PNG'
bpy.ops.render.render(write_still=True)
print('rendered',time.time()-T)
