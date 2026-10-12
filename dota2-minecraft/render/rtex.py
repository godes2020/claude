import bpy, sys, math, os
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:]
out,res,spp,mode=a[0],int(a[1]),int(a[2]),a[3]
expo=float(a[4]) if len(a)>4 else 0.0
ROT=float(os.environ.get('ROT','-90'))
S=bpy.context.scene
bad=('black','petals_plumblossom','leaves_white000','dota_nav_walkable','solid_white','glow_00','vapor','lightrays','cracks_glow','liquid_pour','dark_statue_fade')
import re
for o in list(bpy.data.objects):
    if o.type=='MESH':
        ms=[m.name.lower() for m in o.data.materials if m]
        if ms and all(any(b in m for b in bad) for m in ms):
            bpy.data.objects.remove(o,do_unlink=True)
    elif o.type in ('LIGHT','CAMERA'):
        bpy.data.objects.remove(o,do_unlink=True)
for m in bpy.data.materials:
    n=m.name.lower()
    if m.use_nodes and any(b in n for b in bad):
        nt=m.node_tree; mo=next(x for x in nt.nodes if x.type=='OUTPUT_MATERIAL'); t=nt.nodes.new('ShaderNodeBsdfTransparent'); nt.links.new(t.outputs[0],mo.inputs[0])
    if m.use_nodes and n.startswith(('good_base_stone','bad_base_stone','mod_')):
        p=next((x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
        if p:
            for l in list(p.inputs['Alpha'].links): m.node_tree.links.remove(l)
            p.inputs['Alpha'].default_value=1
            if os.environ.get('NONORM'):
                for l in list(p.inputs['Normal'].links): m.node_tree.links.remove(l)
nfix=0
for o in bpy.data.objects:
    if o.type=='MESH' and o.data.has_custom_normals and any(m and m.name.startswith(('mod_','good_base_stone','bad_base_stone','tile_stone')) for m in o.data.materials):
        with bpy.context.temp_override(object=o,active_object=o,selected_objects=[o]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        o.data.shade_smooth(); nfix+=1
print('NFIX',nfix)
ns=0
for o in bpy.data.objects:
    if o.type=='MESH' and ('mesh_overlay' in o.name or any(m and m.name.startswith(('mod_','path_border','wagon_path','ground_edge','good_base_stone','bad_base_stone','tile_stone','water_')) for m in o.data.materials)):
        o.visible_shadow=False; ns+=1
print('NOSHADOW',ns)
# water materials -> glossy translucent
for m in bpy.data.materials:
    n=m.name.lower()
    if n.startswith(('water_generic','water_flow','riverflow','water_edges')) and m.use_nodes:
        nt=m.node_tree
        p=next((x for x in nt.nodes if x.type=='BSDF_PRINCIPLED'),None)
        if p:
            for l in list(p.inputs['Base Color'].links): nt.links.remove(l)
            for l in list(p.inputs['Alpha'].links): nt.links.remove(l)
            p.inputs['Base Color'].default_value=(0.02,0.09,0.11,1)
            p.inputs['Roughness'].default_value=0.05
            p.inputs['Alpha'].default_value=0.88

R_G=(0.40,0.62,0.20); D_G=(0.42,0.36,0.26)
TINT=[('mod_radiant_path_destruction',(0.62,0.56,0.45)),('mod_radiant_dire',(1.0,1.0,1.0)),('mod_radiant',(0.27,0.46,0.12)),
 ('mod_dire',(0.24,0.20,0.165)),('cliff_wall',(0.62,0.58,0.50)),('ground_rock',(0.62,0.58,0.50)),('river_rocks',(0.70,0.68,0.62)),
 ('grass_clump_tintable',('POS',(0.5,0.85,0.25),(0.36,0.30,0.22))),('path_border_tint',('POS',(0.62,0.6,0.40),(0.36,0.30,0.24))),
 ('wagon_path_tintable',('POS',(0.66,0.58,0.40),(0.36,0.30,0.24))),('ground_edge001_tintable',('POS',(0.45,0.6,0.25),(0.34,0.29,0.22))),
 ('petals_pink001',(1.0,0.55,0.72)),('water_edges',(0.35,0.62,0.62)),('riverflow',(0.35,0.62,0.62)),('waterfall_mod',(0.5,0.75,0.75)),
 ('waterfall_00',(0.6,0.85,0.85)),('wood_fence001_tintable',(0.75,0.58,0.40)),('campfire_rocks',(0.8,0.78,0.72)),('statue001',(0.85,0.82,0.75)),
 ('tree_oak_leaves_blank',(0.30,0.50,0.15)),('fountain_radiant_00',(0.6,0.9,1.0))]
def tinted(m,spec):
    nt=m.node_tree; p=next((x for x in nt.nodes if x.type=='BSDF_PRINCIPLED'),None)
    if not p or not p.inputs['Base Color'].links: return
    src=p.inputs['Base Color'].links[0].from_socket
    mul=nt.nodes.new('ShaderNodeMix'); mul.data_type='RGBA'; mul.blend_type='MULTIPLY'; mul.inputs[0].default_value=1.0
    nt.links.new(src,mul.inputs[6])
    if spec[0]=='POS':
        g=nt.nodes.new('ShaderNodeNewGeometry'); sep=nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(g.outputs['Position'],sep.inputs[0])
        add=nt.nodes.new('ShaderNodeMath'); add.operation='SUBTRACT'; nt.links.new(sep.outputs[0],add.inputs[0]); nt.links.new(sep.outputs[1],add.inputs[1])
        mr=nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value=-40; mr.inputs[2].default_value=40; nt.links.new(add.outputs[0],mr.inputs[0])
        mx=nt.nodes.new('ShaderNodeMix'); mx.data_type='RGBA'; nt.links.new(mr.outputs[0],mx.inputs[0])
        mx.inputs[6].default_value=(*spec[1],1); mx.inputs[7].default_value=(*spec[2],1); nt.links.new(mx.outputs[2],mul.inputs[7])
    else: mul.inputs[7].default_value=(*spec,1)
    nt.links.new(mul.outputs[2],p.inputs['Base Color'])
for m in bpy.data.materials:
    if not m.use_nodes: continue
    n=m.name.lower()
    for k,spec in TINT:
        if n.startswith(k): tinted(m,spec); break
# bounds of terrain
mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
for o in bpy.data.objects:
    if o.type=='MESH' and len(o.data.vertices)>5000:
        for c in o.bound_box:
            w=o.matrix_world@Vector(c); mn=Vector(map(min,mn,w)); mx=Vector(map(max,mx,w))
print('BOUNDS',mn,mx)
cx,cy=(mn.x+mx.x)/2,(mn.y+mx.y)/2; size=max(mx.x-mn.x,mx.y-mn.y)
# world
W=bpy.data.worlds.new('w'); S.world=W; W.use_nodes=True
sky=W.node_tree.nodes.new('ShaderNodeTexSky'); sky.sky_type='NISHITA'; sky.sun_elevation=math.radians(40); sky.sun_rotation=math.radians(210)
bg=W.node_tree.nodes['Background']; W.node_tree.links.new(sky.outputs[0],bg.inputs[0]); bg.inputs[1].default_value=0.25
wt=W.node_tree; lp=wt.nodes.new('ShaderNodeLightPath'); bg2=wt.nodes.new('ShaderNodeBackground'); bg2.inputs[1].default_value=1.6
wt.links.new(sky.outputs[0],bg2.inputs[0]); mx=wt.nodes.new('ShaderNodeMixShader'); wt.links.new(lp.outputs['Is Camera Ray'],mx.inputs[0])
wt.links.new(bg.outputs[0],mx.inputs[1]); wt.links.new(bg2.outputs[0],mx.inputs[2]); wt.links.new(mx.outputs[0],wt.nodes['World Output'].inputs[0])
L=bpy.data.lights.new('sun','SUN'); L.energy=4.0; L.angle=math.radians(1.5); L.color=(1,0.95,0.88)
so=bpy.data.objects.new('sun',L); S.collection.objects.link(so); so.rotation_euler=(math.radians(45),0,math.radians(30))
C=bpy.data.cameras.new('cam'); co=bpy.data.objects.new('cam',C); S.collection.objects.link(co); S.camera=co
r=S.render; r.engine='CYCLES'; S.cycles.device='CPU'; S.cycles.samples=spp; S.cycles.use_denoising=False
S.cycles.max_bounces=4; S.cycles.transparent_max_bounces=16
r.film_transparent=False
S.view_settings.view_transform='AgX'; S.view_settings.look='AgX - Punchy'; S.view_settings.exposure=expo
if mode=='top':
    Z=os.environ.get('ZOOM')
    if Z: zx,zy,zs=map(float,Z.split(',')); cx,cy,size=zx,zy,zs
    C.type='ORTHO'; C.ortho_scale=size*1.01; co.location=(cx,cy,300); co.rotation_euler=(0,0,math.radians(ROT))
    r.resolution_x=r.resolution_y=res
else:
    C.lens=28; C.clip_end=5000
    co.location=(cx-size*0.62,cy+size*0.55,size*0.33)
    d=Vector((cx+size*0.05,cy+size*0.05,0))-co.location
    co.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    r.resolution_x=res; r.resolution_y=int(res*9/16)
r.resolution_percentage=100; r.filepath=out
bpy.ops.render.render(write_still=True)
print('DONE')
